"""Small, bounded model boundary. Gateway bearer tokens are NOT OpenAI keys."""
import json
import hashlib
from datetime import datetime, timezone
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


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
    if "text/event-stream" not in response.headers.get("Content-Type", ""):
        return extract_response(json.load(response))
    for raw_line in response:
        line = raw_line.decode("utf-8").strip()
        if not line.startswith("data:") or line[5:].strip() == "[DONE]":
            continue
        event = json.loads(line[5:])
        if event.get("type") == "response.completed":
            return extract_response(event["response"])
        if event.get("type") in {"error", "response.failed", "response.incomplete"}:
            raise ValueError("Model stream failed or was incomplete")
    raise ValueError("Model stream ended without response.completed")


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
    for attempt in range(2):
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
        except HTTPError as error:
            if error.code >= 500 and attempt == 0:
                time.sleep(1)
                continue
            record_event("failed", error="http", http_status=error.code)
            raise RuntimeError(f"Model HTTP {error.code}; no provider/model fallback") from None
        except (URLError, TimeoutError):
            if attempt == 0:
                time.sleep(1)
                continue
            record_event("failed", error="connection_or_timeout")
            raise RuntimeError("Model connection failed; check gateway/OAuth") from None
        except (ValueError, KeyError, TypeError):
            record_event("failed", error="invalid_response")
            raise RuntimeError("Model response format invalid or incomplete") from None
