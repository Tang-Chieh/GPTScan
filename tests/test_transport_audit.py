import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model_transport import extract_response, request_wall_timeout


class AuditTests(unittest.TestCase):
    def test_question_timeout_default_override_and_explicit_value(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(request_wall_timeout(), 90)
        with patch.dict(os.environ, {"GPTSCAN_WALL_TIMEOUT": "180"}):
            self.assertEqual(request_wall_timeout(), 180)
            self.assertEqual(request_wall_timeout(25), 25)

    def test_question_timeout_rejects_invalid_limits(self):
        for value in ("0", "-1", "nan", "inf", "bad"):
            with patch.dict(os.environ, {"GPTSCAN_WALL_TIMEOUT": value}):
                with self.assertRaises(ValueError):
                    request_wall_timeout()

    def test_audit_keeps_usage_not_text_or_identifier(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'events.jsonl'
            body = {'status': 'completed', 'model': 'actual-model', 'id': 'private-response-id',
                    'usage': {'input_tokens': 10, 'output_tokens': 3,
                              'input_tokens_details': {'cached_tokens': 2}, 'sensitive_extra': 'omit'},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'private answer'}]}]}
            with patch.dict(os.environ, {'GPTSCAN_EVENTS': str(log)}):
                self.assertEqual(extract_response(body), 'private answer')
            text = log.read_text()
            event = json.loads(text)
            self.assertEqual(event['server_model'], 'actual-model')
            self.assertEqual(event['usage'], {'input_tokens': 10, 'output_tokens': 3, 'cached_tokens': 2})
            self.assertNotIn('private answer', text)
            self.assertNotIn('private-response-id', text)
            self.assertNotIn('sensitive_extra', text)

    def test_missing_or_bad_optional_metadata_does_not_change_answer(self):
        for usage in (None, 'unavailable', {'input_tokens_details': 'unavailable'}):
            body = {'status': 'completed', 'usage': usage,
                    'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'yes'}]}]}
            self.assertEqual(extract_response(body), 'yes')
