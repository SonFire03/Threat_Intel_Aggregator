from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.enums import IOCType


@dataclass(frozen=True)
class IOCSnapshot:
    id: str
    value: str
    ioc_type: IOCType
    observation_count: int
    is_watchlisted: bool
    is_private_ip: bool | None
    last_seen: datetime


@dataclass(frozen=True)
class EnrichmentResult:
    enricher_name: str
    data: dict[str, object]


class BaseEnricher(ABC):
    name: str

    @abstractmethod
    def enrich(self, ioc: IOCSnapshot) -> EnrichmentResult:
        raise NotImplementedError
