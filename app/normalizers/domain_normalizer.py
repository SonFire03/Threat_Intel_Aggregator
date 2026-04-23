from app.models.enums import IOCType
from app.normalizers.base import NormalizationResult, refang


def normalize_domain(value: str) -> NormalizationResult:
    normalized = refang(value).lower().rstrip(".")
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return NormalizationResult(value=normalized, ioc_type=IOCType.DOMAIN)
