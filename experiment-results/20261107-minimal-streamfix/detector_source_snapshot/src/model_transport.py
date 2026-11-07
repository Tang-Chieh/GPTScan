"""Small, bounded model boundary. Gateway bearer tokens are NOT OpenAI keys."""
import json
import hashlib
import math
from datetime import datetime, timezone
from http.client import IncompleteRead
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class StreamResponseError(ValueError):
    """Transport diagnostics only: never retain provider messages or partial text."""
    def __init__(self, event_type, reason, retryable=False):
        self.event_type = event_type
        self.reason = reason
        self.retryable = retryable
        super().__init__(f"Model stream {event_type}: {reason}")


def stream_failure(event):
    """Distinguish explicit incomplete output from a recoverable transport failure."""
    kind = event.get('type')
    response = event.get('response') if isinstance(event.get('response'), dict) else {}
    error = response.get('error') or event.get('error') or event
    error = error if isinstance(error, dict) else {}
    details = response.get('incomplete_details')
    details = details if isinstance(details, dict) else {}
    code = details.get('reason') if kind == 'response.incomplete' else error.get('code') or error.get('type')
    fatal = {'max_output_tokens', 'content_filter', 'context_length_exceeded', 'invalid_request_error',
             'invalid_api_key', 'authentication_error', 'permission_denied', 'insufficient_quota',
             'token_expired', 'unauthorized', 'rate_limit_exceeded'}
    transient = {'server_error', 'internal_server_error', 'upstream_error', 'connection_error',
                 'network_error', 'timeout', 'request_timeout', 'overloaded_error'}
    if code in fatal:
        return StreamResponseError(kind, code)
    if code in transient:
        return StreamResponseError(kind, code, True)
    # Inspect but never log free-text provider messages (which may contain secrets).
    message = error.get('message', '')
    if kind != 'response.incomplete' and isinstance(message, str) and any(
            token in message.lower() for token in ('connection reset', 'connection lost', 'disconnected',
                                                  'socket hang up', 'fetch failed', 'network error')):
        return StreamResponseError(kind, 'connection_interrupted', True)
    return StreamResponseError(kind, 'unspecified_incomplete' if kind == 'response.incomplete' else 'unspecified_failure')


def request_wall_timeout(explicit=None):
    """Bound one complete model question independently of the repository budget."""
    value = float(explicit if explicit is not None else os.environ.get("GPTSCAN_WALL_TIMEOUT", "90"))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Model question timeout must be finite and positive")
    return value


def record_event(status, **fields):
    path = os.environ.get("GPTSCAN_EVENTS")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"status": status, **fields}) + "\n")


def gateway_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path.rstrip("/") != "/v1"):
        raise ValueError("Gateway must be an HTTP loopback URL ending in /v1")
    return value.rstrip("/")


def extract_response(body):
    if not isinstance(body, dict):
        raise StreamResponseError('protocol_error', 'invalid_response_shape')
    if body.get('status') in {'failed', 'incomplete'}:
        raise stream_failure({'type': 'response.' + body['status'], 'response': body})
    if body.get("status") != "completed":
        raise ValueError("Model response did not complete")
    text = "".join(part.get("text", "") for item in body.get("output", [])
                   if item.get("type") == "message"
                   for part in item.get("content", []) if part.get("type") == "output_text")
    if not text.strip():
        raise ValueError("Model returned no output text")
    # Audit only server metadata, not prompts, responses or bearer tokens.
    usage = body.get('usage') if isinstance(body.get('usage'), dict) else {}
    counts = {k: usage[k] for k in ('input_tokens', 'output_tokens', 'total_tokens')
              if type(usage.get(k)) is int and usage[k] >= 0}
    for category, field in (('input_tokens_details', 'cached_tokens'), ('output_tokens_details', 'reasoning_tokens')):
        detail = usage.get(category) if isinstance(usage.get(category), dict) else {}
        value = detail.get(field)
        if type(value) is int and value >= 0:
            counts[field] = value
    record_event('response_metadata', server_model=body.get('model') if isinstance(body.get('model'), str) else None, usage=counts,
                 response_id_sha256=hashlib.sha256(str(body['id']).encode()).hexdigest() if body.get('id') else None,
                 observed_at=datetime.now(timezone.utc).isoformat())
    return text


def read_response(response):
    try:
        if "text/event-stream" not in response.headers.get("Content-Type", "").lower():
            return extract_response(json.load(response))
        for event in sse_events(response):
            if event.get("type") == "response.completed":
                return extract_response(event["response"])
            if event.get("type") in {"error", "response.failed", "response.incomplete"}:
                raise stream_failure(event)
    except (IncompleteRead, ConnectionError):
        raise StreamResponseError('connection', 'connection_interrupted', True) from None
    raise StreamResponseError('eof', 'missing_completed_event', True)


