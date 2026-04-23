from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.models.enums import IOCType

_HASH_RE = re.compile(r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}\.?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormalizationResult:
    value: str
    ioc_type: IOCType
    is_private_ip: bool | None = None
    is_empty_hash: bool = False


def refang(value: str) -> str:
    return value.strip().replace("[.]", ".").replace("hxxp://", "http://").replace("hxxps://", "https://")


def detect_ioc_type(value: str) -> IOCType:
    cleaned = refang(value)

    try:
        ip = ipaddress.ip_address(cleaned)
        return IOCType.IPV4 if ip.version == 4 else IOCType.IPV6
    except ValueError:
        pass

    if _HASH_RE.fullmatch(cleaned):
        length_to_type = {32: IOCType.MD5, 40: IOCType.SHA1, 64: IOCType.SHA256}
        return length_to_type[len(cleaned)]

    parsed = urlparse(cleaned)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return IOCType.URL

    if len(cleaned) <= 253 and _DOMAIN_RE.fullmatch(cleaned):
        return IOCType.DOMAIN

    raise ValueError(f"Unsupported IOC format: {value!r}")
