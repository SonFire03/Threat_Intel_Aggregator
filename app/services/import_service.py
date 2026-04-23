from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ImportJobStatus, IOCType, SourceType
from app.models.import_job import ImportJob
from app.models.source import Source
from app.normalizers import normalize_domain, normalize_hash, normalize_ip, normalize_url
from app.normalizers.base import NormalizationResult
from app.parsers import ParseError, parse_csv, parse_json, parse_txt
from app.parsers.base import ParsedIndicator
from app.services.dedup_service import DedupService
from app.services.enrichment_service import EnrichmentService
from app.services.scoring_service import ScoringService


class ImportService:
    def __init__(self) -> None:
        self.enrichment_service = EnrichmentService()

    def import_content(
        self,
        *,
        session: Session,
        filename: str,
        content: str,
        source_name: str,
        fmt: str | None = None,
    ) -> ImportJob:
        source = self._get_or_create_source(session=session, source_name=source_name)
        now = datetime.now(UTC)
        job = ImportJob(
            filename=filename,
            source_id=source.id,
            status=ImportJobStatus.PROCESSING,
            total_lines=0,
            imported_count=0,
            duplicate_count=0,
            error_count=0,
            errors=[],
            started_at=now,
        )
        session.add(job)
        session.flush()

        detected_format = self._resolve_format(filename=filename, requested_format=fmt)

        try:
            parsed_items, candidate_lines = self._parse_with_candidates(
                content=content,
                fmt=detected_format,
            )
        except ParseError as exc:
            job.status = ImportJobStatus.FAILED
            job.error_count = 1
            job.errors = [{"line": "0", "reason": str(exc)}]
            job.completed_at = datetime.now(UTC)
            session.commit()
            return job

        parsed_lines = {item.line_number for item in parsed_items}
        missing_lines = sorted(candidate_lines - parsed_lines)

        job.total_lines = len(candidate_lines)

        for line_number in missing_lines:
            job.errors.append({"line": str(line_number), "reason": "No IOC detected"})

        for parsed in parsed_items:
            try:
                normalized = self._normalize(parsed.value, parsed.ioc_type)
            except ValueError as exc:
                job.errors.append({"line": str(parsed.line_number), "reason": str(exc)})
                continue

            ioc, created = DedupService.upsert_ioc(
                session=session,
                normalized_value=normalized.value,
                ioc_type=normalized.ioc_type,
                source_id=source.id,
                import_job_id=job.id,
                raw_value=parsed.value,
                is_private_ip=normalized.is_private_ip,
            )

            score = ScoringService.calculate(
                source_reliability=source.reliability,
                observation_count=ioc.observation_count,
                days_since_last_seen=0,
                is_watchlisted=ioc.is_watchlisted,
                tags=set(),
                has_enrichment=False,
                ioc_type=ioc.ioc_type,
            )
            ioc.confidence_score = score.confidence
            ioc.severity_score = score.severity
            ioc.priority_score = score.priority

            enrichment = self.enrichment_service.enrich_ioc(ioc)
            session.add(enrichment)

            if created:
                job.imported_count += 1
            else:
                job.duplicate_count += 1

        job.error_count = len(job.errors)
        job.status = ImportJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        session.commit()
        return job

    def _get_or_create_source(self, *, session: Session, source_name: str) -> Source:
        source = session.execute(
            select(Source).where(Source.name == source_name)
        ).scalar_one_or_none()
        if source is not None:
            return source

        source = Source(name=source_name, source_type=SourceType.FILE, reliability=0.5)
        session.add(source)
        session.flush()
        return source

    def _resolve_format(self, *, filename: str, requested_format: str | None) -> str:
        if requested_format:
            normalized = requested_format.lower().strip()
        else:
            normalized = Path(filename).suffix.lstrip(".").lower()

        if normalized in {"txt", "csv", "json"}:
            return normalized
        raise ParseError(f"Unsupported format: {normalized}")

    def _parse_with_candidates(
        self, *, content: str, fmt: str
    ) -> tuple[list[ParsedIndicator], set[int]]:
        if fmt == "txt":
            parsed = parse_txt(content)
            candidate_lines = {
                idx
                for idx, line in enumerate(content.splitlines(), start=1)
                if line.strip() and not line.strip().startswith("#")
            }
            return parsed, candidate_lines

        if fmt == "csv":
            parsed = parse_csv(content)
            candidate_lines = self._csv_candidate_lines(content)
            return parsed, candidate_lines

        if fmt == "json":
            parsed = parse_json(content)
            candidate_lines = self._json_candidate_lines(content)
            return parsed, candidate_lines

        raise ParseError(f"Unsupported format: {fmt}")

    def _csv_candidate_lines(self, content: str) -> set[int]:
        reader = csv.DictReader(StringIO(content))
        if reader.fieldnames is None:
            return set()

        normalized_columns = {field.lower(): field for field in reader.fieldnames}
        columns = [
            normalized_columns[col]
            for col in ("indicator", "value", "ioc")
            if col in normalized_columns
        ]
        if not columns:
            return set()

        lines: set[int] = set()
        for line_number, row in enumerate(reader, start=2):
            if any((row.get(column) or "").strip() for column in columns):
                lines.add(line_number)
        return lines

    def _json_candidate_lines(self, content: str) -> set[int]:
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise ParseError("JSON payload must be a list")

        lines: set[int] = set()
        for line_number, item in enumerate(payload, start=1):
            if isinstance(item, dict) and str(item.get("value", "")).strip():
                lines.add(line_number)
        return lines

    def _normalize(self, value: str, ioc_type: IOCType) -> NormalizationResult:
        if ioc_type in {IOCType.IPV4, IOCType.IPV6}:
            return normalize_ip(value)
        if ioc_type is IOCType.DOMAIN:
            return normalize_domain(value)
        if ioc_type is IOCType.URL:
            return normalize_url(value)
        if ioc_type in {IOCType.MD5, IOCType.SHA1, IOCType.SHA256}:
            return normalize_hash(value)
        raise ValueError(f"Unsupported IOC type: {ioc_type.value}")
