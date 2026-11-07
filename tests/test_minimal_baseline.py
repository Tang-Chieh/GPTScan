"""Regression checks: retain upstream analysis, keep adapters outside decisions."""
import ast
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


class MinimalBaselineTests(unittest.TestCase):
    def test_static_question_functions_match_upstream_ast(self):
        expected = {
            'ask_for_static_multistep': '8920607c65b55d979537851ae6524bb003b1cbfae6b3f8d9468264e1ead23368',
            'ask_for_static_json': 'a7f8bc9c90fe5fe5e58bddc900fac2a9e8df79041e37e24727e515c904a95318',
            'ask_for_static_json_single': 'fb3af20be26fc4c8591eaa1eca812a55bf8fdb2fff6163123498f6bac1cdbba4',
        }
        functions = {n.name: n for n in ast.parse((ROOT / 'src/analyze_pipeline.py').read_text()).body
                     if isinstance(n, ast.FunctionDef)}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(ast.dump(functions[name], include_attributes=False).encode()).hexdigest(), digest)

    def test_no_global_failure_gate_or_strict_answer_modules(self):
        text = (ROOT / 'src/analyze_pipeline.py').read_text()
        self.assertNotIn('Earlier model/analysis failure', text)
        self.assertNotIn('GPTSCAN_EVENTS', text)
        self.assertNotIn('parse_choices(', text)
        self.assertNotIn('is_yes(', text)
        self.assertIn('function_data["data"][int_key-1]', text)

    def test_base_system_prompt_is_upstream_text(self):
        from chatgpt_api import BASE_SYSTEM_MESSAGE
        expected = 'You are a smart contract auditor. You will be asked questions related to code properties. You can mimic answering them in the background five times and provide me with the most frequently appearing answer. Furthermore, please strictly adhere to the output format specified in the question; there is no need to explain your answer.'
        self.assertEqual(BASE_SYSTEM_MESSAGE, expected)

    def test_error_logs_are_diagnostics_not_output_veto(self):
        tree = ast.parse((ROOT / 'src/tasks.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and any(isinstance(t, ast.Attribute) and t.attr == 'count'
                    and isinstance(t.value, ast.Name) and t.value.id == 'tracker' for t in ast.walk(node.test)):
                self.fail('Do not veto Judge output based on ERROR log count')

    def test_first_deposit_checker_not_optimized(self):
        tree = ast.parse((ROOT / 'src/falcon_adapter.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'first_deposit_check')
        text = ast.unparse(fn)
        self.assertIn("text.index('(')", text)
        self.assertIn('logger.error(traceback.format_exc())', text)
