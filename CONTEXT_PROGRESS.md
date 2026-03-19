# CONTEXT_PROGRESS.md — Nova (Data-Kitchen) Full Context & Progress Dump

> **Last updated:** 2026-03-15
> **Purpose:** Single-source briefing for any LLM session to resume work on Nova. Contains project identity, what's built, what's not, architecture decisions, and exact file inventory.
> **Repo state:** 40+ files, ~4,200 lines of application code, 25 passing tests, Sprints 1–4 complete.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Name** | Nova |
| **Repo** | `ShreyPatel4/Data-Kitchen` |
| **Tagline** | AI-driven data platform — connect sources, model data, ship dashboards in one day |
| **Target user** | Data engineers at Series A–C startups and mid-market companies (50–500 employees) |
| **Architecture** | Single FastAPI monolith + connector framework + lakehouse layer + Next.js frontend |
| **Stack** | Python 3.11, FastAPI, SQLAlchemy async, Pydantic v2, PyIceberg, Trino, Flink, Kafka, Temporal, Neo4j |

---

## 2. Sprint Status

| Sprint | Theme | Status | Key Deliverables |
|--------|-------|--------|-----------------|
| **1** | Bootable Platform | DONE | Docker Compose (12 services), FastAPI app, Next.js skeleton, CI/CD, Taskfile |
| **2** | Metadata Backbone | DONE | 9 SQLAlchemy models, full CRUD API (27 endpoints), Pydantic schemas, Alembic |
| **3** | First Data Flows | DONE | Connector framework (Postgres CDC, S3 file, Kafka sink), Iceberg writer, pipeline executor, Trino config |
| **4** | Schema Evolution | DONE | Schema diff detection (safe vs breaking), quarantine framework, contract validation |
| **5** | Lineage + Impact | NOT STARTED | Neo4j integration, impact analysis API, freshness SLOs |
| **6** | AI: Root Cause | NOT STARTED | AI skill registry, telemetry lake, Claude API integration, RCA skill |
| **7** | Frontend: UI | NOT STARTED | Mission Control, Catalog, lineage graph (React Flow), AI chat panel |
| **8** | AI Skills #2+#3 | NOT STARTED | SQL assistant, pipeline proposal, S3 connector, query editor UI |
| **9** | Quality + Builder | NOT STARTED | Data contracts DSL, drift detection, visual pipeline builder |
| **10** | Security + Demo | NOT STARTED | Keycloak SSO, RBAC, audit log, end-to-end demo |

---

## 3. Complete File Inventory

### 3.1 API Application (`apps/api/src/nova_api/`) — 1,080 lines

| File | Lines | What It Does |
|------|-------|-------------|
| `config.py` | 47 | Pydantic Settings — all env vars (DB, Neo4j, Kafka, MinIO, Temporal, JWT, CORS) prefixed `NOVA_` |
| `database.py` | 37 | Async SQLAlchemy engine + session factory. SQLite-compatible (pool_size only for Postgres). `get_db()` dependency. |
| `models.py` | 359 | 9 ORM models with GUID type decorator (works SQLite + Postgres), JSON columns, enums, indexes, unique constraints |
| `schemas.py` | 252 | Pydantic v2 Create/Update/Response schemas for all models. Field validation (min_length, max_length). |
| `app.py` | 65 | FastAPI factory. CORS middleware. Mounts 7 routers under `/api/v1`. Lifespan with engine disposal. |
| `routes/projects.py` | 67 | POST, GET (list), GET (detail), PATCH, DELETE |
| `routes/datasets.py` | 135 | POST (with nested columns), GET (list with zone filter), GET (detail with columns), PATCH, DELETE |
| `routes/connectors.py` | 123 | POST, GET (list), GET (detail), PATCH, DELETE |
| `routes/pipelines.py` | 152 | POST, GET (list), GET (detail), PATCH, DELETE, GET runs |
| `routes/quality.py` | 57 | POST contract, GET contracts |
| `routes/lineage.py` | 57 | POST edge, GET graph (upstream/downstream) |
| `routes/ai.py` | 31 | GET skills (3 planned: RCA, SQL, pipeline proposal) |
| `services/pipeline_executor.py` | 166 | Orchestrates extraction: connect → discover schema → extract → detect changes → emit OpenLineage |

### 3.2 Connector Framework (`engines/connectors/`) — 545 lines

