# Implementation Roadmap & Future Scalability

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design, in collaboration with Frontend Engineering
**Depends on:** all other files in `docs/design/`

---

## 1. Principle: tokens before components, components before screens

The order below is deliberate and matters: implementing a signature molecule before its tokens exist means guessing at values that get thrown away; implementing a screen before its molecules exist means duplicating one-off styling that has to be un-tangled later. Each stage should be a small, reviewable PR (or a handful of them), matching EngineeringStandards.md §5's existing "small, single-purpose PRs" discipline — this is a design system rollout, not a single milestone, and shouldn't be treated as one giant undertaking.

## 2. Staged plan

### Stage 0 — Design foundation — **Complete**

**Revision note (post-implementation):** Stage 0 shipped with a broader scope
than originally written below — the user explicitly asked for the
application shell (header, icon rail, Meridian Line), layout primitives, a
small set of core UI components, and motion primitives alongside the token
layer, with the existing M4 frontend refactored onto all of it without
behavior change. Full detail: [Stage0-Migration.md](./Stage0-Migration.md).

- Extended `frontend/app/globals.css`'s `@theme` block with Ink/Paper/Slate/
  Signal + the four semantic ramps (DesignSystem.md §4), a type scale
  (§5.2), and motion easings/durations (§9) — then remapped the *existing*
  semantic tokens (`--background`, `--primary`, `--border`, `--destructive`,
  `--ring`, etc.) to point at these primitives, which reskinned `Button`/
  `Card`/`Input`/`Label` to Meridian with zero component code changes.
  Tailwind's default spacing scale already matched Meridian's 1:1 — no new
  spacing tokens were needed.
- Dropped the Geist webfont in favor of the system-font stack (§5.1).
- Built the application shell (`AppShell` = icon rail + header + Meridian
  Line) and wired it onto the Dashboard — the Meridian Line renders its
  real, honest dormant state (no fabricated activity/DNA data, since neither
  exists yet in M4).
- Built the primitives with a real, immediate consumer today: `Badge`,
  `Tooltip`, `Skeleton`, `LoadingState`, `FormError`, `LiveDot`,
  `CenteredScreen`. Primitives with no consumer yet (`Select`, `Checkbox`/
  `Switch`, `Dialog`/`Sheet`, `Table`, `Tabs`, `CommandPalette`, `Toast`
  wiring) stayed deferred, per this document's own principle below.
- **Verification:** `npm run lint` + `npm run build` clean; end-to-end
  Playwright smoke test against a running production build and the real
  backend, screenshots captured in both themes.

**Extension (post-implementation, `Stage0-Migration.md` §11):** a follow-up
brief asked for the remaining scope pulled forward too — `Avatar`,
`DropdownMenu`, `Dialog`, `Tabs`, `Separator`, `EmptyState`, `Toast` (all
built; `Dialog`/`Tabs`/`EmptyState`/`Toast` demonstrated on an internal
design-preview page, no real consumer yet), the layout primitives (`Stack`/
`Cluster`/`Grid`/`Section`/`ContentContainer`/`SplitPanel`/`PageHeader`),
elevation/scrim/layout-dimension tokens, and — overriding Stage 2 below —
all six signature molecules, built now as **presentation-only** components
with typed props and no real data source, demonstrated the same way. Real
data wiring for the molecules is still Stage 2 work; only their existence
as reusable components moved earlier. `Select`/`Checkbox`/`Switch`/`Table`/
`CommandPalette` remain deferred (Stage 1, below).

### Stage 1 — Primitives (remaining)

- What remains: `Select`/`Checkbox`/`Switch`/`Table`/`CommandPalette`,
  prioritized by which upcoming milestone needs them first (`Select`/
  `Switch` before Company DNA or Departments work; `CommandPalette` before
  any milestone adds a third top-level destination beyond Dashboard/
  Onboarding — the icon rail today has exactly one item).

### Stage 2 — Signature molecules: real data

- The six molecules themselves were built early (Stage 0's extension, as
  presentation-only components — see above). What's left is real data: each
  gets wired to its actual backend once that backend exists — Digital
  Employee Card to the roster, Autonomy Dial to the permission system, Goal
  Progress Ring to Goals, Approval Queue Item to the approval system,
  Decision Trace Timeline to Task history, and the full canvas-based Org
  Pulse (with animated task edges, per the `meridian.html` artifact) once
  real Digital Employees and Departments exist to animate — the DOM/SVG
  `OrgPulse` built in Stage 0 is a foundation, not that final version. No
  redesign needed for any of them; same typed props, real values.

### Stage 3 — Screens

- Apply the Wireframes.md layouts to real milestones as they're built (the Workforce Command Center's full Org Pulse arrives with the first milestone that has real Digital Employees, not before).
- Login/Register/Onboarding stay on `CenteredScreen` (Stage 0) — deliberately not wrapped in the full shell, per Journey 1's "momentum matters more than confirmation." The Dashboard now uses `AppShell` as of Stage 0.

## 3. What does not change

- The modular monolith / Clean Architecture backend is entirely unaffected — this is a frontend and design-token exercise.
- `lucide-react`, `class-variance-authority`, `tailwind-merge`, shadcn's copy-in-repo component pattern — all kept.
- No new frontend framework or state-management dependency is implied by anything in this system; the signature molecules are React components like any other, built from the existing primitive set.

## 4. Future scalability

- **Everything is a token, so re-skinning is a config change.** If Velora ever needs a white-label variant, an enterprise-tier visual distinction (Database.md's `isolation_tier = silo` tenants, say), or simply evolves the palette in year two, the change happens in the theme layer — component code never hard-codes a color, size, or duration value directly (this is a rule to enforce in code review, not just a hope).
- **The signature-molecule set is intentionally small and closed.** Future features should default to composing existing molecules and primitives; a genuinely new visual concept (a future "Company DNA diff view," say) earns its own molecule only when an existing one demonstrably can't express it — matching AGENTS.md's "avoid unnecessary complexity" applied to design, not just code.
- **Dark mode stays co-equal as the system grows** — every new token added to the system needs both a light and dark value defined together, never a light value with dark mode left to "just invert it later."
- **This document set versions alongside the product.** A future milestone that meaningfully extends Meridian (a new molecule, a revised color) updates the relevant file in the same PR as the implementation, exactly as EngineeringStandards.md §5 already requires for architecture docs — design debt (a real screen that quietly diverges from this spec) is exactly as costly as architecture debt, and should be caught the same way: in review, against a written spec, not from memory.
