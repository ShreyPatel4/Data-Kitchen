# Nova (Data-Kitchen) — Build Progress

> **Last updated:** 2026-03-15
> **Current state:** Sprints 1-4 complete. 25 tests passing, lint clean.

---

## Completed Sprints

### Sprint 1: "Bootable Platform" — DONE
- Docker Compose with 12 services (Postgres, MinIO, Kafka, Neo4j, Temporal+UI, Trino, Flink, Keycloak, nova-api)
- All services have healthchecks and proper dependency ordering
- MinIO auto-creates buckets (raw, staging, curated, warehouse)
- Postgres auto-creates databases via init script
- Python venv with all deps installed, ruff linter, pytest
- Next.js frontend skeleton (4 pages, sidebar, typed API client)
- GitHub Actions CI (lint, test, Docker build)
- Taskfile with real commands (bootstrap, up, down, dev, fmt, lint, test, migrate, health)

### Sprint 2: "Metadata Backbone" — DONE
- **9 SQLAlchemy models**: Project, Dataset, Column, DataContract, Connector, Pipeline, PipelineRun, LineageEdge, QuarantineRecord
- All models use UUID PKs, proper FKs with CASCADE, indexes, unique constraints
- **Pydantic v2 schemas** with validation for all models (Create, Update, Response variants)
- **Full CRUD API** (7 routers, 25+ endpoints):
  - Projects: create, list, get, update, delete
  - Datasets: create, list (with zone filter), get (with columns), update, delete
  - Connectors: create, list, get, update, delete
  - Pipelines: create, list, get, update, delete, list runs
  - Data Contracts: create, list
  - Lineage: create edge, get graph (upstream/downstream)
  - AI Skills: list planned skills
- Alembic migration infrastructure (ready for `alembic revision --autogenerate`)
- Config via Pydantic Settings (all env vars prefixed NOVA_)

### Sprint 3: "First Data Flows" — DONE
- **Connector framework** (`engines/connectors/`):
  - `PullConnector` base class for APIs/files
  - `CDCConnector` base class for databases
  - Data types: ColumnSchema, TableSchema, ExtractBatch, ConnectorMetrics, ConnectorConfig
  - OpenLineage event emission built into base class
- **Postgres CDC connector**: schema discovery (30+ type mappings), logical replication, health check
- **S3 file connector**: CSV/JSON/Parquet support, schema inference, incremental extraction
- **Kafka sink**: topic naming convention, idempotent producer, message envelopes with metadata
- **Connector registry**: factory pattern, auto-registers built-in connectors
- **Iceberg writer** (`lakehouse/writer.py`):
  - PyIceberg integration (when available)
  - Parquet fallback for MVP
  - Schema evolution support
  - Write batches to MinIO/S3
- **Pipeline executor service**: orchestrates connector → extract → validate → write → metadata
- **Trino catalog config**: Iceberg on MinIO via REST catalog

### Sprint 4: "Schema Evolution + Self-Healing" — DONE
- **Schema evolution** (`lakehouse/evolution.py`):
  - Diff detection: add column, drop column, widen type, narrow type, nullable changes
  - Safety classification: safe (auto-apply) vs breaking (human review)
  - Type widening rules: int→long→double→string, date→timestamp, etc.
  - Apply safe changes to produce evolved schema
- **Quarantine framework** (`lakehouse/quarantine.py`):
  - Contract rules: not_null, range, allowed_values, type_check
  - Batch validation: check all rows against all rules
  - Split batch into clean + quarantine batches
  - Validation failures include row data, rule name, column, reason
- **7 schema evolution tests** (no changes, add column, drop column, widen, narrow, mixed, apply)
- **7 quarantine tests** (clean, not_null, range, allowed_values, type_check, split, multiple rules)

---

## File Inventory

