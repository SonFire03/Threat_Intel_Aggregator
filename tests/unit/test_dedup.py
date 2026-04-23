from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.enums import ImportJobStatus, IOCType, SourceType
from app.models.import_job import ImportJob
from app.models.ioc import IOC
from app.models.observation import Observation
from app.models.source import Source
from app.normalizers.url_normalizer import normalize_url
from app.services.dedup_service import DedupService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    with local_session() as session:
        yield session


def _create_source_and_job(db_session: Session, source_name: str) -> tuple[int, str]:
    source = Source(name=source_name, source_type=SourceType.FILE, reliability=0.8)
    db_session.add(source)
    db_session.flush()

    job = ImportJob(
        id=uuid4(),
        filename=f"{source_name}.txt",
        source_id=source.id,
        status=ImportJobStatus.COMPLETED,
        total_lines=1,
        imported_count=1,
        duplicate_count=0,
        error_count=0,
        errors=[],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(job)
    db_session.commit()
    return source.id, job.id


def test_importing_same_ioc_twice_keeps_one_ioc_and_increments_observations(
    db_session: Session,
) -> None:
    source_id, job_id = _create_source_and_job(db_session, "src-a")

    DedupService.upsert_ioc(
        session=db_session,
        normalized_value="evil.example",
        ioc_type=IOCType.DOMAIN,
        source_id=source_id,
        import_job_id=job_id,
        raw_value="evil.example",
    )
    DedupService.upsert_ioc(
        session=db_session,
        normalized_value="evil.example",
        ioc_type=IOCType.DOMAIN,
        source_id=source_id,
        import_job_id=job_id,
        raw_value="evil.example",
    )
    db_session.commit()

    ioc_rows = db_session.execute(select(IOC)).scalars().all()
    assert len(ioc_rows) == 1
    assert ioc_rows[0].observation_count == 2


def test_same_ioc_from_two_sources_creates_two_observations(db_session: Session) -> None:
    source_a_id, job_a_id = _create_source_and_job(db_session, "src-a")
    source_b_id, job_b_id = _create_source_and_job(db_session, "src-b")

    DedupService.upsert_ioc(
        session=db_session,
        normalized_value="8.8.8.8",
        ioc_type=IOCType.IPV4,
        source_id=source_a_id,
        import_job_id=job_a_id,
        raw_value="8.8.8.8",
    )
    DedupService.upsert_ioc(
        session=db_session,
        normalized_value="8.8.8.8",
        ioc_type=IOCType.IPV4,
        source_id=source_b_id,
        import_job_id=job_b_id,
        raw_value="8.8.8.8",
    )
    db_session.commit()

    ioc_rows = db_session.execute(select(IOC)).scalars().all()
    observation_rows = db_session.execute(select(Observation)).scalars().all()

    assert len(ioc_rows) == 1
    assert len(observation_rows) == 2


def test_defanged_and_normal_url_deduplicate_to_same_ioc(db_session: Session) -> None:
    source_id, job_id = _create_source_and_job(db_session, "src-a")

    defanged = normalize_url("hxxps://evil[.]com/path")
    normal = normalize_url("https://evil.com/path")

    DedupService.upsert_ioc(
        session=db_session,
        normalized_value=defanged.value,
        ioc_type=defanged.ioc_type,
        source_id=source_id,
        import_job_id=job_id,
        raw_value="hxxps://evil[.]com/path",
    )
    DedupService.upsert_ioc(
        session=db_session,
        normalized_value=normal.value,
        ioc_type=normal.ioc_type,
        source_id=source_id,
        import_job_id=job_id,
        raw_value="https://evil.com/path",
    )
    db_session.commit()

    ioc_rows = db_session.execute(select(IOC)).scalars().all()
    assert len(ioc_rows) == 1
    assert ioc_rows[0].value == "https://evil.com/path"
    assert ioc_rows[0].observation_count == 2
