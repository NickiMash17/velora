# Database

**Status:** v1.0 — Foundational
**Owner:** Backend / Platform Engineering
**Stack:** PostgreSQL (primary OLTP), Redis (cache/ephemeral), Qdrant (vector store — see [Memory.md](./Memory.md))

---

## 1. Purpose and Scope

This document defines the relational data model, multi-tenancy strategy, and scaling path for Velora's PostgreSQL layer. It does not cover vector storage (Qdrant) or ephemeral working memory (Redis) in depth — those are covered in [Memory.md](./Memory.md) — but it does define how relational rows relate to entries in those systems via shared identifiers.

Every design decision here optimizes for one non-negotiable constraint: **no data path may cross a tenant boundary, ever, by accident.** Convention is not sufficient; the schema and query layer must make cross-tenant leakage structurally difficult.

---

## 2. Multi-Tenancy Model

### 2.1 Strategy: Pool Model with Silo Escape Hatch

Velora starts with a **shared-schema, row-level tenancy model**: all organizations share the same database and tables, isolated by an `organization_id` column present on every tenant-scoped table. This is the only model that is economically viable at "millions of businesses" scale — a database-per-tenant model does not survive past a few thousand tenants.

Regulated or enterprise tenants requiring stronger isolation are the escape hatch, not the default: they can be promoted to a **dedicated schema or dedicated database instance**, using the same table definitions, reachable through the same application code via a connection-routing layer keyed on `organization_id`. This decision is made once, at provisioning time, and recorded on the `organizations` row itself (`isolation_tier`).

### 2.2 Enforcement, Not Convention

Row-level tenant scoping is enforced at three layers, deliberately redundant:

1. **Application layer:** every repository/query-builder method that touches a tenant-scoped table requires an `organization_id` argument. There is no "unscoped" query method exposed on tenant-scoped repositories — if you need one, it lives in an explicitly named `_admin` or `_system` repository reviewed separately.
2. **Database layer:** PostgreSQL **Row-Level Security (RLS)** policies are enabled on every tenant-scoped table, keyed on a session-local variable (`app.current_org_id`) set at the start of every request-scoped DB session. This means even a bug in application-layer scoping cannot leak rows — the database itself refuses to return them.
3. **CI layer:** a lint rule (custom `ast`-based check in the Python codebase) flags any raw SQL or ORM query on a tenant-scoped table that does not visibly filter by `organization_id`, and a cross-tenant-isolation test suite runs on every PR that touches the data layer.

RLS is the load-bearing layer; the other two are defense in depth. This mirrors the architectural principle that tenant isolation is "non-negotiable... by construction, not by convention."

### 2.3 Why Not Schema-per-Tenant by Default

Schema-per-tenant (or database-per-tenant) does provide stronger default isolation, but it fails at scale in three concrete ways relevant to Velora specifically:

- **Connection pool exhaustion** — Postgres connection limits are per-instance, not per-schema; millions of tenants would require prohibitively large pools or an additional pooling tier (PgBouncer) that itself becomes the bottleneck.
- **Migration fan-out** — an Alembic migration that must run against 500,000 schemas individually turns a 2-minute deploy into a multi-hour operation.
- **Operational cost** — background jobs, vacuum, and monitoring all multiply per schema.

The pool model with RLS gets tenant isolation guarantees close to schema-per-tenant without any of these costs, and reserves the heavier isolation model for the tenants who are actually willing to pay for it (enterprise/regulated).

---

## 3. Core Schema

Names below are illustrative of shape and intent; exact column types/constraints are finalized in the first Alembic migration, not in this document.

### 3.1 Identity & Organization

