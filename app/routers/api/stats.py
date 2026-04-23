from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.ioc import IOC
from app.schemas.stats import IOCStatsResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=IOCStatsResponse)
def get_stats(db: Session = Depends(get_db_session)) -> IOCStatsResponse:
    total_iocs = db.execute(select(func.count()).select_from(IOC)).scalar_one()
    watchlisted_iocs = db.execute(
        select(func.count()).select_from(IOC).where(IOC.is_watchlisted.is_(True))
    ).scalar_one()
    avg_score = db.execute(select(func.avg(IOC.priority_score))).scalar_one()

    return IOCStatsResponse(
        total_iocs=total_iocs,
        watchlisted_iocs=watchlisted_iocs,
        average_priority_score=round(float(avg_score or 0.0), 4),
    )
