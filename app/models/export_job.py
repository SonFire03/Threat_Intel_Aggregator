from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import ExportFormat


class ExportJob(Base):
    __tablename__ = "export_job"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    format: Mapped[ExportFormat] = mapped_column(Enum(ExportFormat), nullable=False)
    filters: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1024), nullable=False)
