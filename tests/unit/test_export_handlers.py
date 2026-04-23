from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models.enums import ExportFormat, IOCType
from app.models.export_job import ExportJob
from app.models.ioc import IOC
from app.routers.api.exports import download_export
from app.services.export_service import ExportService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    with local_session() as session:
        yield session


def _seed_iocs(db_session: Session) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            IOC(
                id=uuid4(),
                value="evil.example",
                ioc_type=IOCType.DOMAIN,
                first_seen=now,
                last_seen=now,
                observation_count=2,
                confidence_score=50.0,
                severity_score=8.0,
                priority_score=4.0,
                is_watchlisted=True,
                is_active=True,
            ),
            IOC(
                id=uuid4(),
                value="8.8.8.8",
                ioc_type=IOCType.IPV4,
                first_seen=now,
                last_seen=now,
                observation_count=1,
                confidence_score=30.0,
                severity_score=5.0,
                priority_score=1.5,
                is_watchlisted=False,
                is_active=True,
            ),
        ]
    )
    db_session.commit()


def test_export_service_creates_json_file_with_filters(tmp_path: Path, db_session: Session) -> None:
    _seed_iocs(db_session)
    service = ExportService(export_dir=tmp_path)

    job = service.create_export(
        session=db_session,
        export_format=ExportFormat.JSON,
        filters={"watchlist": "true"},
    )

    output_path = Path(job.filepath)
    assert job.row_count == 1
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["is_watchlisted"] == "True"


def test_export_service_creates_csv_and_txt(tmp_path: Path, db_session: Session) -> None:
    _seed_iocs(db_session)
    service = ExportService(export_dir=tmp_path)

    csv_job = service.create_export(
        session=db_session,
        export_format=ExportFormat.CSV,
        filters=None,
    )
    txt_job = service.create_export(
        session=db_session,
        export_format=ExportFormat.TXT,
        filters={"q": "evil"},
    )

    csv_text = Path(csv_job.filepath).read_text(encoding="utf-8")
    txt_text = Path(txt_job.filepath).read_text(encoding="utf-8")

    assert "value" in csv_text
    assert "evil.example" in txt_text


def test_download_export_raises_404_when_job_missing(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        download_export(job_id=uuid4(), db=db_session)
    assert exc.value.status_code == 404


def test_download_export_raises_404_when_file_missing(db_session: Session) -> None:
    job = ExportJob(
        id=uuid4(),
        format=ExportFormat.JSON,
        filters={},
        row_count=0,
        filepath="/tmp/does-not-exist-export.json",
    )
    db_session.add(job)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        download_export(job_id=job.id, db=db_session)
    assert exc.value.status_code == 404


def test_download_export_returns_fileresponse(db_session: Session, tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    path.write_text("[]", encoding="utf-8")

    job = ExportJob(
        id=uuid4(),
        format=ExportFormat.JSON,
        filters={},
        row_count=0,
        filepath=str(path),
    )
    db_session.add(job)
    db_session.commit()

    response = download_export(job_id=job.id, db=db_session)

    assert isinstance(response, FileResponse)
