from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.ioc_tag import IOCTag
from app.models.tag import Tag
from app.schemas.tag import TagCreateRequest, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


def _normalize_tag_name(raw_name: str) -> str:
    normalized = "-".join(raw_name.strip().lower().split())
    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    cleaned = "".join(char for char in normalized if char in allowed_chars)
    return cleaned.strip("-_")


@router.get("", response_model=list[TagRead])
def list_tags(db: Session = Depends(get_db_session)) -> list[TagRead]:
    statement = (
        select(Tag.id, Tag.name, Tag.color, func.count(IOCTag.tag_id).label("ioc_count"))
        .select_from(Tag)
        .outerjoin(IOCTag, IOCTag.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.name.asc())
    )
    rows = db.execute(statement).all()
    return [
        TagRead(id=row.id, name=row.name, color=row.color, ioc_count=row.ioc_count)
        for row in rows
    ]


@router.post("", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreateRequest, db: Session = Depends(get_db_session)) -> TagRead:
    tag_name = _normalize_tag_name(payload.name)
    if not tag_name:
        raise HTTPException(status_code=400, detail="Invalid tag name")

    existing = db.execute(select(Tag).where(Tag.name == tag_name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(name=tag_name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagRead(id=tag.id, name=tag.name, color=tag.color, ioc_count=0)


@router.delete("/{tag_id}", status_code=204, response_class=Response)
def delete_tag(tag_id: int, db: Session = Depends(get_db_session)) -> Response:
    tag = db.execute(select(Tag).where(Tag.id == tag_id)).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return Response(status_code=204)
