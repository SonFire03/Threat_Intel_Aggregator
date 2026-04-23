# IOCvault — Design Specification

**Date:** 2026-04-23
**Status:** Approved
**Author:** Design session — Claude Code + user

---

## Summary

IOCvault is a local-first IOC (Indicator of Compromise) aggregation, normalization, and scoring workbench for SOC analysts and threat intelligence practitioners. It runs entirely offline, requires no API keys to function, and is packaged as a single Docker Compose service.

**Tagline:** *A local-first IOC aggregation, normalization and scoring workbench for SOC analysts.*

---

## Constraints and decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Deployment | Local only (Docker) | Zero infrastructure, single user, portfolio focus |
| Auth | None in MVP | Local tool, no exposure |
| UI | Jinja2 + HTMX | Server-rendered, zero build step, interactivity without a JS framework |
| Enrichment | Offline only in MVP, extensible interface | No API key dependency; AbuseIPDB/VT plug-in later |
| Database | SQLite | Zero config, single file, sufficient for the MVP scale |
| Architecture | FastAPI layered (dual interface: API JSON + HTML) | Clean REST API + UI from one process, testable layers |

---

## 1. Concept

**For:** Analysts who want to structure personal threat intel without standing up MISP or OpenCTI.
**Not:** A SIEM, a collaborative platform, an active scanner, or an offensive tool.

The tool occupies the space between a spreadsheet of IOCs and a full enterprise CTI platform. It stores, normalises, deduplicates, scores, tags, and exports IOCs — nothing more.

---

## 2. Project name

**Name:** `IOCvault`
**GitHub description:** *A local-first IOC aggregation, normalization and scoring workbench for SOC analysts. Import TXT/CSV/JSON, normalize, deduplicate, score and export your threat intelligence — no API keys required.*

Alternatives considered: Argus, ThreatLens, Strix, Sentinex, IOCwarden, IOCflow, ThreatStash, Meridian, Pellucid.

---

## 3. MVP scope

### In scope

- Import file (TXT, CSV, JSON) with import job report
- Parsing + IOC type auto-detection
- Normalisation: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256
- Deduplication by `(value_normalized, ioc_type)`
- Automatic local scoring (confidence + severity + priority)
- Manual tagging
- Watchlist toggle per IOC
- Search by value + filters (type, score, tag, watchlist)
- IOC list view + IOC detail view
- Dashboard with global stats
- Export CSV, JSON, TXT
- Full documented REST API (Swagger auto)
- Docker for one-command launch

### Deferred

| Feature | Phase |
|---------|-------|
| CVE type | V1 |
| HTTP feed import (fetch URL) | V1 |
| Analyst notes (Markdown) | V1 |
| Score history table | V1 |
| SQLite FTS5 search | V1 |
| External enrichment (AbuseIPDB, VirusTotal) | V2 |
| Scheduled feeds (APScheduler) | V2 |
| STIX / MISP export | V2 |
| API token auth | V2 |
| PostgreSQL migration | V2 |
| Watchlist hit notifications | V3 |
| Multi-user auth | V3 |

---

## 4. Feature modules

### Ingestion
- Multipart file upload (TXT line-by-line, CSV configurable columns, JSON list/NDJSON)
- Format validation before processing
- Import report: N imported, N duplicates, N errors with per-line detail
- Partial import: valid IOCs always pass even when some lines fail
- Import job tracked (timestamp, source, stats)
- Defang support on input: `hxxp://` → `http://`, `[.]` → `.`

### Parsing
- IOC type auto-detection by regex per line
- Extraction from raw mixed lines
- Extraction from named CSV columns
- Non-parseable lines logged in `ImportJob.errors`

### Normalisation
- IPv4: strip whitespace, RFC validation, flag private ranges
- IPv6: canonical compressed form via Python stdlib
- Domain: lowercase, strip `www.`, strip trailing dot
- URL: lowercase host, strip fragment, rebuild defanged URLs
- Hash: uppercase, type derived from length (MD5=32, SHA1=40, SHA256=64)
- CVE (V1): normalise to `CVE-YYYY-NNNNN` uppercase

### Deduplication
- Unique key: `(value_normalized, ioc_type)` — DB UNIQUE constraint
- Upsert strategy: on conflict → update `last_seen`, increment `observation_count`, merge new tags
- Multiple observations allowed per IOC (multiple sources tracked separately)

