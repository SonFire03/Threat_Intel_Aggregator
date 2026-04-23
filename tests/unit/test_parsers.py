from pathlib import Path

import pytest

from app.models.enums import IOCType
from app.parsers.base import ParseError
from app.parsers.csv_parser import parse_csv
from app.parsers.json_parser import parse_json
from app.parsers.txt_parser import parse_txt

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_txt_ignores_comments_blank_lines_and_whitespace() -> None:
    content = """
# comment

  192.0.2.1

example.com
"""
    parsed = parse_txt(content)

    assert len(parsed) == 2
    assert {item.ioc_type for item in parsed} == {IOCType.IPV4, IOCType.DOMAIN}


def test_csv_missing_expected_columns_raises_clear_error() -> None:
    content = "foo,bar\na,b\n"
    with pytest.raises(ParseError):
        parse_csv(content)


def test_malformed_json_raises_parse_error() -> None:
    malformed = (FIXTURES_DIR / "malformed.json").read_text(encoding="utf-8")
    with pytest.raises(ParseError):
        parse_json(malformed)


def test_empty_file_returns_no_iocs() -> None:
    assert parse_txt("") == []


def test_lines_with_mixed_iocs_are_separated_correctly() -> None:
    content = "Seen hxxps://evil[.]com/path and 8.8.8.8 and 44d88612fea8a8f36de82e1278abb02f"
    parsed = parse_txt(content)

    types = {item.ioc_type for item in parsed}
    assert IOCType.URL in types
    assert IOCType.IPV4 in types
    assert IOCType.MD5 in types
