# Deployment

**Status:** v1.0 — Foundational
**Owner:** Platform / Infrastructure Engineering
**Stack:** Docker, Azure, GitHub Actions, Terraform
**Depends on:** [Database.md](./Database.md), [Security.md](./Security.md), [API.md](./API.md)

---

## 1. Purpose

This document defines how Velora is packaged, deployed, scaled, and operated. It is written for the actual v1 build target — a **modular monolith**, containerized, deployed on Azure — not for the cell-based multi-region topology described in the earlier conceptual draft. That topology remains a valid *future* direction once genuine scale demands it (see §8); this document describes what we build first.

## 2. Environments

| Environment | Purpose | Notes |
|---|---|---|
| `local` | Developer machines | Docker Compose: FastAPI app, Postgres, Redis, Qdrant, all local |
| `staging` | Pre-production validation | Mirrors production topology at smaller scale; seeded with synthetic multi-tenant data to exercise isolation tests |
| `production` | Live customer traffic | Azure-hosted, per §4 |

Configuration is environment-based throughout (§3) — the same container image runs unmodified across all three; only environment variables and connected infrastructure differ.

## 3. Configuration & Secrets

- **Environment-based configuration**: all environment-specific values (database URLs, feature flags, provider API keys) are injected via environment variables, validated at startup via Pydantic Settings — the app fails fast on missing/malformed config rather than failing confusingly mid-request.
- **Secrets management**: Azure Key Vault is the source of truth for all secrets (DB credentials, LLM provider keys, OAuth client secrets, per-tenant encryption keys — [Security.md §6](./Security.md#6-encryption)). Secrets are injected into the runtime environment at container start, never committed to the repository, never baked into a container image.
- **No environment-specific code branches** — `if environment == "production"` checks in application code are a smell; behavior differences belong in configuration, not conditionals.

## 4. Containerization & Topology (v1)

- The backend ships as a single **Docker image** built from the FastAPI application — the modular monolith. Internal module boundaries (Organization, AI Workforce, Company DNA, Memory, Goal Engine, etc.) are enforced by Python package structure and import-linting rules (no module reaching into another's internal package), not by network boundaries — this is what "microservice-ready" means in practice at this stage: extraction later is a deployment change, not a rewrite.
- The frontend (Next.js 15) ships as its own container, deployed independently — frontend and backend release cadences are decoupled.
- **Azure hosting:** Azure Container Apps (or AKS if/when workload complexity justifies the additional operational surface — deferred until there's a concrete driver, not adopted speculatively) for the backend and frontend containers; **Azure Database for PostgreSQL – Flexible Server** for the primary datastore; **Azure Cache for Redis**; Qdrant self-hosted in-cluster or via Qdrant Cloud (evaluated on cost/ops tradeoff before v1 launch, not decided prematurely here).
- Application containers are **stateless** — horizontal scaling is adding replicas, never pinning session/agent state to a specific instance (consistent with [AIEmployees.md §7](./AIEmployees.md#7-execution-model)).

## 5. CI/CD Pipeline

GitHub Actions, per service (backend, frontend), each running:

```
Build → Lint/Typecheck → Unit tests → Integration tests
      → Contract tests (OpenAPI schema diff, event schema compatibility)
      → Build container image → Push to registry
      → Run DB migrations (staging first, gated) → Deploy (canary → progressive rollout)
```

Key gates, none of which are skippable via a fast-path:

- **Migration-before-traffic**: Alembic migrations run as a distinct pipeline step before the new application version receives any traffic, and must be backward-compatible with the *currently running* version ([Database.md §5](./Database.md#5-migrations)) so a rollback never leaves the schema ahead of the code.
- **Cross-tenant isolation test suite**: any PR touching the data layer must pass the isolation test suite described in [Security.md §4](./Security.md#4-tenant-isolation) before merge — this is a release-blocking category, not advisory.
- **Event schema compatibility check**: any change to an event payload schema is checked for backward compatibility against existing consumers before deploy is allowed to proceed.

## 6. Observability

**This section is a summary.** Full spec — including the metrics cardinality rule, async trace-context propagation across the Event Store, and alerting philosophy — lives in [Observability.md](./Observability.md).

Three standard pillars plus the AI-native fourth pillar:

| Pillar | Captures | Tooling direction |
|---|---|---|
| Metrics | Latency, error rate, cost-per-task, token usage, per-tenant SLA adherence | OpenTelemetry metrics → Azure Monitor |
| Logs | Structured, correlation-ID-tagged logs across the app | Structured JSON logging → Azure Monitor / Log Analytics |
| Traces | Distributed traces: Gateway → Goal Engine → Agent Collaboration → Skill Runtime → external API | OpenTelemetry tracing |
| **Decision Traces** | Full reasoning trace per Digital Employee action: input context, retrieved memory, DNA version used, model + prompt version, output, confidence, policy checks passed | Written alongside the Audit Log; this is a compliance artifact as much as a debugging one — see [Security.md §7](./Security.md#7-audit-logging) |

Every request/response error carries a `request_id` (see [API.md §7](./API.md#7-error-format)) that ties directly to a trace — this is the mechanism, not an aspiration; if a `request_id` can't be traced end-to-end, that's a gap to close before launch, not after.

**Health checks:** every container exposes a liveness (`/healthz`) and readiness (`/readyz`) endpoint — readiness specifically checks DB/Redis/Qdrant connectivity so a container is never routed traffic before its dependencies are reachable.

**Cost observability:** the Model Gateway emits granular cost-per-call telemetry attributed down to `organization_id → department_id → ai_employee_id → task_id` ([AIEmployees.md §9](./AIEmployees.md#9-performance-record)) — LLM inference cost is a first-class operating expense here, not an afterthought bolted onto generic infra metrics.

## 7. Disaster Recovery

- Postgres: continuous WAL archiving + point-in-time recovery via Azure Flexible Server, daily full snapshots retained per plan tier ([Database.md §7](./Database.md#7-backup--recovery)).
- Target posture (to be finalized before first enterprise contract, not before MVP): tiered RPO/RTO commitments — e.g., enterprise tier RPO < 5 min / RTO < 30 min; lower tiers on a more relaxed, cost-appropriate schedule.
- Because platform state is event-derived, projections (materialized memory rollups, audit projections) are in principle rebuildable from the Event Store — treated as a recovery *option*, not a substitute for PITR, since full replay time at any real scale is non-trivial and untested until it's actually exercised in a DR drill.

## 8. Scaling Path (Deployment Dimension)

Mirrors the database scaling path ([Database.md §6](./Database.md#6-scaling-path)) at the infrastructure layer:

1. **Horizontal replica scaling** of the stateless application containers — the default, cheapest lever, available from day one.
2. **Module extraction** — when a specific module (most likely Skill Runtime or the Model Gateway, given their distinct load profiles) genuinely outgrows the monolith's shared deployment unit, it is extracted into its own service and deployment pipeline. Because module boundaries are already enforced at the code level (§4), this is a deployment change, not a design change.
3. **Regional expansion** — additional Azure regions stood up for latency and data-residency reasons (EU, APAC tenants) once there's real demand, using the same Terraform modules rather than bespoke per-region setup.
4. **Cell-based partitioning** — the conceptual multi-cell model from the earlier draft becomes relevant only if a single regional deployment's blast radius or scale genuinely becomes a problem. This is explicitly the *last* lever, deferred until there's evidence it's needed, not built preemptively into v1 infrastructure.

## 9. Infrastructure as Code

All infrastructure (Container Apps/AKS, Postgres, Redis, Key Vault, networking) is defined in **Terraform**, reviewed like application code. Spinning up staging, a new environment, or (eventually) a new region is a repeatable pipeline run, not a manual console click-through — this is what "Terraform-ready" means in practice: it's not optional tooling to add later, it's how environments are created from Sprint 0 onward.

## 10. Non-Goals (v1)

- No multi-region active-active deployment — single-region (with cross-AZ replication) until data residency or latency requirements from actual enterprise tenants force the question.
- No Kubernetes (AKS) adoption by default — Azure Container Apps first; AKS is adopted only when a concrete operational need (not a general preference for "more control") justifies its added complexity.
- No per-tenant dedicated infrastructure at deploy time for the default pool-tier tenant — consistent with [Database.md §2](./Database.md#2-multi-tenancy-model); the silo escape hatch is a provisioning-time decision for specific enterprise tenants, not a deployment default.
