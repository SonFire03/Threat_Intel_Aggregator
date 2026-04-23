from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ioc import IOC


class Enrichment(Base):
    __tablename__ = "enrichment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ioc_id: Mapped[UUID] = mapped_column(ForeignKey("ioc.id"), nullable=False)
    enricher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    ioc: Mapped[IOC] = relationship(back_populates="enrichments")
