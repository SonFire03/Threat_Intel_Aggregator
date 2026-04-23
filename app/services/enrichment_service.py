from __future__ import annotations

from app.enrichers.base import IOCSnapshot
from app.enrichers.local_enricher import LocalEnricher
from app.models.enrichment import Enrichment
from app.models.ioc import IOC


class EnrichmentService:
    def __init__(self) -> None:
        self._enricher = LocalEnricher()

    def enrich_ioc(self, ioc: IOC) -> Enrichment:
        snapshot = IOCSnapshot(
            id=str(ioc.id),
            value=ioc.value,
            ioc_type=ioc.ioc_type,
            observation_count=ioc.observation_count,
            is_watchlisted=ioc.is_watchlisted,
            is_private_ip=ioc.is_private_ip,
            last_seen=ioc.last_seen,
        )
        result = self._enricher.enrich(snapshot)
        return Enrichment(ioc_id=ioc.id, enricher_name=result.enricher_name, data=result.data)
