# Nova — Project Handoff & Archive Notice

**Archived 2026-04-16.** This repo is no longer under active development. The scaffolded MVP (Sprints 1–4, ~4,200 LoC, 25 tests passing) is preserved here for reuse. If you're considering picking it up, read this file before the README.

---

## What this was

Nova (Data-Kitchen) was a solo-founder attempt at an AI-native, customer-VPC data platform targeting mid-market (50–500 employee SaaS companies). Four sprints were shipped between March and April 2026: a bootable local stack, a metadata control plane, a connector framework, and a schema-evolution + quarantine layer. Execution worked. Positioning did not.

## Why it was paused

An honest pre-customer strategic review concluded the original framing — *"AI-native auto-healing master data platform"* — was DOA for three independent reasons:

1. **Substitutive positioning vs the data-engineer tribe.** Products framed as "AI replaces the DE" (Devin, Ascend, Continual, Prophecy v1) got champion-sabotaged in evals. Products framed as copilots (Cursor, dbt, Monte Carlo) won. The DE is the buyer's trusted advisor; hostility from them is fatal in B2B data infra.
2. **All-in-one category curse.** Every integrated-platform corpse (Informatica stagnating, Talend absorbed, Onehouse struggling, Mozart stalled, Y42 pivoted, Dremio IPO pulled) points the same direction: the modern data stack won by being composable. A solo founder with 2026 runway cannot carry a 2028 master-platform story.
3. **Auto-mutation trust gap.** Enterprises in 2026 do not trust AI to irreversibly modify production warehouses. Monte Carlo's auto-apply adoption sits in single-digit percentages. The "auto-heal schema break" hero demo dazzles in a pitch and then never gets enabled in production.

A viable reposition existed (*"AI-drafted, DE-approved schema-change copilot for dbt + Iceberg teams"* — ~80% of this code reusable via verb inversion from `auto_apply` to `draft_pr`). The founder chose to stop rather than carry the reposition forward. That call stands.

---

## What works today (reusable modules)

Every module below is self-contained, tested, and written with SQLite-or-Postgres portability. Pull whichever pieces are useful.

### 1. Schema Evolution Engine — `lakehouse/evolution.py` (~220 lines)
Diff two Iceberg-style schemas. Classifies changes as **safe** (add column, widen type, loosen nullability) or **breaking** (drop column, narrow type, tighten nullability). Applies safe changes to produce an evolved schema. Type-widening rules include `int→long→double→string`, `date→timestamp`.
- **Useful for:** anyone managing Iceberg tables, CDC sinks, schema registries, or contract-based ingestion.
- **Deps:** Python stdlib + dataclasses.
- **Tests:** `tests/test_evolution.py` (7 tests).

### 2. Quarantine Framework — `lakehouse/quarantine.py` (~230 lines)
Contract-rule validation (`not_null`, `range`, `allowed_values`, `type_check`). `validate_batch()` returns a `ValidationResult`. `split_batch()` separates clean rows from quarantine rows so pipelines keep moving.
- **Useful for:** any ingestion pipeline that needs bad-row isolation without failing the whole batch.
- **Tests:** `tests/test_quarantine.py` (7 tests).

### 3. Connector Framework — `engines/connectors/` (~545 lines)
- `base.py`: `PullConnector` and `CDCConnector` ABCs with OpenLineage event emission built in.
- `postgres_cdc.py`: Postgres CDC via logical replication, 30+ type mappings, `information_schema`-based discovery, `wal_level=logical` health check.
- `s3_file.py`: S3/MinIO reader for CSV/JSON/Parquet, schema inference, incremental extraction by `LastModified`.
- `kafka_sink.py`: Idempotent Kafka producer, snappy compression, `_nova_metadata` envelopes.
- `registry.py`: Factory pattern, auto-registers built-in connectors.

### 4. Iceberg Writer — `lakehouse/writer.py` (~315 lines)
PyIceberg catalog integration with a Parquet fallback for environments without a catalog. Supports `create_table`, `write_batch`, `evolve_schema`. Writes to MinIO or S3.

### 5. Metadata API — `apps/api/`
FastAPI monolith with async SQLAlchemy. 9 ORM models (Project, Dataset, Column, DataContract, Connector, Pipeline, PipelineRun, LineageEdge, QuarantineRecord). 27 REST endpoints, Pydantic v2 schemas, Alembic migrations. GUID type decorator makes the whole thing portable between SQLite (tests) and Postgres (prod).

### 6. Local Dev Stack — `compose.yml`
12 Docker services with healthchecks: Postgres 15, MinIO, Kafka 3.5 (KRaft), Neo4j 5, Temporal 1.21 + UI, Trino, Flink 1.17 (JM+TM), Keycloak 23, nova-api. Good reference for anyone spinning up a local lakehouse.

---

## How to run

```bash
# Prerequisites: Python 3.11+, Docker, Node.js 20+ (for frontend)
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

# Run tests (no Docker needed — uses aiosqlite)
PYTHONPATH="$PWD/apps/api/src:$PWD" .venv/bin/python -m pytest -v

# Full stack
task up            # all 12 services
task down          # shut down
```

API docs at `http://localhost:8000/docs` once the API is running.

---

## If you want to resume

### Viable Direction A — DE Copilot
Reposition as *"Nova: AI drafts schema-change PRs for data engineers to review."* DE is the hero. Sell alongside dbt + Snowflake/Databricks, never against them. Invert the engine verbs: `auto_apply` → `draft_pr` as default, auto-apply becomes an opt-in Tier 3 feature that's off by default and never leads the pitch. Target NSM: DE-hours-saved-per-week-per-seat. ~80% of this codebase is directly reusable.

### Viable Direction B — Narrow OSS Tool
Extract `lakehouse/evolution.py` as a standalone pip library for Iceberg users. No business, just a useful artifact with a real audience. Could pair with `lakehouse/quarantine.py` as a two-module library for contract-aware Iceberg ingestion.

### Dead-End Direction — Original Master-Platform Vision
*"AI-native auto-healing all-in-one data platform that replaces the modern data stack."* Don't. Market history and 2026 trust levels make this DOA. If you believe the vision is real, the earliest honest window is ~2028, earned via copilot trust capital — not a 2026 wedge.

---

## Strategic lesson (the part worth keeping)

The best code in this repo is the schema-evolution engine. The worst decision in this repo was positioning the platform as a data-engineer replacement.

In B2B data infrastructure: **build with the incumbent tribe, never against it.** Fivetran made DEs more productive; dbt promoted them to analytics engineers; Monte Carlo gave them an alerting layer they could claim credit for. Every tool that tried to replace the tribe died or pivoted. The AI era does not change this — it amplifies it, because trust is the bottleneck and the tribe is the trust graph.

If you take one thing from this archive, take that.

---

## License & reuse

Public repo. Reuse freely under the repo's existing license terms. No warranty, no support, no active maintenance. If you build something interesting from these pieces, the author would be glad to hear about it — but there is no obligation.
