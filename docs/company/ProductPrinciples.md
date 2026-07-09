# Product Principles

**Status:** Active — Foundational
**Owner:** Founders
**Referenced by:** [product/PRD.md](../product/PRD.md), [product/UserJourney.md](../product/UserJourney.md), [product/WireframeSpec.md](../product/WireframeSpec.md), [architecture/AIEmployees.md](../architecture/AIEmployees.md), [architecture/Security.md](../architecture/Security.md), [architecture/Observability.md](../architecture/Observability.md)

---

These principles guide every decision at Velora. They outrank a stakeholder's preference, a competitor's feature, and a shortcut that would ship faster — if a proposed feature or design fails one of these, that's the discussion to have before the how gets debated.

Each principle below is followed by a short note on where it already lives in the system, so this document stays a working reference — a thing you can point to and check against — rather than a wall poster. Where a principle isn't fully enforced yet, that's flagged as a gap, not glossed over.

---

## Principle 1

Every feature must pass the Employee Test.

If a Digital Employee behaves like a chatbot, we redesign it.

If it behaves like a trusted colleague, we keep it.

> **Where this lives today:** this is the reason a Digital Employee has identity, a Department, a performance record, and a lifecycle ([AIEmployees.md](../architecture/AIEmployees.md)) instead of being an API endpoint with a persona painted on. It's also why [UserJourney.md](../product/UserJourney.md) treats "employees introducing themselves" and "watching employees collaborate" as load-bearing moments, not decoration.
>
> **How to apply it in review:** if you can describe a proposed feature entirely in terms of "the user sends input, the system returns output," it hasn't passed the test yet — ask what a trusted colleague would do differently (follow up unprompted, flag their own uncertainty, remember the last conversation) and design toward that.

## Principle 2

Digital Employees own outcomes.

They do not merely answer questions.

