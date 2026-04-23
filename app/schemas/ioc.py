from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import IOCType


class IOCRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    value: str
    ioc_type: IOCType
    first_seen: datetime
    last_seen: datetime
    observation_count: int
    confidence_score: float
    severity_score: float
    priority_score: float
    is_watchlisted: bool
    is_active: bool
    is_private_ip: bool | None


class IOCListResponse(BaseModel):
    total: int
    items: list[IOCRead]