### Scoring
- Two dimensions: confidence (0–100) + severity (0–10)
- Composite: `priority = (confidence / 100) × severity` → 0–10
- Recalculated on: import, tag added/removed, watchlist toggle, new enrichment

### Enrichment
- `BaseEnricher` ABC with `enrich(ioc) -> EnrichmentResult`
- V1: `LocalEnricher` — computes metadata from existing fields (age, frequency, watchlist status, type)
- V2: `AbuseIPDBEnricher`, `VirusTotalEnricher` — plug-in without refactor
- Result stored as JSON in `Enrichment` table

### Tagging
- Free-form tags (slugified, case-insensitive)
- Suggested tags: `malware`, `phishing`, `c2`, `ransomware`, `cryptomining`, `scanner`, `tor-exit`, `false-positive`
- Inline assignment via HTMX (no page reload)
- Tag cloud on dashboard

### Watchlist
- Toggle per IOC (`is_watchlisted` flag + `Watchlist` table for reason/history)
- Dedicated filtered view
- Visual indicator in list (star icon, highlighted row)
- Watchlist hit = confidence boost in scoring

### Search / Filters
- Full-text search on IOC value (LIKE in V1, FTS5 in V1.1)
- Combinable filters: type, min score, tag, watchlist only, source, date range
- Sort: priority score, first_seen, last_seen, observation_count

### Export
- Formats: CSV (all fields or selection), JSON (native), TXT (one value per line)
- Applied filters respected in export
- Direct browser download

### Dashboard / API
- Global stats, per-type distribution, top tags, recent imports, recent IOCs
- Auto-documented REST API via FastAPI (Swagger UI at `/docs`)

### Observability / Logs
- Structured logs via `loguru`
- Each import job fully logged (result, per-line errors)
- IOC values appear in DEBUG logs only, never in ERROR/WARNING level

### Administration
- Delete single IOC
- Delete all IOCs from a source
- Purge IOCs older than N days
- Global score recalculation endpoint

---

## 5. IOC types

### IPv4
- Validation: `ipaddress.ip_address()`
- Normalisation: strip whitespace
- Flag: `is_private` for RFC1918 ranges (auto-reduce confidence)
- Pitfall: private IPs are likely false positives — auto-flag them

### IPv6
- Validation: `ipaddress.ip_address()` (same function)
- Normalisation: `str(ipaddress.ip_address(value))` → canonical compressed form
- Pitfall: loopback `::1`, IPv4-mapped `::ffff:x.x.x.x` — auto-flag

### Domain
- Validation: regex + max 253 chars + minimum one dot
- Normalisation: lowercase, strip `www.`, strip trailing dot
- Pitfall: IDN/punycode domains, subdomain of a legitimate domain

### URL
- Validation: `urllib.parse.urlparse()` + valid host check
- Normalisation: lowercase host, strip fragment, rebuild defanged form
- Pitfall: partial defang, very long URLs (>2048 chars), chain redirects

### Hash (MD5 / SHA1 / SHA256)
- Validation: regex `^[0-9a-fA-F]{32|40|64}$`
- Normalisation: uppercase
- Type detection: by character length
- Pitfall: empty-file hashes must be blacklisted
  - MD5 empty: `D41D8CD98F00B204E9800998ECF8427E`
  - SHA1 empty: `DA39A3EE5E6B4B0D3255BFEF95601890AFD80709`
  - SHA256 empty: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

### CVE (V1)
- Validation: regex `^CVE-\d{4}-\d{4,}$`
- Normalisation: uppercase
- Pitfall: 4-digit legacy IDs vs N-digit modern IDs

---

## 6. Data model

### Entities

