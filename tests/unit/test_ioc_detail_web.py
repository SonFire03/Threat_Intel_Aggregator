from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

import app.models  # noqa: F401
from app.database import Base
from app.models.enrichment import Enrichment
from app.models.enums import ImportJobStatus, IOCType, SourceType
from app.models.import_job import ImportJob
from app.models.ioc import IOC
from app.models.ioc_tag import IOCTag
from app.models.observation import Observation
from app.models.source import Source
from app.models.tag import Tag
from app.models.watchlist import Watchlist
from app.routers.web.iocs import add_tag, ioc_detail, remove_tag, update_watchlist


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session
    )


def _request(path: str, *, hx: bool = False) -> Request:
    headers = [(b"hx-request", b"true")] if hx else []
    return Request({"type": "http", "method": "GET", "path": path, "headers": headers})


def _seed_detail_data(session: Session) -> IOC:
    now = datetime.now(UTC)
    source = Source(name="demo-feed", source_type=SourceType.FILE, reliability=0.8)
    ioc = IOC(
        id=uuid4(),
        value="evil.example",
        ioc_type=IOCType.DOMAIN,
        first_seen=now,
        last_seen=now,
        observation_count=1,
        confidence_score=72.5,
        severity_score=8.0,
        priority_score=5.8,
        is_watchlisted=True,
        is_active=True,
    )
    tag = Tag(name="phishing", color="#ff6363")

    session.add_all([source, ioc, tag])
    session.flush()

    import_job = ImportJob(
        id=uuid4(),
        filename="demo.txt",
        source_id=source.id,
        status=ImportJobStatus.COMPLETED,
        total_lines=1,
        imported_count=1,
        duplicate_count=0,
        error_count=0,
        errors=[],
        started_at=now,
        completed_at=now,
    )

    session.add_all(
        [
            import_job,
            Watchlist(ioc_id=ioc.id, reason="Observed in a phishing campaign"),
            IOCTag(ioc_id=ioc.id, tag_id=tag.id),
            Observation(
                ioc_id=ioc.id,
                source_id=source.id,
                import_job_id=import_job.id,
                raw_value="evil.example",
                observed_at=now,
            ),
            Enrichment(ioc_id=ioc.id, enricher_name="local", data={"quality": "demo"}),
        ]
    )
    session.commit()
    return ioc


def test_ioc_detail_page_renders_and_htmx_actions_work() -> None:
    session_factory = _session_factory()
    with session_factory() as session:
        ioc = _seed_detail_data(session)

        detail_response = ioc_detail(
            request=_request(f"/iocs/{ioc.id}"), ioc_id=ioc.id, db=session
        )
        assert detail_response.status_code == 200
        assert "IOC Detail" in detail_response.body.decode()
        assert "evil.example" in detail_response.body.decode()
        assert "phishing" in detail_response.body.decode()
        assert "htmx.org" in detail_response.body.decode()

        add_tag_response = add_tag(
            request=_request(f"/iocs/{ioc.id}/tags", hx=True),
            ioc_id=ioc.id,
            tag_name="malware",
            db=session,
        )
        assert add_tag_response.status_code == 200
        assert "malware" in add_tag_response.body.decode()

        remove_tag_id = session.execute(select(Tag.id).where(Tag.name == "phishing")).scalar_one()
        remove_response = remove_tag(
            request=_request(f"/iocs/{ioc.id}/tags/{remove_tag_id}", hx=True),
            ioc_id=ioc.id,
            tag_id=remove_tag_id,
            db=session,
        )
        assert remove_response.status_code == 200
        assert "phishing" not in remove_response.body.decode()

        watchlist_response = update_watchlist(
            request=_request(f"/iocs/{ioc.id}/watchlist", hx=True),
            ioc_id=ioc.id,
            watchlisted=False,
            reason="",
            db=session,
        )
        assert watchlist_response.status_code == 200
        assert "Add to watchlist" in watchlist_response.body.decode()
