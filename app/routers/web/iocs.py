from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.paths import TEMPLATES_DIR
from app.database import get_db_session
from app.models.enums import IOCType
from app.models.ioc import IOC
from app.models.ioc_tag import IOCTag
from app.models.observation import Observation
from app.models.tag import Tag
from app.models.watchlist import Watchlist

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _slugify_tag_name(raw_name: str) -> str:
    normalized = "-".join(raw_name.strip().lower().split())
    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    slugified = "".join(char for char in normalized if char in allowed_chars)
    return slugified.strip("-_")


def _load_ioc(db: Session, ioc_id: UUID) -> IOC | None:
    statement = (
        select(IOC)
        .where(IOC.id == ioc_id)
        .options(
            selectinload(IOC.observations).selectinload(Observation.source),
            selectinload(IOC.observations).selectinload(Observation.import_job),
            selectinload(IOC.ioc_tags).selectinload(IOCTag.tag),
            selectinload(IOC.watchlist),
            selectinload(IOC.enrichments),
        )
    )
    return db.execute(statement).scalar_one_or_none()


def _render_ioc_detail(
    request: Request,
    ioc: IOC,
) -> Response:
    return templates.TemplateResponse(
        request,
        "iocs/detail.html",
        {"ioc": ioc},
    )


def _render_tag_panel(request: Request, ioc: IOC) -> Response:
    tags = [
        {
            "id": relation.tag.id,
            "name": relation.tag.name,
            "color": relation.tag.color,
            "ioc_count": len(relation.tag.ioc_tags),
        }
        for relation in sorted(ioc.ioc_tags, key=lambda relation: relation.tag.name)
    ]

    return templates.TemplateResponse(
        request,
        "iocs/_tag_panel.html",
        {"ioc": ioc, "tags": tags},
    )


def _render_watchlist_panel(request: Request, ioc: IOC) -> Response:
    return templates.TemplateResponse(
        request,
        "iocs/_watchlist_panel.html",
        {"ioc": ioc},
    )


@router.get("/iocs")
def ioc_list(
    request: Request,
    q: str | None = Query(default=None),
    ioc_type: IOCType | None = Query(default=None),
    watchlist: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db_session),
) -> Response:
    statement = select(IOC)

    if q:
        statement = statement.where(IOC.value.contains(q.strip()))
    if ioc_type is not None:
        statement = statement.where(IOC.ioc_type == ioc_type)
    if watchlist is not None:
        statement = statement.where(IOC.is_watchlisted == watchlist)

    total = db.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    statement = (
        statement.order_by(IOC.priority_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    iocs = list(db.execute(statement).scalars().all())

    return templates.TemplateResponse(
        request,
        "iocs/list.html",
        {
            "iocs": iocs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "q": q or "",
            "ioc_type": ioc_type.value if ioc_type else "",
            "watchlist": "true" if watchlist else "",
            "ioc_types": [t.value for t in IOCType],
        },
    )


@router.get("/iocs/{ioc_id}")
def ioc_detail(
    request: Request,
    ioc_id: UUID,
    db: Session = Depends(get_db_session),
) -> Response:
    ioc = _load_ioc(db, ioc_id)
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")
    return _render_ioc_detail(request, ioc)


@router.post("/iocs/{ioc_id}/watchlist")
def update_watchlist(
    request: Request,
    ioc_id: UUID,
    watchlisted: bool = Form(...),
    reason: str | None = Form(default=None),
    db: Session = Depends(get_db_session),
) -> Response:
    ioc = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    existing = db.execute(select(Watchlist).where(Watchlist.ioc_id == ioc_id)).scalar_one_or_none()
    if watchlisted:
        ioc.is_watchlisted = True
        if existing is None:
            db.add(Watchlist(ioc_id=ioc_id, reason=reason))
        else:
            existing.reason = reason
    else:
        ioc.is_watchlisted = False
        if existing is not None:
            db.delete(existing)

    db.commit()
    db.refresh(ioc)

    if request.headers.get("HX-Request") == "true":
        return _render_watchlist_panel(request, ioc)

    return Response(status_code=303, headers={"Location": f"/iocs/{ioc_id}"})


@router.post("/iocs/{ioc_id}/tags")
def add_tag(
    request: Request,
    ioc_id: UUID,
    tag_name: str = Form(...),
    db: Session = Depends(get_db_session),
) -> Response:
    ioc = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    slug = _slugify_tag_name(tag_name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid tag name")

    tag = db.execute(select(Tag).where(Tag.name == slug)).scalar_one_or_none()
    if tag is None:
        tag = Tag(name=slug)
        db.add(tag)
        db.flush()

    relation = db.execute(
        select(IOCTag).where(IOCTag.ioc_id == ioc_id, IOCTag.tag_id == tag.id)
    ).scalar_one_or_none()
    if relation is None:
        db.add(IOCTag(ioc_id=ioc_id, tag_id=tag.id))
        db.commit()

    db.expire(ioc, ["ioc_tags"])
    ioc = _load_ioc(db, ioc_id)
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    if request.headers.get("HX-Request") == "true":
        return _render_tag_panel(request, ioc)

    return Response(status_code=303, headers={"Location": f"/iocs/{ioc_id}"})


@router.delete("/iocs/{ioc_id}/tags/{tag_id}", response_class=Response)
def remove_tag(
    request: Request,
    ioc_id: UUID,
    tag_id: int,
    db: Session = Depends(get_db_session),
) -> Response:
    relation = db.execute(
        select(IOCTag).where(IOCTag.ioc_id == ioc_id, IOCTag.tag_id == tag_id)
    ).scalar_one_or_none()
    if relation is None:
        raise HTTPException(status_code=404, detail="Tag relation not found")

    db.delete(relation)
    db.commit()

    ioc = db.execute(select(IOC).where(IOC.id == ioc_id)).scalar_one_or_none()
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    db.expire(ioc, ["ioc_tags"])
    ioc = _load_ioc(db, ioc_id)
    if ioc is None:
        raise HTTPException(status_code=404, detail="IOC not found")

    if request.headers.get("HX-Request") == "true":
        return _render_tag_panel(request, ioc)

    return Response(status_code=204)
