# Design

**Status:** Placeholder

This folder holds the design system and UX guidelines that the frontend (Next.js 15 + Tailwind + shadcn/ui) implements against.

## Expected contents (not yet written)

- `DesignSystem.md` — color, typography, spacing, component tokens (should map directly to Tailwind theme config once frontend work starts)
- `ComponentGuidelines.md` — when to use which shadcn/ui primitive, composition patterns
- `UXPrinciples.md` — how a "Digital Employee" should feel to manage in the UI — this is where the product philosophy (Digital Employees, not software modules) becomes concrete interaction patterns
- `Accessibility.md` — baseline a11y requirements

## Ownership

Design, in close collaboration with Frontend Engineering. Component-level decisions here should stay implementation-agnostic where possible; concrete Tailwind/shadcn wiring belongs in the frontend codebase, not here.
