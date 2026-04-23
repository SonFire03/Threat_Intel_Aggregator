from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.import_job import ImportJob
    from app.models.ioc import IOC
    from app.models.source import Source


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        Index("ix_observation_ioc_id", "ioc_id"),
        Index("ix_observation_import_job_id", "import_job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ioc_id: Mapped[UUID] = mapped_column(ForeignKey("ioc.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    import_job_id: Mapped[UUID] = mapped_column(ForeignKey("import_job.id"), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(4096), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    ioc: Mapped[IOC] = relationship(back_populates="observations")
    source: Mapped[Source] = relationship(back_populates="observations")
    import_job: Mapped[ImportJob] = relationship(back_populates="observations")
