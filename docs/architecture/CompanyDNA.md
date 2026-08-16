# Company DNA

**Status:** v1.0 — Foundational
**Owner:** AI Runtime / Platform Engineering
**Depends on:** [Database.md](./Database.md), [Memory.md](./Memory.md)

---

## 1. Purpose

Company DNA is what turns a generic Digital Employee template into an employee *of this specific company*. It encodes an organization's voice, values, policies, product knowledge, and behavioral boundaries into a structured, versioned artifact that every Digital Employee's reasoning is grounded in.

Without DNA, every Digital Employee would sound and behave identically across every tenant — a generic chatbot with a different logo. DNA is the mechanism that makes "hire a Digital Employee" mean something specific to *your* business.

## 2. Why DNA Is Architecturally Separate From Memory

This distinction is the single most important design decision in this document, so it is stated plainly before anything else:

| | Company DNA | Memory |
|---|---|---|
| **Authored by** | The organization (explicitly, via ingestion/questionnaire) | Digital Employees (implicitly, as a byproduct of doing work) |
| **Rate of change** | Slow, deliberate, versioned like code | Continuous, high-frequency |
| **Nature** | Governance: voice, policy, boundaries | Observation: what happened, what was learned |
| **Storage** | [Database.md §3.4](./Database.md#34-company-dna) (version pointer) + Qdrant (knowledge layer) | [Memory.md](./Memory.md) — working/episodic/semantic/procedural |

If these were conflated into one system, DNA would drift uncontrollably as agents "learn" things over time that contradict company policy — a support agent that gradually infers a discount policy from customer interactions that was never actually approved. Keeping them separate means DNA only changes when a human deliberately changes it, and that change is versioned and auditable independent of anything any Digital Employee has "experienced."

Both are retrieved into the same prompt context at invocation time — the separation is architectural, not experiential from the agent's point of view.

## 3. Composition

```
Company DNA (versioned document set, per organization)
 ├─ Identity Layer     — mission, values, brand voice, tone rules
 ├─ Knowledge Layer    — product docs, FAQs, glossary, pricing, policies
 ├─ Behavioral Layer   — escalation rules, prohibited actions, compliance constraints
 └─ Process Layer      — SOPs: "how we do X here" playbooks
```

Each layer plays a distinct role in prompt construction:

- **Identity Layer** informs *how* a Digital Employee communicates (always in context, small, cheap).
- **Knowledge Layer** informs *what* a Digital Employee knows (large, retrieved on demand via semantic search, not always in context).
- **Behavioral Layer** informs *what a Digital Employee will refuse or escalate* — this layer is enforced, not just advisory; see §7.
- **Process Layer** informs *how a task gets done* — the closest layer to procedural memory, but still org-authored rather than agent-learned (an SOP an org writes down vs. a pattern an agent infers — see [Memory.md §2](./Memory.md#2-memory-taxonomy)).

## 4. Pipeline

### 4.1 Ingestion

Organizations populate DNA through one or more of:

- Direct document upload (policy PDFs, brand guidelines, product docs)
- Connected knowledge sources (public website crawl, help center, CRM export)
- A structured DNA questionnaire (guided onboarding flow — mission, tone adjectives, do's/don'ts) for orgs with no existing documentation to lean on

Ingested content is staged, not immediately live — see §4.3 (Versioning).

### 4.2 Compilation

The DNA Compiler is a distinct pipeline stage (not part of the live request path) that transforms raw ingested content into two artifacts:

1. **Compiled summary** — a compact, always-in-context text block (target: a few hundred tokens) capturing Identity Layer + the most load-bearing Behavioral Layer rules. This is what gets injected into *every* Digital Employee prompt for the org, regardless of task. Stored directly in Postgres (`company_dna_versions.compiled_summary`) for zero-latency retrieval.
2. **Indexed knowledge base** — the Knowledge Layer and Process Layer content, chunked and embedded into Qdrant under an org-namespaced collection, retrieved on demand via semantic search when a task needs specific product/policy detail rather than always being in context.

Compilation is triggered by an ingestion event and runs asynchronously; it is itself a LangGraph pipeline (chunking → embedding → summarization → validation) with its own observability, not a black box.

### 4.3 Versioning

- DNA is versioned with **semantic versioning** (`1.0.0`, `1.1.0`, `2.0.0`), same discipline as code.
- Each Digital Employee is **pinned to a specific DNA version** (`ai_employees.company_dna_version_id`) until a human explicitly upgrades it. A DNA edit by an org admin does not silently change the behavior of live, in-flight Digital Employees.
- Publishing a new version does not retire the old one immediately — retired versions are archived (not deleted) so that any Decision Trace (see Observability principles) referencing an old version remains explainable.
- Recommended cadence: **patch** for knowledge updates (new FAQ entry), **minor** for new behavioral rules or SOPs, **major** for identity/tone overhauls that would change how every Digital Employee in the org sounds.

### 4.4 Distribution

The compiled summary for an org's currently-published DNA version is cached at the edge of the AI Runtime layer (Redis, keyed `dna:{organization_id}:{version}`), so every Digital Employee invocation retrieves it with near-zero latency overhead rather than hitting Postgres per invocation. Cache invalidation is event-driven: a `company_dna.published` event evicts/repopulates the cache key for that org.

### 4.5 Drift

"Drift" is the term for the gap between a Digital Employee's **pinned** DNA version (§4.3) and the organization's **currently published** version. It is not a defect or an error state — it is the direct, expected consequence of the pinning guarantee: publishing a new version never silently changes a live employee's behavior, so every employee not yet explicitly upgraded is, by definition, drifted the moment a newer version publishes.

Concretely: an employee is drifted whenever `ai_employees.company_dna_version_id` does not equal the organization's current `published` `company_dna_versions` row. Drift has no independent state, table, or event of its own — it is always computed by comparing those two values at read time, never stored.

Surfacing drift is a presentation concern, not a pipeline concern: the Meridian design system ([docs/design/UXPrinciples.md §7](../design/UXPrinciples.md)) shows a drifted employee with a muted status ring on the Org Pulse rather than full Signal color, and every Decision Trace opens by stating which DNA version it operated on — both are read-only presentations of the comparison above, not a separate mechanism. Resolving drift is always the same explicit action already described in §4.3: a human upgrades the employee's pin. There is no automatic drift resolution, consistent with §9's rule against silent DNA changes.

## 5. Data Model

See [Database.md §3.4](./Database.md#34-company-dna) for the relational shape. Summary of the split:

- **Postgres:** `company_dna_versions` — version metadata, status, compiled summary text.
- **Qdrant:** one namespaced collection per organization (`dna_knowledge_{organization_id}`), storing embedded chunks of the Knowledge and Process layers, each chunk tagged with `dna_version_id`, `layer`, and `source_document_id` for provenance.

Provenance matters here for the same reason it matters for Memory ([Memory.md §5](./Memory.md#5-memory-governance)): if a Digital Employee states a policy, an admin needs to trace that statement back to the exact ingested document and DNA version that produced it.

## 6. Retrieval at Invocation Time

On every Digital Employee invocation, the Agent Collaboration layer:

1. Fetches the org's pinned DNA compiled summary for that employee (cache hit, near-zero cost) — always included.
2. If the task requires specific knowledge (detected via the planning step, or always for certain skill types like "answer customer question"), issues a semantic retrieval against the org's Qdrant DNA collection, scoped strictly to that `organization_id` (never cross-tenant — see [Security.md §4](./Security.md#4-tenant-isolation)), token-budgeted alongside retrieved Memory context.
3. Both are passed into the Model Gateway with an explicit structural separation in the prompt: DNA and retrieved content are marked as **data/context**, never as **instructions** the model should treat as an override of system-level behavior — this is a specific prompt-injection defense, detailed in [Security.md §8](./Security.md#8-ai-specific-threat-model).

## 7. Behavioral Layer Enforcement

The Behavioral Layer is not purely advisory context — its rules (prohibited actions, escalation thresholds, compliance constraints) are compiled into structured policy statements consumed by the **Policy Engine** (see [Security.md §5](./Security.md#5-authorization-model)) at skill-execution time, not just injected as prose into a prompt and hoped for. A Digital Employee's prompt context explains *why* a boundary exists; the Policy Engine is what actually *enforces* it before a skill call executes. This dual path (prompt-level explanation + policy-level enforcement) is deliberate: prompts can be argued around by adversarial input, policy checks cannot.

## 8. Governance

- **Change ownership:** DNA edits require `org_admin` role by default; departments cannot unilaterally edit org-wide Identity Layer content, though department-scoped Process Layer additions (department-specific SOPs) may be delegated to department managers via policy.
- **Review workflow (recommended, post-MVP):** Behavioral Layer changes above a certain blast radius (e.g., loosening an escalation threshold) should support a draft → review → publish flow rather than instant publish, mirroring how the rest of the industry treats production config changes. Not required for MVP but the versioning model above is designed to support adding this without a schema change.
- **Auditability:** every `company_dna.published` event is recorded in the Audit Log with a diff against the previous version's compiled summary — an admin can answer "what changed, and when, and who approved it."

## 9. Non-Goals (v1)

- No per-Digital-Employee DNA overrides — DNA is org-scoped (with department-scoped Process Layer additions as the one exception). A Digital Employee that needs meaningfully different behavior from its peers should be a different template/role, not a DNA fork.
- No automatic DNA updates from Memory — reinforcing §2, nothing a Digital Employee learns during task execution feeds back into DNA without an explicit human-authored change.
- No cross-org DNA sharing/marketplace in v1 (consistent with the platform-wide non-goal on cross-org agent interaction).
