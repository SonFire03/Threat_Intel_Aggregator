from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ImportJobStatus


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    source_id: int
    status: ImportJobStatus
    total_lines: int
    imported_count: int
    duplicate_count: int
    error_count: int
    errors: list[dict[str, str]]
    started_at: datetime
    completed_at: datetime | None
