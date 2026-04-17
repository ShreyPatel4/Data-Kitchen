# Nova (Data-Kitchen)

> **Archived 2026-04-16.** No longer under active development.
> See [`HANDOFF.md`](./HANDOFF.md) for reusable modules, how to run, and notes for anyone considering a resume.

Nova was a solo-founder MVP attempt at an AI-native, customer-VPC data platform for mid-market SaaS companies. Four sprints shipped between March and April 2026 before the project was paused after honest pre-customer strategic review.

## What's in this repo

| Area | Status | Path |
|---|---|---|
| Schema evolution engine (diff + safety classification) | Shipped, tested | `lakehouse/evolution.py` |
| Quarantine framework (contract validation + batch split) | Shipped, tested | `lakehouse/quarantine.py` |
| Connector framework (Postgres CDC, S3, Kafka sink) | Shipped | `engines/connectors/` |
| Iceberg writer (PyIceberg + Parquet fallback) | Shipped | `lakehouse/writer.py` |
| Metadata API (FastAPI, 9 models, 27 endpoints) | Shipped | `apps/api/` |
| Local dev stack (12 Docker services with healthchecks) | Shipped | `compose.yml` |
| Lineage graph, AI service, frontend pages | Not built | — |

Total: ~4,200 LoC, 25 tests passing.

## Quickstart

```sh
# Prerequisites: Python 3.11+, Docker, Node.js 20+ (for frontend)
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

# Run tests (no Docker needed — uses aiosqlite)
PYTHONPATH="$PWD/apps/api/src:$PWD" .venv/bin/python -m pytest -v

# Full local stack
task up
task down
```

API docs at `http://localhost:8000/docs` once the stack is up.

## Why it stopped

Original positioning — *"AI-native auto-healing master data platform"* — was DOA after honest review. Three independent reasons:

1. **Substitutive framing kills B2B data infra products.** The data engineer is the buyer's trusted advisor; positioning the product as their replacement guarantees champion sabotage in evals.
2. **The all-in-one category is a graveyard.** Informatica stagnated, Talend was absorbed, Onehouse is struggling, Mozart stalled, Y42 pivoted, Dremio pulled its IPO. The modern data stack won by being composable.
3. **Auto-mutation of production warehouses doesn't sell in 2026.** Trust isn't there. Hero demo, not a turned-on feature.

A viable copilot reposition existed (~80% of this code reusable). The founder chose to stop rather than carry the reposition forward. See [`HANDOFF.md`](./HANDOFF.md) for the full strategic note and resume directions.

## Strategic lesson

In B2B data infrastructure: **build with the data-engineer tribe, never against it.** Fivetran made DEs more productive, dbt promoted them to analytics engineers, Monte Carlo gave them an alerting layer. Every tool that tried to replace the tribe died or pivoted. The AI era amplifies this rule rather than reversing it.

## Reuse

Public repo. Reuse modules freely under the existing license. No warranty, no support, no active maintenance. The schema-evolution engine and quarantine framework are the two pieces most likely to be useful standalone — both are self-contained and tested.

For the original product vision and architecture context: `CONTEXT.md` and `PROGRESS.md` capture the snapshot at archival time. Earlier git history (`git log eb914ad`) has the original PRD as it stood before archival.