```
IOC
  id                UUID PK
  value             TEXT (normalised)
  ioc_type          ENUM (ipv4, ipv6, domain, url, md5, sha1, sha256, cve)
  first_seen        DATETIME
  last_seen         DATETIME
  observation_count INT default 1
  confidence_score  FLOAT (0–100)
  severity_score    FLOAT (0–10)
  priority_score    FLOAT (0–10)
  is_watchlisted    BOOL default false
  is_active         BOOL default true
  is_private_ip     BOOL nullable

Source
  id           INT PK
  name         TEXT unique
  source_type  ENUM (file, api, manual, feed)
  reliability  FLOAT (0–1)
  created_at   DATETIME

Observation
  id            INT PK
  ioc_id        FK → IOC
  source_id     FK → Source
  import_job_id FK → ImportJob
  raw_value     TEXT
  observed_at   DATETIME

Tag
  id         INT PK
  name       TEXT unique (slugified)
  color      TEXT (hex)
  created_at DATETIME

IOCTag (M2M junction)
  ioc_id    FK → IOC
  tag_id    FK → Tag
  tagged_at DATETIME
  PRIMARY KEY (ioc_id, tag_id)

Watchlist
  ioc_id    FK → IOC PK
  added_at  DATETIME
  reason    TEXT nullable

AnalystNote
  id         INT PK
  ioc_id     FK → IOC
  content    TEXT
  created_at DATETIME
  updated_at DATETIME

Enrichment
  id             INT PK
  ioc_id         FK → IOC
  enricher_name  TEXT
  data           JSON
  enriched_at    DATETIME

ScoreHistory
  id               INT PK
  ioc_id           FK → IOC
  confidence_score FLOAT
  severity_score   FLOAT
  priority_score   FLOAT
  scored_at        DATETIME
  trigger          TEXT
  -- Table created in MVP schema but not populated until V1.
  -- The Alembic migration creates it; the scoring service skips writing to it in MVP.

ImportJob
  id              UUID PK
  filename        TEXT
  source_id       FK → Source
  status          ENUM (pending, processing, completed, failed)
  total_lines     INT
  imported_count  INT
  duplicate_count INT
  error_count     INT
  errors          JSON
  started_at      DATETIME
  completed_at    DATETIME nullable

ExportJob
  id         UUID PK
  format     ENUM (csv, json, txt)
  filters    JSON
  row_count  INT
  created_at DATETIME
  filepath   TEXT
  -- MVP: exports are synchronous (small local datasets). ExportJob is created and
  -- completed in the same request. The table exists for V2 async/large exports.
```

### Relations
```
IOC 1──N Observation N──1 Source
IOC 1──N Enrichment
IOC 1──N AnalystNote
IOC 1──N ScoreHistory
IOC M──N Tag (via IOCTag)
IOC 1──0..1 Watchlist
Observation N──1 ImportJob
```

### Deduplication logic
- UNIQUE constraint on `(value, ioc_type)`
- On conflict: update `last_seen = now()`, `observation_count += 1`
- Insert new Observation row regardless (multiple sources tracked)
- Normalisation always runs before DB lookup

### Useful indexes
```sql
UNIQUE INDEX uq_ioc_value_type      ON ioc(value, ioc_type)
INDEX ix_ioc_priority_score         ON ioc(priority_score)
INDEX ix_ioc_last_seen              ON ioc(last_seen)
INDEX ix_ioc_is_watchlisted         ON ioc(is_watchlisted)
INDEX ix_ioc_ioc_type               ON ioc(ioc_type)
INDEX ix_observation_ioc_id         ON observation(ioc_id)
INDEX ix_observation_import_job_id  ON observation(import_job_id)
```

---

## 7. Scoring logic

### Confidence (0–100) — "Can I trust this IOC?"

| Factor | Max pts | Rule |
|--------|---------|------|
| Source reliability | 30 | `source.reliability × 30` |
| Observation frequency | 20 | `min(observation_count / 5 × 20, 20)` |
| Recency | 20 | `max(0, 20 - days_since_last_seen)` |
| Watchlist hit | 15 | `+15` if `is_watchlisted` |
| Malicious tags | 10 | `+10` if tag ∈ {malware, c2, ransomware, phishing} |
| Enrichment present | 5 | `+5` if enrichment data non-empty |
| False-positive tag | −40 | if tag = `false-positive` |

```python
confidence = (
    source.reliability * 30
    + min(observation_count / 5 * 20, 20)
    + max(0, 20 - days_since_last_seen)
    + (15 if is_watchlisted else 0)
    + (10 if has_malicious_tag else 0)
    + (5 if has_enrichment else 0)
    + (-40 if has_false_positive_tag else 0)
)
confidence = max(0.0, min(100.0, confidence))
```

### Severity (0–10) — "If malicious, how bad?"

| Condition | Severity |
|-----------|---------|
| Tag `ransomware` | 10 |
| Tag `c2` | 9 |
| Tag `malware` | 8 |
| Tag `phishing` | 7 |
| Tag `cryptomining` | 6 |
| Tag `tor-exit` | 5 |
| Tag `scanner` | 4 |
| No tag — hash type | 7 |
| No tag — URL type | 6 |
| No tag — IP / domain | 5 |

