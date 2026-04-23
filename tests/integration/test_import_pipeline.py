from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.enrichment import Enrichment
from app.models.enums import ImportJobStatus
from app.models.ioc import IOC
from app.models.observation import Observation
from app.services.import_service import ImportService


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    return local_session()


def test_import_pipeline_processes_valid_and_invalid_lines() -> None:
    service = ImportService()
    content = """
# Ignore this
8.8.8.8
not-an-ioc
hxxps://evil[.]com/path#frag
8.8.8.8
"""

    with _session() as session:
        job = service.import_content(
            session=session,
            filename="batch.txt",
            content=content,
            source_name="test-feed",
        )

        iocs = session.execute(select(IOC)).scalars().all()
        observations = session.execute(select(Observation)).scalars().all()
        enrichments = session.execute(select(Enrichment)).scalars().all()

    assert job.status is ImportJobStatus.COMPLETED
    assert job.total_lines == 4
    assert job.imported_count == 2
    assert job.duplicate_count == 1
    assert job.error_count == 1

    assert len(iocs) == 2
    assert len(observations) == 3
    assert len(enrichments) == 3
    assert all(ioc.confidence_score > 0.0 for ioc in iocs)


def test_import_pipeline_marks_malformed_json_as_failed() -> None:
    service = ImportService()

    with _session() as session:
        job = service.import_content(
            session=session,
            filename="broken.json",
            content='{"bad": [}',
            source_name="test-feed",
            fmt="json",
        )

    assert job.status is ImportJobStatus.FAILED
    assert job.imported_count == 0
    assert job.duplicate_count == 0
    assert job.error_count == 1
