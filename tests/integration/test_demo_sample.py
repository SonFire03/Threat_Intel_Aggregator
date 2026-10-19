from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.ioc import IOC
from app.services.import_service import ImportService


def test_demo_csv_sample_is_importable() -> None:
    sample_path = Path(__file__).resolve().parents[2] / "samples" / "demo_iocs.csv"
    content = sample_path.read_text(encoding="utf-8")

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )

    with local_session() as session:
        job = ImportService().import_content(
            session=session,
            filename=sample_path.name,
            content=content,
            source_name="demo-feed",
        )
        values = session.execute(select(IOC.value)).scalars().all()
        assert job.imported_count >= 3
        assert "evil.example" in values
