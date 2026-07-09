# Memory

**Status:** v1.0 — Foundational
**Owner:** AI Runtime / Platform Engineering
**Depends on:** [Database.md](./Database.md), [CompanyDNA.md](./CompanyDNA.md), [AIEmployees.md](./AIEmployees.md)
**Stack:** Redis (working memory), PostgreSQL (episodic/relational), Qdrant (semantic/procedural, vector)

---

## 1. Purpose

Memory is what lets a Digital Employee behave like it has actually worked at the company for a while — it remembers what happened, what it learned about the business and its customers, and what approaches worked. Memory is deliberately separated from orchestration (the Goal Engine and Agent Collaboration layers never touch storage directly — everything goes through the Memory Service) and from Company DNA (org-authored, static governance vs. agent-generated, dynamic observation — see [CompanyDNA.md §2](./CompanyDNA.md#2-why-dna-is-architecturally-separate-from-memory)).

## 2. Memory Taxonomy

| Type | Description | Storage | Write trigger |
|---|---|---|---|
| **Working memory** | Current task/conversation context | Redis, TTL-bound, per invocation | Start of invocation, discarded after |
| **Episodic memory** | "What happened" — interactions, decisions, outcomes | Event Store (source of truth) + summarized rollups in Postgres | Every meaningful agent action/observation |
| **Semantic memory** | Facts, entities, relationships learned about the business/customers | Qdrant, namespaced per org, tagged per department | Extraction step after task completion |
| **Procedural memory** | Learned "how to do this task well" patterns, successful playbooks | Qdrant + Skill Catalog feedback loop | Outcome-linked, after task success/failure evaluation |

This taxonomy is intentionally the same shape as the Company DNA layers are *not* — DNA is what the org tells the Digital Employee; memory is what the Digital Employee has itself observed. A Digital Employee's procedural memory might discover "customers in the EU timezone respond better to emails sent before 9am local time" — that's memory, not DNA, because no human declared it as policy; it was learned and remains revisable as evidence changes.

## 3. Sharing Model

Memory is namespaced hierarchically: **`organization → department → ai_employee`.**

- An AI Employee, by default, reads/writes its own namespace and its Department's shared namespace.
- Cross-department or org-wide memory access requires an **explicit policy grant** via the Policy Engine — not a default. Finance's Digital Employee does not automatically see Sales' customer notes, mirroring real-world confidentiality boundaries within a company.
- This hierarchy is enforced at the same layer as relational tenant isolation: every memory read/write call to the Memory Service requires `organization_id` and the caller's namespace scope; there is no "query all memory" method exposed to agent-facing code.

## 4. Write Path

Every meaningful agent action or observation is emitted as an event (consistent with the platform-wide principle that state changes are event-derived, not the reverse) and flows:

```
Agent action → Event Bus → Memory Indexing Service → {
    embed + write to Qdrant (semantic/procedural)
    write structured row to Postgres (episodic, exact-match/relational queries)
}
```

This **dual-write** (vector + relational) is deliberate, not redundant: Qdrant supports "what does this Digital Employee know that's *similar* to X," while Postgres supports "show me every action taken on Account X, in order" — an audit-style query that semantic similarity search cannot answer precisely. Both are downstream consumers of the same event, so they never drift out of sync with each other or with the Audit Log ([Database.md §3.6](./Database.md#36-audit--metering-relational-projections)).

## 5. Retrieval Path

At invocation time, the Agent Collaboration Layer issues a single **memory retrieval request** to the Memory Service — agents never query Qdrant or Postgres directly. The request is:

- **Hybrid** — combines semantic similarity (Qdrant), recency weighting, and explicit entity match (e.g., "this ticket is about Account X" → prioritize memory tagged with that account).
- **Scoped** — to the calling Digital Employee's namespace permissions (§3), enforced server-side in the Memory Service, not trusted from caller input.
- **Token-budgeted** — returns a ranked context bundle sized to fit the remaining prompt budget after DNA and system instructions are accounted for, so retrieval never silently blows the context window.

## 6. Memory Governance

### 6.1 Retention

Retention policies are set per organization (compliance-driven — e.g., a 90-day PII retention limit for a regulated tenant) and enforced by a background purge job triggered off org/department settings, not by ad hoc manual cleanup.

### 6.2 Right-to-Forget

Deleting a customer record emits a cascading redaction event (`memory.redacted`) consumed by the Memory Indexing Service, which scrubs matching entries in both Qdrant and Postgres. Because episodic memory's source of truth is the Event Store, redaction operates on the derived projections and the vector index — the underlying event itself may be retained in a redacted/tombstoned form for audit continuity depending on the org's compliance tier, per [Security.md §9](./Security.md#9-compliance-posture).

### 6.3 Provenance

Every memory entry retains a pointer back to its source event. This means any fact a Digital Employee "knows" is traceable to *why* it knows it — which document, which conversation, which task. This is not optional metadata: it is the primary tool for debugging hallucination-like behavior ("why did it say that?") and for satisfying an auditor's "prove this Digital Employee had a legitimate basis for this action."

## 7. Data Model Notes

- Qdrant collections are namespaced per organization (`memory_{organization_id}`), with `department_id` and `ai_employee_id` stored as payload fields for filtered search within the collection — not separate collections per department, to avoid an unbounded proliferation of small collections as departments are created/renamed.
- Redis working-memory keys follow `working:{organization_id}:{ai_employee_id}:{invocation_id}`, TTL set to comfortably exceed the longest expected invocation, and are never treated as durable — anything that must survive past the invocation is written through the event-driven path in §4, not left in Redis.
- Postgres episodic rollups reference `organization_id`, `department_id`, and `ai_employee_id` directly (not just via join to `ai_employees`) on hot query paths, to keep the same composite-index-first indexing discipline as the rest of the schema ([Database.md §4](./Database.md#4-indexing-strategy)).

## 8. Non-Goals (v1)

- No org-wide "global memory" tier above the organization namespace — memory never crosses tenant boundaries, full stop, consistent with the platform's non-negotiable tenant isolation principle.
- No agent-to-agent direct memory sharing outside the department/org hierarchy in §3 — cross-boundary sharing is always mediated by an explicit policy grant, never a side channel.
- No client-side or agent-local memory caching that outlives an invocation — reinforcing [AIEmployees.md §7](./AIEmployees.md#7-execution-model)'s statelessness requirement; anything durable goes through the Memory Service.
