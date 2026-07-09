# Velora — Product Requirements Document (MVP)

**Status:** Draft v1.0 — written to align with the completed engineering specification; needs founder/product sign-off on the scope calls flagged with **[Assumption]** below before it's treated as final.
**Owner:** Product, drafted in collaboration with Engineering
**Depends on:** [architecture/DomainModel.md](../architecture/DomainModel.md), [architecture/AIEmployees.md](../architecture/AIEmployees.md), [architecture/CompanyDNA.md](../architecture/CompanyDNA.md), [architecture/StateMachines.md](../architecture/StateMachines.md), [architecture/IntegrationStrategy.md](../architecture/IntegrationStrategy.md)

---

## 1. Purpose

This PRD defines what Velora's MVP actually lets a user do — the product surface on top of the engineering foundation already specified in `docs/architecture/`. It intentionally does not re-derive technical design: where a requirement below implies a specific lifecycle, permission model, or data shape, it links to the architecture doc that already owns that detail rather than restating it. If this document and an architecture doc ever disagree on how something behaves, the architecture doc wins on *how*; this document wins on *whether and why* — that's a signal the two need to be reconciled, not a rule for picking a winner.

## 2. Problem Statement

Businesses run on software modules — a CRM here, a helpdesk there, a spreadsheet holding it all together — and increasingly bolt AI features onto each one independently. The result is fragmented automation with no shared memory, no shared context, and no single place a business owner can go to see "what is my software actually doing on my behalf right now." Velora's bet is that the more useful abstraction isn't another module — it's a **workforce**: named, accountable, manageable digital employees that share context about the business and can be hired, assigned, evaluated, and trusted with increasing autonomy over time, the way a real employee is.

## 3. Target Users & Personas

