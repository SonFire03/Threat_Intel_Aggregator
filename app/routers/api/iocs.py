from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.enums import IOCType
from app.models.ioc import IOC
from app.models.ioc_tag import IOCTag
from app.models.tag import Tag
from app.models.watchlist import Watchlist
from app.schemas.ioc import IOCListResponse, IOCRead
from app.schemas.tag import AddTagRequest, TagRead
from app.schemas.watchlist import WatchlistPatchRequest

router = APIRouter(prefix="/iocs", tags=["iocs"])


@router.get("", response_model=IOCListResponse)
def list_iocs(
    q: str | None = Query(default=None),
    ioc_type: IOCType | None = Query(default=None),
    score_min: float | None = Query(default=None, ge=0.0, le=10.0),
    watchlist: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> IOCListResponse:
    statement = select(IOC)

    if q:
        statement = statement.where(IOC.value.contains(q.strip()))
    if ioc_type is not None:
        statement = statement.where(IOC.ioc_type == ioc_type)
    if score_min is not None:
        statement = statement.where(IOC.priority_score >= score_min)
    if watchlist is not None:
        statement = statement.where(IOC.is_watchlisted == watchlist)

    total = db.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    statement = (
        statement.order_by(IOC.priority_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = list(db.execute(statement).scalars().all())
    return IOCListResponse(total=total, items=[IOCRead.model_validate(item) for item in items])


@router.get("/{ioc_id}", response_model=IOCRead)
def get_ioc(ioc_id: UUID, db: Session = Depends(get_db_session)) -> IOCRead:
    item = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="IOC not found")
    return IOCRead.model_validate(item)


def _slugify_tag_name(raw_name: str) -> str:
    normalized = "-".join(raw_name.strip().lower().split())
    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    slugified = "".join(char for char in normalized if char in allowed_chars)
    return slugified.strip("-_")


@router.patch("/{ioc_id}/watchlist", response_model=IOCRead)
def patch_watchlist(
    ioc_id: UUID,
    payload: WatchlistPatchRequest,
    db: Session = Depends(get_db_session),
) -> IOCRead:
    ioc = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    existing = db.execute(select(Watchlist).where(Watchlist.ioc_id == ioc_id)).scalar_one_or_none()
    if payload.watchlisted:
        ioc.is_watchlisted = True
        if existing is None:
            db.add(Watchlist(ioc_id=ioc_id, reason=payload.reason))
        else:
            existing.reason = payload.reason
    else:
        ioc.is_watchlisted = False
        if existing is not None:
            db.delete(existing)

    db.commit()
    db.refresh(ioc)
    return IOCRead.model_validate(ioc)


@router.post("/{ioc_id}/tags", response_model=TagRead)
def add_tag_to_ioc(
    ioc_id: UUID,
    payload: AddTagRequest,
    db: Session = Depends(get_db_session),
) -> TagRead:
    ioc = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    tag_name = _slugify_tag_name(payload.tag_name)
    if not tag_name:
        raise HTTPException(status_code=400, detail="Invalid tag name")

    tag = db.execute(select(Tag).where(Tag.name == tag_name)).scalar_one_or_none()
    if tag is None:
        tag = Tag(name=tag_name)
        db.add(tag)
        db.flush()

    relation = db.execute(
        select(IOCTag).where(IOCTag.ioc_id == ioc_id, IOCTag.tag_id == tag.id)
    ).scalar_one_or_none()
    if relation is None:
        db.add(IOCTag(ioc_id=ioc_id, tag_id=tag.id))
        db.commit()

    count = db.execute(
        select(func.count()).select_from(IOCTag).where(IOCTag.tag_id == tag.id)
    ).scalar_one()
    return TagRead(id=tag.id, name=tag.name, color=tag.color, ioc_count=count)


@router.delete("/{ioc_id}/tags/{tag_id}", status_code=204, response_class=Response)
def remove_tag_from_ioc(
    ioc_id: UUID, tag_id: int, db: Session = Depends(get_db_session)
) -> Response:
    relation = db.execute(
        select(IOCTag).where(IOCTag.ioc_id == ioc_id, IOCTag.tag_id == tag_id)
    ).scalar_one_or_none()
    if relation is None:
        raise HTTPException(status_code=404, detail="Tag relation not found")

    db.delete(relation)
    db.commit()
    return Response(status_code=204)
