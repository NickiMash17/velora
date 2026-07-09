# Product

**Status:** Active — [PRD.md](./PRD.md) written; the rest below is still placeholder.

This folder holds product specifications: what we're building, for whom, and why — as distinct from `architecture/`, which documents how it's built underneath.

## Contents

- [`PRD.md`](./PRD.md) — MVP product requirements: personas, the core product loop, functional requirements by area (with acceptance criteria tracing into `architecture/`), MVP scope boundaries, success metrics, release phasing, and open questions pending founder/product sign-off.

## Expected contents (not yet written)

- `Roadmap.md` — sequencing across sprints/quarters (PRD.md §9 has a first-pass phase boundary; this would own detailed sequencing)
- `PersonasAndUseCases.md` — deeper elaboration of PRD.md §3
- `Features/` — one spec per major feature area (e.g. `DigitalEmployeeBuilder.md`, `DepartmentManagement.md`, `GoalTracking.md`), each expanding a §6 subsection of PRD.md
- `MetricsAndSuccess.md` — deeper elaboration of PRD.md §8

## Ownership

Product, in collaboration with Engineering (architecture/) and Design (design/). Feature specs here should reference the relevant architecture doc rather than re-describing implementation details.
