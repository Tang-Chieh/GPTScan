import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from json_questions import ask_json


class JSONQuestionTests(unittest.TestCase):
    def test_one_format_retry_without_inventing_values(self):
        valid = {"VariableA": {"reserve0": "reserve"}, "VariableB": {"price": "price"}}
        ask = Mock(side_effect=['{"unescaped": "x"quote"}', json.dumps(valid)])
        self.assertEqual(ask_json(ask, "Original question and source", ("VariableA", "VariableB")), valid)
        self.assertEqual(ask.call_count, 2)
        self.assertTrue(ask.call_args.args[0].startswith("Original question and source"))

    def test_two_bad_replies_fail_not_negative(self):
        ask = Mock(return_value='{"VariableA":"wrong type"}')
        with self.assertRaises(ValueError):
            ask_json(ask, "q", ("VariableA", "VariableB"))
        self.assertEqual(ask.call_count, 2)

    def test_transport_errors_not_retried_or_downgraded(self):
        ask = Mock(side_effect=RuntimeError("OAuth failed"))
        with self.assertRaises(RuntimeError):
            ask_json(ask, "q", ("VariableA",))
        self.assertEqual(ask.call_count, 1)
