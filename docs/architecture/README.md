# Architecture

**Status:** Active — Sprint 0 Foundation

This folder is the technical source of truth for how Velora is built. Every document here should be detailed enough that a new senior engineer could implement against it without needing a Slack thread to fill in gaps.

## Documents

| Document | Covers |
|---|---|
| [DomainModel.md](./DomainModel.md) | Every domain object and how they relate — start here for the conceptual map |
| [Database.md](./Database.md) | PostgreSQL schema, multi-tenancy model, indexing, migrations, scaling path |
| [CompanyDNA.md](./CompanyDNA.md) | Org-specific grounding context: ingestion, compilation, versioning, distribution |
| [AIEmployees.md](./AIEmployees.md) | Digital Employee domain model, lifecycle, execution, permissions |
| [Memory.md](./Memory.md) | Memory taxonomy, storage mapping, namespacing, retrieval, governance |
| [EventCatalog.md](./EventCatalog.md) | Every event Velora emits — producer, consumers, payload, purpose |
| [StateMachines.md](./StateMachines.md) | Lifecycle state machines: Digital Employees, Goals, Tasks, Knowledge |
| [Security.md](./Security.md) | AuthN/AuthZ, multi-tenant isolation, encryption, AI-specific threat model |
| [API.md](./API.md) | API design conventions, versioning, async task pattern, error format |
| [IntegrationStrategy.md](./IntegrationStrategy.md) | Connector framework, OAuth, provider notes, webhooks, future MCP support |
| [Observability.md](./Observability.md) | Logging, metrics, tracing, Decision Traces, alerts, health checks (full spec) |
| [Deployment.md](./Deployment.md) | Environments, containerization, Azure topology, CI/CD, observability (summary) |
| [decisions/](./decisions/README.md) | Architecture Decision Records — why we deviated from or extended the above |

## Note on scope vs. the original `Architecture.md` draft

An earlier conceptual draft (not currently committed to this repo) described Velora as a cell-based, polyglot microservices platform on Kafka/Pulsar with per-cell Kubernetes clusters. That draft was useful for thinking through the *shape* of the problem at extreme scale, but it predates the concrete stack decision below. It is **not** the current build target and should not be treated as authoritative until reconciled into a v2 that reflects the decisions in this folder.

## Stack (decided, Sprint 0)

- **Backend:** FastAPI, Python, PostgreSQL, Redis, LangGraph, Qdrant, SQLAlchemy, Alembic, Docker
- **Frontend:** Next.js 15, React, TypeScript, TailwindCSS, shadcn/ui, React Query, Zustand
- **Infra:** Docker, Azure, GitHub Actions, Terraform, env-based config, secrets management, structured logging/metrics/tracing, health checks
- **Architecture style:** Domain-Driven Design, Clean Architecture, SOLID, Event-Driven where it earns its cost, CQRS where appropriate — **modular monolith first**, microservice-ready by design (clear module boundaries, no cross-module DB access), not by premature deployment topology.

## Reading order for a new engineer

1. This README
2. `DomainModel.md` — the conceptual map of every object in the system
3. `Database.md` — the physical shape of the data underlying that map
4. `AIEmployees.md` and `CompanyDNA.md` — the core domain concepts
5. `Memory.md` — how Digital Employees retain context
6. `EventCatalog.md` and `StateMachines.md` — how state actually changes over time
7. `Security.md` — non-negotiable constraints on all of the above
8. `API.md` and `IntegrationStrategy.md` — how the above is exposed and connected externally
9. `Observability.md` and `Deployment.md` — how it all ships, runs, and is watched
10. `decisions/` — why specific deviations from the "obvious" design were made
