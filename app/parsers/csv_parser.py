from __future__ import annotations

import csv
from io import StringIO

from app.parsers.base import ParsedIndicator, ParseError, extract_iocs_from_text

DEFAULT_COLUMNS = ("indicator", "value", "ioc")


def parse_csv(content: str, columns: tuple[str, ...] = DEFAULT_COLUMNS) -> list[ParsedIndicator]:
    reader = csv.DictReader(StringIO(content))
    if reader.fieldnames is None:
        return []

    normalized_columns = {field.lower(): field for field in reader.fieldnames}
    candidate_fields = [normalized_columns[col] for col in columns if col in normalized_columns]

    if not candidate_fields:
        raise ParseError("CSV has no IOC value column. Expected one of: indicator,value,ioc")

    parsed: list[ParsedIndicator] = []
    for line_number, row in enumerate(reader, start=2):
        for field in candidate_fields:
            raw_value = (row.get(field) or "").strip()
            if not raw_value:
                continue
            parsed.extend(extract_iocs_from_text(raw_value, line_number=line_number))
    return parsed
