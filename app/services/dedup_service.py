from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IOCType
from app.models.ioc import IOC
from app.models.observation import Observation


class DedupService:
    @staticmethod
    def upsert_ioc(
        *,
        session: Session,
        normalized_value: str,
        ioc_type: IOCType,
        source_id: int,
        import_job_id: UUID,
        raw_value: str,
        is_private_ip: bool | None = None,
    ) -> tuple[IOC, bool]:
        now = datetime.now(UTC)
        existing_ioc = session.execute(
            select(IOC).where(IOC.value == normalized_value, IOC.ioc_type == ioc_type)
        ).scalar_one_or_none()

        created = False
        if existing_ioc is None:
            ioc = IOC(
                value=normalized_value,
                ioc_type=ioc_type,
                first_seen=now,
                last_seen=now,
                observation_count=1,
                confidence_score=0.0,
                severity_score=0.0,
                priority_score=0.0,
                is_watchlisted=False,
                is_active=True,
                is_private_ip=is_private_ip,
            )
            session.add(ioc)
            session.flush()
            created = True
        else:
            ioc = existing_ioc
            ioc.last_seen = now
            ioc.observation_count += 1
            if ioc.is_private_ip is None and is_private_ip is not None:
                ioc.is_private_ip = is_private_ip

        session.add(
            Observation(
                ioc_id=ioc.id,
                source_id=source_id,
                import_job_id=import_job_id,
                raw_value=raw_value,
                observed_at=now,
            )
        )
        session.flush()
        return ioc, created
