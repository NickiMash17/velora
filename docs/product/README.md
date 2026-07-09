# Product

**Status:** Active — [PRD.md](./PRD.md) written; the rest below is still placeholder.

This folder holds product specifications: what we're building, for whom, and why — as distinct from `architecture/`, which documents how it's built underneath.

## Contents

- [`PRD.md`](./PRD.md) — MVP product requirements: personas, the core product loop, functional requirements by area (with acceptance criteria tracing into `architecture/`), MVP scope boundaries, success metrics, release phasing, and open questions pending founder/product sign-off.
- [`UserJourney.md`](./UserJourney.md) — narrative walkthrough of PRD.md's core loop per persona, the "trust ramp" (how autonomy is meant to expand over time), edge-case journeys (failure, deletion, integration loss), and open UX questions for Design.
- [`WireframeSpec.md`](./WireframeSpec.md) — every MVP screen's purpose, components, actions, and behavior in every state (empty/loading/error/success), plus role visibility and navigation. No visual design — that's `docs/design/`'s job.

## Expected contents (not yet written)

- `Roadmap.md` — sequencing across sprints/quarters (PRD.md §9 has a first-pass phase boundary; this would own detailed sequencing)
- `PersonasAndUseCases.md` — deeper elaboration of PRD.md §3 / UserJourney.md
- `Features/` — one spec per major feature area (e.g. `DigitalEmployeeBuilder.md`, `DepartmentManagement.md`, `GoalTracking.md`), each expanding a §6 subsection of PRD.md
- `MetricsAndSuccess.md` — deeper elaboration of PRD.md §8

## Ownership

Product, in collaboration with Engineering (architecture/) and Design (design/). Feature specs here should reference the relevant architecture doc rather than re-describing implementation details.