When an IOC has multiple tags, severity = max severity across all present tags.

### Priority (0–10) — "What to look at first?"

```python
priority = (confidence / 100.0) * severity
```

### Concrete examples

| Scenario | Confidence | Severity | Priority |
|----------|-----------|---------|---------|
| IP seen once, low-reliability source (0.3), no tag | 19 | 5 | 0.95 |
| SHA256, trusted source (1.0), seen 10×, `ransomware`, watchlisted | 95 | 10 | **9.5** |
| Domain, source (0.7), seen 3×, tag `false-positive` | 5 | 5 | 0.25 |
| IP, source (0.8), seen 5×, `c2`, watchlisted | 88 | 9 | **7.9** |

---

## 8. Ingestion sources

### V1 — File import

**TXT** (one value per line)
```
# Comments ignored
192.0.2.1
evil-domain.example
https://malware.example/payload.exe
d41d8cd98f00b204e9800998ecf8427e
hxxp://bad[.]actor/path
```

**CSV**
```csv
indicator,type,confidence,tags
8.8.8.8,ip,high,"scanner,recon"
evil.com,domain,medium,phishing
44d88612fea8a8f36de82e1278abb02f,md5,,malware
```

**JSON**
```json
[
  {"value": "evil.com", "type": "domain", "tags": ["phishing"]},
  {"value": "192.0.2.1"},
  {"value": "44d88612fea8a8f36de82e1278abb02f", "tags": ["malware"]}
]
```

**Error handling rules:**
- Invalid line → logged in `ImportJob.errors` with reason, skipped
- Partial import → valid IOCs always persist
- Empty file → `imported_count = 0`, status = completed (not failed)
- Unknown format → status = failed immediately
- File too large (> 10 MB default) → 413 before processing

### V2 — External API feeds (public, free)
- abuse.ch URLHaus (CSV public)
- Feodo Tracker (JSON public)
- AlienVault OTX (free API key)
- CISA KEV (JSON public)

### V3 — Scheduled feeds
- APScheduler: periodic re-fetch (every 6h / 24h, configurable)
- Delta-only: compare `last_seen` to avoid mass re-imports
- Each scheduled run tracked as `ImportJob` with `source_type = feed`

---

## 9. Technical stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend | FastAPI | Async, Pydantic native, auto Swagger, typed |
| ORM | SQLAlchemy 2.0 | Modern, typed, clean patterns |
| Migrations | Alembic | Schema versioning |
| Database | SQLite | Zero config, local file, MVP-sufficient |
| Validation | Pydantic v2 | Strict validation, clear error messages |
| Templates | Jinja2 | Native FastAPI, no build step |
| Frontend | HTMX | Dynamic interactions without a JS framework |
| CSS | TailwindCSS CDN | Fast, dark mode native, no build |
| Tests | pytest + httpx | Standard Python async-compatible |
| Linting | Ruff | Replaces flake8 + isort, ultra-fast |
| Types | mypy | Static rigour on business logic |
| Logging | loguru | Simple, structured, coloured in dev |
| Packaging | uv | Modern, fast, replaces pip + venv |
| Scheduling | APScheduler (V2) | Lightweight, embeds in FastAPI, no Redis |

---

## 10. Project structure

