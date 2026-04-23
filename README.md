# IOCvault

Local-first IOC aggregation, normalization, scoring and export workbench.

---

## FR

### Pourquoi ce projet existe

IOCvault a été conçu pour répondre à un besoin simple: travailler rapidement sur des IOC (Indicators of Compromise) sans dépendre d'une plateforme lourde ni d'API externes.

L'objectif est de proposer un outil local, testable et reproductible pour:
- importer des IOC depuis des fichiers texte/CSV/JSON,
- normaliser et dédupliquer automatiquement les données,
- prioriser l'analyse via un score explicable,
- filtrer, tagger, watchlister et exporter les résultats.

### Objectif du programme

Le programme sert de socle opérationnel pour un flux de travail Threat Intel / SOC:
- ingestion fiable de données hétérogènes,
- nettoyage automatique des formats (defang/refang, normalisation IP/domain/hash/URL),
- suivi des observations et scoring,
- exposition API + interface web légère pour usage quotidien.

### Pourquoi avoir fait ces choix techniques

- `FastAPI`: API claire + documentation Swagger native.
- `SQLAlchemy + Alembic + SQLite`: base locale simple, migrations versionnées.
- `Jinja2`: interface web sans build frontend complexe.
- `pytest + mypy + ruff`: qualité de code et régressions contrôlées.

### Fonctionnalités actuelles

- API REST:
  - `/api/v1/imports`
  - `/api/v1/iocs`
  - `/api/v1/tags`
  - `/api/v1/stats`
  - `/api/v1/exports`
- UI Web:
  - `/` dashboard
  - `/iocs`
  - `/imports`
  - `/exports`
- Import TXT/CSV/JSON avec rapport de job.
- Déduplication + scoring + enrichissement local.
- Export en `csv`, `json`, `txt`.

### Lancer le projet

```bash
cd /path/to/Threat_Intel_Aggregator
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Ensuite:
- Application web: `http://127.0.0.1:8000/`
- Documentation API: `http://127.0.0.1:8000/docs`

### Qualité actuelle

- Lint: `ruff check .`
- Typage: `mypy app`
- Tests: `pytest`

---

## EN

### Why this project exists

IOCvault was built to solve a practical problem: handling indicators of compromise quickly without relying on heavy external platforms or paid API integrations.

The goal is to provide a local, reproducible workflow to:
- import IOCs from text/CSV/JSON files,
- normalize and deduplicate data automatically,
- prioritize investigation with an explainable score,
- filter, tag, watchlist, and export results.

### Program purpose

This application acts as a compact Threat Intel / SOC workbench:
- reliable ingestion of heterogeneous IOC feeds,
- automatic cleanup and normalization (defang/refang, IP/domain/hash/URL),
- observation tracking and scoring,
- both API and lightweight web interface for daily operations.

### Why these technical choices

- `FastAPI`: clean API layer with native Swagger docs.
- `SQLAlchemy + Alembic + SQLite`: simple local persistence with versioned schema.
- `Jinja2`: zero-build web interface.
- `pytest + mypy + ruff`: strong quality gates and regression control.

### Current capabilities

- REST API:
  - `/api/v1/imports`
  - `/api/v1/iocs`
  - `/api/v1/tags`
  - `/api/v1/stats`
  - `/api/v1/exports`
- Web UI:
  - `/` dashboard
  - `/iocs`
  - `/imports`
  - `/exports`
- TXT/CSV/JSON import with job reports.
- Deduplication + scoring + local enrichment.
- `csv`, `json`, `txt` export.

### Run locally

```bash
cd /path/to/Threat_Intel_Aggregator
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Then open:
- Web app: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

### Quality status

- Lint: `ruff check .`
- Types: `mypy app`
- Tests: `pytest`
