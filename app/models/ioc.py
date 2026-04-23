from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IOCType

if TYPE_CHECKING:
    from app.models.enrichment import Enrichment
    from app.models.ioc_tag import IOCTag
    from app.models.observation import Observation
    from app.models.watchlist import Watchlist


class IOC(Base):
    __tablename__ = "ioc"
    __table_args__ = (
        UniqueConstraint("value", "ioc_type", name="uq_ioc_value_type"),
        Index("ix_ioc_priority_score", "priority_score"),
        Index("ix_ioc_last_seen", "last_seen"),
        Index("ix_ioc_is_watchlisted", "is_watchlisted"),
        Index("ix_ioc_ioc_type", "ioc_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    value: Mapped[str] = mapped_column(String(4096), nullable=False)
    ioc_type: Mapped[IOCType] = mapped_column(Enum(IOCType), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_watchlisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_private_ip: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    observations: Mapped[list[Observation]] = relationship(
        back_populates="ioc", cascade="all, delete-orphan"
    )
    ioc_tags: Mapped[list[IOCTag]] = relationship(
        back_populates="ioc", cascade="all, delete-orphan"
    )
    watchlist: Mapped[Watchlist | None] = relationship(
        back_populates="ioc", uselist=False, cascade="all, delete-orphan"
    )
    enrichments: Mapped[list[Enrichment]] = relationship(
        back_populates="ioc", cascade="all, delete-orphan"
    )
