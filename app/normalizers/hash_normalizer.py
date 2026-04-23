from app.models.enums import IOCType
from app.normalizers.base import NormalizationResult, refang

_EMPTY_HASHES = {
    "D41D8CD98F00B204E9800998ECF8427E",
    "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709",
    "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
}


def normalize_hash(value: str) -> NormalizationResult:
    normalized = refang(value).upper()
    if len(normalized) == 32:
        ioc_type = IOCType.MD5
    elif len(normalized) == 40:
        ioc_type = IOCType.SHA1
    elif len(normalized) == 64:
        ioc_type = IOCType.SHA256
    else:
        raise ValueError(f"Invalid hash IOC length: {value!r}")

    if any(ch not in "0123456789ABCDEF" for ch in normalized):
        raise ValueError(f"Invalid hash IOC characters: {value!r}")

    return NormalizationResult(
        value=normalized,
        ioc_type=ioc_type,
        is_empty_hash=normalized in _EMPTY_HASHES,
    )