```
organizations
  id                  uuid PK
  name                text
  slug                text UNIQUE            -- used for subdomain routing
  plan_tier           enum(trial, starter, growth, enterprise)
  isolation_tier       enum(pool, silo)
  region               enum(us, eu, apac)     -- data residency pin
  status               enum(trial, active, suspended, churned)
  created_at, updated_at

users
  id                  uuid PK
  email               text UNIQUE
  password_hash       text NULL              -- NULL if SSO-only
  mfa_enabled          boolean
  token_version         integer                -- Security.md §3.1 access-token claim; bumped to
                                                --   invalidate all outstanding access tokens for
                                                --   this user (added Milestone 3)
  created_at, updated_at

refresh_tokens                                 -- added Milestone 3 — Security.md §3.1 says refresh
                                                --   tokens are "stored hashed"; this is where.
                                                --   Not tenant-scoped, no RLS — same reasoning as
                                                --   `users` (see AIEmployees.md-style module docs).
  id                  uuid PK
  user_id             uuid FK -> users
  token_hash           text UNIQUE             -- SHA-256 of the opaque secret, not Argon2id — see
                                                --   Security.md's authentication notes: a
                                                --   high-entropy generated secret needs protection
                                                --   from DB-dump exposure, not a slow/memory-hard KDF
  family_id             uuid                    -- groups a chain of rotations for replay detection
  issued_at              timestamptz
  expires_at             timestamptz
  organization_id        uuid FK -> organizations NULL  -- added Milestone 4: mirrors the access
                                                --   token's own claims, so rotation can preserve or
                                                --   change organization scope (Security.md §3.1.2)
  role                   text NULL              -- added Milestone 4: plain string, not the
                                                --   membership_role enum — identity has no
                                                --   knowledge of the organizations module's types
  revoked_at             timestamptz NULL
  replaced_by_id          uuid FK -> refresh_tokens NULL

organization_memberships
  id                  uuid PK
  organization_id     uuid FK -> organizations
  user_id             uuid FK -> users
  role                enum(org_admin, department_manager, member, viewer)
  status               enum(invited, active, suspended)
  created_at, updated_at
  UNIQUE (organization_id, user_id)
  -- RLS (Milestone 4): a SECOND, SELECT-only permissive policy grants
  -- self-visibility (user_id = app.current_user_id), alongside the
  -- original tenant_isolation policy (organization_id = app.current_org_id)
  -- — see ADR 0002 for why a user discovering their own organization
  -- memberships needs this and why it's deliberately SELECT-only.
```

