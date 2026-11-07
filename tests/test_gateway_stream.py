"""Protocol recovery only: identical request, no model-answer repair or fallback."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model_transport import read_response, send, StreamResponseError


def response(text, content_type='text/event-stream'):
    stream = io.BytesIO(text.encode('utf-8'))
    stream.headers = {'Content-Type': content_type}
    return stream


def completed(text='yes'):
    return {'type': 'response.completed', 'response': {'status': 'completed', 'output': [
        {'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}]}}


def event(data):
    return response('data: ' + json.dumps(data) + '\n\n')


class StreamTests(unittest.TestCase):
    def test_multiline_sse_comments_crlf_bom(self):
        text = ('\ufeff:heartbeat\r\n\r\nevent: response.completed\r\nid: ignored\r\n'
                'data: {"type":"response.completed",\r\n'
                'data: "response":{"status":"completed", "output":[\r\n'
                'data: {"type":"message","content":[{"type":"output_text","text":"yes"}]}]}}\r\n\r\n')
        self.assertEqual(read_response(response(text)), 'yes')

    def test_terminal_event_without_final_blank_line(self):
        self.assertEqual(read_response(response('data: ' + json.dumps(completed()))), 'yes')

    def test_event_header_can_supply_type(self):
        data = completed()
        del data['type']
        self.assertEqual(read_response(response('event: response.completed\ndata: ' + json.dumps(data) + '\n\n')), 'yes')

    def test_delta_and_done_are_not_success(self):
        text = 'data: {"type":"response.output_text.delta","delta":"yes"}\n\ndata: [DONE]\n\n'
        with self.assertRaises(StreamResponseError) as error:
            read_response(response(text))
        self.assertEqual(error.exception.reason, 'missing_completed_event')
        self.assertTrue(error.exception.retryable)

    def test_incomplete_length_or_filter_not_retryable(self):
        for reason in ('max_output_tokens', 'content_filter'):
            with self.subTest(reason=reason), self.assertRaises(StreamResponseError) as error:
                read_response(event({'type': 'response.incomplete', 'response': {
                    'status': 'incomplete', 'incomplete_details': {'reason': reason}}}))
            self.assertEqual(error.exception.reason, reason)
            self.assertFalse(error.exception.retryable)

    def test_unknown_incomplete_is_not_blindly_retried(self):
        with self.assertRaises(StreamResponseError) as error:
            read_response(event({'type': 'response.incomplete'}))
        self.assertFalse(error.exception.retryable)

    def test_json_body_failure_is_classified_too(self):
        with self.assertRaises(StreamResponseError) as error:
            read_response(response(json.dumps({'status': 'failed', 'error': {'code': 'server_error'}}), 'application/json'))
        self.assertTrue(error.exception.retryable)

    def test_connection_reset_is_recoverable(self):
        class Broken:
            headers = {'Content-Type': 'text/event-stream'}
            def __iter__(self):
                raise ConnectionResetError('private low-level message')
        with self.assertRaises(StreamResponseError) as error:
            read_response(Broken())
        self.assertEqual(error.exception.reason, 'connection_interrupted')

    def test_invalid_outer_event_json_is_protocol_error(self):
        with self.assertRaises(StreamResponseError) as error:
            read_response(response('data: {invalid}\n\n'))
        self.assertEqual(error.exception.reason, 'invalid_event_json')


class SendTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.token = root / 'bearer'
        self.token.write_text('private-test-bearer')
        self.events = root / 'events.jsonl'
        self.env = {'GPTSCAN_GATEWAY_TOKEN_FILE': str(self.token), 'GPTSCAN_EVENTS': str(self.events),
                    'GPTSCAN_MODEL': 'openai-codex/gpt-5.6-luna'}
        self.messages = [{'role': 'system', 'content': 'Original price instruction'},
                         {'role': 'user', 'content': 'Original function question'}]

    def run_send(self, streams):
        with patch.dict(os.environ, self.env, clear=True), patch('model_transport.build_opener') as opener, patch('model_transport.time.sleep'):
            opener.return_value.open.side_effect = streams
            result = send(self.messages)
            return result, opener.return_value.open.call_args_list

    def test_server_failure_then_success_reuses_identical_request(self):
        failed = {'type': 'response.failed', 'response': {'error': {
            'code': 'server_error', 'message': 'private-test-bearer and private response content'}}}
        result, calls = self.run_send([event(failed), event(completed())])
        self.assertEqual(result, 'yes')
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[0].data, calls[1].args[0].data)
        payload = json.loads(calls[0].args[0].data)
        self.assertEqual(payload['instructions'], self.messages[0]['content'])
        self.assertEqual(payload['input'], self.messages[1:])
        self.assertEqual(payload['model'], self.env['GPTSCAN_MODEL'])
        log = self.events.read_text()
        self.assertNotIn('private-test-bearer', log)
        self.assertNotIn('private response content', log)
        events = [json.loads(line) for line in log.splitlines()]
        self.assertEqual(sum(e['status'] == 'transport_retry' for e in events), 1)
        self.assertFalse(any(e['status'] == 'failed' for e in events))

    def test_eof_then_success_does_not_use_partial_text(self):
        partial = response('data: {"type":"response.output_text.delta","delta":"no"}\n\n')
        result, calls = self.run_send([partial, event(completed('yes'))])
        self.assertEqual(result, 'yes')
        self.assertEqual(len(calls), 2)

    def test_repeated_server_failure_is_bounded(self):
        failed = {'type': 'response.failed', 'response': {'error': {'code': 'server_error'}}}
        with patch.dict(os.environ, self.env, clear=True), patch('model_transport.build_opener') as opener, patch('model_transport.time.sleep'):
            opener.return_value.open.side_effect = [event(failed), event(failed)]
            with self.assertRaises(RuntimeError):
                send(self.messages)
            self.assertEqual(opener.return_value.open.call_count, 2)

    def test_authentication_error_does_not_retry(self):
        with patch.dict(os.environ, self.env, clear=True), patch('model_transport.build_opener') as opener:
            opener.return_value.open.return_value = event({'type': 'error', 'code': 'authentication_error'})
            with self.assertRaises(RuntimeError):
                send(self.messages)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_incomplete_length_does_not_retry_or_change_budget(self):
        with patch.dict(os.environ, self.env, clear=True), patch('model_transport.build_opener') as opener:
            opener.return_value.open.return_value = event({'type': 'response.incomplete', 'response': {
                'incomplete_details': {'reason': 'max_output_tokens'}}})
            with self.assertRaises(RuntimeError):
                send(self.messages)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_model_answer_json_is_not_repaired_or_reasked(self):
        result, calls = self.run_send([event(completed('{bad model answer'))])
        self.assertEqual(result, '{bad model answer')
        self.assertEqual(len(calls), 1)
