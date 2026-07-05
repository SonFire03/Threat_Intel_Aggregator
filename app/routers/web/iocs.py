from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import TEMPLATES_DIR
from app.database import get_db_session
from app.models.enums import IOCType
from app.models.ioc import IOC

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


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
