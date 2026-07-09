# AI Employees (Digital Employees)

**Status:** v1.0 — Foundational
**Owner:** AI Runtime / Platform Engineering
**Depends on:** [Database.md](./Database.md), [CompanyDNA.md](./CompanyDNA.md), [Memory.md](./Memory.md), [Security.md](./Security.md)

---

## 1. Purpose

This document defines the domain model, lifecycle, and execution semantics of a **Digital Employee** — the core unit of Velora's product. Digital Employees are not a UI skin over a chatbot API; they are first-class runtime entities with identity, permissions, memory, and a lifecycle, provisioned and managed the way a real business manages staff.

Everything in this document should reinforce one framing: a Digital Employee is hired, assigned, evaluated, and can be retired — not "called" like a function.

## 2. Domain Model

A Digital Employee has:

| Attribute | Description |
|---|---|
| **Identity** | A machine credential, name, avatar — e.g., "Riley, Support Agent." Never a copy of a human's credentials. |
| **Role / Template** | Origin in the Skill Catalog (`ai_employee_templates`) — defines default skills and a system-prompt scaffold. |
| **Department assignment** | Exactly one `department_id` at a time — the primary scope for permissions and budget. |
| **Company DNA binding** | A pinned `company_dna_version_id` — see [CompanyDNA.md §4.3](./CompanyDNA.md#43-versioning). |
| **Permission scope** | What data, tools, and spend it can touch — enforced by the Policy Engine, not self-declared. |
| **Memory namespace** | Its own working memory plus read access to its department's shared namespace — see [Memory.md §3](./Memory.md#3-sharing-model). |
| **Performance record** | Task success rate, escalation rate, cost-to-serve — visible to human managers like a real employee review. |
| **Autonomy configuration** | Per action-type: `autonomous` / `notify` / `approve` — see §6. |

Relational shape: [Database.md §3.3](./Database.md#33-ai-workforce).

## 3. Lifecycle

```
Draft → Configured → Active ⇄ Paused → Retired
```

| State | Meaning | Entry condition |
|---|---|---|
| `draft` | Template selected, not yet usable | Provisioning initiated |
| `configured` | DNA + permissions bound | Department assignment, DNA binding, and permission scope all set |
| `active` | Executing tasks | Explicitly activated by a human (org admin or department manager) |
| `paused` | Temporarily disabled | Manual pause, or automatic pause on policy violation / budget exhaustion |
| `retired` | Archived | Explicit retirement — memory and audit history retained, not deleted |

Every transition emits an event (`ai_employee.hired`, `.activated`, `.paused`, `.retired`) consumed by:

- **Billing** — seat metering keys off `active` status.
- **Audit Log** — every transition is independently attributable and timestamped.
- **Goal Engine / Task Board** — a `.paused` or `.retired` transition triggers reassignment of any `claimed`/`in_progress` tasks rather than leaving them stranded.

A Digital Employee **cannot skip `configured`** — a Digital Employee without a bound DNA version and an explicit permission scope cannot be activated. This is enforced at the Provisioning Service level, not left to UI validation.

## 4. Provisioning Flow

1. A human (via BFF) selects a template from the Skill Catalog and a target Department.
2. Provisioning Service creates the `ai_employees` row in `draft`, generates its **machine identity** (see §5), and binds the template's default skill set.
3. Human configures: DNA version (defaults to the org's currently published version), permission scope (defaults to the template's recommended minimum, adjustable but never expandable beyond what the Department's own policy allows — see [Security.md §5](./Security.md#5-authorization-model)), and autonomy levels per action type.
4. On confirmation, state moves to `configured`, then `active` (may be combined into one confirmation step in the UI — this document defines the state machine, not the click-flow).

## 5. Identity & Machine Credentials

Every Digital Employee has its own scoped service credential — a short-lived signed token, automatically rotated — never a copy of a human's session or a shared "system" account. This is the mechanism that makes every action attributable to a specific Digital Employee rather than to an ambiguous "the AI did it."

Full mechanics (token structure, rotation, delegated-authority chain when acting "on behalf of" a human) are defined in [Security.md §2](./Security.md#2-identity-model) — this document only asserts the requirement: **no Digital Employee action is ever unattributable.**

## 6. Human Oversight Model (Autonomy Levels)

Every Digital Employee has a configurable autonomy level **per action type** (not one global setting):

- **Autonomous** — executes without approval.
- **Notify** — executes, then notifies a human after the fact.
- **Approve** — queues for human sign-off before executing.

This is enforced by the Policy Engine at skill-invocation time, not hardcoded into the agent's own reasoning — which means autonomy can be tightened or loosened org-wide or department-wide via policy change, without redeploying or reconfiguring any individual Digital Employee. A newly hired Digital Employee should default to conservative autonomy (`approve` for anything with external or financial effect) until its performance record justifies loosening it — this is a recommended default, enforced at the template level, not a hard platform rule.

## 7. Execution Model

**Digital Employees are not long-running processes.** There is no persistent worker holding a Digital Employee's "session" in memory. Each invocation is a stateless activation of the Agent Collaboration Layer (implemented as a LangGraph graph), triggered by one of:

- An incoming event (new support ticket, new lead, inbound email)
- A scheduled goal check-in (cron-like, from the Goal Engine)
- A direct human request (chat message via the Realtime Gateway)

On each invocation, the runtime:

1. Loads the Digital Employee's identity and machine credential.
2. Loads its pinned Company DNA (compiled summary, cached — [CompanyDNA.md §6](./CompanyDNA.md#6-retrieval-at-invocation-time)).
3. Loads relevant Memory (working + retrieved episodic/semantic — [Memory.md §4](./Memory.md#4-retrieval-path)) scoped to its namespace permissions.
4. Loads current goal/task context from the Task Board.
5. Executes the LangGraph graph — planning, tool/skill calls (via Skill Runtime, each call policy-checked), and response generation.
6. Emits events for every meaningful action (`skill.invoked`, `task.completed`, etc.) and writes new memory back through the Memory Service.

This statelessness is deliberate: **any worker node can pick up any invocation**, which gives horizontal scalability and safe failover for free, and keeps the runtime consistent with the modular-monolith-first infra decision — invocation handling scales by adding worker processes/replicas, not by pinning agents to machines.

## 8. Collaboration

Digital Employees coordinate with each other and with humans via the Agent Collaboration Layer's shared Task Board (per Department) and event-based messaging — never direct agent-to-agent RPC. Collaboration patterns (direct handoff, broadcast/subscribe, supervisor/worker, human-in-the-loop relay) and conflict resolution are defined in the platform-level Agent Collaboration design (companion doc, not duplicated here) — the relevant constraint for AI Employee identity is that a Digital Employee's contribution to a shared task remains individually attributable even when multiple Digital Employees work the same task.

## 9. Performance Record

Every Digital Employee accumulates a performance record derived from the event stream (not a separately maintained mutable score):

- **Task success rate** — completed vs. failed/escalated tasks.
- **Escalation rate** — how often it hands off to a human vs. resolves autonomously.
- **Cost-to-serve** — LLM token cost + paid skill invocations, attributed via the Model Gateway's per-`ai_employee_id` cost telemetry.

This is surfaced to human managers as a review-like view — consistent with the product framing of managing a workforce, not monitoring a script. It is also the primary input a human uses to decide whether to loosen a Digital Employee's autonomy configuration (§6).

## 10. Non-Goals (v1)

- No Digital Employee-initiated self-modification of its own permission scope, DNA binding, or autonomy level — all of these require explicit human action.
- No cross-organization Digital Employee interaction (consistent with the platform-wide non-goal).
- No persistent in-process agent state — reinforcing §7; anything that looks like it needs to persist between invocations belongs in Memory, not in a long-lived process.
