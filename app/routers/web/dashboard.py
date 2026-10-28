from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import TEMPLATES_DIR
from app.database import get_db_session
from app.models.import_job import ImportJob
from app.models.ioc import IOC

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db_session)) -> Response:
    total_iocs = db.execute(select(func.count()).select_from(IOC)).scalar_one()
    watchlisted_iocs = db.execute(
        select(func.count()).select_from(IOC).where(IOC.is_watchlisted.is_(True))
    ).scalar_one()
    average_priority = db.execute(select(func.avg(IOC.priority_score))).scalar_one()

    recent_iocs = list(
        db.execute(select(IOC).order_by(IOC.last_seen.desc()).limit(10)).scalars().all()
    )
    recent_jobs = list(
        db.execute(select(ImportJob).order_by(ImportJob.started_at.desc()).limit(5)).scalars().all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "total_iocs": total_iocs,
            "watchlisted_iocs": watchlisted_iocs,
            "average_priority": round(float(average_priority or 0.0), 2),
            "recent_iocs": recent_iocs,
            "recent_jobs": recent_jobs,
        },
    )
