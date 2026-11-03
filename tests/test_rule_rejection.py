import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rule_validation import CandidateRejected, require_rule_condition


class RejectionTests(unittest.TestCase):
    def test_expected_rejection_is_distinct_from_runtime_failure(self):
        require_rule_condition(True, "accepted")
        with self.assertRaises(CandidateRejected):
            require_rule_condition(False, "negative rule predicate")
        self.assertFalse(issubclass(RuntimeError, CandidateRejected))

    def test_candidate_handlers_do_not_log_error_and_other_errors_still_fail(self):
        tree = ast.parse((ROOT / "src/tasks.py").read_text())
        handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
                    and isinstance(n.type, ast.Name) and n.type.id == "CandidateRejected"]
        self.assertEqual(len(handlers), 2)
        for handler in handlers:
            calls = [n for n in ast.walk(handler) if isinstance(n, ast.Call)]
            self.assertFalse(any(isinstance(c.func, ast.Attribute) and c.func.attr == "error" for c in calls))
        self.assertIn('if options.strict and tracker.count:', (ROOT / "src/tasks.py").read_text())
