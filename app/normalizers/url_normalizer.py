from urllib.parse import urlparse, urlunparse

from app.models.enums import IOCType
from app.normalizers.base import NormalizationResult, refang


def normalize_url(value: str) -> NormalizationResult:
    parsed = urlparse(refang(value))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL IOC: {value!r}")

    normalized = parsed._replace(netloc=parsed.netloc.lower(), fragment="")
    return NormalizationResult(value=urlunparse(normalized), ioc_type=IOCType.URL)
