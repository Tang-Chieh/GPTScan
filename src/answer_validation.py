"""Malformed answers must not silently become a negative finding."""
import json
import re


def is_yes(text):
    if not isinstance(text, str):
        raise ValueError("Expected a yes/no string")
    match = re.match(r"^(yes|no)\b", text.strip(), re.IGNORECASE)
    if not match:
        raise ValueError("Model did not answer yes/no")
    return match.group(1).lower() == "yes"


def parse_choices(text, count):
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {str(i) for i in range(1, count + 1)}:
        raise ValueError("Expected one numbered yes/no answer for each scenario")
    for value in data.values():
        is_yes(value)
    return data
