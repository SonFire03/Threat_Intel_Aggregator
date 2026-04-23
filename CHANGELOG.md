# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-04-23

### Added

- FastAPI application with documented REST endpoints under `/api/v1`.
- IOC import pipeline (TXT/CSV/JSON) with parsing, normalization, deduplication, and scoring.
- Local enrichment layer and export pipeline (JSON/CSV/TXT).
- Web interface pages for dashboard, IOC listing, import center, and export center.
- SQLAlchemy models, Alembic migration, and SQLite local persistence.
- Test suite covering unit, integration, and API handler logic.
- Initial project docs in `docs/specs/` and `docs/plans/`.

### Quality

- Ruff linting, mypy type checks, and pytest validation integrated into workflow.
