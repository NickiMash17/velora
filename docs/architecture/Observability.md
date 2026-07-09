# Observability

**Status:** v1.0 — Foundational
**Owner:** Platform Engineering / SRE
**Depends on:** [EventCatalog.md §3](./EventCatalog.md#3-envelope), [Security.md §7](./Security.md#7-audit-logging)
**Summarized in:** [Deployment.md §6](./Deployment.md#6-observability) — that section is the operational summary; this document is the full spec.

---

## 1. Purpose

This document specifies how Velora is observed at runtime: structured logging, metrics, tracing, alerting, and health checks. For an AI-native platform, standard three-pillar observability is necessary but not sufficient — Decision Traces (§5) are the fourth pillar, and they exist because "the request succeeded" and "the Digital Employee did the right thing" are different questions, and only one of them is answerable by a normal APM tool.

## 2. Logging

- **Format:** structured JSON, one object per line. No unstructured `print`/free-text logging in application code.
- **Required fields on every log line:** `timestamp`, `level`, `request_id` (or `event_id` for async/event-triggered work), `organization_id` (when the log line is tenant-scoped — most are), `module`, `message`.
- **Levels:** `DEBUG` (local/dev only, never shipped to production log aggregation), `INFO` (default — request lifecycle, task transitions), `WARN` (recoverable anomaly — retried failure, degraded dependency), `ERROR` (failed operation requiring attention). Paging is driven by alert rules on `ERROR` rate and SLO burn (§6), not by log level alone.
- **Never logged, under any level:** raw secrets/credentials, full unredacted PII beyond what's operationally necessary, raw LLM prompt/response content containing customer data outside the governed Decision Trace store (§5) — logs and Decision Traces have different access-control models, and prompt content belongs in the latter, not general-purpose logs.
- **Correlation:** every log line within one request or one event-triggered flow carries the same `request_id`/`correlation_id` as the originating HTTP request or Event envelope ([EventCatalog.md §3](./EventCatalog.md#3-envelope)) — this is what makes "show me everything that happened for this failed task" a single query instead of a manual reconstruction.

## 3. Metrics

- **Convention:** `{namespace}.{module}.{metric_name}`, e.g. `velora.skill_runtime.invocation_duration_seconds`.
- **Cardinality discipline — the one non-obvious rule in this document:** `organization_id` must **not** be used as a metrics label at "millions of tenants" scale — a labeled time series per organization is a cardinality explosion that will degrade or break the metrics backend long before it becomes useful. Per-tenant detail belongs in logs, traces, and Decision Traces (all queryable by `organization_id` without a cardinality cost), not in Prometheus-style labels. Metrics aggregate by dimensions that stay bounded: `plan_tier`, `cell`/`region`, `module`, `skill_key`, `status`.
- **Core metrics (v1 minimum):** request latency (p50/p95/p99) and error rate per endpoint; task completion latency per Goal/Department; LLM token usage and cost per invocation (aggregated by `plan_tier`, attributed per-org via Decision Traces/Usage Records for billing, not via metrics labels — see [AIEmployees.md §9](./AIEmployees.md#9-performance-record)); Event Store outbox relay lag (`events` rows with `relayed_at IS NULL`, age of oldest unrelayed row) — this is the health signal for the v1 event delivery mechanism ([ADR 0001](./decisions/0001-event-store-implementation.md)) and should be treated as a first-class SLO input, not an afterthought.

## 4. Tracing

- **Standard:** OpenTelemetry, spans named `{module}.{operation}` (e.g. `goal_engine.decompose`, `skill_runtime.execute`).
- **Synchronous path:** standard HTTP trace-context propagation (`traceparent` header) through Gateway → BFF → downstream module calls.
- **Asynchronous path (the part a naive tracing setup misses):** because state changes flow through the Event Store/outbox rather than a live call ([DomainModel.md §2.14](./DomainModel.md#214-event)), trace context must be carried **in the event envelope itself** — `correlation_id` and `causation_id` ([EventCatalog.md §3](./EventCatalog.md#3-envelope)) double as the async trace-linking mechanism, allowing a trace to span "API call → event written → outbox relay → consumer processes it → new event produced" even though no single HTTP connection stays open across that whole path. Without this, a trace would falsely appear to end at the moment the event was written.
- Every span that touches a tenant-scoped resource carries `organization_id` as a span **attribute** (not a metric label — no cardinality concern here, since traces are stored/queried per-trace, not aggregated into fixed-cardinality time series).

## 5. Decision Traces

A Decision Trace is written for every Digital Employee invocation, capturing: input context, retrieved Memory, the Company DNA version used, model + prompt version, output, confidence (where applicable), and which Policy Engine checks passed or blocked the action. It is linked to the originating Event and Task.

This serves two audiences simultaneously, which is why it's specified once and referenced rather than duplicated:

- **Engineering/debugging:** "why did this Digital Employee do that" — the first thing anyone reaches for when behavior looks wrong.
- **Compliance/audit:** retained per the org's audit retention policy ([Security.md §7](./Security.md#7-audit-logging)), it is the artifact that answers an auditor's "prove this action had a legitimate basis."

Access to Decision Traces is itself permission-scoped (an org's own admins can see their own org's traces; Velora engineering access for debugging is itself an audited action) — a Decision Trace is not a generic internal log, it often contains customer data by nature of what it records.

## 6. Alerts

- **SLO-based, not just threshold-based:** alerts fire on SLO burn rate (e.g., error-budget consumption for the p95 latency SLO), not on raw metric thresholds in isolation — this avoids both alert fatigue on noisy-but-harmless blips and missed slow-burn degradations that a static threshold wouldn't catch early enough.
- **Tenant-impact-weighted routing:** an issue affecting one enterprise tenant is not equivalent, from a paging perspective, to the same issue affecting a handful of trial accounts — severity/routing accounts for the tier and blast radius of who's affected, not just the raw error count.
- **Every alert links to a runbook.** An alert with no corresponding runbook entry is treated as incomplete — "what fired" without "what to do about it" pages someone into a cold start at 3am, which is precisely what a mature on-call practice avoids.
- **Outbox relay lag** (§3) has its own alert threshold independent of general error-rate alerting — since a stalled relay produces no errors, only silence, and silent event-delivery failure is the kind of failure mode that otherwise goes unnoticed until something downstream (Memory, Billing, Audit) is visibly wrong.

## 7. Health Checks

Every container exposes:

- **Liveness (`/healthz`):** process is up and able to serve requests at all — no dependency checks, so a transient DB blip doesn't cause a healthy process to be killed and restarted unnecessarily.
- **Readiness (`/readyz`):** actively checks connectivity to Postgres, Redis, and Qdrant (for modules that depend on each), and — specifically for the outbox relay process — that it has successfully relayed within an acceptable recency window. A container fails readiness (and is pulled from the load balancer) before it fails liveness, which is the whole point of having both.

## 8. Non-Goals (v1)

- No dedicated APM/observability vendor commitment in this document — Azure Monitor / OpenTelemetry-compatible backends are the default direction consistent with the Azure hosting decision ([Deployment.md §4](./Deployment.md#4-containerization--topology-v1)), but the specific vendor is an infrastructure decision, not an architectural one, and can change without this document changing.
- No client-side (browser) RUM/observability specified here — this document covers backend/AI-runtime observability; frontend performance monitoring is a `docs/design/` or frontend-engineering concern if/when it's prioritized.
- No anomaly-detection ML system in v1 — SLO/threshold-based alerting (§6) is the starting point; a dedicated Anomaly Detection Service (mentioned as a future domain in the original conceptual draft) is not a v1 build target.
