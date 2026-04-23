from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ImportJobStatus

if TYPE_CHECKING:
    from app.models.observation import Observation
    from app.models.source import Source


class ImportJob(Base):
    __tablename__ = "import_job"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    status: Mapped[ImportJobStatus] = mapped_column(
        Enum(ImportJobStatus), default=ImportJobStatus.PENDING, nullable=False
    )
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    source: Mapped[Source] = relationship(back_populates="import_jobs")
    observations: Mapped[list[Observation]] = relationship(back_populates="import_job")
