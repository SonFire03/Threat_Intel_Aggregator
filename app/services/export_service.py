from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ExportFormat, IOCType
from app.models.export_job import ExportJob
from app.models.ioc import IOC


class ExportService:
    def __init__(self, export_dir: Path | None = None) -> None:
        if export_dir is None:
            export_dir = Path("./exports")
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def create_export(
        self,
        *,
        session: Session,
        export_format: ExportFormat,
        filters: dict[str, str] | None,
    ) -> ExportJob:
        sanitized_filters = filters or {}
        rows = self._query_iocs(session=session, filters=sanitized_filters)

        export_job = ExportJob(
            format=export_format,
            filters=sanitized_filters,
            row_count=len(rows),
            filepath="",
        )
        session.add(export_job)
        session.flush()

        output_path = self.export_dir / f"{export_job.id}.{export_format.value}"
        if export_format is ExportFormat.JSON:
            output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        elif export_format is ExportFormat.CSV:
            self._write_csv(output_path=output_path, rows=rows)
        elif export_format is ExportFormat.TXT:
            output_path.write_text("\n".join(row["value"] for row in rows), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        export_job.filepath = str(output_path)
        session.commit()
        session.refresh(export_job)
        return export_job

    def _query_iocs(self, *, session: Session, filters: dict[str, str]) -> list[dict[str, str]]:
        statement = select(IOC)

        if q := filters.get("q"):
            statement = statement.where(IOC.value.contains(q))

        if ioc_type := filters.get("ioc_type"):
            statement = statement.where(IOC.ioc_type == IOCType(ioc_type))

        if score_min := filters.get("score_min"):
            statement = statement.where(IOC.priority_score >= float(score_min))

        if watchlist := filters.get("watchlist"):
            watchlisted = watchlist.lower() in {"1", "true", "yes"}
            statement = statement.where(IOC.is_watchlisted == watchlisted)

        iocs = list(session.execute(statement.order_by(IOC.priority_score.desc())).scalars().all())
        return [
            {
                "id": str(ioc.id),
                "value": ioc.value,
                "ioc_type": ioc.ioc_type.value,
                "confidence_score": str(ioc.confidence_score),
                "severity_score": str(ioc.severity_score),
                "priority_score": str(ioc.priority_score),
                "observation_count": str(ioc.observation_count),
                "is_watchlisted": str(ioc.is_watchlisted),
                "last_seen": ioc.last_seen.isoformat(),
            }
            for ioc in iocs
        ]

    def _write_csv(self, *, output_path: Path, rows: list[dict[str, str]]) -> None:
        headers = [
            "id",
            "value",
            "ioc_type",
            "confidence_score",
            "severity_score",
            "priority_score",
            "observation_count",
            "is_watchlisted",
            "last_seen",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
