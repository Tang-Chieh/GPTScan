"""One bounded format retry, never JSON repair or invented finding content."""
import json
from model_transport import record_event


def ask_json(ask, prompt, required_keys=(), single=False):
    for attempt in range(2):
        request = prompt if attempt == 0 else prompt + (
            "\nYour previous reply could not be parsed in the requested format. "
            "Return only one valid JSON object, without markdown or explanations. "
            "Escape quotes inside JSON strings. Keep the original requested keys and value types."
        )
        response = ask(request)
        try:
            data = json.loads(response)
            if not isinstance(data, dict) or not data:
                raise ValueError("Expected a nonempty JSON object")
            if single:
                if len(data) != 1 or not isinstance(next(iter(data.values())), str):
                    raise ValueError("Expected one variable string")
            else:
                for key in required_keys:
                    if key not in data or not isinstance(data[key], dict):
                        raise ValueError("Expected a variable-to-description object for each key")
                    if any(not isinstance(name, str) or not isinstance(value, str) for name, value in data[key].items()):
                        raise ValueError("Invalid variable description")
            return data
        except (ValueError, TypeError):
            if attempt:
                raise ValueError("Model JSON schema invalid after one format retry") from None
            record_event("format_retry", reason="invalid_json_or_variable_schema")
    raise AssertionError("Unreachable")
