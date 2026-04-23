from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobRead
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportJobRead, status_code=201)
def create_import_job(
    file: Annotated[UploadFile, File(...)],
    source_name: Annotated[str, Form(...)],
    db: Session = Depends(get_db_session),
    fmt: Annotated[str | None, Form()] = None,
) -> ImportJob:
    content = file.file.read().decode("utf-8", errors="replace")
    service = ImportService()
    return service.import_content(
        session=db,
        filename=file.filename or "upload.txt",
        content=content,
        source_name=source_name,
        fmt=fmt,
    )


@router.get("", response_model=list[ImportJobRead])
def list_import_jobs(db: Session = Depends(get_db_session)) -> list[ImportJob]:
    return list(db.execute(select(ImportJob).order_by(ImportJob.started_at.desc())).scalars().all())


@router.get("/{job_id}", response_model=ImportJobRead)
def get_import_job(
    job_id: UUID, db: Session = Depends(get_db_session)
) -> ImportJob:
    job = db.execute(select(ImportJob).where(ImportJob.id == job_id)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job
