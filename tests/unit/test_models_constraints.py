from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.enums import IOCType, SourceType
from app.models.ioc import IOC
from app.models.ioc_tag import IOCTag
from app.models.tag import Tag
from app.models.watchlist import Watchlist


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    with local_session() as session:
        yield session


def _make_ioc() -> IOC:
    now = datetime.now(UTC)
    return IOC(
        id=uuid4(),
        value="evil.example",
        ioc_type=IOCType.DOMAIN,
        first_seen=now,
        last_seen=now,
        observation_count=1,
        confidence_score=10.0,
        severity_score=5.0,
        priority_score=0.5,
        is_watchlisted=False,
        is_active=True,
    )


def test_unique_ioc_value_type_is_enforced(db_session: Session) -> None:
    first = _make_ioc()
    duplicate = IOC(
        id=uuid4(),
        value="evil.example",
        ioc_type=IOCType.DOMAIN,
        first_seen=first.first_seen,
        last_seen=first.last_seen,
        observation_count=1,
        confidence_score=10.0,
        severity_score=5.0,
        priority_score=0.5,
        is_watchlisted=False,
        is_active=True,
    )

    db_session.add(first)
    db_session.commit()

    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ioc_tag_composite_primary_key_is_enforced(db_session: Session) -> None:
    ioc = _make_ioc()
    tag = Tag(name="malware")
    db_session.add_all([ioc, tag])
    db_session.commit()

    db_session.add(IOCTag(ioc_id=ioc.id, tag_id=tag.id))
    db_session.commit()

    db_session.add(IOCTag(ioc_id=ioc.id, tag_id=tag.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_watchlist_is_one_to_one_per_ioc(db_session: Session) -> None:
    ioc = _make_ioc()
    db_session.add(ioc)
    db_session.commit()

    db_session.add(Watchlist(ioc_id=ioc.id, reason="first"))
    db_session.commit()

    db_session.add(Watchlist(ioc_id=ioc.id, reason="second"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_source_name_is_unique(db_session: Session) -> None:
    from app.models.source import Source

    db_session.add(Source(name="feed-A", source_type=SourceType.FILE, reliability=0.8))
    db_session.commit()

    db_session.add(Source(name="feed-A", source_type=SourceType.FILE, reliability=0.5))
    with pytest.raises(IntegrityError):
        db_session.commit()