```
iocvault/
├── pyproject.toml
├── README.md
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
│
├── alembic/
│   └── versions/
│
├── app/
│   ├── main.py
│   ├── database.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   ├── ioc.py
│   │   ├── source.py
│   │   ├── observation.py
│   │   ├── tag.py
│   │   ├── enrichment.py
│   │   ├── analyst_note.py
│   │   ├── score_history.py
│   │   ├── import_job.py
│   │   └── export_job.py
│   │
│   ├── schemas/
│   │   ├── ioc.py
│   │   ├── tag.py
│   │   ├── import_job.py
│   │   └── export.py
│   │
│   ├── repositories/
│   │   ├── ioc_repo.py
│   │   ├── tag_repo.py
│   │   ├── source_repo.py
│   │   └── import_job_repo.py
│   │
│   ├── services/
│   │   ├── import_service.py
│   │   ├── export_service.py
│   │   ├── scoring_service.py
│   │   ├── dedup_service.py
│   │   └── enrichment_service.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── txt_parser.py
│   │   ├── csv_parser.py
│   │   └── json_parser.py
│   │
│   ├── normalizers/
│   │   ├── base.py
│   │   ├── ip_normalizer.py
│   │   ├── domain_normalizer.py
│   │   ├── url_normalizer.py
│   │   └── hash_normalizer.py
│   │
│   ├── enrichers/
│   │   ├── base.py
│   │   └── local_enricher.py
│   │
│   ├── routers/
│   │   ├── api/
│   │   │   ├── iocs.py
│   │   │   ├── tags.py
│   │   │   ├── imports.py
│   │   │   ├── exports.py
│   │   │   └── stats.py
│   │   └── web/
│   │       ├── dashboard.py
│   │       ├── iocs.py
│   │       ├── imports.py
│   │       └── exports.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── iocs/
│   │   │   ├── list.html
│   │   │   └── detail.html
│   │   ├── imports/
│   │   │   └── upload.html
│   │   └── partials/
│   │       ├── ioc_row.html
│   │       ├── tag_badge.html
│   │       └── score_badge.html
│   │
│   └── static/
│       ├── css/custom.css
│       └── js/app.js
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── valid_ips.txt
│   │   ├── mixed_iocs.csv
│   │   ├── malformed.json
│   │   └── defanged.txt
│   ├── unit/
│   │   ├── test_normalizers.py
│   │   ├── test_parsers.py
│   │   ├── test_scoring.py
│   │   └── test_dedup.py
│   ├── api/
│   │   ├── test_iocs_api.py
│   │   ├── test_imports_api.py
│   │   └── test_exports_api.py
│   └── integration/
│       └── test_import_pipeline.py
│
├── samples/
│   └── demo_iocs.csv
│
└── docs/
    └── specs/
        └── 2026-04-23-iocvault-design.md
```

---

## 11. REST API endpoints

### IOC

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/iocs` | Paginated list with filters (`type`, `q`, `score_min`, `tag`, `watchlist`, `sort`, `page`) |
| GET | `/api/v1/iocs/{id}` | Full detail with enrichments, tags, observations, notes |
| DELETE | `/api/v1/iocs/{id}` | Delete IOC |
| PATCH | `/api/v1/iocs/{id}/watchlist` | Toggle watchlist (`{"watchlisted": true, "reason": "..."}`) |
| POST | `/api/v1/iocs/{id}/tags` | Add tag (`{"tag_name": "malware"}`) |
| DELETE | `/api/v1/iocs/{id}/tags/{tag_id}` | Remove tag |
| POST | `/api/v1/iocs/{id}/notes` | Add analyst note (`{"content": "..."}`) |
| POST | `/api/v1/iocs/{id}/score/recalculate` | Force score recalculation |

### Tags

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/tags` | All tags with IOC count |
| POST | `/api/v1/tags` | Create tag (`{"name": "phishing"}`) |
| DELETE | `/api/v1/tags/{id}` | Delete tag |

### Import

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/imports` | Upload file (`multipart/form-data`: `file`, `source_name`, `format?`) → ImportJob |
| GET | `/api/v1/imports` | List import jobs |
| GET | `/api/v1/imports/{id}` | Job detail (status, stats, errors) |

### Export

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/exports` | Create export (`{"format": "csv", "filters": {...}}`) → ExportJob |
| GET | `/api/v1/exports/{id}/download` | Download file |

