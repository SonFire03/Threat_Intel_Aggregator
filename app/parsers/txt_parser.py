from app.parsers.base import ParsedIndicator, extract_iocs_from_text


def parse_txt(content: str) -> list[ParsedIndicator]:
    parsed: list[ParsedIndicator] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed.extend(extract_iocs_from_text(stripped, line_number=line_number))
    return parsed