> **Where this lives today:** the Goal → Project → Task model ([DomainModel.md §2.8–2.10](../architecture/DomainModel.md#28-goal)) exists specifically so work is tracked against an outcome and a success metric, not just a completed request. A Digital Employee's performance record ([AIEmployees.md §9](../architecture/AIEmployees.md#9-performance-record)) measures task success and escalation rate — outcome-shaped metrics — not response volume.
>
> **Tension to watch:** it's easy to build a feature that answers a question well and call that done. This principle is the check that stops there — the question is whether the Digital Employee could have taken the next step toward the actual outcome, not just answered accurately.

## Principle 3

Humans manage.

Digital Employees execute.

> **Where this lives today:** this is enforced structurally, not just culturally — [Security.md §5.1](../architecture/Security.md#51-delegated-authority) makes it a hard rule that a Digital Employee never carries more authority than the policy a human set, checked on every skill call, not just at task assignment. The autonomy model (`autonomous`/`notify`/`approve`, [AIEmployees.md §6](../architecture/AIEmployees.md#6-human-oversight-model-autonomy-levels)) is this principle made configurable rather than absolute — humans manage *how much* execution latitude a Digital Employee has, which is itself an act of management, not an exception to it.

## Principle 4

Every action must be explainable.

Users should understand:

- What happened
- Why it happened
- What evidence was used
- What will happen next

> **Where this lives today:** this is, almost verbatim, the definition of a Decision Trace ([Observability.md §5](../architecture/Observability.md#5-decision-traces)) — input context, retrieved memory, DNA version, model/prompt version, output, confidence, and policy checks passed, linked to the originating event and task. This principle is why Decision Traces are treated as a compliance artifact as much as a debugging tool, and why [WireframeSpec.md](../product/WireframeSpec.md) surfaces a Decision Trace summary inline at every approval point rather than behind a separate "logs" screen nobody opens.
>
> **Gap to watch:** "what will happen next" is the hardest of the four to satisfy today — Decision Traces capture what happened and why well; a forward-looking statement of consequence (what this action leads to, what's now irreversible) isn't yet a first-class field anywhere in the architecture. Worth raising as a follow-up to [Observability.md](../architecture/Observability.md) rather than assuming it's covered.

## Principle 5

Trust is more valuable than autonomy.

When uncertain, ask.

When confident, act.

> **Where this lives today:** the conservative-default-then-earn-trust arc is exactly what [UserJourney.md §5, "The Trust Ramp"](../product/UserJourney.md#5-the-trust-ramp-a-dedicated-journey) describes, and it's enforced the same way Principle 3 is — through the Policy Engine's autonomy gates, not through a Digital Employee's own self-assessment of its confidence. A Decision Trace's `confidence` field ([Observability.md §5](../architecture/Observability.md#5-decision-traces)) is the mechanism that could make "when uncertain, ask" concrete rather than aspirational — but see the tension below before treating it as solved.

## Principle 6

Every interaction should reduce founder workload.

If a feature doesn't save meaningful time, question why it exists.

> **Where this lives today:** this is the direct ancestor of `time-to-first-hire` and `escalation rate` as the leading success metrics in [PRD.md §8](../product/PRD.md#8-success-metrics) — both are, in effect, "is this actually saving time" measured two different ways (onboarding friction, and ongoing supervision burden). It's also why [UserJourney.md §3](../product/UserJourney.md#3-primary-journey-founder--org-admin--the-first-15-minutes) treats the permissions/autonomy screen as the single highest drop-off risk in the whole first session — a screen that asks a founder to do unpaid configuration work before they've seen any time saved is this principle's clearest violation risk in the current design.

## Principle 7

The product should feel like hiring people — not configuring software.

> **Where this lives today:** this is the throughline of the entire vocabulary choice across every doc in this repo — "hire," "Department," "performance record," "autonomy," not "instantiate," "namespace," "success rate," "permission scope." [UserJourney.md](../product/UserJourney.md) is essentially this principle applied to a single session end-to-end.

---

## Principle 5 vs. Principle 6: The Tension That Actually Drives the Design

These two principles are in direct, unavoidable tension, and it's worth naming explicitly rather than letting each read as independently obvious:

- Principle 5 says: when uncertain, ask a human.
- Principle 6 says: every interaction should save the founder time, and a feature that doesn't should be questioned.

Taken literally, "ask whenever uncertain" for a system that is *often* uncertain (which, honestly, most AI systems are, most of the time, on anything nontrivial) would produce a constant stream of approval requests — which is exactly the founder-workload cost Principle 6 exists to prevent. Neither principle is wrong; the resolution is that they operate on different timescales:

- **Principle 5 governs a single action, right now.** Ask this time, if this specific action is uncertain enough to warrant it.
- **Principle 6 governs the trend, over time.** The autonomy level for *this class of action* should be moving toward requiring fewer asks, as evidence (the performance record) accumulates — that's the entire point of the Trust Ramp.

In other words: Principle 5 is about *this decision*; Principle 6 is the reason the system should be getting better at not needing to make Principle 5 apply as often, for the same Digital Employee, on the same kind of action, over time. A design that satisfies Principle 5 in a way that never improves — a Digital Employee still asking about the same routine action after three months — has failed Principle 6, even though each individual "ask" was correct in isolation. This is the standard every autonomy-related feature should be checked against, not just "does it ask when uncertain."

## How to Use This Document

- In design or code review, citing "Principle N" is a legitimate, sufficient objection to a proposed approach — it should trigger a real conversation, not a dismissal, but it doesn't need to be re-argued from first principles every time.
- When a new feature is proposed, run it against Principle 1 (the Employee Test) first — it's the fastest filter, and most features that fail it fail visibly once asked.
- When two principles genuinely conflict (as with §Principle 5 vs. 6 above), the resolution is almost always a timescale or evidence question, not a matter of picking a winner — look for the mechanism (like the Trust Ramp) that lets both be true at different points in the same relationship.
- If a shipped feature can't point to where in `architecture/` or `product/` it's actually enforced — the way each principle above does — treat that as unfinished, not as "covered by intent."
