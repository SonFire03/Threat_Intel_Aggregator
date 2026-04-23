from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ioc import IOC
    from app.models.tag import Tag


class IOCTag(Base):
    __tablename__ = "ioc_tag"

    ioc_id: Mapped[UUID] = mapped_column(ForeignKey("ioc.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)
    tagged_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    ioc: Mapped[IOC] = relationship(back_populates="ioc_tags")
    tag: Mapped[Tag] = relationship(back_populates="ioc_tags")
