from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.export_job import ExportJob
from app.schemas.export import ExportCreateRequest, ExportJobRead
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("", response_model=ExportJobRead, status_code=201)
def create_export(payload: ExportCreateRequest, db: Session = Depends(get_db_session)) -> ExportJob:
    service = ExportService()
    return service.create_export(
        session=db,
        export_format=payload.format,
        filters=payload.filters,
    )


@router.get("/{job_id}/download")
def download_export(job_id: UUID, db: Session = Depends(get_db_session)) -> FileResponse:
    export_job = db.execute(select(ExportJob).where(ExportJob.id == job_id)).scalar_one_or_none()
    if export_job is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    path = Path(export_job.filepath)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")

    media_type = {
        "csv": "text/csv",
        "json": "application/json",
        "txt": "text/plain",
    }.get(export_job.format.value, "application/octet-stream")

    return FileResponse(path=path, media_type=media_type, filename=path.name)
