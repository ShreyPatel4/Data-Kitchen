# CONTEXT.md — Nova (Data-Kitchen)

> **Purpose of this:** Single-source briefing document for an LLM (Opus 4.6) to reason about project status, strategic positioning, and next-step execution for the Nova MVP. This file is self-contained — no other repo file needs to be read.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Name** | Nova |
| **Repo** | `ShreyPatel4/Data-Kitchen` |
| **Tagline** | AI-driven data platform — connect sources, model data, ship dashboards in one day |
| **Target user** | Data engineers, analytics engineers, and data-aware operators at Series A–C startups and mid-market companies (50–500 employees) who today stitch together 5–8 tools (Fivetran + dbt + Airflow + Snowflake + Monte Carlo + …) and want a single, intelligent platform |
| **Repo state (as of scaffolding)** | 4 commits, zero application code. Directory structure, Docker Compose (9 services), Taskfile, package.json, pyproject.toml, and a comprehensive README containing the full PRD |

---

## 2. Vision & Problem Statement

### The Problem

The "Modern Data Stack" (MDS) of 2020–2024 promised simplicity but delivered fragmentation. A typical company runs Fivetran (ingestion) → Snowflake/Databricks (warehouse) → dbt (transforms) → Airflow/Dagster (orchestration) → Monte Carlo (observability) → Looker/Metabase (BI). That is 5–8 vendors, 5–8 bills, and a full-time data engineer just to keep the glue working. When something breaks — a schema change upstream, a stale dashboard, a silent data quality regression — the mean time to detect is hours, the mean time to repair is days, and the root-cause analysis is a manual archaeology exercise across disconnected tools.

### The Vision

Nova is a **unified, AI-native data platform** where:

1. **Ingestion, transformation, storage, orchestration, lineage, quality, and serving all live in one system** — but built on open standards (Apache Iceberg, OpenLineage, Trino, Flink) so there is no vendor lock-in.
2. **AI is not a feature bolted on top — it is the nervous system.** The platform observes every run, every schema change, every query plan, every cost signal. It proposes pipelines from natural language, explains failures in plain English, heals itself within guardrails, and gets smarter with every resolution.
3. **Data stays in the customer's cloud account.** The control plane is managed SaaS; the data plane is an agent in the customer's VPC. This solves the #1 enterprise objection to managed data platforms: "I won't send my data to your servers."

### Why Now

- Apache Iceberg has won the table format war (Snowflake, Databricks, AWS all support it natively now). For the first time, a startup can build a lakehouse without inventing a storage format.
- LLMs crossed the threshold where they can reliably do root-cause analysis on structured telemetry (logs + lineage + schema diffs) — the core loop Nova needs for self-healing.
- The MDS fragmentation backlash is peaking. Definite, Peliqan, and others are gaining traction with "all-in-one" stories, but none combine open lakehouse + AI-native self-healing + customer-VPC data plane.

---

## 3. Core User Stories

### Story 1: One-Day Pipeline
> A data engineer connects three sources (Salesforce, Postgres, S3 files), defines a simple model, and ships a fresh dashboard **in one day** without touching cloud console screens.

### Story 2: Schema Self-Healing
> The platform detects an upstream schema change (new column added, type widened) and **keeps tables fresh** by evolving the Iceberg schema automatically and quarantining risky rows — no human intervention for additive changes.

### Story 3: Natural Language Root-Cause
> A user asks in plain English "why is the revenue dashboard stale?" and gets a **precise root cause** (e.g., "the Salesforce connector failed at 3:12 AM due to API rate limiting; 2 downstream models are blocked") with a **one-click fix** ("retry with exponential backoff and notify Salesforce admin").

---

## 4. Architecture

### Two-Plane Design

