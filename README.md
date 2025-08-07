# Nova

Minimal scaffold for the AI-driven data platform MVP.

## Quickstart

Prerequisites: Docker, Node.js LTS, Python 3.11, and [Task](https://taskfile.dev).

```sh
# bootstrap environment (placeholder)
task bootstrap

# start local stack
task up

# run tests
task test

# stop stack
task down
```



MVP definition

Primary user stories

A data engineer connects three sources, defines a simple model, and ships a fresh dashboard in one day without touching cloud console screens.

The platform detects a schema change and keeps tables fresh by evolving the table and quarantining risky rows.

The user asks in plain English why a dashboard is stale and gets a precise root cause with a one click fix.

Hard constraints for MVP

One cloud region at first. Use AWS us east one to start.

Data plane runs in the customer account using an agent. Control plane is managed by us.

Table format is Apache Iceberg on S3. No proprietary storage.

Query engine is Trino for ad hoc and BI. Stream processing is Flink. Batch transforms can use Flink or Spark later.

Orchestration uses Temporal for durable workflows.

Lineage uses OpenLineage events and a graph store.

Catalog uses a simple metadata service plus an embedded OpenMetadata for search and glossary.

AI assistant ships with three skills: schema proposal, root cause analysis for late data, and basic SQL authoring.

Non goals for MVP

No cross cloud at day one.

No on prem at day one.

No full BI suite. Provide a lightweight explore view and a semantic layer. Allow connection from Looker, Power BI, and Mode.

Architecture at a glance

Control plane

API gateway and auth service with OIDC and SSO.

Metadata service that stores datasets, schemas, owners, tags, contracts, and lineage edges.

Scheduler and run coordinator built on Temporal, with queues and priorities.

AI service that hosts models and automation policies.

Cost and usage service that tracks compute time, storage, data transfer, and credits.

Data plane in customer VPC

Agent that receives signed work orders from the control plane and executes on Kubernetes.

Connectors for sources and sinks that run as containers and emit OpenLineage events.

Kafka for ingestion buffers and change data capture.

Flink for streaming transforms and materialized views.

Trino for SQL queries, with catalogs on Iceberg tables in S3.

Object storage buckets for raw, staging, and curated zones using Iceberg.

Optional Spark on Kubernetes for heavy batch transforms in later phases.

Observability and governance

OpenTelemetry for traces and logs, Prometheus for metrics, Grafana for support dashboards.

Role based access control and attribute based policies at table and column level.

Column level lineage and data quality scores shown in the catalog.

Build versus buy choices

Use and contribute to Apache Iceberg for table format and schema evolution.

Use Trino for SQL, with optional DuckDB for small data previews.

Use Flink for streaming. Use Kafka plus Debezium for CDC.

Use Temporal for orchestration and durable retries.

Use OpenLineage for lineage events and build a graph service on top of JanusGraph or Neo4j.

Use OpenMetadata for glossary and search. Keep our own metadata service as the source of truth.

Build the AI and automation layer in house with open model bases and proprietary telemetry.

Phased delivery plan

Phase zero discovery and architecture, four weeks

Validate three design partners and agree on success criteria and data sets.

Finalize reference stack and service boundaries.

Write threat model and security baseline.

Produce runbooks for top five failure modes and the first self healing policies.

Deliverables: PRD, system architecture doc, data model for metadata, UX wireframes, security and privacy baseline, onboarding flow spec, program plan.

Phase one MVP, days one to ninety

Ingestion

Build SaaS connectors for Salesforce, Google Analytics, Stripe.

Build database connectors using Debezium for Postgres and MySQL CDC.

Build file ingest for S3 and GCS with schema inference.

Lakehouse

Ship Iceberg catalog and table creation, partition evolution, compaction, and vacuum.

Implement raw, staging, curated databases and retention policies.

Compute and orchestration

Stand up Kubernetes operator for the agent and a minimal control loop.

Integrate Temporal for data flows, retries, and backoff.

Provide one click pipelines for batch and streaming templates.

Lineage and metadata

Emit OpenLineage from connectors and Flink and Trino.

Build lineage graph service and impact analysis view.

Index schemas and descriptions in the catalog, support search and ownership.

AI assistant v1

Prompt to pipeline flow. User describes sources and outputs. System proposes a draft plan and creates a runnable pipeline with placeholders for secrets.

Root cause analysis for stale dataset using lineage and run history. Produce a natural language answer and one click actions.

SQL assistant for joins across curated tables with guardrails.

Data contracts and quality

Allow users to define column constraints and freshness SLOs.

Add automatic profile and drift detection per dataset.

Quarantine framework that routes failed rows to a side table and continues the pipeline.

UX

Home mission control view with pipeline status, freshness, and suggested fixes.

Visual pipeline builder with nodes for source, transform, model, output.

Catalog page with schema, contracts, owners, lineage, sample data.

Security and tenancy

SSO, project level isolation, audit logs, secret storage with KMS.

Row and column masking policies enforced in Trino.

External access

JDBC and ODBC endpoints for BI tools.

REST API and SDK for automation.

Acceptance criteria

A design partner ships two pipelines in one week with zero manual cloud setup.

Platform handles an additive schema change without a broken dashboard.

Mean time to detect data delay is under five minutes and mean time to fix with suggested action is under fifteen minutes.

Phase two hardening and scale, months four to nine

Performance

Cost based query planning with Iceberg metadata.

Smart file sizing and clustering. Automatic compaction policies.

Self healing v2

Policy engine for automated actions with guardrails and audits.

Adaptive retries and dynamic resource scaling based on live metrics.

Semantic layer

Central metric and dimension definitions with versioning and tests.

Materialized views and cache for common metrics.

Cost and FinOps

Per job and per user cost breakdown, anomaly detection, budget alerts.

Advisor that suggests partition keys, z ordering analogs, or data skipping to cut cost.

Security and compliance

Field level lineage and PII discovery.

Bring your own key encryption, retention controls, data residency controls.

SOC 2 program kickoff.

Phase three enterprise and cross cloud, months ten to eighteen

Multi region and disaster recovery.

Cross cloud execution with best execution venue and minimal egress.

Private cloud and on prem install with a controller that mirrors the managed control plane.

Partner marketplace for connectors and blueprints.

Admin guardrails and chargeback inside large customers.

Workstreams and detailed tasks

A. Connectors

Build a connector framework with a pull based abstraction for APIs and a log based abstraction for CDC.

Shipping set one: Salesforce, Google Analytics, Stripe, Postgres CDC, MySQL CDC, S3 files.

Shipping set two: Snowflake reader, BigQuery reader, Ads APIs, Shopify, NetSuite, Jira.

Each connector must provide schema inference, type hints, column descriptions, sampling, and rate control.

Connectors publish lineage, data volumes, latency, and error codes.

B. Lakehouse and storage management

Iceberg catalog and table service with REST API.

Schema evolution handler that can add columns, widen types, and stage breaking changes for review.

Small file compaction and clustering service with automatic policies.

Retention rules for raw and staging zones with safe delete and time travel for curated.

C. Compute engines and autoscaling

Kubernetes operators for Trino and Flink.

Autoscaling with KEDA and queue depth signals.

Resource classes for small, medium, large. Later, predictive warm pools for peak times.

Workload isolation per project and per user.

D. Orchestration and workflow

Temporal application for pipeline graphs. Each node is a durable activity. Each run captures inputs, outputs, logs, and lineage IDs.

Dependency engine that understands dataset readiness and event triggers.

Schedule editor with calendars, windows, and catch up policies.

E. Metadata, catalog, and lineage graph

Metadata schema that covers datasets, columns, owners, contracts, SLOs, lineage edges, and incidents.

Graph service with impact analysis and blast radius view.

Search service with ranking based on usage, recency, and endorsements.

F. AI and automation engine

Telemetry lake that stores runs, query plans, errors, volumes, skews.

Feature store for models that power anomaly and drift detection.

Skills

Design assistant that turns a prompt into a pipeline and a schema draft.

Root cause analysis that uses lineage plus logs to explain staleness or failure.

Optimizer that suggests partitioning, clustering, materialization, or rewrite.

Action framework

Quarantine bad records and continue.

Change compute size for a single run.

Backfill a window after a fix.

Switch to a fallback source when primary is delayed.

Policy controls with human in the loop until trust is proven. Then allow auto apply within budgets.

G. Observability and cost

Unified run timeline with spans for ingest, transform, and serve.

Dataset freshness heatmap with SLO tracking and alerts.

Cost by job and by dataset. Budgets and alerts with suggested savings.

H. Semantic layer and basic explore

YAML and UI editor for metrics and dimensions. Tests and documentation side by side.

Generate Trino views and materialized tables. Cache common joins.

Explore UI for quick slice and dice, export to CSV, and embed.

I. Security, privacy, and compliance

SSO with SAML and OIDC. Role based access control and attribute based access control.

Encryption at rest and in flight. Bring your own key.

Row and column masking rules and tokenization for sensitive fields.

Full audit trail for every query, job, and change.

Data residency and deletion controls.

J. Cross cloud and on prem enablement

Control plane that is portable across clouds. Data plane that runs in customer VPC with a small agent.

Pluggable storage backends for S3, GCS, Azure Blob, and HDFS.

Minimal mode for air gapped environments with periodic license checks.

K. Developer experience

CLI and SDK with local dev and unit test harness for pipelines.

Git based versioning of pipelines and contracts. CI checks for tests and policies.

Notebook experience for SQL and Python with data previews and lineage context.

Self healing design

Event types the system watches

Schedule miss or long running tasks.

Upstream data delay or volume drift.

Schema changes, both additive and breaking.

Data quality contract violations.

Cost spikes and skewed partitions.

Detection

Statistical baselines per pipeline and per dataset.

Rules for SLOs and contracts.

Decision and action

Map event type to a catalog of playbooks.

Simulate blast radius and present user with a plan and a preview diff.

Execute, monitor, and roll back if needed.

Learning loop

Capture outcomes and user feedback to tune future suggestions.

Data contracts and schema evolution

Contract language with column types, nullability, ranges, allowed values, and reference integrity.

Producer and consumer handshake with alerts and staging areas for breaking changes.

Auto evolution for additive changes and a review queue for shrinking or type changes.

Real time monitoring and AI Ops

Health model that rolls up dataset freshness, pipeline success rate, and incident count into a simple score.

Change feed that explains what changed in the last day and why it matters.

Suggested actions sorted by impact and cost.

Deployment model and SRE

Control plane runs in our cloud with multi tenant isolation.

Data plane runs in customer VPC with a thin agent. All data stays in the customer account.

Blue green deploys and canary for engines and connectors.

Error budgets and SLOs for the service itself.

Pricing and packaging idea

Base platform fee per project plus usage for compute hours and storage managed.

Credits that cover Trino and Flink compute and connector throughput.

Discounts for design partners and for annual terms.

Resourcing plan for MVP

Team of twelve for ninety days

Two for connectors and ingestion.

Two for lakehouse and storage.

Two for compute and orchestration.

Two for metadata, catalog, and lineage.

Two for AI and automation.

One for security and SRE.

One for product and design.

Risks and mitigations

Integration complexity grows fast. Mitigation: strict scope for connectors and use of a framework.

Self healing can cause harm if wrong. Mitigation: human in the loop and audit trails with easy roll back.

Cost of running Trino and Flink for many tenants. Mitigation: aggressive autoscaling and a small query engine for previews.

Data residency and privacy concerns. Mitigation: data plane in customer account and bring your own key.

Proof of concept plan for a design partner, sixty days

Day one to seven, discovery and secure setup using their cloud account.

Day eight to twenty one, ingest three sources and deliver two curated tables with basic metrics.

Day twenty two to forty two, enable lineage view, freshness alerts, and quarantine.

Day forty three to sixty, deliver the assistant flow, root cause for staleness, and one click fixes.

Exit criteria: daily dashboard is fresh, additive schema changes do not break delivery, and two incidents handled by the platform without on call.

Success metrics

Time from first login to first dashboard under one day.

Ninety percentile pipeline build time under one week for a new source and model.

Mean time to detect issues under five minutes, mean time to repair under fifteen minutes with assistant.

At least fifty percent of common incidents resolved by the platform with user approval in phase one.

Customer NPS above forty for the builder experience.
