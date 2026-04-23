from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ioc import IOC


class Watchlist(Base):
    __tablename__ = "watchlist"

    ioc_id: Mapped[UUID] = mapped_column(ForeignKey("ioc.id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    ioc: Mapped[IOC] = relationship(back_populates="watchlist")
