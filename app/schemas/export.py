from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ExportFormat


class ExportCreateRequest(BaseModel):
    format: ExportFormat
    filters: dict[str, str] | None = None


class ExportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    format: ExportFormat
    filters: dict[str, str]
    row_count: int
    created_at: datetime
    filepath: str