```
┌─────────────────────────────────────────────────┐
│                 CONTROL PLANE                    │
│              (Managed by Nova)                   │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ API GW + │ │ Metadata │ │  AI Service      │ │
│  │ Auth     │ │ Service  │ │  (Skills engine,  │ │
│  │ (OIDC/   │ │ (schemas,│ │   RCA, SQL gen,   │ │
│  │  SSO)    │ │  lineage,│ │   policy engine)  │ │
│  │          │ │  owners) │ │                   │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────────────────────────┐   │
│  │ Scheduler│ │ Cost & Usage Service         │   │
│  │ (Temporal│ │ (compute hrs, storage, xfer) │   │
│  │  coord.) │ │                              │   │
│  └──────────┘ └──────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │ Signed work orders (mTLS)
                       ▼
┌─────────────────────────────────────────────────┐
│              DATA PLANE                          │
│         (Customer's AWS VPC)                     │
│                                                  │
│  ┌──────┐  ┌───────┐  ┌───────┐  ┌───────────┐ │
│  │Agent │  │Kafka  │  │Flink  │  │Trino      │ │
│  │(K8s) │  │(CDC + │  │(stream│  │(SQL on    │ │
│  │      │  │buffer)│  │xform) │  │Iceberg)   │ │
│  └──────┘  └───────┘  └───────┘  └───────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ S3 Buckets: raw / staging / curated         │ │
│  │ (Apache Iceberg tables)                     │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ Connectors (containers, OpenLineage events) │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Observability & Governance (Cross-Cutting)
- OpenTelemetry for traces/logs, Prometheus for metrics, Grafana for support dashboards
- RBAC + ABAC at table and column level
- Column-level lineage and data quality scores in the catalog

---

## 5. Tech Stack — Every Choice and Why

| Layer | Technology | Why This |
|---|---|---|
| **Table format** | Apache Iceberg on S3 | Open standard, no proprietary lock-in. Snowflake/Databricks/Trino all read it natively. Schema evolution built in. |
| **Query engine (ad hoc + BI)** | Trino | Open source, federated query across catalogs, strong Iceberg support. DuckDB for small-data previews. |
| **Stream processing** | Apache Flink | Best-in-class streaming + batch unification. Iceberg sink connector. |
| **Ingestion / CDC** | Debezium + Kafka | Proven CDC for Postgres/MySQL. Kafka as ingestion buffer and event backbone. |
| **SaaS connectors** | Custom framework (pull-based for APIs, log-based for CDC) | Control over schema inference, rate limiting, OpenLineage emission. |
| **Orchestration** | Temporal | Durable workflows with built-in retry, backoff, versioning. Superior to Airflow for long-running, stateful pipelines. |
| **Lineage** | OpenLineage events → JanusGraph or Neo4j | Open standard for event emission. Graph DB for impact analysis and blast radius. |
| **Catalog** | Custom metadata service + OpenMetadata (search/glossary) | Own service is source of truth; OpenMetadata adds search, glossary, discovery UI. |
| **AI / LLM** | In-house skill engine with open model bases | Three MVP skills: pipeline design, root-cause analysis, SQL authoring. Proprietary telemetry for fine-tuning. |
| **Semantic layer** | YAML + UI editor for metrics/dimensions | Generate Trino views and materialized tables. Cube-like approach. |
| **Frontend** | React (Next.js assumed) | `ui/web` directory exists in scaffold. |
| **Backend API** | Python (FastAPI assumed) + Node.js | `pyproject.toml` + `package.json` both present. |
| **Infrastructure** | Docker Compose (local), Kubernetes (prod), Terraform (planned) | K8s operators for Trino/Flink. KEDA for autoscaling. |
| **Observability** | OpenTelemetry + Prometheus + Grafana | Industry standard. |
| **Security** | OIDC/SSO, KMS for secrets, row/column masking in Trino | Enterprise-grade from day one. |

---

## 6. Current Implementation Status

### What EXISTS (scaffolded, no application code)

| Artifact | Status | Notes |
|---|---|---|
| `README.md` | ✅ Complete | Contains the full PRD (user stories, architecture, phased plan, risks, resourcing) |
| `compose.yml` | ✅ Exists | Defines 9 Docker services for local dev |
| `Taskfile.yml` | ✅ Exists | Task runner with `bootstrap`, `up`, `test`, `down` commands (placeholder implementations) |
| `package.json` | ✅ Exists | Node.js project config (likely for UI workspace) |
| `pyproject.toml` | ✅ Exists | Python project config (likely for backend/engines) |
| `.github/workflows/` | ✅ Exists | CI/CD directory (likely empty or minimal) |
| `apps/` | ✅ Directory | Intended for application services (API gateway, metadata service, etc.) |
| `engines/` | ✅ Directory | Intended for compute engines (Trino, Flink configs/operators) |
| `lakehouse/` | ✅ Directory | Intended for Iceberg catalog, table service, compaction |
| `deploy/` | ✅ Directory | Intended for Terraform, Helm, K8s manifests |
| `docs/` | ✅ Directory | Intended for architecture docs, runbooks |
| `ui/web/` | ✅ Directory | Intended for React frontend |

### What DOES NOT EXIST (zero code written)

- Any source code in any language
- Terraform modules
- Helm charts
- CI/CD pipeline definitions (actual workflows)
- API schemas (OpenAPI, protobuf)
- Database migrations or schema definitions
- Test files
- Documentation beyond the README
- Dockerfile for any service
- Any connector implementation
- Any AI/LLM integration code

---

## 7. Directory Map

```
Data-Kitchen/
├── .github/
│   └── workflows/          # CI/CD — GitHub Actions (empty/minimal)
├── apps/                   # Application services
│   ├── api-gateway/        # (planned) API gateway + auth (OIDC/SSO)
│   ├── metadata-service/   # (planned) Datasets, schemas, lineage edges, contracts
│   ├── scheduler/          # (planned) Temporal coordinator
│   ├── ai-service/         # (planned) LLM skills engine, policy engine
│   └── cost-service/       # (planned) Compute/storage/transfer tracking
├── engines/                # Compute engine configs and operators
│   ├── trino/              # (planned) Trino K8s operator, catalogs
│   └── flink/              # (planned) Flink K8s operator, job configs
├── lakehouse/              # Storage layer
│   ├── catalog/            # (planned) Iceberg REST catalog service
│   ├── compaction/         # (planned) Small file compaction service
│   └── retention/          # (planned) Zone retention policies
├── deploy/                 # Infrastructure-as-code
│   ├── terraform/          # (planned) AWS infrastructure
│   ├── helm/               # (planned) K8s Helm charts
│   └── k8s/                # (planned) Raw manifests, KEDA configs
├── docs/                   # Documentation
│   ├── architecture/       # (planned) System design docs
│   ├── runbooks/           # (planned) Operational runbooks
│   └── api/                # (planned) API reference
├── ui/
│   └── web/                # (planned) React frontend
│       ├── src/
│       └── package.json
├── CONTEXT.md              # ← THIS FILE
├── README.md               # Full PRD
├── Taskfile.yml            # Task runner (bootstrap, up, test, down)
├── compose.yml             # Docker Compose — 9 local dev services
├── package.json            # Node.js workspace config
└── pyproject.toml          # Python project config
```

---

## 8. Local Dev Setup

### Docker Compose Services (9 total, from compose.yml)

The local development environment uses Docker Compose to spin up the core infrastructure services. Application code (when written) will run on the host or in additional containers.

**Expected services:**
1. **PostgreSQL** — metadata store, Temporal persistence
2. **Kafka** (+ Zookeeper or KRaft) — event backbone, CDC buffer
3. **Kafka Connect / Debezium** — CDC connectors
4. **Flink** (JobManager + TaskManager) — stream processing
5. **Trino** — SQL query engine on Iceberg
6. **MinIO** — S3-compatible object storage (local stand-in for AWS S3)
7. **Temporal** (server + UI) — workflow orchestration
8. **OpenMetadata** — catalog, search, glossary
9. **Redis** or similar — caching layer

### Running Locally

```bash
# Prerequisites: Docker, Node.js LTS, Python 3.11+, Task (taskfile.dev)

