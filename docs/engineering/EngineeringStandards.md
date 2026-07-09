# Engineering Standards

**Status:** v1.0 — Foundational
**Owner:** Engineering Leadership
**Depends on:** [../architecture/Database.md](../architecture/Database.md), [../architecture/EventCatalog.md](../architecture/EventCatalog.md), [../architecture/Observability.md](../architecture/Observability.md)

---

## 1. Purpose

This document is how we work, day to day — folder structure, naming, testing, review, git conventions, Definition of Done, and documentation standards. `architecture/` documents *what* we're building and why; this document is *how* we build it consistently, so that code written by different engineers (or different AI-assisted sessions) two years apart still looks like it came from the same team.

## 2. Folder Structure

### 2.1 Backend (modular monolith, FastAPI)

Module boundaries mirror the domains in [DomainModel.md](../architecture/DomainModel.md) and are enforced by import-linting (a module may not import another module's `internal` package), not just convention — this is what keeps "microservice-ready" real rather than aspirational.

```
backend/
  app/
    modules/
      organizations/
        domain/          # entities, value objects, domain events — no framework imports
        application/      # use cases / services, orchestrates domain + infrastructure
        infrastructure/   # SQLAlchemy models, repositories, external clients
        api/              # FastAPI routers, Pydantic request/response schemas
      departments/
      ai_workforce/
      company_dna/
      knowledge/
      memory/
      goals/              # goals, projects, tasks together — see DomainModel.md §2.8-2.10
      collaboration/       # conversations, messages, agent collaboration orchestration
      skills/              # skill catalog + skill runtime
      integrations/         # connector framework + provider implementations
      security/             # policy engine client, permission grants
      billing/
      events/                # outbox writer, relay process, event envelope helpers — shared by every module
    shared/                  # cross-module utilities with NO domain knowledge (pagination, error types, base classes)
    main.py                   # FastAPI app assembly — wires routers, not business logic
  alembic/
    versions/
  tests/
    unit/                      # mirrors app/modules structure
    integration/                # real Postgres/Redis/Qdrant via containers, per Testing (§4)
    contract/                    # OpenAPI schema diff, event schema compatibility
    isolation/                    # cross-tenant isolation suite — see Security.md §4
```

Each module's `domain/` layer has zero framework imports (no FastAPI, no SQLAlchemy) — this is the Clean Architecture boundary that makes a module's core logic independently testable without spinning up infrastructure, which is the actual point of the layering, not layering for its own sake.

### 2.2 Frontend (Next.js 15, App Router)

```
frontend/
  app/                    # routes — thin, delegate to features/
  features/                # one folder per product feature area, mirrors docs/product/Features/
    digital-employees/
      components/
      hooks/
      api/                 # React Query hooks calling the backend API
      store/                # Zustand slices, feature-scoped
  components/               # shared, feature-agnostic UI (shadcn/ui-based)
  lib/                       # framework-agnostic utilities
```

Feature folders are structured to mirror `docs/product/Features/` one-to-one where that folder gets populated — a product feature spec and its implementation should be trivially findable from each other.

## 3. Naming

| Context | Convention | Example |
|---|---|---|
| Python modules/functions/variables | `snake_case` | `claim_task()` |
| Python classes | `PascalCase` | `TaskRepository` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Database tables/columns | `snake_case`, plural table names | `ai_employees`, `organization_id` |
| Domain event types | `PascalCase` verb-past-tense | `GoalCompleted` — see [EventCatalog.md §2](../architecture/EventCatalog.md#2-naming-convention) |
| Event wire topics | `dot.snake_case` | `goal.completed` |
| TypeScript/React components | `PascalCase`, one component per file, filename matches component | `DigitalEmployeeCard.tsx` |
| TypeScript functions/variables | `camelCase` | `useTaskStatus()` |
| TypeScript types/interfaces | `PascalCase`, no `I`/`T` prefix | `DigitalEmployee`, not `IDigitalEmployee` |
| REST resource paths | plural, kebab-case | `/v1/digital-employees` |

## 4. Testing

**Test pyramid**, weighted toward the base:

- **Unit tests** — the majority. Test a module's `domain/` and `application/` layers with infrastructure mocked/faked. Fast, no containers.
- **Integration tests** — real Postgres/Redis/Qdrant via test containers, one module's `infrastructure/` layer against real dependencies. Verifies repositories, migrations, and RLS policies actually behave as documented.
- **Contract tests** — OpenAPI schema diff (no breaking change without a version bump, per [API.md §3](../architecture/API.md#3-versioning)) and event payload compatibility checks (no breaking change to an existing event `type`'s payload shape, per [EventCatalog.md §3](../architecture/EventCatalog.md#3-envelope)). Run in CI on every PR, not just before release.
- **Cross-tenant isolation suite** — a dedicated test category (`tests/isolation/`) that asserts no query path can return another organization's rows, run on every PR touching the data layer, per [Security.md §4](../architecture/Security.md#4-tenant-isolation) and [Database.md §2.2](../architecture/Database.md#22-enforcement-not-convention). This is the one test category that is never optional or skippable for a passing build.
- **End-to-end tests** — a small number, covering the highest-value user journeys through the real API + frontend. Not a substitute for the layers above; e2e tests are expensive to maintain and slow to run, so they cover breadth of critical paths, not depth of logic.

**Testing LangGraph agents specifically:** live LLM calls are non-deterministic and slow — unit/integration tests for agent graphs run against **recorded, replayed model responses** (fixture-based), asserting on graph structure, tool-call sequencing, and policy-check invocation, not on exact model output text. A separate, smaller **eval suite** (not part of the standard CI gate, run on a schedule or before a model/prompt version upgrade) exercises real model calls against a curated task set to judge actual behavioral quality — these are different tools answering different questions ("does the code work" vs. "is the agent good"), and conflating them produces either a flaky CI pipeline or an untested one.

**Independent testability**, restated as a concrete rule: if testing module A requires standing up module B's infrastructure, the module boundary is wrong or the test is wrong — module boundaries exist specifically so this doesn't happen.

## 5. Review Process

- Every change lands via pull request — no direct commits to `main`.
- At least one approval required; **two approvals** for changes touching: Row-Level Security policies, the Policy Engine's policy definitions, authentication/token logic, or Alembic migrations that alter a column from nullable to `NOT NULL` (per [Database.md §5](../architecture/Database.md#5-migrations)) — these are the categories where a subtle mistake has outsized, hard-to-detect blast radius.
- A PR that changes documented behavior (an API shape, an event payload, a state machine transition, a schema) **updates the corresponding `docs/architecture/` file in the same PR** — a behavior change and its documentation are one unit of review, not a follow-up task that's easy to skip.
- Prefer small, single-purpose PRs. A PR mixing a refactor with a behavior change is harder to review correctly than two PRs — split them unless genuinely inseparable.

## 6. Git Conventions

- **Trunk-based**, short-lived feature branches off `main`. Branch naming: `{type}/{short-description}` — `feat/ai-employee-provisioning`, `fix/task-claim-race`, `docs/event-catalog`.
- **Commit messages** follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) — this makes changelog generation and "what kind of change is this" scannable without opening the diff.
- **Squash merge** is the default into `main`, so `main`'s history reads as one commit per reviewed change, not per work-in-progress checkpoint.
- No force-push to `main` or any shared branch. No skipped hooks/checks to land a PR faster — if a check is wrong, fix the check, don't bypass it.

## 7. Definition of Done

A change is done when, not before:

- [ ] Tests pass (unit, integration, contract, and isolation where applicable) — none skipped, none newly `xfail`'d without a tracked follow-up.
- [ ] Relevant `docs/architecture/` (or `docs/engineering/`) file updated in the same PR, per §5.
- [ ] Any new Alembic migration is backward-compatible with the currently deployed application version, per [Database.md §5](../architecture/Database.md#5-migrations).
- [ ] Any new event type is added to [EventCatalog.md](../architecture/EventCatalog.md) in the same PR — per that document's own rule, an event that isn't cataloged doesn't exist.
- [ ] Observability is present for anything new that can fail: structured logs with the required fields ([Observability.md §2](../architecture/Observability.md#2-logging)), and a metric or trace span if it's a new operation on a hot path.
- [ ] No new lint, type-check, or import-boundary-lint errors.
- [ ] For anything touching tenant-scoped data: the cross-tenant isolation suite passes, and any new tenant-scoped table has Row-Level Security enabled in the same migration.

## 8. Documentation Standards

- Follow the conventions already established in [docs/README.md](../README.md) — Markdown, one topic per file, cross-link rather than duplicate, mark placeholders explicitly.
- **Architecture Decision Records (ADRs):** for a decision that deviates from or meaningfully extends what's already documented — the kind of call a future engineer will reasonably ask "wait, why is it built this way?" about — write a short ADR in `docs/architecture/decisions/`, numbered sequentially. See [decisions/README.md](../architecture/decisions/README.md) for the template and [ADR 0001](../architecture/decisions/0001-event-store-implementation.md) for a worked example (the decision to implement the Event Store on Postgres + Redis Streams instead of adopting a broker in v1). An ADR is short — the decision, the alternatives considered, and the reasoning — not a full design document.
- A README placeholder (`Status: Placeholder`) is not a license to leave a folder empty indefinitely — it's a marker that the content is scoped but not yet written, so the next person to look doesn't mistake silence for "nothing belongs here."

## 9. Non-Goals (v1)

- No mandated 100% code coverage threshold — coverage is a signal, not a target; the actual bar is "every module is independently testable and its critical paths are tested," per §4, which a raw coverage percentage does not reliably measure.
- No monorepo tooling (Nx, Turborepo, Bazel) commitment yet — `backend/` and `frontend/` as two top-level projects is sufficient at current team size and deploy cadence; revisit if/when build orchestration complexity actually demands it.
- No enforced PR template beyond what's implied by §5–§7 — process should stay lightweight until its absence causes a real, recurring problem.