A `user` can belong to multiple organizations (agencies managing client orgs) via multiple `organization_memberships` rows — see [Security.md §3](./Security.md#3-session--token-model) for how session tokens scope to exactly one active org at a time.

### 3.2 Departments

```
departments
  id                  uuid PK
  organization_id     uuid FK -> organizations
  name                text
  function_type        enum(sales, support, finance, marketing, ops, custom)
  budget_cents_monthly  integer NULL          -- spend cap, enforced by Model Gateway
  created_at, updated_at
```

### 3.3 AI Workforce

```
ai_employee_templates            -- the "Skill Catalog" entry a Digital Employee is instantiated from
  id                  uuid PK
  name                text
  default_skills       jsonb      -- references into skills table
  system_prompt_scaffold text
  created_at, updated_at

ai_employees
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments
  template_id         uuid FK -> ai_employee_templates
  name                text                  -- e.g. "Riley"
  role_title           text                  -- e.g. "Support Agent"
  company_dna_version_id uuid FK -> company_dna_versions
  status               enum(draft, configured, active, paused, retired)
  autonomy_defaults     jsonb                 -- per action-type autonomy level, see AIEmployees.md
  created_at, updated_at

skills
  id                  uuid PK
  key                 text UNIQUE            -- e.g. "send_email", "query_crm"
  description          text
  input_schema          jsonb                 -- JSON Schema for tool-call args
  required_permission_scope jsonb
  created_at, updated_at

ai_employee_skills               -- many-to-many, an employee's actual bound skillset (may be a subset of template defaults)
  ai_employee_id      uuid FK -> ai_employees
  skill_id            uuid FK -> skills
  PRIMARY KEY (ai_employee_id, skill_id)
```

### 3.4 Company DNA

See [CompanyDNA.md](./CompanyDNA.md) for the full model; the relational anchor is:

```
company_dna_versions
  id                  uuid PK
  organization_id     uuid FK -> organizations
  version              text                  -- semver, e.g. "1.3.0"
  status               enum(draft, published, archived)
  compiled_summary      text                  -- the "always-in-context" compact summary
  published_at, created_at
```

The full knowledge-layer content (docs, FAQs, policies) is chunked and embedded into Qdrant, not stored as relational rows — Postgres holds the version pointer and the compact summary only.

### 3.5 Goals, Projects & Tasks

See [DomainModel.md §2.8–2.10](./DomainModel.md#28-goal) for the conceptual distinction between these three — in short: Goals measure outcomes, Projects are the initiatives pursued toward them, Tasks are the atomic assignable unit of work. Both `goal_id` and `project_id` on `tasks` are nullable and independent — a Task may reference a Project, a Goal directly, both, or neither (ad hoc work).

```
goals
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments NULL   -- org-scoped goals have no department
  title                text
  success_metric        jsonb                 -- {metric, target, current}
  status               enum(proposed, active, at_risk, achieved, abandoned)
  created_at, updated_at

projects
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments
  goal_id             uuid FK -> goals NULL     -- a project may exist without a tracked goal behind it
  name                 text
  status               enum(planned, active, completed, cancelled)
  created_at, updated_at

tasks
  id                  uuid PK
  organization_id     uuid FK -> organizations
  goal_id             uuid FK -> goals NULL
  project_id           uuid FK -> projects NULL
  assigned_ai_employee_id uuid FK -> ai_employees NULL
  assigned_user_id     uuid FK -> users NULL
  status               enum(pending, claimed, in_progress, blocked, done, failed)
  idempotency_key       text                  -- see API.md, prevents duplicate execution on retry
  created_at, updated_at
```

### 3.6 Audit & Metering (relational projections)

The **Event Store is the source of truth** (see Architecture overview / event-driven principle); the tables below are queryable projections rebuilt from the event stream, not independently written.

```
audit_log_entries
  id                  uuid PK
  organization_id     uuid FK -> organizations
  actor_type           enum(user, ai_employee, system)
  actor_id             uuid
  action               text
  resource_type         text
  resource_id           uuid
  event_id             uuid                  -- pointer back to the originating event
  occurred_at           timestamptz

usage_records
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments NULL
  ai_employee_id       uuid FK -> ai_employees NULL
  metric_type           enum(llm_tokens, skill_invocation, storage_bytes)
  quantity             numeric
  cost_cents            integer
  occurred_at           timestamptz
```

`audit_log_entries` is append-only at the application layer (`INSERT`-only DB role; no `UPDATE`/`DELETE` grants) — see [Security.md §7](./Security.md#7-audit-logging).

### 3.7 Knowledge

See [DomainModel.md §2.7](./DomainModel.md#27-knowledge-source) for the conceptual model. Chunked/embedded content itself lives in Qdrant (tagged `knowledge_source_id`), not in Postgres — this table is the provenance and status record.

```
knowledge_sources
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments NULL     -- NULL = org-wide
  source_type           enum(upload, connector, questionnaire, web_crawl)
  destination            enum(company_dna, memory, both)
  status                enum(uploaded, validating, queued, processing, indexed, failed, archived)
  origin_connector_id    uuid NULL              -- references an integration connection; see IntegrationStrategy.md
  created_by_user_id     uuid FK -> users
  created_at, updated_at
```

### 3.8 Projects

See §3.5 above — `projects` is defined there alongside `goals` and `tasks` since the three are best read together.

### 3.9 Collaboration (Conversations & Messages)

See [DomainModel.md §2.12](./DomainModel.md#212-conversation--message).

```
conversations
  id                  uuid PK
  organization_id     uuid FK -> organizations
  department_id       uuid FK -> departments NULL
  task_id             uuid FK -> tasks NULL
  context_type          enum(task_thread, direct_chat, broadcast)
  created_at

messages
  id                  uuid PK
  organization_id     uuid FK -> organizations
  conversation_id      uuid FK -> conversations
  sender_type           enum(user, ai_employee, system)
  sender_id             uuid NULL
  content               text
  attachments            jsonb
  created_at
```

### 3.10 Permission Grants

See [DomainModel.md §2.13](./DomainModel.md#213-permission-grant). This table models explicit, auditable exceptions only — standing rules live in the Policy Engine's policy-as-code, not here.

```
permission_grants
  id                  uuid PK
  organization_id     uuid FK -> organizations
  grantee_type          enum(ai_employee, user, department)
  grantee_id            uuid
  resource_scope         jsonb        -- e.g. {"department_id": "...", "resource": "memory", "access": "read"}
  granted_by_user_id     uuid FK -> users
  expires_at             timestamptz NULL
  created_at
```

### 3.11 Event Store

See [DomainModel.md §2.14](./DomainModel.md#214-event) and [ADR 0001](./decisions/0001-event-store-implementation.md) for why this table — plus a Redis Streams relay — stands in for a message broker in v1. This is the platform's actual source of truth; every other projection in this schema (`audit_log_entries`, `usage_records`, Memory's episodic rollups) is rebuildable from it.

```
events
  id                  uuid PK          -- event_id
  organization_id     uuid FK -> organizations NULL   -- NULL only for platform-internal/system events
  type                 text             -- canonical PascalCase domain event name, e.g. "GoalCompleted"
  topic                 text             -- dot.snake_case wire routing key, e.g. "goal.completed" — see EventCatalog.md
  producer              text             -- emitting module name
  correlation_id         uuid
  causation_id           uuid NULL
  payload               jsonb
  occurred_at            timestamptz
  relayed_at             timestamptz NULL   -- set once the Outbox Relay has published to Redis Streams
```

`events` is `INSERT`-only, same discipline as `audit_log_entries` (§3.6). The outbox relay process reads unrelayed rows (`relayed_at IS NULL`) in occurrence order per organization and publishes to the corresponding Redis Stream, then stamps `relayed_at` — this is what makes the write to `events` and the publish to consumers two separate, individually-retryable steps rather than a single point of failure.

---

## 4. Indexing Strategy

- Every tenant-scoped table has a **composite index leading with `organization_id`** — even on columns that would otherwise get a single-column index (e.g. `(organization_id, status)` on `tasks`, not just `status`). Postgres query plans should never need to scan across tenants to satisfy a filtered query.
- `organization_memberships` and `ai_employee_skills` (join tables) index both directions of the relationship.
- `usage_records`, `audit_log_entries`, and `events` are high-write, append-only, time-ordered — indexed on `(organization_id, occurred_at)` for range queries, and are candidates for **partitioning by month** once volume warrants it (see §6). `events` additionally indexes `(relayed_at)` (partial index `WHERE relayed_at IS NULL`) so the Outbox Relay's poll query stays cheap regardless of total table size.
- JSONB columns (`success_metric`, `autonomy_defaults`, `input_schema`) are not indexed by default; if a specific JSONB key becomes a common filter predicate, add a targeted `GIN` or expression index at that time rather than speculatively.

---

## 5. Migrations

- **Alembic** manages all schema changes. Every migration is reviewed like production code — no direct schema edits against any environment.
- **Backward-compatible by default:** migrations that add a column must make it nullable or provide a default; a two-step process (add nullable → backfill → add `NOT NULL` in a follow-up migration) is required for any column that needs to become required, so that a mid-deploy rollback never leaves the schema in a state the previous application version can't read.
- **RLS policies are part of the migration**, not a manual post-deploy step — every `CREATE TABLE` migration for a tenant-scoped table includes its `ENABLE ROW LEVEL SECURITY` and policy definition in the same migration.
- Migrations run as a distinct CI/CD pipeline step before the new application version receives traffic — see [Deployment.md §5](./Deployment.md#5-cicd-pipeline).

---

## 6. Scaling Path

The pool model on a single primary is the correct starting point and will comfortably serve Velora through its early growth stage. The scaling path, in order of when each lever gets pulled:

1. **Read replicas** — read-heavy paths (dashboards, activity feeds via BFFs) route to a replica; anything in the same request as a just-completed write stays on the primary or uses read-your-writes session affinity.
2. **Connection pooling (PgBouncer)** — introduced once application-server instance count makes direct Postgres connections a limiting factor, well before raw query load is the bottleneck.
3. **Partitioning of high-volume append-only tables** (`audit_log_entries`, `usage_records`, and eventually `tasks`/event-derived tables) by `organization_id` range or by time — chosen based on actual query patterns at the time, not speculatively now.
4. **Sharding by `organization_id`** — only once a single primary's write throughput or storage genuinely becomes the ceiling (this is a "cell-based" concern; see the deferred cell architecture noted in [architecture/README.md](./README.md)). This is deliberately the *last* lever, not the first, because it multiplies operational complexity (cross-shard queries, migration fan-out, rebalancing) and Velora does not need it at MVP or early-growth scale.

The schema above is designed so that adding a shard key later is additive (the `organization_id` column already exists everywhere) rather than a rewrite.

---

## 7. Backup & Recovery

- Continuous WAL archiving with point-in-time recovery (PITR); Azure-managed Postgres (Flexible Server) provides this natively — see [Deployment.md](./Deployment.md).
- Daily full snapshot retained per the org's plan tier; enterprise tenants get configurable RPO/RTO commitments (see [Deployment.md §7](./Deployment.md#7-disaster-recovery)).
- Because state is event-derived at the platform level, relational tables that are pure projections (`audit_log_entries`, materialized memory rollups) are theoretically rebuildable from the Event Store — this is a recovery option, not a substitute for PITR, since replay time at scale is non-trivial.

---

## 8. Explicit Non-Goals (v1)

- No database-per-tenant at the pool tier — only as the paid silo escape hatch.
- No cross-shard transactions — sharding, when it arrives, is a partitioning strategy for scale, not a distributed-transaction system. Cross-org operations do not exist in the product model, so this is not a real constraint.
- No speculative partitioning of low-volume tables — applied when metrics justify it, not preemptively.