| File | Lines | What It Does |
|------|-------|-------------|
| `base.py` | 159 | `PullConnector` + `CDCConnector` ABCs. Dataclasses: ColumnSchema, TableSchema, ExtractBatch, ConnectorMetrics, ConnectorConfig. OpenLineage event builder. |
| `postgres_cdc.py` | 273 | Full Postgres CDC. 30+ type mappings. Schema discovery via `information_schema`. Logical replication. Health check (verifies `wal_level=logical`). |
| `s3_file.py` | 263 | S3/MinIO file reader. CSV/JSON/Parquet. Schema inference from sample records. Incremental extraction by LastModified. Batched yields. |
| `kafka_sink.py` | 104 | Kafka producer. Topic: `nova.cdc.{source}.{table}`. Idempotent, snappy compression. Message envelope with `_nova_metadata`. PK-based message keys. |
| `registry.py` | 59 | Factory pattern. `registry.create(config)` returns the right connector class. Auto-registers Postgres + S3. |

### 3.3 Lakehouse Layer (`lakehouse/`) — 764 lines

| File | Lines | What It Does |
|------|-------|-------------|
| `writer.py` | 315 | Iceberg writer. PyIceberg catalog (when available) + Parquet fallback. `create_table()`, `write_batch()`, `evolve_schema()`. Writes to MinIO/S3. |
| `evolution.py` | 220 | Schema diff engine. Detects: add/drop column, widen/narrow type, nullable changes. Classifies as SAFE (auto-apply) or BREAKING (human review). Type widening rules: int→long→double→string, date→timestamp. `apply_safe_changes()` produces evolved schema. |
| `quarantine.py` | 229 | Contract validation. Rules: not_null, range, allowed_values, type_check. `validate_batch()` → `ValidationResult` with clean records + failures. `split_batch()` → clean + quarantine ExtractBatches. |

### 3.4 Tests — 551 lines, 25 passing

| File | Tests | What They Cover |
|------|-------|----------------|
| `conftest.py` | — | Async fixtures: SQLite test DB, table create/drop per test, httpx AsyncClient with dependency override |
| `test_api.py` | 11 | Health, project CRUD (create, list, 404), dataset with columns + zone filter, connector, pipeline with DAG, contract, lineage graph, AI skills |
| `test_evolution.py` | 7 | No changes, add column (safe), drop column (breaking), widen type (safe), narrow type (breaking), mixed changes, apply safe changes |
| `test_quarantine.py` | 7 | All clean, not_null violation, range violation, allowed_values, type_check, split batch, multiple rules on one row |

### 3.5 Frontend (`ui/web/`) — 382 lines TypeScript

| File | Lines | What It Does |
|------|-------|-------------|
| `src/lib/api.ts` | 161 | Typed API client. Interfaces for all entities. CRUD methods for projects, datasets, connectors, pipelines, lineage, AI skills. |
| `src/components/sidebar.tsx` | 55 | Navigation sidebar. 4 items (Mission Control, Catalog, Pipelines, Query). Active state. Dark theme. |
| `src/app/layout.tsx` | 27 | Root layout with fixed sidebar + main content |
| `src/app/page.tsx` | 5 | Redirects to /dashboard |
| `src/app/dashboard/page.tsx` | 45 | Status cards (pipelines, datasets, freshness). Empty state. |
| `src/app/catalog/page.tsx` | 17 | Placeholder for dataset browser |
| `src/app/pipelines/page.tsx` | 17 | Placeholder for pipeline management |
| `src/app/query/page.tsx` | 17 | Placeholder for SQL editor |
| Config files | 28 | tailwind.config.ts (Nova colors), next.config.ts, postcss.config.mjs, tsconfig.json |

### 3.6 Infrastructure & DevOps

| File | Lines | What It Does |
|------|-------|-------------|
| `compose.yml` | 207 | 12 services: Postgres 15, MinIO, Kafka 3.5 (KRaft), Neo4j 5, Temporal 1.21 + UI, Trino, Flink 1.17 (JM+TM), Keycloak 23, nova-api. All with healthchecks. |
| `apps/api/Dockerfile` | 26 | Python 3.11-slim. pip install → copy source → uvicorn. Health check via curl. |
| `Taskfile.yml` | 110 | 12 tasks: bootstrap, up, up:infra, down, down:clean, dev, fmt, lint, lint:fix, test, test:v, migrate, migrate:new, health |
| `.github/workflows/ci.yml` | 63 | 3 jobs: Python lint+test, frontend lint+build, Docker build |
| `deploy/scripts/init-postgres.sh` | 11 | Creates 3 databases: nova_metadata, nova_temporal, nova_temporal_visibility |
| `engines/trino/catalog/iceberg.properties` | 9 | Trino Iceberg catalog pointing at MinIO with REST catalog |
| `pyproject.toml` | 57 | Deps: FastAPI, SQLAlchemy async, asyncpg, Alembic, Neo4j, Pydantic, ruff, pytest. Packages: apps, engines, lakehouse, tests. |
| `.gitignore` | 34 | Python, Node, IDE, env, .pytest_cache, .ruff_cache |
| `apps/api/alembic.ini` | 35 | Alembic config for async PostgreSQL |
| `apps/api/alembic/env.py` | 65 | Async migration runner with all 9 models imported |