task bootstrap    # Install deps, pull images, generate configs
task up           # docker compose up -d (all 9 services)
task test         # Run test suite (currently empty)
task down         # docker compose down
```

> **Note:** All `task` commands are currently placeholders. The actual implementations need to be built.

---

## 9. MVP Scope & Constraints (Phase 1 — Days 1–90)

### Hard Boundaries

| Constraint | Detail |
|---|---|
| **Single cloud** | AWS `us-east-1` only. No cross-cloud. |
| **Data plane location** | Customer VPC via agent. All data stays in customer account. |
| **Table format** | Apache Iceberg on S3 exclusively. No proprietary storage. |
| **Query engine** | Trino (ad hoc + BI). Flink (streaming). Spark deferred. |
| **Orchestration** | Temporal. Not Airflow, not Dagster. |
| **Lineage standard** | OpenLineage events. Graph store (JanusGraph or Neo4j). |
| **AI assistant skills** | Exactly 3: (1) schema/pipeline proposal, (2) root-cause analysis, (3) SQL authoring. |
| **Connectors (Set 1)** | Salesforce, Google Analytics, Stripe, Postgres CDC, MySQL CDC, S3 files. |
| **BI** | Lightweight explore view + semantic layer. No full BI suite. External connection via JDBC/ODBC for Looker, Power BI, Mode. |

### Non-Goals for MVP

- No cross-cloud / multi-region
- No on-prem deployment
- No full BI suite (explore view only)
- No Spark (Flink handles batch + streaming)
- No marketplace for connectors
- No multi-tenant cost isolation (single-tenant first)

### Acceptance Criteria

1. A design partner ships 2 pipelines in 1 week with zero manual cloud setup
2. Platform handles additive schema change without breaking a dashboard
3. MTTD (mean time to detect data delay) < 5 minutes
4. MTTF (mean time to fix with suggested action) < 15 minutes

---

## 10. Phased Roadmap

### Phase 0: Discovery & Architecture (4 weeks)
- Validate 3 design partners, agree on success criteria and datasets
- Finalize reference stack and service boundaries
- Write threat model and security baseline
- Produce runbooks for top 5 failure modes
- **Deliverables:** PRD ✅, system architecture doc, data model for metadata, UX wireframes, security baseline, onboarding flow spec

### Phase 1: MVP (Days 1–90)
- **Ingestion:** 6 connectors (Salesforce, GA, Stripe, Postgres CDC, MySQL CDC, S3)
- **Lakehouse:** Iceberg catalog, table creation, partition evolution, compaction, vacuum
- **Compute:** K8s operator for agent, Temporal integration, one-click pipeline templates
- **Lineage:** OpenLineage from connectors/Flink/Trino, graph service, impact analysis
- **AI v1:** Prompt-to-pipeline, root-cause analysis, SQL assistant
- **Quality:** Column constraints, freshness SLOs, drift detection, quarantine framework
- **UX:** Mission control, visual pipeline builder, catalog page
- **Security:** SSO, project isolation, audit logs, KMS, row/column masking
- **External:** JDBC/ODBC endpoints, REST API + SDK

### Phase 2: Hardening & Scale (Months 4–9)
- Cost-based query planning, smart file sizing, self-healing v2 (policy engine), semantic layer, FinOps (per-job cost, budget alerts), field-level lineage, PII discovery, BYOK, SOC 2 kickoff

### Phase 3: Enterprise & Cross-Cloud (Months 10–18)
- Multi-region + DR, cross-cloud execution, private cloud / on-prem, partner marketplace, admin guardrails and chargeback

---

## 11. Key Design Decisions

### Decision 1: Data Plane in Customer VPC
**Why:** The #1 enterprise objection to managed data platforms is data leaving their account. By running compute and storage in the customer's VPC (with a thin agent receiving signed work orders from the control plane), Nova eliminates this objection entirely. Competitors like Fivetran, Airbyte Cloud, and Snowflake all hold customer data in their infrastructure.

### Decision 2: Iceberg-Only (No Proprietary Storage)
**Why:** Iceberg has won the open table format war. Both Snowflake and Databricks now support it natively. By going Iceberg-only, Nova guarantees zero lock-in — customers can always query their data with any Iceberg-compatible engine. This is a strong differentiator against Snowflake (proprietary format) and even Databricks (Delta Lake first, Iceberg second).

### Decision 3: Temporal over Airflow
**Why:** Airflow's DAG model is brittle for long-running, stateful data workflows. Temporal provides durable execution with built-in retry, backoff, versioning, and state management. It's a better fit for data pipelines that need to handle partial failures, schema evolution mid-run, and human-in-the-loop approvals.

### Decision 4: AI as Nervous System, Not Feature
**Why:** Every existing platform (Databricks Genie, Snowflake Cortex, Ascend.io) is bolting AI onto an existing architecture. Nova builds the telemetry lake, the feature store for anomaly detection, and the action framework from day one. The AI doesn't just generate SQL — it observes every run, learns failure patterns, proposes self-healing actions, and executes them within policy guardrails.

### Decision 5: OpenLineage for Lineage Events
**Why:** Vendor-neutral standard. Connectors, Flink, and Trino all emit OpenLineage events. The graph service (JanusGraph/Neo4j) stores them. This means lineage is not locked to any catalog vendor, and the blast-radius/impact-analysis queries can be arbitrarily complex.

---

## 12. Competitive Landscape & Strategic Positioning

### Direct Competitors (Platforms That Overlap Significantly)

| Competitor | What They Do | How Nova Differs |
|---|---|---|
| **Databricks** | Lakehouse platform (Delta Lake + Spark + Unity Catalog). Just launched "Genie Code" (Mar 2026) — autonomous AI agents for data engineering. $5.4B ARR. | Databricks is enterprise-heavy, Delta-Lake-first, and runs in their cloud. Nova is Iceberg-native, customer-VPC, and purpose-built for the self-healing loop. Nova targets the mid-market that can't afford $50K–200K/yr Databricks spend. |
| **Snowflake** | Cloud data warehouse with Cortex (AI). Proprietary storage format. Over 52% of Snowflake customers also use Databricks (convergence trend). | Proprietary lock-in. Data lives in Snowflake's infrastructure. No self-healing, no natural-language pipeline creation. Nova is the anti-Snowflake: open format, customer-owned data, AI-first. |
| **Ascend.io** | "Agentic Data Engineering Platform." AI pipeline builder, self-healing workflows, natural language queries. Recently integrated with DuckLake. | Closest competitor in vision. But Ascend is a pipeline orchestration layer that sits on top of existing warehouses (Snowflake, Databricks, BigQuery). Nova is a full-stack platform — ingestion to serving — with its own lakehouse. Less tool sprawl. |
| **Maia.ai** | "AI Data Automation platform." Claims to be industry's first. Agentic pipeline building, governance, lineage. Claims 90% reduction in manual data work. | Similar AI-first vision. Enterprise-focused, closed platform. Nova differentiates with open standards (Iceberg, OpenLineage), customer-VPC data plane, and streaming-first (Flink) architecture. |
| **Definite** | All-in-one data platform for startups. 500+ connectors, AI assistant "Fi", Iceberg-based. Claims "zero to dashboards in minutes." | Targets very small teams (< 40 people). No streaming, no self-healing, no customer-VPC option. Nova targets the next tier up (50–500 employees) that needs real-time data and enterprise security. |
| **Mage.ai** | Open-source data pipeline framework with AI-driven self-healing (Mage Pro). | Pipeline tool only, not a full platform. No lakehouse, no catalog, no lineage graph, no semantic layer. Nova is the integrated platform that Mage users would graduate into. |
| **Mozart Data** | YC-backed all-in-one data pipeline (ingest + transform + warehouse). | Small-team focused, sits on Snowflake. No AI self-healing, no streaming, no customer-VPC. Stagnating in the market. |
| **Y42** | DataOps orchestration on BigQuery/Snowflake. Pivoted to orchestration (2023). | Depends on external warehouse. No AI-native capabilities. Limited traction. |
| **Peliqan** | Unified cloud-native data platform (ELT + warehouse + analytics + activation). 250+ connectors, AI SQL assistant. | All-in-one story but no streaming, no self-healing, no customer-VPC. Smaller scale ambition. |
| **Autonmis** | "Autonomous Data Workspace." NL-to-SQL/Python/ETL. "Ask once, automate forever." | Newer entrant, similar autonomous vision. Less clear on open standards and enterprise security. Watch closely. |

### Adjacent / Partial Competitors

| Category | Players | Nova's Angle |
|---|---|---|
| **Ingestion only** | Fivetran, Airbyte, Hevo | Nova includes ingestion as one layer. Airbyte (open source) could be leveraged or competed with. |
| **Orchestration only** | Airflow, Dagster, Prefect | Nova uses Temporal. These are point solutions; Nova is integrated. |
| **Observability only** | Monte Carlo, Ataccama, Acceldata | Nova builds observability into the platform (OpenLineage + quality contracts). |
| **Catalog only** | Atlan, Alation, OpenMetadata | Nova embeds OpenMetadata and builds its own metadata service. |
| **Semantic layer only** | Cube, Looker, AtScale | Nova includes a lightweight semantic layer (YAML-defined metrics). |
| **Enterprise giants** | Oracle AI Data Platform, Microsoft Fabric, Google BigQuery | Too expensive, too complex, too locked-in for mid-market. Nova is the nimble alternative. |

### The White Space: Where Nobody Has Solved the Problem

After extensive market research (March 2026), the gap Nova can own is:

**An AI-native, open-lakehouse platform where AI is the data engineer — not an assistant to one.**

Here is what that means concretely:

1. **No one has built "data plane in customer VPC" + "AI-native self-healing" + "open Iceberg lakehouse" as a single product.** Databricks has the lakehouse but not customer-VPC as default. Ascend has the AI but sits on others' warehouses. Definite has the simplicity but no streaming or self-healing.

2. **The "agentic data engineering" space (Ascend, Maia, Databricks Genie Code) is 3–6 months old.** It is wide open. But every incumbent is bolting agents onto existing architecture. Nova can be purpose-built for agents from the ground up — the telemetry lake, the action framework, the policy guardrails, the human-in-the-loop → full-autonomy graduation path.

3. **The mid-market ($5K–$25K/mo data spend) is underserved.** Databricks/Snowflake are too expensive ($50K–200K/yr). The fragmented MDS (Fivetran+dbt+Airflow+Monte Carlo) costs $5K–25K/mo in tool sprawl alone. Definite/Mozart are too simple for teams that need real-time data and enterprise security. Nova fits the gap: real platform, real AI, affordable, open.

---

## 13. Strategic Differentiation: Making Nova "AI-Intensive" (Not Just AI-Enabled)

> This section addresses the core strategic directive: "integrate AI in the roots — making it a DATA AI INTENSIVE TOOL, not just an AI-enabled project."

### The Difference Between AI-Enabled and AI-Intensive

| AI-Enabled (what competitors do) | AI-Intensive (what Nova should be) |
|---|---|
| Chatbot that generates SQL | AI that observes every query, learns access patterns, and pre-materializes views before users ask |
| "Ask a question about your data" | AI that proactively tells you "your revenue metric drifted 12% — here's why and here's the fix" |
| Schema inference on ingest | AI that understands the semantic meaning of columns across sources and auto-maps them |
| Retry with backoff on failure | AI that diagnoses root cause, simulates blast radius, proposes a remediation plan, and executes it within policy guardrails |
| Dashboard builder | AI that generates the dashboard you need based on your role, your past queries, and your team's OKRs |

### Concrete AI-Intensive Features for Nova MVP

#### A. The Telemetry Brain (Foundation Layer)
Every action in Nova feeds a **telemetry lake**: connector runs, query plans, schema changes, data volumes, error logs, user interactions, lineage events, cost signals. This is not just for observability — it is the training data for Nova's AI. No competitor captures this breadth because they only see one slice (Fivetran sees ingestion, Monte Carlo sees quality, Airflow sees scheduling).

#### B. Autonomous Pipeline Synthesis
User says: "I need daily revenue by product from Salesforce and Stripe, joined with web traffic from Google Analytics."
Nova does not just suggest SQL. It:
1. Identifies the 3 source connectors needed
2. Proposes an Iceberg schema for the curated table
3. Generates the Flink streaming job OR batch Temporal workflow
4. Wires up OpenLineage events
5. Sets default freshness SLOs and quality contracts
6. Creates the semantic layer metrics
7. Deploys the entire pipeline with one approval click

#### C. Self-Healing with Learning Loop
When a pipeline fails:
1. **Detect** — statistical baseline says this dataset should refresh by 6 AM; it is 6:05 AM → alert
2. **Diagnose** — AI traces the lineage graph, reads error logs, identifies root cause (e.g., Salesforce API rate limit hit at 3:12 AM)
3. **Simulate** — blast radius analysis: 2 downstream models, 1 dashboard, 3 Slack alerts affected
4. **Propose** — "Retry with exponential backoff in 15 min. If still failing, switch to cached snapshot from 11 PM and alert data team."
5. **Execute** — within policy guardrails (human-in-the-loop for first N incidents, then auto-approve for known patterns)
6. **Learn** — store the incident, the resolution, and the outcome. Next time this pattern appears, skip to step 5.

#### D. Semantic Understanding Layer
Nova does not just store schemas — it understands what columns mean. Using embeddings over column names, descriptions, sample values, and usage patterns, Nova can:
- Auto-map `revenue` from Salesforce to `amount` from Stripe
- Detect when two teams define "active user" differently and flag the conflict
- Suggest joins across curated tables that no human has thought of
- Power the SQL assistant with genuine semantic context, not just table names

#### E. Cost Intelligence Agent
Nova's AI watches compute costs in real-time and acts:
- "This Trino query scans 50GB but only needs 2GB if you partition by date — want me to add the partition?"
- "Your Flink job is over-provisioned; I can save $400/mo by right-sizing"
- "This materialized view is queried 200x/day but refreshed 1x/day — let me add an hourly refresh"

#### F. Progressive Autonomy Model
This is the key architectural insight: Nova's AI starts in "suggest mode" (human approves every action). As trust builds through successful resolutions, the AI graduates to "auto-approve within guardrails" for known patterns. Each customer's Nova instance learns their specific patterns, failure modes, and preferences. This is NOT a one-size-fits-all model — it is a per-tenant, continuously-learning system.

---

## 14. What Needs to Be Built Next — Prioritized MVP Execution Plan

### Priority 0: Foundation (Week 1–2)
> Without these, nothing else works.

1. **Docker Compose: make it actually work**
   - Verify all 9 services start and are healthy
   - Add healthchecks, proper networking, volume mounts
   - MinIO bucket initialization (raw, staging, curated)

2. **Project scaffolding: actual code structure**
   - `apps/api-gateway/` — FastAPI skeleton with auth middleware stub
   - `apps/metadata-service/` — FastAPI + SQLAlchemy + Postgres schema
   - `apps/ai-service/` — FastAPI skeleton with skill registry
   - `ui/web/` — Next.js or Vite+React skeleton with routing

3. **CI/CD baseline**
   - GitHub Actions: lint, type-check, unit test for Python + Node
   - Docker build + push for each service

### Priority 1: Data Path (Week 2–5)
> The minimum path from source to queryable table.

4. **Iceberg catalog service** (`lakehouse/catalog/`)
   - REST API for table creation, schema evolution
   - Backed by Postgres metadata + MinIO/S3 storage
   - Integration with Trino catalog

5. **First connector: Postgres CDC**
   - Debezium → Kafka → Iceberg writer
   - Schema inference, OpenLineage event emission
   - This proves the end-to-end data path

6. **Trino integration**
   - Configure Trino to read Iceberg tables from the catalog
   - JDBC/ODBC endpoint for external BI tools

7. **Temporal integration**
   - Basic pipeline workflow: trigger connector → wait for completion → update metadata
   - Retry and backoff policies

### Priority 2: Metadata & Lineage (Week 4–7)
> The intelligence layer that AI depends on.

8. **Metadata service: core schema**
   - Datasets, columns, owners, tags, contracts, SLOs
   - Lineage edges (source → transform → output)
   - REST API for CRUD

9. **OpenLineage ingestion**
   - Consume events from connectors, Flink, Trino
   - Store in graph DB (start with Postgres + adjacency list; graduate to Neo4j)

10. **Lineage API + impact analysis**
    - "What depends on this table?" — upstream and downstream traversal
    - Blast radius calculation

### Priority 3: AI v1 (Week 6–9)
> The differentiator.

11. **Telemetry lake setup**
    - Structured storage for: run logs, query plans, schema changes, error events, cost signals
    - Iceberg table in the curated zone (dog-fooding the platform)

12. **Skill 1: Root-cause analysis**
    - Input: "why is dataset X stale?"
    - Process: query lineage graph, read recent run logs, identify failure point
    - Output: natural language explanation + suggested action
    - This is the highest-impact AI feature and the most provable.

13. **Skill 2: SQL assistant**
    - Input: natural language question about curated tables
    - Process: read schema + semantic metadata, generate Trino SQL
    - Output: executable query with guardrails (row limits, cost estimates)

14. **Skill 3: Pipeline proposal**
    - Input: "I need [description of desired output] from [sources]"
    - Process: identify connectors, propose schema, generate workflow definition
    - Output: draft pipeline for human review

### Priority 4: UX (Week 5–9, parallel)
> The user's window into everything.

15. **Mission control page**
    - Pipeline status grid (running, succeeded, failed, stale)
    - Freshness heatmap for key datasets
    - AI-suggested actions with one-click execution

16. **Catalog page**
    - Dataset browser with schema, owners, contracts, lineage
    - Sample data preview
    - Search (powered by OpenMetadata or custom)

17. **Visual pipeline builder**
    - Node graph: source → transform → model → output
    - Drag-and-drop with code-behind for power users

### Priority 5: Quality & Contracts (Week 7–10)

18. **Data contracts DSL**
    - Column constraints (type, nullability, range, allowed values)
    - Freshness SLOs ("this table must refresh by 6 AM daily")
    - Defined in YAML, enforced at ingest and transform time

19. **Quarantine framework**
    - Failed rows route to a side table with error metadata
    - Pipeline continues with clean rows
    - Dashboard shows quarantine stats

20. **Drift detection**
    - Statistical profiling per column per run
    - Alert on significant distribution changes

### Priority 6: Security & External Access (Week 8–10)

21. **SSO integration** (OIDC/SAML)
22. **RBAC** at project and dataset level
23. **Row/column masking** in Trino
24. **Audit log** for every query, job, schema change
25. **JDBC/ODBC endpoints** verified with Looker, Power BI, Mode

---

## 15. Resourcing Plan (from PRD)

**Team of 12 for 90 days:**

| Role | Count | Focus |
|---|---|---|
| Connectors & Ingestion | 2 | Connector framework, Set 1 connectors, CDC |
| Lakehouse & Storage | 2 | Iceberg catalog, compaction, retention, zones |
| Compute & Orchestration | 2 | K8s operators, Temporal workflows, autoscaling |
| Metadata, Catalog & Lineage | 2 | Metadata service, OpenLineage, graph service, search |
| AI & Automation | 2 | Telemetry lake, 3 skills, action framework, policy engine |
| Security & SRE | 1 | SSO, RBAC, masking, audit, deployment, monitoring |
| Product & Design | 1 | UX design, user research, design partner management |

---

## 16. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Integration complexity grows fast | High | Strict scope on connectors. Reusable connector framework with schema inference, rate limiting, OpenLineage built in. |
| Self-healing causes harm if wrong | High | Human-in-the-loop for all actions in Phase 1. Progressive autonomy with audit trail and easy rollback. |
| Trino + Flink cost for multi-tenant | Medium | Aggressive autoscaling with KEDA. DuckDB for small-data previews. Resource classes (S/M/L). |
| Data residency / privacy | Medium | Data plane in customer VPC. BYOK encryption. Retention controls. |
| Competing with Databricks' $5.4B war chest | High | Don't compete on the same axis. Win on simplicity, openness, mid-market pricing, and AI-native self-healing. Be the "Vercel of data" — opinionated, fast, developer-loved. |
| AI hallucination in root-cause analysis | Medium | Ground all AI responses in lineage graph data and run logs. Never hallucinate — say "I don't know" with confidence. Cite specific events and timestamps. |

---

## 17. Success Metrics

| Metric | Target |
|---|---|
| Time from first login to first dashboard | < 1 day |
| 90th percentile pipeline build time (new source + model) | < 1 week |
| Mean time to detect issues (MTTD) | < 5 minutes |
| Mean time to repair with AI assistant (MTTR) | < 15 minutes |
| Common incidents resolved by platform (with user approval) | ≥ 50% in Phase 1 |
| Customer NPS for builder experience | > 40 |

---

## 18. Proof of Concept Plan (Design Partner — 60 Days)

| Days | Milestone |
|---|---|
| 1–7 | Discovery: secure setup in partner's AWS account |
| 8–21 | Ingest 3 sources → deliver 2 curated tables with basic metrics |
| 22–42 | Enable lineage view, freshness alerts, quarantine |
| 43–60 | Deliver AI assistant flow: root-cause for staleness, one-click fixes |

**Exit criteria:** Daily dashboard is fresh, additive schema changes don't break delivery, 2+ incidents handled by the platform without on-call.

---

## 19. Pricing Idea (from PRD)

- Base platform fee per project + usage (compute hours + storage managed)
- Credits covering Trino/Flink compute and connector throughput
- Design partner discounts + annual term discounts
- Target mid-market: $5K–$25K/month total platform cost (vs. $25K–$200K for Databricks/Snowflake stack equivalents)
