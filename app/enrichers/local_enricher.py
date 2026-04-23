from __future__ import annotations

from app.enrichers.base import BaseEnricher, EnrichmentResult, IOCSnapshot


class LocalEnricher(BaseEnricher):
    name = "local"

    def enrich(self, ioc: IOCSnapshot) -> EnrichmentResult:
        return EnrichmentResult(
            enricher_name=self.name,
            data={
                "ioc_type": ioc.ioc_type.value,
                "is_watchlisted": ioc.is_watchlisted,
                "is_private_ip": ioc.is_private_ip,
                "observation_count": ioc.observation_count,
                "last_seen": ioc.last_seen.isoformat(),
            },
        )
