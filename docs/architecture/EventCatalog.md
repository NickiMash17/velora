# Event Catalog

**Status:** v1.0 — Foundational
**Owner:** Platform Engineering
**Depends on:** [DomainModel.md §2.14](./DomainModel.md#214-event), [Database.md §3.11](./Database.md#311-event-store), [ADR 0001](./decisions/0001-event-store-implementation.md)

---

## 1. Purpose

This is the registry of every event Velora emits: who produces it, who consumes it, what it carries, and why it exists. If an event isn't listed here, it doesn't exist — no service should emit an ad hoc event type that hasn't been added to this catalog first, because undocumented events are exactly how "what does this system actually do" stops being answerable from the docs.

### 1.1 Implementation status legend

**This catalog documents intended event contracts — it does not, by itself, mean an event is emitted by any running code today.** As of this update, exactly two event types have a real emitter:
`OrganizationCreated` and `MembershipActivated` (both in `backend/app/modules/organizations/application/services.py`, registered in `backend/app/modules/events/domain/catalog.py`). Every other event below is a decided contract for a domain that has no backend module yet — planning ahead of implementation is the point of this document, but conflating "documented" with "built" is exactly the mistake this legend exists to prevent.

Two markers, applied per-section below (per-row only where a section is mixed):

| Marker | Meaning |
|---|---|
| ✅ **Implemented** | A real emitter exists in code today, registered in `catalog.py`. |
| 📋 **Planned** | A decided contract with no emitter yet — safe to build against once its owning module exists, not before. |

## 2. Naming Convention

Two names exist for every event, deliberately:

| | Format | Example | Used for |
|---|---|---|---|
| **Type** | `PascalCase`, verb-past-tense | `GoalCompleted` | The canonical domain event name — used in code, in `events.type`, in Decision Traces, in this catalog |
| **Topic** | `dot.snake_case` | `goal.completed` | The Redis Stream key (`events.topic` — see [Database.md §3.11](./Database.md#311-event-store)) — used for routing/subscription, supports wildcard-style consumer grouping by prefix (`goal.*`) |

`type` is the semantic identity of the event (what a domain expert would call it); `topic` is the wire-level routing key (what a consumer subscribes to). They map 1:1 and are both stored on every event row — never derive one from the other at read time, since that coupling is exactly what makes renaming painful later.

## 3. Envelope

Every event, regardless of type, carries the same envelope (see [Database.md §3.11](./Database.md#311-event-store) for the physical columns):

```json
{
  "id": "uuid",
  "organization_id": "uuid | null",
  "type": "GoalCompleted",
  "topic": "goal.completed",
  "producer": "goal_engine",
  "correlation_id": "uuid",
  "causation_id": "uuid | null",
  "occurred_at": "2026-07-09T12:00:00Z",
  "payload": { }
}
```

- `correlation_id` ties every event in one end-to-end flow together (e.g., one human request → decomposition → N task events) — propagated through the Tenant Context / trace context, not regenerated per event.
- `causation_id` points at the specific event that directly caused this one (distinct from `correlation_id`, which spans the whole flow) — this is what lets a Decision Trace answer "why did this happen" one hop at a time, not just "what flow was this part of." See [Observability.md §4](./Observability.md#4-tracing) for how this interacts with distributed tracing.
- `payload` is versioned implicitly by `type` — a breaking payload change ships as a new `type` (e.g., `GoalCompletedV2`) rather than mutating the meaning of an existing type for existing consumers, mirroring the backward-compatibility discipline in [Database.md §5](./Database.md#5-migrations).

## 4. Delivery

Recap from [ADR 0001](./decisions/0001-event-store-implementation.md): every event is written to the `events` table in the same DB transaction as the state change that produced it (outbox pattern), then relayed by a background process to a Redis Stream named after its `topic`. Consumers read from Redis Streams using consumer groups (at-least-once delivery, idempotent handlers keyed on `event.id`). A poison event lands in a per-topic dead-letter stream after N retries rather than blocking the stream.

## 5. Catalog

### 5.1 Identity & Organization

**Implementation status:** mixed — the only section where it is; see per-row markers.

| Status | Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|---|
| ✅ Implemented | `OrganizationCreated` | Organization Service | Billing, Audit Log, Analytics | `organization_id`, `plan_tier`, `region` | New tenant provisioned |
| 📋 Planned | `OrganizationPlanChanged` | Billing | Organization Service, Analytics | `organization_id`, `old_tier`, `new_tier` | Entitlements/quota recalculation trigger |
| 📋 Planned | `DepartmentCreated` | Department Service | Audit Log, Analytics | `department_id`, `organization_id`, `function_type` | New department |
| 📋 Planned | `UserInvited` | Membership Service | Notification Service, Audit Log | `user_id`, `organization_id`, `role` | Invitation sent |
| ✅ Implemented | `MembershipActivated` | Membership Service | Billing (seat count), Audit Log | `organization_id`, `user_id`, `role` | User accepted invite |

### 5.2 AI Workforce

**Implementation status:** 📋 Planned — no `ai_employees` module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `EmployeeHired` | Provisioning Service | Billing (seat metering), Audit Log, Goal Engine | `ai_employee_id`, `department_id`, `template_id` | Digital Employee created in `draft` |
| `EmployeeConfigured` | Provisioning Service | Audit Log | `ai_employee_id`, `company_dna_version_id`, `permission_scope` | DNA + permissions bound; eligible for activation |
| `EmployeeActivated` | Provisioning Service | Billing, Task Board, Audit Log | `ai_employee_id` | Now eligible to claim tasks |
| `EmployeePaused` | Provisioning Service / Policy Engine (auto-pause) | Task Board (reassign in-flight tasks), Notification Service, Audit Log | `ai_employee_id`, `reason` | Manual pause or automatic (policy violation, budget exhaustion) |
| `EmployeeRetired` | Provisioning Service | Task Board (reassign), Billing, Audit Log | `ai_employee_id` | Archived; memory retained |
| `EmployeeCompletedTask` | Agent Collaboration | Goal Engine, Memory Indexing, Analytics, Audit Log | `ai_employee_id`, `task_id`, `outcome` | Feeds performance record ([AIEmployees.md §9](./AIEmployees.md#9-performance-record)) |

### 5.3 Company DNA

**Implementation status:** 📋 Planned — no Company DNA module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `CompanyDnaDraftCreated` | DNA Ingestion Service | Audit Log | `dna_version_id`, `organization_id` | New draft version opened |
| `CompanyDnaCompiled` | DNA Compiler Service | Cache invalidation, Audit Log | `dna_version_id`, `compiled_summary_hash` | Compilation pipeline finished ([CompanyDNA.md §4.2](./CompanyDNA.md#42-compilation)) |
| `CompanyDnaPublished` | DNA Versioning Service | Cache (Redis) eviction/repopulate, Audit Log, all bound Digital Employees (next invocation) | `dna_version_id`, `organization_id`, `previous_version_id` | New version live; existing employees stay pinned until upgraded |

### 5.4 Knowledge

**Implementation status:** 📋 Planned — no Knowledge module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `KnowledgeUploaded` | Document Ingestion Service | Knowledge Processing pipeline, Audit Log | `knowledge_source_id`, `organization_id`, `source_type` | Raw source registered, staged for validation |
| `KnowledgeProcessingStarted` | Knowledge Processing pipeline | Audit Log | `knowledge_source_id` | Chunk/embed pipeline began |
| `KnowledgeIndexed` | Knowledge Processing pipeline | Memory Indexing / DNA Compiler (per `destination`), Notification Service, Audit Log | `knowledge_source_id`, `destination`, `chunk_count` | Available for retrieval |
| `KnowledgeProcessingFailed` | Knowledge Processing pipeline | Notification Service, Audit Log | `knowledge_source_id`, `error_class` | Retryable or terminal failure — see [StateMachines.md §6](./StateMachines.md#6-knowledge-processing-pipeline) |
| `KnowledgeRedacted` | Memory Governance (right-to-forget) | Memory Indexing, Qdrant cleanup job, Audit Log | `knowledge_source_id`, `redaction_reason` | Cascading scrub per [Memory.md §6.2](./Memory.md#62-right-to-forget) |

### 5.5 Memory

**Implementation status:** 📋 Planned — no Memory module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `MemoryWritten` | Memory Service (on behalf of any producer) | Memory Indexing Service | `organization_id`, `department_id`, `ai_employee_id`, `memory_type`, `source_event_id` | Triggers dual-write to Qdrant + Postgres ([Memory.md §4](./Memory.md#4-write-path)) |
| `MemoryUpdated` | Memory Indexing Service | Analytics | `memory_id`, `memory_type` | An existing memory entry was revised (e.g., procedural pattern confidence updated) rather than newly created |
| `MemoryRedacted` | Memory Governance | Qdrant cleanup job, Audit Log | `organization_id`, `scope` | Retention purge or right-to-forget cascade |

### 5.6 Goals, Projects & Tasks

**Implementation status:** 📋 Planned — no Goals/Tasks module exists yet; none of the events below has an emitter in code. The three `Approval*` rows are the M5-approved human-in-the-loop events (Domain Contract review, Decision 1/8) — modeled here against `tasks`/`TaskBlocked`, per the M5 decision to attach approval to a task-scoped sidecar (`task_pending_approvals`) rather than a standalone Approval domain; see [Security.md §5.2](./Security.md#52-human-in-the-loop-gates).

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `GoalProposed` | Goal Engine | Notification Service (human approval prompt) | `goal_id`, `proposed_plan` | Decomposition proposed, awaiting approval unless auto-approve policy applies |
| `GoalActivated` | Goal Engine | Task Board, Analytics, Audit Log | `goal_id` | Approved (manually or auto) and live |
| `GoalAssigned` | Goal Engine | Task Board, Notification Service | `goal_id`, `department_id` | Routed to a department |
| `GoalAtRisk` | Goal Engine (Evaluation Loop) | Notification Service, Audit Log | `goal_id`, `current_metric_value` | Continuous evaluation detected stalled progress |
| `GoalCompleted` | Goal Engine (Evaluation Loop) | Billing (if tied to plan reporting), Analytics, Audit Log | `goal_id`, `final_metric_value` | Success metric target reached |
| `ProjectCreated` / `ProjectCompleted` / `ProjectCancelled` | Goal Engine or direct human action | Task Board, Analytics, Audit Log | `project_id`, `goal_id?` | Project lifecycle transitions ([DomainModel.md §2.9](./DomainModel.md#29-project)) — **out of scope for M5**, per the M5 Domain Contract review's decision to defer Projects |
| `TaskAssigned` | Goal Engine / Agent Collaboration | Task Board, Notification Service | `task_id`, `department_id` | Lands on the shared Task Board |
| `TaskClaimed` | Agent Collaboration | Task Board, Audit Log | `task_id`, `ai_employee_id` | Optimistic-lock claim succeeded |
| `TaskBlocked` | Agent Collaboration | Notification Service | `task_id`, `reason` | Awaiting dependency or human input — `reason` includes `awaiting_approval`, the trigger for the three events below |
| `TaskCompleted` | Agent Collaboration | Goal Engine (metric re-evaluation), Memory Indexing, Billing, Audit Log | `task_id`, `outcome` | Terminal success |
| `TaskFailed` | Agent Collaboration | Notification Service (escalation), Goal Engine, Audit Log | `task_id`, `error_class`, `retry_count` | Terminal failure after retry policy exhausted — see [StateMachines.md §3](./StateMachines.md#3-task-lifecycle) |
| `ApprovalRequested` | Skill Runtime / Agent Collaboration | Notification Service, Audit Log | `task_id`, `ai_employee_id`, `skill_key`, `attempted_action_summary` | A policy-gated action needs human sign-off before executing; task moves to `blocked` (`reason=awaiting_approval`) — see [Security.md §5.2](./Security.md#52-human-in-the-loop-gates) |
| `ApprovalGranted` | BFF (human action) | Skill Runtime (resumes execution), Audit Log | `task_id`, `approved_by_user_id` | Human approved; the gated skill call proceeds |
| `ApprovalDenied` | BFF (human action) | Skill Runtime, Task Board, Audit Log | `task_id`, `denied_by_user_id`, `reason?` | Human rejected; task returns to a terminal or reassignable state |

### 5.7 Collaboration

**Implementation status:** 📋 Planned — no Collaboration/Conversations module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `MessageSent` | Agent Collaboration / BFF (human messages) | Memory Indexing (episodic), Realtime Gateway (push to subscribed clients) | `message_id`, `conversation_id`, `sender_type` | New message in a Conversation |
| `ConversationEscalated` | Agent Collaboration (conflict resolution) | Notification Service, Audit Log | `conversation_id`, `escalation_reason` | Supervisor pattern or tie-breaker punted to a human |

### 5.8 Skill Execution

**Implementation status:** 📋 Planned — no Skill Runtime/Policy Engine exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `SkillInvoked` | Skill Runtime | Memory Indexing, Audit Log, Model Gateway (cost telemetry) | `task_id`, `ai_employee_id`, `skill_key`, `idempotency_key` | Policy check passed, execution started |
| `SkillSucceeded` | Skill Runtime | Task orchestration, Memory Indexing, Audit Log | `task_id`, `skill_key`, `result_summary` | — |
| `SkillFailed` | Skill Runtime | Task orchestration (retry/backoff), Audit Log | `task_id`, `skill_key`, `error_class` | — |
| `PolicyViolationDetected` | Policy Engine | Guardrail Service, Notification Service (security), Audit Log | `ai_employee_id`, `attempted_action`, `policy_id` | A skill call was blocked before execution — see [Security.md §5](./Security.md#5-authorization-model) |

### 5.9 Integration

**Implementation status:** 📋 Planned — no Integration/Connector module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `IntegrationConnected` | Connector Hub | Audit Log, Notification Service | `connector_id`, `provider`, `organization_id` | OAuth flow completed — see [IntegrationStrategy.md §3](./IntegrationStrategy.md#3-oauth-as-the-common-auth-backbone) |
| `IntegrationTokenRefreshFailed` | Token Refresh Service | Notification Service (org admin alert), Audit Log | `connector_id`, `provider` | Re-auth needed |
| `IntegrationEventReceived` | Webhook Gateway | Agent Collaboration (may trigger a Digital Employee invocation), Audit Log | `provider`, `raw_payload_ref` | Normalized inbound event from an external system |

### 5.10 Billing

**Implementation status:** 📋 Planned — no Billing/Model Gateway module exists yet; none of the events below has an emitter in code.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `UsageRecorded` | Model Gateway, Skill Runtime | Billing, Analytics | `organization_id`, `department_id`, `ai_employee_id`, `metric_type`, `quantity`, `cost_cents` | Feeds `usage_records` projection ([Database.md §3.6](./Database.md#36-audit--metering-relational-projections)) |
| `BudgetExceeded` | Model Gateway / Skill Runtime (spend cap check) | Notification Service, Policy Engine (auto-pause trigger) | `department_id`, `budget_cents_monthly`, `spent_cents` | Enforced independently of any single Digital Employee's own logic — [Security.md §8.4](./Security.md#84-runaway-agent-loops--cost-bombs) |

### 5.11 Security

**Implementation status:** 📋 Planned — `identity` has real token-revocation logic (`token_version` increment, `backend/app/modules/identity/application/services.py`) but does not call `write_event` anywhere; neither event below has an emitter in code today.

| Type | Producer | Consumers | Payload (key fields) | Purpose |
|---|---|---|---|---|
| `AuthTokenRevoked` | Auth Service | Gateway (revocation-list sync), Audit Log | `token_version`, `subject_id` | Kill-switch propagation — [Security.md §3.1](./Security.md#31-authn-flow) |
| `PermissionGrantIssued` / `PermissionGrantExpired` | Policy Engine / scheduled expiry job | Audit Log | `grant_id`, `grantee_id`, `resource_scope` | Explicit exception lifecycle — [DomainModel.md §2.13](./DomainModel.md#213-permission-grant) |

## 6. Non-Goals (v1)

- No event schema registry service (e.g., Confluent Schema Registry) — payload compatibility is enforced by code review and the CI contract-test gate ([Deployment.md §5](./Deployment.md#5-cicd-pipeline)), appropriate for the current event volume and single-broker-less deployment. Revisit if/when a real broker is adopted.
- No cross-organization event subscriptions — every event's blast radius is its own `organization_id`; there is no platform-wide "firehose" topic a tenant could subscribe to.
- This catalog does not enumerate every conceivable future event — it is a living document. Adding a new event type to the system requires adding it here in the same change, but the reverse (listing hypothetical future events) is not the goal.
- The §1.1 implementation-status legend and per-section markers exist to keep "documented" and "built" visibly distinct in a catalog that necessarily documents contracts ahead of the modules that will emit them — treat 📋 Planned exactly as seriously as the rest of this catalog's naming/payload discipline, just not as evidence that the emitter exists yet.