| Persona | Role in the system | Primary needs |
|---|---|---|
| **Founder / Business Owner** | `org_admin` ([Security.md §5](../architecture/Security.md#5-authorization-model)) | Set up the org, define Company DNA, see the whole workforce at a glance, trust that nothing autonomous happens without visibility |
| **Department Manager** | `department_manager` | Hire and configure Digital Employees for their department, set goals, review performance, approve flagged actions |
| **Team Member** | `member` | Collaborate with Digital Employees day-to-day — assign tasks, chat, review outputs — without needing admin access |
| **Viewer** (e.g., an investor, auditor, or exec without operational control) | `viewer` | Read-only visibility into activity, goals, and performance |

**[Assumption]** MVP targets small-to-mid-size businesses (roughly 5–200 employees) who currently have no dedicated engineering/ops team to build custom automation — they need Digital Employees to be genuinely self-service to configure, not something that requires a technical implementation partner. Confirm this matches the intended go-to-market before it drives onboarding-flow complexity decisions.

## 4. Core Product Loop

This is the single loop the MVP must support end-to-end before anything else is prioritized:

```
Create Org → Set up Company DNA → Create a Department → Hire a Digital Employee
   → Configure it (DNA binding, permission scope, autonomy) → Activate it
   → Assign it a Goal or Task → It works, within its autonomy level
   → Human reviews / approves flagged actions → Performance record accumulates
```

Every requirement in §6 exists to make one segment of this loop real. A feature that doesn't sit on this loop is, by definition, post-MVP (§7) unless it's a hard compliance/security requirement.

## 5. Core Concepts (Recap)

Full definitions live in [DomainModel.md](../architecture/DomainModel.md); this is only enough to read the requirements below without cross-referencing constantly.

- **Organization** — the account. **Department** — how work is delegated inside it.
- **Digital Employee** — a named, persistent AI agent with a role, a Department, a Company DNA binding, a permission scope, memory, and a performance record.
- **Company DNA** — the org's voice, knowledge, policies, and playbooks, versioned, shared by every Digital Employee in the org.
- **Goal → Project → Task** — outcome, initiative, atomic unit of work, in that order of granularity.
- **Autonomy level** (`autonomous` / `notify` / `approve`) — set per action type per Digital Employee; this is the primary trust dial a human controls.

## 6. Functional Requirements (MVP)

Each requirement includes acceptance criteria and a pointer to the architecture doc governing its behavior. Requirement IDs are stable — reference them in engineering tickets rather than restating the requirement text, so this document stays the single source of truth for *what*, and tickets stay focused on *how*.

### 6.1 Organization Onboarding

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| ORG-1 | A new user can create an Organization and becomes its first `org_admin`. | Org created with `status = trial`; user's `organization_memberships` row created with `role = org_admin`. See [Database.md §3.1](../architecture/Database.md#31-identity--organization). |
| ORG-2 | An org admin can invite teammates by email, assigning a role. | Invited user receives an email; on acceptance, `MembershipActivated` fires ([EventCatalog.md §5.1](../architecture/EventCatalog.md#51-identity--organization)). |
| ORG-3 | An org admin can create Departments with a name and function type. | At least the four seeded function types (Sales, Support, Finance, Ops) are selectable, plus Custom. |

### 6.2 Company DNA Setup

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| DNA-1 | A new org is guided through a structured DNA questionnaire (mission, tone, do's/don'ts) if it has no existing documentation to import. | Produces a `draft` `company_dna_versions` row; org cannot activate its first Digital Employee until a DNA version is `published` ([CompanyDNA.md §4.3](../architecture/CompanyDNA.md#43-versioning)). |
| DNA-2 | An org admin can instead (or additionally) upload documents or connect a knowledge source to seed DNA's Knowledge Layer. | Creates a `KnowledgeSource` with `destination = company_dna`; status visible through its processing pipeline ([StateMachines.md §5–6](../architecture/StateMachines.md#5-knowledge-source-lifecycle)). |
| DNA-3 | An org admin can publish a new DNA version, and see a diff against the previous version's compiled summary before doing so. | Publishing emits `CompanyDnaPublished`; existing active Digital Employees remain pinned to their prior version until explicitly upgraded ([CompanyDNA.md §4.3](../architecture/CompanyDNA.md#43-versioning)). |

### 6.3 Digital Employee Lifecycle

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| EMP-1 | A user with department-manager-or-above role can hire a Digital Employee from a template into a Department. | Creates an `ai_employees` row in `draft` ([AIEmployees.md §4](../architecture/AIEmployees.md#4-provisioning-flow)); template's default skills pre-selected. |
| EMP-2 | Before activation, the hiring user must bind a DNA version, confirm/adjust the permission scope, and set an autonomy level for each action type the role supports. | Cannot transition to `active` without all three set ([StateMachines.md §2](../architecture/StateMachines.md#2-digital-employee-lifecycle)); defaults to the template's recommended minimum scope and conservative (`approve`) autonomy for anything external or financial ([AIEmployees.md §6](../architecture/AIEmployees.md#6-human-oversight-model-autonomy-levels)). |
| EMP-3 | A user can rename, re-department, pause, resume, or retire a Digital Employee. | Each action emits its corresponding lifecycle event; pausing/retiring reassigns any `claimed`/`in_progress` tasks rather than stranding them. |
| EMP-4 | A user can view a Digital Employee's performance record: task success rate, escalation rate, cost-to-serve. | Sourced from the event stream, not a separately maintained score ([AIEmployees.md §9](../architecture/AIEmployees.md#9-performance-record)). |

### 6.4 Goals, Projects & Tasks

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| GOAL-1 | A department manager can state a goal in natural language with a target metric. | Produces a `proposed` Goal with a system-generated decomposition plan for review ([StateMachines.md §4](../architecture/StateMachines.md#4-goal-lifecycle)). |
| GOAL-2 | A human can approve, edit, or reject a proposed goal decomposition before it goes live. | Approval transitions the Goal to `active` and creates its initial Projects/Tasks; **[Assumption]** MVP does not ship auto-approval for any department — every Goal requires an explicit human approval step at launch, even though the architecture supports policy-driven auto-approval later ([original Goal Engine design, referenced in StateMachines.md §4](../architecture/StateMachines.md#4-goal-lifecycle)). Confirm this conservative default is acceptable for launch. |
| GOAL-3 | A Goal's progress is visible against its target metric, and flips to "at risk" automatically when progress stalls. | Reflects the Evaluation Loop's `GoalAtRisk` transition; visible on a dashboard, not just in event logs. |
| TASK-1 | A user can create an ad hoc Task not tied to any Goal, and assign it to a Digital Employee directly. | Task created with `goal_id = NULL`, `project_id = NULL`; still goes through the standard claim/execute lifecycle ([StateMachines.md §3](../architecture/StateMachines.md#3-task-lifecycle)). |
| TASK-2 | A user can see a Kanban-style board of Tasks per Department (`pending / claimed / in_progress / blocked / done / failed`). | Reflects real-time Task state, not a polled snapshot — via the Realtime Gateway. |

### 6.5 Human Oversight

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| OVR-1 | An action flagged `approve` queues visibly for the responsible human, with enough context to decide without digging through logs. | Surfaces the Decision Trace summary inline ([Observability.md §5](../architecture/Observability.md#5-decision-traces)) — what the Digital Employee wants to do and why — not just a bare approve/reject button. |
| OVR-2 | An action flagged `notify` executes immediately and surfaces a clear after-the-fact notification. | Delivered via the Notification Service; distinguishable in the UI from an `approve`-gated item awaiting action. |
| OVR-3 | A user can change a Digital Employee's autonomy level per action type at any time. | Takes effect on the next invocation; enforced by the Policy Engine, not by redeploying the agent ([AIEmployees.md §6](../architecture/AIEmployees.md#6-human-oversight-model-autonomy-levels)). |

### 6.6 Knowledge Management

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| KNOW-1 | A user can upload a document or connect a knowledge source scoped to a specific Department (rather than org-wide). | Creates a `KnowledgeSource` with that `department_id`; feeds that Department's Memory namespace by default ([Memory.md §3](../architecture/Memory.md#3-sharing-model)). |
| KNOW-2 | A user can see the processing status of an uploaded Knowledge Source and be notified if it fails. | Reflects [StateMachines.md §5](../architecture/StateMachines.md#5-knowledge-source-lifecycle); failure surfaces `error_class` in plain language, not a raw error code. |
| KNOW-3 | A user can delete a Knowledge Source and have it (and anything a Digital Employee learned from it) actually removed. | Triggers the redaction cascade ([Memory.md §6.2](../architecture/Memory.md#62-right-to-forget)) — this is a compliance requirement, not a nice-to-have, and must ship in MVP. |

### 6.7 Collaboration

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| COLLAB-1 | A user can chat directly with a Digital Employee outside of any specific Task. | Creates a `direct_chat` Conversation ([DomainModel.md §2.12](../architecture/DomainModel.md#212-conversation--message)). |
| COLLAB-2 | Multiple Digital Employees collaborating on one Task share a visible, coherent thread. | Reflects a `task_thread` Conversation; every message attributable to a specific sender, human or Digital Employee. |

### 6.8 Integrations (MVP Scope)

**[Assumption]** MVP ships with **Email and Slack only**, despite [IntegrationStrategy.md](../architecture/IntegrationStrategy.md) specifying the full connector pattern for seven providers. The Connector Framework is designed so the remaining providers (Google Workspace, Microsoft 365, GitHub, Jira, WhatsApp, generic Calendar) are additive post-MVP work, not a redesign — but confirm Email + Slack is actually sufficient for the earliest target customers before treating this as fixed.

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| INT-1 | An org admin can connect an email inbox to a Department. | OAuth flow per [IntegrationStrategy.md §3](../architecture/IntegrationStrategy.md#3-oauth-as-the-common-auth-backbone); inbound mail becomes Tasks/Conversations per Department routing rules. |
| INT-2 | An org admin can connect a Slack workspace. | Workspace-level OAuth; a Digital Employee posts under its own bot identity, never impersonating a human ([IntegrationStrategy.md §4](../architecture/IntegrationStrategy.md#4-provider-notes)). |
| INT-3 | A failed integration token refresh notifies the org admin rather than failing silently mid-task. | Reflects `IntegrationTokenRefreshFailed` ([EventCatalog.md §5.9](../architecture/EventCatalog.md#59-integration)). |

### 6.9 Billing & Plans

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| BILL-1 | An org on a `trial` plan is limited to a small number of active Digital Employees and a token/spend ceiling. | Enforced at the Model Gateway and Provisioning Service, not just displayed as a soft limit. |
| BILL-2 | A Department has a configurable monthly spend cap. | Enforced before costly operations execute, not reconciled after the fact ([Security.md §8.4](../architecture/Security.md#84-runaway-agent-loops--cost-bombs)). |
| BILL-3 | An org admin can see cost attributed per Digital Employee and per Department. | Sourced from Usage Records / Decision Trace cost telemetry ([AIEmployees.md §9](../architecture/AIEmployees.md#9-performance-record)). |

## 7. Out of Scope for MVP

Restated from the relevant architecture docs' own non-goals sections, gathered here so Product doesn't need to hunt through each one:

- Cross-organization Digital Employee interaction or any agent marketplace.
- Auto-approval of Goal decompositions (§6.4, GOAL-2) — every Goal requires human approval at launch.
- Integrations beyond Email and Slack (§6.8).
- MCP support, in either direction ([IntegrationStrategy.md §6](../architecture/IntegrationStrategy.md#6-future-mcp-support)).
- Per-Digital-Employee DNA overrides — DNA is org-scoped (department-scoped Process Layer additions excepted).
- A public partner API / marketplace surface.
- Self-service BYOK encryption UI (available to enterprise tenants at the infra level only).
- Dedicated-cell / silo infrastructure provisioning UI — available as a manual, sales-assisted process for enterprise deals, not self-service.

## 8. Success Metrics

**[Assumption]** These are proposed starting metrics, not yet validated against an actual funnel — revisit once there's real usage data.

| Metric | What it tells us |
|---|---|
| **Time-to-first-hire** | Minutes from org creation to first Digital Employee reaching `active`. Proxy for onboarding friction. |
| **Goal/Task completion rate** | Of Tasks claimed, % reaching `done` without escalation. Proxy for whether Digital Employees are actually capable of the work assigned. |
| **Escalation rate** | % of `approve`-gated actions vs. `autonomous` — should trend down per Digital Employee over time as trust is earned, per its performance record. |
| **Weekly active Digital Employees per org** | Adoption depth, not just account creation. |
| **Cost-to-serve vs. plan revenue** | Margin health — LLM inference cost is a real operating expense, not incidental infra ([Observability.md §3](../architecture/Observability.md#3-metrics)). |
| **Trial → paid conversion** | Standard SaaS funnel health. |

## 9. Release Phasing

| Phase | Scope |
|---|---|
| **MVP (this document)** | §6 in full, Email + Slack only, single-region, pool-tier tenancy only |
| **Phase 2** | Remaining integrations (Google Workspace, Microsoft 365, GitHub, Jira, Calendar); policy-driven Goal auto-approval; WhatsApp |
| **Phase 3** | Enterprise silo tier self-service provisioning; BYOK UI; MCP support; partner API |

Detailed sequencing belongs in `docs/product/Roadmap.md` (placeholder, not yet written) — this section only establishes that the phase boundary is deliberate, not an oversight.

## 10. Open Questions

Tracked here until resolved, then removed and reflected directly into the relevant section above:

1. Is Email + Slack actually the right MVP integration pair for the target persona (§3, §6.8), or does the earliest target customer need CRM/helpdesk connectivity from day one?
2. Should Goal auto-approval (§6.4) really wait for Phase 2, or is there a launch customer for whom that manual-approval-every-time friction kills adoption?
3. What is the actual trial plan's Digital Employee/spend ceiling (§6.9, BILL-1)? Placeholder numbers need a pricing decision this document doesn't own.
4. Pricing/packaging itself is explicitly out of scope for this PRD (business strategy, not engineering-adjacent product spec) — needs its own document once decided, referenced here.
5. **(New, from [UserJourney.md §3](./UserJourney.md#3-primary-journey-founder--org-admin--the-first-15-minutes))** Should DNA ingestion do structured entity extraction (auto-detect products, services, brand voice, suggested departments from an uploaded website/PDFs) rather than only chunk-and-summarize? This is a materially bigger build than DNA-1/DNA-2 as currently scoped — tentatively `DNA-4` — and needs sizing before it's treated as MVP rather than Phase 2.
6. **(New, from [UserJourney.md §3](./UserJourney.md#3-primary-journey-founder--org-admin--the-first-15-minutes))** Should Velora recommend specific Digital Employee roles based on the org's detected business type/departments, instead of (or alongside) browse-and-hire (EMP-1)? Tentatively `EMP-5` — depends on question 5 above, since a good recommendation needs the extraction it relies on.

## 11. Traceability

Every requirement ID above should be referenced by its corresponding engineering ticket at implementation time, and every new capability added post-MVP should get a new ID in the relevant §6 subsection (or a new subsection) rather than an unlabeled addition — this is what keeps "what does Velora's MVP actually do" answerable from this one document instead of reconstructed from a ticket backlog.
