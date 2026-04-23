from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.enums import IOCType
from app.normalizers import detect_ioc_type


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedIndicator:
    value: str
    ioc_type: IOCType
    line_number: int


_HASH_TOKEN_RE = re.compile(r"\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{64}\b")
_IPV4_TOKEN_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_TOKEN_RE = re.compile(r"\b(?:hxxps?|https?)://[^\s]+")
_DOMAIN_TOKEN_RE = re.compile(r"\b(?:[A-Za-z0-9-]+(?:\[\.\]|\.))+[A-Za-z]{2,}\.?\b")


def extract_iocs_from_text(line: str, line_number: int) -> list[ParsedIndicator]:
    candidates: set[str] = set()
    url_tokens = [match.group(0).strip() for match in _URL_TOKEN_RE.finditer(line)]
    candidates.update(url_tokens)

    def token_inside_url(token: str) -> bool:
        return any(token in url for url in url_tokens)

    for pattern in (_HASH_TOKEN_RE, _IPV4_TOKEN_RE, _DOMAIN_TOKEN_RE):
        for match in pattern.finditer(line):
            token = match.group(0).strip()
            if token_inside_url(token):
                continue
            candidates.add(token)

    results: list[ParsedIndicator] = []
    for value in sorted(candidates):
        try:
            ioc_type = detect_ioc_type(value)
        except ValueError:
            continue
        results.append(ParsedIndicator(value=value, ioc_type=ioc_type, line_number=line_number))
    return results
