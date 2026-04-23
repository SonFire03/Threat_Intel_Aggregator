# IOCvault — Implementation Plan (TDD)

**Date:** 2026-04-23  
**Input spec:** `docs/superpowers/specs/2026-04-23-iocvault-design.md`  
**Status:** Ready for execution

---

## Goal

Ship an offline-first IOC workbench MVP (`IOCvault`) with:
- import TXT/CSV/JSON
- normalize + deduplicate
- score + tag + watchlist
- search/filter + export
- FastAPI API + Jinja2/HTMX UI
- Docker one-command run

---

## Execution Rules

- Work in small vertical slices.
- For each slice: **test first**, then implementation, then refactor.
- No external enrichment/API dependency in MVP.
- Keep migrations deterministic and reversible.
- Definition of done for each task requires tests passing.

---

## Phase 0 — Foundations

### Task 0.1: Project bootstrap

**Deliverables**
- `pyproject.toml` with FastAPI, SQLAlchemy, Alembic, Pydantic v2, pytest, httpx, ruff, mypy, loguru
- folder skeleton as defined in spec
- `.env.example`, `.gitignore`, `README.md` placeholder
- `app/main.py` health route + app factory

**Tests first**
- `tests/api/test_health.py`:
  - `GET /health` returns `200` and `{"status":"ok"}`

**Implementation**
- Create app factory + router registration shell
- Add settings loader (`app/core/config.py`)

**Done when**
- `pytest tests/api/test_health.py -q` passes
- `ruff check .` passes

### Task 0.2: Database setup

**Deliverables**
- `app/database.py` session + engine
- Alembic initialized and configured
- initial migration scaffold

**Tests first**
- `tests/unit/test_db_boot.py`:
  - session can open/close
  - metadata create/drop runs without exception on SQLite

**Done when**
- migration can be generated and applied locally

---

## Phase 1 — Core data model + migration

### Task 1.1: MVP models

**Model scope now (MVP-critical)**
- IOC, Source, Observation, Tag, IOCTag, Watchlist, ImportJob, Enrichment, ExportJob

**Tests first**
- `tests/unit/test_models_constraints.py`:
  - unique `(value, ioc_type)` enforced
  - IOCTag composite PK enforced
  - watchlist one-to-one behavior enforced

**Implementation**
- SQLAlchemy 2.0 typed models
- enums for IOC type/import status/export format/source type
- indexes from spec

### Task 1.2: Migration v001

**Tests first**
- `tests/integration/test_migration_smoke.py`:
  - upgrade head succeeds on empty DB
  - downgrade base succeeds

**Done when**
- `alembic upgrade head` and `alembic downgrade base` both pass

---

## Phase 2 — Normalization + parsing (TDD heavy)

### Task 2.1: Normalizers

**Tests first**
- `tests/unit/test_normalizers.py` for:
  - IPv4 validation + private flag
  - IPv6 canonical compression
  - domain lowercase + strip `www.` + trailing dot
  - URL defang (`hxxp`, `[.]`) + fragment stripping
  - hash uppercase + empty-hash detection

**Implementation**
- `app/normalizers/` modules + shared interface
- deterministic normalize result object:
  - `normalized_value`
  - `ioc_type`
  - flags (`is_private_ip`, `is_empty_hash`, etc.)

### Task 2.2: Parsers

**Tests first**
- `tests/unit/test_parsers.py` + fixtures:
  - TXT comments/blank lines
  - CSV missing columns handling
  - JSON malformed error path
  - defanged mixed lines extraction

**Implementation**
- `txt_parser.py`, `csv_parser.py`, `json_parser.py`
- parser returns structured `ParsedIndicator` records

**Done when**
- all parser/normalizer unit tests green

---

## Phase 3 — Scoring + dedup + import pipeline

### Task 3.1: Scoring service

**Tests first**
- `tests/unit/test_scoring.py`:
  - high confidence ransomware/watchlist case > 9 priority
  - `false-positive` confidence penalty
  - recency decay correctness
  - hard bounds confidence [0..100]

**Implementation**
- `app/services/scoring_service.py`
- pure functions for confidence/severity/priority

### Task 3.2: Dedup service

**Tests first**
- `tests/unit/test_dedup.py`:
  - repeated IOC increments observation_count
  - one IOC across two sources => one IOC row, two observations
  - defanged and normal form deduplicate together

**Implementation**
- upsert on `(value, ioc_type)`
- always insert `Observation`

### Task 3.3: Import service

**Tests first**
- `tests/integration/test_import_pipeline.py`:
  - upload file -> ImportJob completed
  - stats: imported/duplicate/error are accurate
  - valid lines persist even when invalid lines present

**Implementation**
- orchestration: parse -> normalize -> dedup -> score -> enrichment -> persist
- errors recorded in `ImportJob.errors`

---

## Phase 4 — Repository + API layer

### Task 4.1: Repository layer

**Tests first**
- `tests/unit/test_ioc_repo.py`:
  - filter by type/tag/watchlist/min score
  - search by value
  - sorting + pagination

**Implementation**
- `ioc_repo.py`, `tag_repo.py`, `source_repo.py`, `import_job_repo.py`

### Task 4.2: API routes

**Tests first**
- `tests/api/test_iocs_api.py`
- `tests/api/test_imports_api.py`
- `tests/api/test_exports_api.py`
- `tests/api/test_stats_api.py`

**Implementation**
- `/api/v1/iocs`, `/api/v1/imports`, `/api/v1/tags`, `/api/v1/exports`, `/api/v1/stats`
- Pydantic schemas for request/response

**Done when**
- `pytest tests/api -q` green
- OpenAPI docs complete at `/docs`

---

## Phase 5 — Web UI (Jinja2 + HTMX)

### Task 5.1: Base shell + dashboard

**Tests first**
- minimal route tests for `/` and template render 200

**Implementation**
- `templates/base.html`, `dashboard.html`
- dark theme and metrics cards

### Task 5.2: IOC list + detail

**Implementation**
- `/iocs` list with filters + pagination + search
- `/iocs/{id}` details with HTMX tabs
- partials for rows/tags/scores

### Task 5.3: Import/export/tag/watchlist screens

**Implementation**
- `/imports` upload + job feedback
- `/exports` download by filter
- tag manager + watchlist view

**Done when**
- all core UI pages functional without full SPA framework

---

## Phase 6 — Docker + polish

### Task 6.1: Containerization

**Deliverables**
- `Dockerfile`
- `docker-compose.yml`

**Validation**
- `docker compose up` starts app
- app reachable at `http://localhost:8000`

### Task 6.2: Portfolio readiness

**Deliverables**
- README complete (quickstart, screenshots placeholders, API examples)
- `samples/demo_iocs.csv`
- optional `SECURITY.md` defensive-use statement

---

## Suggested branch strategy

- `feat/bootstrap-foundation`
- `feat/models-migration`
- `feat/parsers-normalizers`
- `feat/scoring-import-pipeline`
- `feat/api-v1`
- `feat/web-ui-htmx`
- `chore/docker-readme`

---

## Quality gates per phase

Run on each phase end:

```bash
ruff check .
mypy app
pytest -q
```

For API-focused phases:

```bash
pytest tests/api -q
```

For import pipeline phases:

```bash
pytest tests/unit/test_normalizers.py tests/unit/test_parsers.py tests/unit/test_scoring.py tests/unit/test_dedup.py tests/integration/test_import_pipeline.py -q
```

---

## Immediate next action (now)

Start **Phase 0 / Task 0.1** and deliver the first runnable FastAPI skeleton + health test.
