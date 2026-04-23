import ipaddress

from app.models.enums import IOCType
from app.normalizers.base import NormalizationResult, refang


def normalize_ip(value: str) -> NormalizationResult:
    parsed = ipaddress.ip_address(refang(value))
    ioc_type = IOCType.IPV4 if parsed.version == 4 else IOCType.IPV6
    return NormalizationResult(
        value=str(parsed),
        ioc_type=ioc_type,
        is_private_ip=parsed.is_private,
    )