---

## 4. API Endpoints (27 total)

```
GET  /health

POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}
DELETE /api/v1/projects/{id}

POST   /api/v1/projects/{pid}/datasets
GET    /api/v1/projects/{pid}/datasets              ?zone=raw|staging|curated
GET    /api/v1/projects/{pid}/datasets/{id}
PATCH  /api/v1/projects/{pid}/datasets/{id}
DELETE /api/v1/projects/{pid}/datasets/{id}

POST   /api/v1/projects/{pid}/connectors
GET    /api/v1/projects/{pid}/connectors
GET    /api/v1/projects/{pid}/connectors/{id}
PATCH  /api/v1/projects/{pid}/connectors/{id}
DELETE /api/v1/projects/{pid}/connectors/{id}

POST   /api/v1/projects/{pid}/pipelines
GET    /api/v1/projects/{pid}/pipelines
GET    /api/v1/projects/{pid}/pipelines/{id}
PATCH  /api/v1/projects/{pid}/pipelines/{id}
DELETE /api/v1/projects/{pid}/pipelines/{id}
GET    /api/v1/projects/{pid}/pipelines/{id}/runs

POST   /api/v1/projects/{pid}/datasets/{did}/contracts
GET    /api/v1/projects/{pid}/datasets/{did}/contracts

POST   /api/v1/lineage/edges
GET    /api/v1/lineage/datasets/{id}

GET    /api/v1/ai/skills
```

---

## 5. Data Models (9 tables)

| Model | Columns | Key Relationships |
|-------|---------|------------------|
| **Project** | id, name (unique), description, created_at, updated_at | → datasets, connectors, pipelines |
| **Dataset** | id, project_id (FK), name, description, zone (raw/staging/curated), format (iceberg), schema_version, owner, tags (JSON), table_location, freshness_slo_seconds, timestamps | → columns, contracts |
| **Column** | id, dataset_id (FK), name, data_type, nullable, description, is_pii, is_partition_key, ordinal_position, metadata (JSON) | → dataset |
| **DataContract** | id, dataset_id (FK), name, description, rules (JSON), severity (warn/error/block), enabled, created_at | → dataset |
| **Connector** | id, project_id (FK), name, connector_type (cdc/api/file), source_type, config (JSON), credentials_ref, enabled, last_sync_at, created_at | → project |
| **Pipeline** | id, project_id (FK), name, description, graph (JSON DAG), schedule (cron), status (draft→active→paused→failed→archived), created_at | → runs |
| **PipelineRun** | id, pipeline_id (FK), status (pending→running→succeeded/failed/cancelled), started_at, finished_at, temporal_workflow_id, error_message, metrics (JSON), rows_processed | → pipeline |
| **LineageEdge** | id, source_dataset_id (FK), target_dataset_id (FK), source_column, target_column, transformation_type, transformation_sql, job_name, created_at | → source dataset, target dataset |
| **QuarantineRecord** | id, dataset_id (FK), pipeline_run_id (FK), contract_id (FK), row_data (JSON), error_reason, resolved, quarantined_at | → dataset, run, contract |

---

## 6. Architecture Decisions In Effect

1. **Single API service** — not microservices. Solo dev, no benefit from splitting at MVP stage. Module boundaries (routes/, services/) are future service boundaries if needed.
2. **GUID type decorator** for UUIDs — `String(36)` that works on both SQLite (tests) and PostgreSQL (production). Auto-converts between `str` and `uuid.UUID`.
3. **JSON instead of JSONB** in models — SQLite compatible. PostgreSQL still performs well on JSON columns. Can switch to JSONB with a migration when needed.
4. **Connector framework decoupled from ORM** — Uses plain dataclasses (`ColumnSchema`, `TableSchema`, `ExtractBatch`), not SQLAlchemy models. Connectors can run in the data plane agent with zero API dependency.
5. **Schema evolution safety classification** — `diff_schemas()` returns a plan with SAFE (add column, widen type, nullable→true) and BREAKING (drop column, narrow type, nullable→false) changes. Safe changes auto-apply, breaking requires human review.
6. **Quarantine pattern** — Bad rows go to a side batch/table, pipeline continues with clean data. Contract rules validate at ingest time.
7. **Async everywhere** — Every DB call, connector, route handler is async. No synchronous blocking.
8. **Config via env vars** — Pydantic Settings, all prefixed `NOVA_`. `.env.example` not yet created.

---

## 7. What Needs to Be Built (Sprints 5–10)