### Stats / Search

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/stats` | Global stats: total, per type, top tags, score distribution |
| GET | `/api/v1/search?q=...` | Search — LIKE-based in MVP, SQLite FTS5 in V1.1 |

---

## 12. User interface

### Pages

**Dashboard** (`/`)
- 4-metric strip: total IOC | watchlisted | imported today | avg priority score
- Per-type distribution (horizontal bars, no chart library)
- Tag cloud (top 10 tags, proportional size)
- Recent IOCs table (5 rows, with coloured score badge)
- Recent import jobs (3, with status badge)

**IOC List** (`/iocs`)
- Table: value (monospace), type (coloured badge), priority score (coloured badge), tags, watchlist (star icon), last_seen
- Filter sidebar: type checkboxes, min score slider, tag multiselect, watchlist toggle, date range
- HTMX search bar (results update inline)
- Pagination
- Inline HTMX: watchlist toggle, add tag (no page reload)
- "Export (current filters)" button

**IOC Detail** (`/iocs/{id}`)
- Header: large monospace value, type badge, priority score badge
- 4 HTMX tabs: Summary | Enrichment | Observations | Notes
- Summary: all fields, inline tag add/remove, watchlist toggle + reason
- Enrichment: formatted JSON from LocalEnricher
- Observations: table of source / date / import job / raw value
- Notes: list + add form

**Import Center** (`/imports`)
- Drag-and-drop file zone
- Source name field
- Format selector (auto-detect default)
- HTMX polling on job → progressive feedback (processing → completed)
- Inline result: `47 imported, 3 deduplicated, 0 errors`
- Past jobs list at bottom

**Tags & Watchlist** (`/tags`)
- Tag manager: create, delete, IOC count per tag
- Watchlist view: filtered table on `is_watchlisted = true`, sorted by priority

**Export Center** (`/exports`)
- Form: format (CSV/JSON/TXT), optional filters
- Direct download via `<a href>`

### Visual style

```
Background:       #0f1117  (near-black blue tint)
Sidebar:          #161b22  (GitHub dark)
Cards / panels:   #1c2128
Primary text:     #e6edf3
Secondary text:   #8b949e
Accent / links:   #58a6ff  (GitHub blue)
Danger:           #f85149
Success:          #3fb950
Warning:          #d29922
High score badge: #f85149
Mid score badge:  #d29922
Low score badge:  #3fb950

IOC values:       JetBrains Mono or Fira Code (monospace)
UI text:          Inter
```

TailwindCSS `class`-based dark mode, CDN in dev. No animations except HTMX swap transitions.

---

## 13. Security

For a local tool, the objective is to build defensive reflexes that transfer directly to production projects.

- **Strict input validation:** Pydantic v2 on all API inputs; SQLAlchemy ORM models never exposed directly
- **Parameterised SQL only:** SQLAlchemy ORM queries exclusively; no f-strings in queries; no raw SQL
- **Secure upload:** max file size 10 MB (configurable), Content-Type checked, content parsed not executed
- **No SSRF in V1:** imported URLs are stored as data, never fetched. V2 feed fetches use a configured domain allowlist.
- **Secrets in `.env`:** future API keys in `.env`, never hardcoded; `.env` in `.gitignore`; `.env.example` committed without values
- **Clean logs:** IOC values in DEBUG only, never in ERROR/WARNING
- **CORS:** restricted to `localhost` in dev, configurable via `.env`
- **No offensive modules:** no active scanner, DNS resolver, ping, or any network interaction with IOC values
- **Configurable data retention:** purge endpoint for IOCs older than N days

---

## 14. Roadmap

### Phase 0 — MVP (4–6 weeks)
Functional, demonstrable, Dockerised tool.

- Project setup (uv, ruff, mypy, pytest, Docker)
- SQLAlchemy models + Alembic migrations
- Import pipeline: TXT / CSV / JSON → normalise → deduplicate → score
- IOC types: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256
- Full REST API (Swagger)
- Jinja2 + HTMX dark UI: dashboard, IOC list, IOC detail, import center
- Tags + watchlist
- Export CSV / JSON / TXT
- Unit tests: normalisation, parsing, scoring, deduplication
- Docker + README + demo dataset

### Phase 1 — V1 (2–3 weeks post-MVP)
- CVE as IOC type
- Analyst notes (Markdown, rendered in detail view)
- Score history
- FTS5 full-text search
- HTTP URL import (fetch a public feed directly)
- UX improvements: HTMX transitions, persistent filters, improved pagination
- Integration tests for full pipeline

### Phase 2 — V2 (ongoing)
- External enrichers: AbuseIPDB (IPs), VirusTotal (hashes)
- Scheduled feeds: abuse.ch URLHaus, Feodo Tracker (APScheduler)
- STIX 2.1 / MISP JSON export
- Static API token (`X-API-Key`) for local network exposure
- Optional PostgreSQL migration (Alembic managed)
- Score history chart (minimal Chart.js)

### Phase 3 — V3 (long term)
- Multi-source correlation (auto score boost when N distinct sources observe same IOC)
- Watchlist hit webhook notifications
- CLI for command-line import (`iocvault import file.txt`)
- Basic single-user login (if public exposure desired)
- MISP push/pull

---

## 15. Development plan

Steps in optimal build order — each step is testable before moving to the next.

```
Step 1  — Project foundations
          pyproject.toml (uv), folder structure, .env, config.py, logging.py, main.py skeleton

Step 2  — SQLAlchemy models + Alembic
          All entities, database.py, alembic init, initial migration v001
          Verify schema with DB Browser for SQLite

