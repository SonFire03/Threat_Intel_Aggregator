from __future__ import annotations

import json

from app.parsers.base import ParsedIndicator, ParseError, extract_iocs_from_text


def parse_json(content: str) -> list[ParsedIndicator]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ParseError("Malformed JSON payload") from exc

    if not isinstance(payload, list):
        raise ParseError("JSON payload must be a list")

    parsed: list[ParsedIndicator] = []
    for line_number, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        raw_value = str(item.get("value", "")).strip()
        if not raw_value:
            continue
        parsed.extend(extract_iocs_from_text(raw_value, line_number=line_number))
    return parsed
