# Design

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design, in close collaboration with Frontend Engineering

This folder holds Velora's design system — named **Meridian** — and the UX guidelines the frontend (Next.js 15 + Tailwind + shadcn/ui) implements against. It was written as a complete proposal, before any implementation, per the product-design review this system originated from; see [Roadmap.md](./Roadmap.md) for how it rolls into the codebase in stages once approved.

## Contents

- [DesignSystem.md](./DesignSystem.md) — design philosophy, brand personality, visual identity, color system, typography, spacing, iconography, elevation, motion. Start here.
- [ComponentGuidelines.md](./ComponentGuidelines.md) — component philosophy, the primitive inventory, Velora's signature molecules (Digital Employee Card, Autonomy Dial, Goal Progress Ring, Approval Queue Item, Decision Trace Timeline, Org Pulse), navigation philosophy.
- [UXPrinciples.md](./UXPrinciples.md) — empty/loading/error/success state philosophy, dashboard philosophy, AI Employee visualization philosophy. Where "Digital Employees, not software modules" (AGENTS.md) becomes concrete interaction rules.
- [Accessibility.md](./Accessibility.md) — the WCAG 2.1 AA baseline, color-independent status signaling, and responsive/breakpoint behavior.
- [UserJourneys.md](./UserJourneys.md) — five key emotional journeys (first organization, first hire, watching work happen, reviewing analytics, an approval request) specified as experiences, not page inventories.
- [Wireframes.md](./Wireframes.md) — low-fidelity structural layouts for the global shell, Dashboard, Org Pulse, Employee Profile, Decision Trace, and Goals board.
- [Roadmap.md](./Roadmap.md) — the staged implementation plan (tokens → primitives → molecules → screens) and how the system scales as the product grows.
- [Stage0-Migration.md](./Stage0-Migration.md) — the Stage 0 implementation: token layer, application shell, new primitives, and the behavior-preserving refactor of the M4 frontend onto them. Screenshots in `screenshots/`.

## Ownership

Design, in close collaboration with Frontend Engineering. Component-level decisions here stay implementation-agnostic where possible; concrete Tailwind/shadcn wiring belongs in the frontend codebase, not here.