Step 3  — Normalizers (with immediate unit tests)
          ip_normalizer, domain_normalizer, url_normalizer, hash_normalizer
          → tests/unit/test_normalizers.py before continuing

Step 4  — Parsers (with immediate unit tests)
          txt_parser, csv_parser, json_parser, defang support
          → tests/unit/test_parsers.py + fixtures in tests/fixtures/

Step 5  — Scoring service
          scoring_service.py: confidence, severity, priority calculation
          → tests/unit/test_scoring.py with edge cases

Step 6  — Import service + deduplication
          import_service.py: orchestrates parse → normalise → deduplicate → score → persist
          dedup_service.py: upsert logic
          → tests/unit/test_dedup.py

Step 7  — Repositories
          ioc_repo, tag_repo, source_repo, import_job_repo
          Queries: filtered + paginated list, get by id, create, update, delete

Step 8  — REST API
          routers/api/: iocs, tags, imports, exports, stats
          → tests/api/ with httpx TestClient

Step 9  — Local enricher
          base.py (ABC), local_enricher.py, enrichment_service.py
          Wired into import pipeline as final step

Step 10 — Integration tests
          test_import_pipeline.py: upload → job → IOC in DB → score calculated → export

Step 11 — UI base
          base.html (dark sidebar, nav), TailwindCSS CDN, HTMX CDN
          dashboard.html with real data from API

Step 12 — IOC list + detail UI
          list.html with HTMX filters and search
          detail.html with HTMX tabs
          Partials: ioc_row.html, score_badge.html, tag_badge.html

Step 13 — Import + export UI
          upload.html with drag-and-drop + HTMX polling on job
          Export form with direct download

Step 14 — Tags + watchlist UI
          Inline HTMX swap from list view
          Tags manager page

Step 15 — Docker
          Dockerfile (clean multi-stage), docker-compose.yml
          Verify: docker compose up → app accessible at localhost:8000

Step 16 — Portfolio
          README with screenshots, GIF demos
          samples/demo_iocs.csv with real public IOCs (abuse.ch)
          GitHub topics, badges, repo description