def sse_events(response):
    """Join data fields until a blank line; ignore comments, ids and heartbeats."""
    data = []
    event_name = None
    first = True

    def decode_event():
        raw = '\n'.join(data)
        if not raw.strip() or raw.strip() == '[DONE]':
            return None
        try:
            event = json.loads(raw)
        except (ValueError, TypeError):
            raise StreamResponseError('protocol_error', 'invalid_event_json', True) from None
        if not isinstance(event, dict):
            raise StreamResponseError('protocol_error', 'invalid_event_shape')
        if 'type' not in event and event_name:
            event['type'] = event_name
        return event

    for raw_line in response:
        try:
            line = raw_line.decode('utf-8-sig' if first else 'utf-8').rstrip('\r\n')
        except UnicodeError:
            raise StreamResponseError('protocol_error', 'invalid_event_encoding', True) from None
        first = False
        if line == '':
            if data:
                event = decode_event()
                if event is not None:
                    yield event
            data, event_name = [], None
        elif line.startswith(':'):
            continue
        else:
            field, _, value = line.partition(':')
            value = value[1:] if value.startswith(' ') else value
            if field == 'data':
                data.append(value)
            elif field == 'event':
                event_name = value
    if data:
        # Some compatible gateways omit the final blank line. A complete JSON
        # terminal event is still required; text deltas alone never succeed.
        event = decode_event()
        if event is not None:
            yield event


def send(messages):
    provider = os.environ.get("GPTSCAN_PROVIDER", "codex-gateway")
    model = os.environ.get("GPTSCAN_MODEL", "openai-codex/gpt-5.6-luna")
    timeout = float(os.environ.get("GPTSCAN_REQUEST_TIMEOUT", "75"))
    if provider == "codex-gateway":
        base = gateway_url(os.environ.get("GPTSCAN_BASE_URL", "http://127.0.0.1:4000/v1"))
        token_path = os.environ.get("GPTSCAN_GATEWAY_TOKEN_FILE")
        if not token_path:
            raise ValueError("Set GPTSCAN_GATEWAY_TOKEN_FILE; OAuth stays in your gateway")
        token = Path(token_path).read_text().strip()
        if not token:
            raise ValueError("Empty gateway token file")
        payload = {"model": model, "instructions": messages[0]["content"],
                   "input": messages[1:], "stream": True, "store": False}
        url = base + "/responses"
        opener = build_opener(ProxyHandler({}), NoRedirect())
    elif provider == "api":
        token = os.environ.get("OPENAI_API_KEY", "")
        if not token:
            raise ValueError("API mode requires OPENAI_API_KEY")
        url = "https://api.openai.com/v1/chat/completions"
        payload = {"model": model, "messages": messages, "temperature": 0}
        opener = build_opener(NoRedirect())
    else:
        raise ValueError("Unknown provider")
    request = Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    # Keep upstream-style transport retries inside the caller's wall timeout.
    # Never re-ask semantic questions to repair a model answer.
    stream_retries = 0
    while True:
        started = time.monotonic()
        try:
            with opener.open(request, timeout=timeout) as response:
                result = (read_response(response) if provider == "codex-gateway"
                          else json.load(response)["choices"][0]["message"]["content"])
            if not isinstance(result, str) or not result.strip():
                raise ValueError("Empty model response")
            record_event("completed", model=model, provider=provider,
                         observed_at=datetime.now(timezone.utc).isoformat(),
                         elapsed_seconds=round(time.monotonic() - started, 3))
            return result
        except StreamResponseError as error:
            fields = {'error': 'stream_response', 'event_type': error.event_type,
                      'reason': error.reason, 'attempt': stream_retries + 1}
            if error.retryable and stream_retries < 1:
                record_event('transport_retry', **fields)
                stream_retries += 1
                time.sleep(1)
                continue
            record_event('failed', **fields)
            raise RuntimeError(str(error)) from None
        except HTTPError as error:
            if error.code >= 500 or error.code == 429:
                record_event('transport_retry', error='http', http_status=error.code)
                time.sleep(30 if error.code == 429 else 1)
                continue
            record_event("failed", error="http", http_status=error.code)
            raise RuntimeError(f"Model HTTP {error.code}; no provider/model fallback") from None
        except (URLError, TimeoutError):
            record_event('transport_retry', error='connection_or_timeout')
            time.sleep(1)
            continue
        except (ValueError, KeyError, TypeError) as exc:
            safe_reasons = {'Model response did not complete', 'Model returned no output text',
                            'Model stream failed or was incomplete',
                            'Model stream ended without response.completed', 'Empty model response'}
            reason = str(exc) if str(exc) in safe_reasons else type(exc).__name__
            record_event("failed", error="invalid_response", reason=reason)
            raise RuntimeError("Model response format invalid or incomplete") from None