### Sprint 5: Lineage Graph + Impact Analysis
- [ ] Neo4j graph client — sync lineage edges from Postgres to Neo4j
- [ ] Cypher queries for upstream/downstream traversal (multi-hop)
- [ ] Impact analysis API: "what breaks if this dataset changes?" with blast radius
- [ ] Column-level lineage enrichment
- [ ] Freshness SLO periodic check (Temporal workflow or background task)
- [ ] `GET /api/v1/lineage/datasets/{id}/impact` endpoint

### Sprint 6: AI Service — Root Cause Analysis
- [ ] AI skill registry with pluggable skill interface
- [ ] Telemetry lake: store run logs, errors, schema changes as Iceberg table (dog-fooding)
- [ ] RCA skill implementation: trace lineage → read run logs → identify failure → explain in natural language
- [ ] Claude API integration (`anthropic` SDK) with structured prompts grounded in real data
- [ ] `POST /api/v1/ai/chat` endpoint with streaming responses
- [ ] Action suggestions ("retry pipeline Y", "check source Z")

### Sprint 7: Frontend — Mission Control + Catalog
- [ ] Install Node.js (not currently on machine)
- [ ] Mission Control: pipeline status grid, freshness heatmap (real API data)
- [ ] Catalog: dataset browser with schema, lineage graph (React Flow), sample data preview
- [ ] AI chat panel: embedded chat with streaming responses from `/api/v1/ai/chat`
- [ ] All pages backed by real API calls (no mocks)

### Sprint 8: AI Skills #2+#3 + Connectors
- [ ] SQL Assistant skill: NL → Trino SQL, execute with guardrails, display results
- [ ] Pipeline Proposal skill: "I need X from Y sources" → connector + schema + workflow proposal
- [ ] S3 file connector: end-to-end (upload CSV → ingest → query in Trino)
- [ ] Salesforce connector stub (auth flow, mock responses)
- [ ] Query editor page in UI with results grid

### Sprint 9: Data Contracts + Quality + Pipeline Builder
- [ ] Data contracts YAML DSL: define in YAML, enforce at ingest
- [ ] Drift detection: statistical profiling per column per run, alert on distribution changes
- [ ] Visual pipeline builder: drag-and-drop node graph → generates Temporal workflow
- [ ] Run timeline: unified execution view with duration and status per stage
- [ ] Dataset health score (freshness + quality + success rate)

### Sprint 10: Security + Polish + Demo
- [ ] Keycloak SSO integration: login flow, JWT validation in API
- [ ] Basic RBAC: project-level isolation, dataset-level permissions
- [ ] Audit log: every API call, query, pipeline run, schema change
- [ ] UI polish: error handling, loading states, empty states, toast notifications
- [ ] End-to-end demo of 3 user stories:
  1. One-Day Pipeline: connect sources → model → query → catalog
  2. Schema Self-Healing: ALTER source → auto-evolution → no break
  3. NL Root-Cause: break pipeline → ask AI → correct answer → one-click fix

---

## 8. How to Run

```bash
# Prerequisites: Python 3.11+, Docker (for full stack), Node.js 20+ (for frontend)

# Install Python deps
cd Data-Kitchen
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

# Run tests (no Docker needed)
PYTHONPATH="$PWD/apps/api/src:$PWD" .venv/bin/python -m pytest -v

# Lint
.venv/bin/ruff check apps/ engines/ lakehouse/ tests/

# Start full stack (requires Docker)
task up

# Run API in dev mode (hot-reload, requires Postgres running)
PYTHONPATH="$PWD/apps/api/src:$PWD" .venv/bin/python -m uvicorn nova_api.app:app --reload --port 8000

# API docs
open http://localhost:8000/docs
```

---

## 9. Dependencies

**Production:** FastAPI 0.115.6, uvicorn 0.34.0, httpx 0.28.1, SQLAlchemy[asyncio] 2.0.36, asyncpg 0.30.0, Alembic 1.14.1, neo4j 5.27.0, Pydantic 2.10.4, pydantic-settings 2.7.1

**Dev:** pytest 8.3.4, pytest-asyncio 0.25.0, ruff 0.8.6, aiosqlite 0.21.0

**Optional:** boto3 (S3/MinIO), aiokafka (Kafka)

---

## 10. Environment Notes

- **Docker:** Not currently installed on dev machine. All Docker services defined but not runnable yet.
- **Node.js:** Not currently installed. Frontend skeleton exists but can't be built/run.
- **Python 3.13.7:** Installed and working. venv with all deps.
- **Tests:** Run with SQLite (via aiosqlite) — no external services needed. GUID type decorator and JSON columns ensure SQLite + Postgres compatibility.