```

---

## 16. Portfolio / GitHub strategy

### README structure
1. Name + tagline + badges
2. Dashboard screenshot (full width, above the fold)
3. 3-line description: what, for whom, why
4. Features bullet list
5. Quick Start (3 commands max)
6. API section with 2–3 curl examples + JSON responses
7. Architecture: ASCII pipeline diagram
8. Screenshots gallery

### Screenshots to prepare
1. Dashboard (metrics + tag cloud + recent IOCs)
2. IOC list with active filters and score badges
3. IOC detail (Enrichment tab open)
4. Import Center (result of a successful import)
5. Export with filters selected

### GIF demos
- GIF 1: import `demo_iocs.csv` → import report → populated list (30s)
- GIF 2: search IOC → add tag → watchlist toggle (15s)

### Badges
```markdown
![Python](https://img.shields.io/badge/python-3.12+-3776AB?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![SQLite](https://img.shields.io/badge/db-SQLite-07405E?logo=sqlite)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
```

### Credibility checklist
- Include `samples/demo_iocs.csv` with real public IOCs (abuse.ch URLHaus export)
- Document the scoring logic in the README (show the formula, not just "we score IOCs")
- GitHub topics: `cybersecurity` `threat-intelligence` `ioc` `blue-team` `soc` `fastapi` `python`
- README answers "why this project exists" from an analyst perspective
- `SECURITY.md` with "defensive use only" note

---

## 17. Test strategy

### Philosophy
Test business-critical modules, not the framework.

### Unit tests — `tests/unit/`

`test_normalizers.py`
- Private IPv4 → flagged correctly
- IPv6 multiple representations → same normalised output
- Domain with `WWW.` and trailing dot → `example.com`
- Defanged URL `hxxps://evil[.]com/path` → `https://evil.com/path`
- MD5 lowercase → uppercase
- Empty-file MD5 hash → flagged

`test_parsers.py`
- TXT with blank lines, `#` comments, whitespace → correct IOC count
- CSV with missing columns → absent values handled cleanly
- Malformed JSON → clear exception, no silent crash
- Empty file → 0 IOCs, no error
- Lines with mixed IOC types → correctly separated

`test_scoring.py`
- Source reliability 1.0 + watchlist + `ransomware` tag → priority > 9
- `false-positive` tag → confidence < 10
- IOC 30 days old → correct recency decay
- Score always bounded [0, 100] — never negative or > 100

`test_dedup.py`
- Same file imported twice → same IOC count, `observation_count` doubled
- Two different sources, same IOC → two Observation rows, one IOC in DB
- Defanged value and normal value → same IOC after normalisation

### API tests — `tests/api/`

`test_iocs_api.py`
- GET list: 200, correct pagination, filters functional
- GET detail: 200, full structure, 404 for unknown ID
- DELETE: 204, IOC absent after deletion
- PATCH watchlist: toggle true then false
- POST tag: tag added, idempotent if already present

`test_imports_api.py`
- Valid TXT upload → 201, job created, IOCs in DB
- Valid CSV upload → 201
- Malformed JSON → ImportJob.status = failed, no server crash
- Empty file → imported_count = 0, status = completed
- File too large → 413

`test_exports_api.py`
- CSV export → correct Content-Type, row count matches IOC count
- JSON export → valid JSON, correct structure
- Export with watchlist filter → only watchlisted IOCs

### Integration tests — `tests/integration/`

`test_import_pipeline.py`
- Full pipeline: upload demo CSV → job completed → IOCs in DB → scores calculated → local enrichment → CSV export of result

### Fixtures
- `conftest.py`: in-memory SQLite (`:memory:`), httpx TestClient, initial source seed data
- `tests/fixtures/`: valid_ips.txt, mixed_iocs.csv, malformed.json, defanged.txt

---

## 18. Common mistakes to avoid

1. **MVP scope too large** — implementing CVE + feeds + auth + MISP simultaneously → delivering nothing. The IP/domain/hash pipeline alone is already a complete, demonstrable project.

2. **Mandatory external API dependency in V1** — if the project requires an AbuseIPDB key to function, it cannot be demonstrated in an interview or to a recruiter. Everything must work offline.

3. **Bullshit scoring** — a 15-parameter formula with magic weights producing arbitrary scores. Prefer 4 simple, documented, tested, verbally-explainable rules.

4. **Normalisation after insert** — if normalisation runs after DB insertion, deduplication breaks (`evil.com` and `EVIL.COM` create two entries). Always normalise first.

5. **All-or-nothing import** — if one invalid line aborts the entire import, the tool is unusable with real-world files. Always skip + log errors.

6. **SQLAlchemy misuse** — raw SQL with f-strings, ORM models exposed directly via the API. Both break security and maintainability.

7. **No demo data** — a recruiter who clones the repo and sees an empty app does not understand the project. Always include `samples/demo_iocs.csv`.

8. **Zero tests** — a portfolio project without tests is the fastest signal a senior engineer uses to disqualify it. 40% coverage on critical modules is enough.

9. **Generic name** — `ThreatAnalyzer`, `IOCManager` → 50 identical projects on GitHub. A unique, findable name is a business decision.

10. **Fake project feel** — invented IOCs, fantasy scores, fictional sources. Using real public IOCs (abuse.ch, Feodo Tracker are legal and free) makes the project immediately credible.

---

## Final summary

| Item | Decision |
|------|---------|
| **Name** | IOCvault |
| **GitHub description** | A local-first IOC aggregation, normalization and scoring workbench for SOC analysts. Import TXT/CSV/JSON, normalize, deduplicate, score and export your threat intelligence — no API keys required. |
| **Stack** | FastAPI + SQLAlchemy 2.0 + Alembic + SQLite + Pydantic v2 + Jinja2 + HTMX + TailwindCSS CDN + pytest + httpx + loguru + ruff + mypy + uv |

### First 10 tasks to implement

```
1.  Init project: uv, pyproject.toml, ruff + mypy config, folder structure
2.  SQLAlchemy models (ioc, source, observation, tag, import_job) + Alembic migration v001
3.  Normalizers (IP, domain, hash, URL) + unit tests
4.  Parsers (TXT, CSV, JSON) + unit tests + test fixtures
5.  ScoringService (confidence / severity / priority) + unit tests
6.  ImportService (parse → normalise → deduplicate → score → persist) + DedupService
7.  Repositories (ioc_repo, tag_repo, source_repo, import_job_repo) with filtered queries
8.  REST API routers (iocs, imports, tags, stats, exports) + API tests
9.  BaseEnricher + LocalEnricher wired into import pipeline
10. Base dark UI: base.html + dashboard.html + IOC list with HTMX
```
