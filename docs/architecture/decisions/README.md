# Architecture Decision Records

**Status:** Active

This folder holds short, numbered records of decisions that deviate from or meaningfully extend what's documented elsewhere in `docs/architecture/` — the kind of call a future engineer will reasonably ask "wait, why is it built this way?" about. See [EngineeringStandards.md §8](../../engineering/EngineeringStandards.md#8-documentation-standards) for when to write one.

An ADR is short on purpose: the decision, the alternatives considered, and the reasoning. It is not a design document — if the decision needs a full design doc, write that in the relevant `docs/architecture/` file and link to it from a short ADR.

## Template

```markdown
# ADR NNNN — Title

**Status:** Proposed | Accepted | Superseded by ADR NNNN
**Date:** YYYY-MM-DD

## Context
What situation/tension made a decision necessary.

## Decision
What we're doing.

## Alternatives Considered
What else we looked at, and why it lost.

## Consequences
What this makes easier, what it makes harder, what it defers.
```

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](./0001-event-store-implementation.md) | Event Store implementation: Postgres + Redis Streams instead of a broker (v1) | Accepted |
| [0002](./0002-organization-membership-self-visibility.md) | Organization membership self-visibility RLS policy | Accepted |