### Application Code
| Path | Lines | Purpose |
|------|-------|---------|
| `apps/api/src/nova_api/config.py` | 46 | Pydantic Settings config |
| `apps/api/src/nova_api/database.py` | 38 | Async SQLAlchemy engine + session |
| `apps/api/src/nova_api/models.py` | ~320 | 9 SQLAlchemy models with enums, indexes |
| `apps/api/src/nova_api/schemas.py` | ~250 | Pydantic v2 schemas (Create/Update/Response) |
| `apps/api/src/nova_api/app.py` | 60 | FastAPI factory with CORS, lifespan, routers |
| `apps/api/src/nova_api/routes/projects.py` | 65 | Full CRUD |
| `apps/api/src/nova_api/routes/datasets.py` | 130 | Full CRUD + zone filter |
| `apps/api/src/nova_api/routes/connectors.py` | 110 | Full CRUD |
| `apps/api/src/nova_api/routes/pipelines.py` | 140 | Full CRUD + runs |
| `apps/api/src/nova_api/routes/lineage.py` | 55 | Create edges, get graph |
| `apps/api/src/nova_api/routes/quality.py` | 60 | Create/list contracts |
| `apps/api/src/nova_api/routes/ai.py` | 35 | Skill registry |
| `apps/api/src/nova_api/services/pipeline_executor.py` | 130 | Pipeline orchestration + schema detection |

### Connector Framework
| Path | Lines | Purpose |
|------|-------|---------|
| `engines/connectors/base.py` | 130 | PullConnector + CDCConnector ABCs |
| `engines/connectors/postgres_cdc.py` | 225 | PostgreSQL CDC via logical replication |
| `engines/connectors/s3_file.py` | 210 | S3/MinIO file reader (CSV/JSON/Parquet) |
| `engines/connectors/kafka_sink.py` | 100 | Kafka writer with idempotent producer |
| `engines/connectors/registry.py` | 55 | Factory pattern registry |

### Lakehouse Layer
| Path | Lines | Purpose |
|------|-------|---------|
| `lakehouse/writer.py` | 260 | Iceberg table writer (PyIceberg + Parquet fallback) |
| `lakehouse/evolution.py` | 195 | Schema diff, safety classification, apply changes |
| `lakehouse/quarantine.py` | 175 | Contract validation + batch splitting |

### Infrastructure
| Path | Purpose |
|------|---------|
| `compose.yml` | 12 Docker services with healthchecks |
| `apps/api/Dockerfile` | Single API service image |
| `apps/api/alembic.ini` | Alembic config |
| `apps/api/alembic/env.py` | Async migration runner |
| `engines/trino/catalog/iceberg.properties` | Trino Iceberg catalog |
| `deploy/scripts/init-postgres.sh` | DB initialization |
| `.github/workflows/ci.yml` | CI pipeline |
| `Taskfile.yml` | Task runner with 16 commands |

### Tests (25 passing)
| Path | Tests | Coverage |
|------|-------|----------|
| `tests/test_api.py` | 11 | Health, CRUD for all entities, lineage, AI skills |
| `tests/test_evolution.py` | 7 | Schema diff detection + safe change application |
| `tests/test_quarantine.py` | 7 | Contract validation + batch splitting |

### Frontend (skeleton, needs Node.js to build)
| Path | Purpose |
|------|---------|
| `ui/web/src/app/dashboard/page.tsx` | Mission Control |
| `ui/web/src/app/catalog/page.tsx` | Dataset catalog |
| `ui/web/src/app/pipelines/page.tsx` | Pipeline management |
| `ui/web/src/app/query/page.tsx` | SQL query editor |
| `ui/web/src/components/sidebar.tsx` | Navigation sidebar |
| `ui/web/src/lib/api.ts` | Typed API client |

---

## What's Next

### Sprint 5: "Lineage Graph + Impact Analysis"
- Neo4j integration for graph lineage queries
- Column-level lineage tracking
- Impact analysis API ("what breaks if this table changes?")
- Freshness SLO definition + periodic check

### Sprint 6: "AI Service v1 — Root Cause Analysis"
- AI skill registry with pluggable skills
- Telemetry lake (run logs → Iceberg table)
- RCA skill: lineage + run logs → natural language explanation
- Claude API integration with structured prompts

### Sprint 7: "Frontend — Mission Control + Catalog"
- Real data on Mission Control page
- Catalog with schema, lineage graph (React Flow), sample data
- AI chat panel with streaming responses

### Sprint 8-10: AI Skills #2+#3, Quality, Security, Demo

---

## Architecture Decisions
1. **Single API service** (not microservices) — solo dev, no benefit from splitting
2. **GUID type decorator** for UUIDs — works with both SQLite (tests) and PostgreSQL (prod)
3. **JSON instead of JSONB** in models — SQLite compatible, PostgreSQL still fast
4. **Connector framework decoupled from ORM** — dataclasses, no DB dependency, can run in data plane
5. **Schema evolution safety classification** — safe changes auto-apply, breaking requires review
6. **Quarantine framework** — bad rows go to side table, pipeline continues with clean data
