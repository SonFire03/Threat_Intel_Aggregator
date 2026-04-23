from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.enums import IOCType
from app.models.ioc import IOC
from app.models.ioc_tag import IOCTag
from app.models.tag import Tag
from app.models.watchlist import Watchlist
from app.routers.api.iocs import (
    add_tag_to_ioc,
    get_ioc,
    list_iocs,
    patch_watchlist,
    remove_tag_from_ioc,
)
from app.routers.api.stats import get_stats
from app.routers.api.tags import create_tag, delete_tag, list_tags
from app.schemas.tag import AddTagRequest, TagCreateRequest
from app.schemas.watchlist import WatchlistPatchRequest


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    with local_session() as session:
        yield session


def _seed_iocs(db_session: Session) -> list[IOC]:
    now = datetime.now(UTC)
    first = IOC(
        id=uuid4(),
        value="evil.example",
        ioc_type=IOCType.DOMAIN,
        first_seen=now,
        last_seen=now,
        observation_count=2,
        confidence_score=50.0,
        severity_score=8.0,
        priority_score=4.0,
        is_watchlisted=True,
        is_active=True,
    )
    second = IOC(
        id=uuid4(),
        value="8.8.8.8",
        ioc_type=IOCType.IPV4,
        first_seen=now,
        last_seen=now,
        observation_count=1,
        confidence_score=30.0,
        severity_score=5.0,
        priority_score=1.5,
        is_watchlisted=False,
        is_active=True,
    )
    db_session.add_all([first, second])
    db_session.commit()
    return [first, second]


def test_list_iocs_filters_and_pagination(db_session: Session) -> None:
    _seed_iocs(db_session)

    response = list_iocs(
        q="evil",
        ioc_type=None,
        score_min=None,
        watchlist=None,
        page=1,
        page_size=10,
        db=db_session,
    )

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].value == "evil.example"


def test_get_ioc_returns_404_for_unknown_id(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        get_ioc(ioc_id=uuid4(), db=db_session)
    assert exc.value.status_code == 404


def test_stats_returns_aggregate_values(db_session: Session) -> None:
    _seed_iocs(db_session)

    response = get_stats(db=db_session)

    assert response.total_iocs == 2
    assert response.watchlisted_iocs == 1
    assert response.average_priority_score > 0.0


def test_patch_watchlist_toggles_row_and_flag(db_session: Session) -> None:
    ioc = _seed_iocs(db_session)[1]

    turned_on = patch_watchlist(
        ioc_id=ioc.id,
        payload=WatchlistPatchRequest(watchlisted=True, reason="investigate"),
        db=db_session,
    )
    assert turned_on.is_watchlisted is True
    assert (
        db_session.query(Watchlist).filter(Watchlist.ioc_id == ioc.id).one_or_none()
        is not None
    )

    turned_off = patch_watchlist(
        ioc_id=ioc.id,
        payload=WatchlistPatchRequest(watchlisted=False, reason=None),
        db=db_session,
    )
    assert turned_off.is_watchlisted is False
    assert (
        db_session.query(Watchlist).filter(Watchlist.ioc_id == ioc.id).one_or_none()
        is None
    )


def test_add_and_remove_tag_from_ioc(db_session: Session) -> None:
    ioc = _seed_iocs(db_session)[0]

    tag = add_tag_to_ioc(
        ioc_id=ioc.id, payload=AddTagRequest(tag_name="Phishing"), db=db_session
    )
    assert tag.name == "phishing"
    assert (
        db_session.query(IOCTag)
        .filter(IOCTag.ioc_id == ioc.id, IOCTag.tag_id == tag.id)
        .count()
        == 1
    )

    remove_tag_from_ioc(ioc_id=ioc.id, tag_id=tag.id, db=db_session)
    assert (
        db_session.query(IOCTag)
        .filter(IOCTag.ioc_id == ioc.id, IOCTag.tag_id == tag.id)
        .count()
        == 0
    )


def test_tags_crud_handlers(db_session: Session) -> None:
    created = create_tag(payload=TagCreateRequest(name="Malware", color="#ff0000"), db=db_session)
    assert created.name == "malware"

    listed = list_tags(db=db_session)
    assert any(item.name == "malware" for item in listed)

    delete_tag(tag_id=created.id, db=db_session)
    assert db_session.query(Tag).filter(Tag.id == created.id).one_or_none() is None
