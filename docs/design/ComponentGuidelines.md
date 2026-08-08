# Component Guidelines

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design, in collaboration with Frontend Engineering
**Depends on:** [DesignSystem.md](./DesignSystem.md)

---

## 1. Component philosophy

**Two tiers, deliberately unbalanced in how much attention each gets.**

1. **Primitives** — button, input, card, dialog, table, tag. These should be as plain and invisible as possible: correct, accessible, consistent, and utterly unremarkable. Their entire job is to disappear so tier 2 stands out. Nearly all of Velora's screens are built almost entirely from primitives — that's correct, not a gap.
2. **Signature molecules** — a small, fixed set of components that exist only in Velora and carry the actual visual identity: the Meridian Line, the Org Pulse (its expanded form), the Digital Employee Card, the Autonomy Dial, the Goal Progress Ring, the Approval Queue Item, the Decision Trace Timeline (full list and rationale in §3). These are where Meridian's "instrumentation, not illustration" idea (DesignSystem.md §3.1) actually lives. **Revision note:** the Meridian Line / Org Pulse is no longer "one of the six" — per the post-review refinement, it is Velora's central, load-bearing visual identity, present on every screen, not a widget confined to one page. See §3's Org Pulse entry and [UXPrinciples.md §6](./UXPrinciples.md#6-ai-employee-visualization-philosophy--the-org-pulse-in-full) for the full reasoning.

**The failure mode this guards against:** a design system that tries to make *every* component distinctive ends up visually noisy and, paradoxically, generic — because "everything is special" reads the same as "nothing is." Meridian makes a small number of things unmistakable and lets everything else get out of the way.

### 1.1 Composition over invention

Match the pattern already established in `frontend/components/ui/` (a `cva`-based variant API, `cn()` for class merging, Radix/Base UI primitives underneath where real interaction behavior is needed — focus trapping, portal rendering, keyboard nav). New primitives should be added the same way, not invented from scratch with a different pattern. Signature molecules compose *from* primitives (a Digital Employee Card is a `Card` with a specific, fixed internal layout) rather than being built as one-off bespoke markup — this is what keeps them maintainable once there are dozens of Digital Employees on screen at once.

## 2. Primitive inventory

**Built (Stage 0 — `docs/design/Stage0-Migration.md`):** `Button`, `Card`
(+ Header/Title/Description/Action/Content/Footer), `ThemeToggle`, `Input`,
`Label`, `Badge`, `Tooltip`, `Skeleton`, `LoadingState`, `FormError`,
`LiveDot`, `Avatar`, `DropdownMenu`, `Dialog`, `Tabs`, `Separator`,
`EmptyState`, `Toast` (typed helper over `sonner`). Layout primitives:
`CenteredScreen`, `Stack`, `Cluster`, `Grid`, `Section`, `ContentContainer`,
`SplitPanel`, `PageHeader`. Shell: `AppShell`, `Header`, `IconRail`,
`MeridianLine`, `AccountMenu`.

Needed, not yet built (ordered by which milestone will need them first):

| Primitive | Purpose | Notes |
|---|---|---|
| `Select` | Role pickers, filters | Native-feeling, keyboard-operable |
| `Checkbox` / `Switch` | Autonomy toggles, settings | Switch specifically for binary on/off states (notifications); Checkbox for multi-select |
| `Popover` | Filters, quick actions | Level-2 elevation |
| `Sheet` | Focused forms that aren't a yes/no confirmation | Slide-in panel; `Dialog` (built) already covers the confirmation case |
| `Table` | Task boards, usage records, member lists | Tabular-nums (DesignSystem.md §5.3) applied by default to any numeric column |
| `CommandPalette` | Global navigation and actions (⌘K) | See §4 — this is not a "nice to have," it's a first-class navigation surface; build once the icon rail has a second real item |

## 3. Signature molecules

Each entry: what it is, what makes it Velora's own rather than a generic pattern, and which real screen uses it first. The Org Pulse is listed first, deliberately out of alphabetical/introduction order — it is the system's center of gravity, not one entry among equals.

**Build status (Stage 0 extension, `docs/design/Stage0-Migration.md` §11.4):** all six exist today as typed, presentation-only components in `frontend/components/molecules/`, demonstrated on an internal design-preview page with mock data — none is wired to a real backend, since none of the underlying systems (Digital Employees, Goals, Approvals, Departments, Company DNA) exist in M4 yet. Wiring real data into each is Stage 2 work, not a redesign — the "first used on" note per entry below is that Stage 2 milestone.

### The Meridian Line & the Org Pulse (the living organization, in two sizes)

Velora's one unmistakable, ownable visual device, in two coordinated forms:

- **The Meridian Line** — a slim (~40px), full-width, permanently present strip built into the global shell itself, directly beneath the header, on **every authenticated screen** — Dashboard, Employee Profile, Settings, all of it. It renders a compressed live read of the organization: small live-state dots for currently-active Digital Employees (using the same Signal pulse as the Loading-state "actively reasoning" indicator — UXPrinciples.md §2 — because it's the same fact, viewed smaller), and the DNA mark anchored at its right edge (UXPrinciples.md §7). This is the single strongest answer to "recognizable from one screenshot": every screenshot of Velora, regardless of which page, carries this same strip.
- **The Org Pulse** — the Meridian Line's expanded form, and the dominant visual of the Workforce Command Center (UXPrinciples.md §5): departments as fixed nodes, Digital Employees as smaller nodes within them, an animated edge drawing from an employee to the Task/Conversation it's engaged in the moment work begins, fading once it completes. A Digital Employee node whose bound Company DNA version has fallen behind the org's current published one renders with a muted ring rather than full Signal color (UXPrinciples.md §7) — DNA drift, visible on the same living map as everything else, not a separate settings-page concern.

Both render the same underlying live-activity stream — the Meridian Line is the compact instrument, the Org Pulse is the same instrument at full size, the way a bridge repeater and the main chart table on a ship show the same position from two distances. Neither is a simplified "preview" of the other; they're two honest views of one fact.

### Digital Employee Card

A roster tile: avatar mark, name, role title, department, a single-word lifecycle status (draft/configured/active/paused/retired — StateMachines.md §2), and one live metric (tasks this week or escalation rate — never both, pick whichever is more relevant to the viewer's role). The avatar is a **restrained geometric monogram** in Ink/Signal only — no illustrated character, no robot mascot — because a cartoon avatar undercuts "colleague with a job" (DesignSystem.md §2) the same way a stock-photo headshot would undercut a real employee directory. First used on: Digital Employees roster (WireframeSpec §8).

### Autonomy Dial

The per-action-type autonomy control (`autonomous` / `notify` / `approve` — AIEmployees.md §6) rendered as a three-position physical-feeling dial rather than a dropdown or three separate radio buttons. This is a deliberate, meaningful investment: autonomy level is the single most trust-sensitive control in the entire product, and it should *feel* weightier to change than a settings toggle — a small resistance in the interaction (a real click-stop at each position, not a free slide) communicates "this is a decision, not a preference." First used on: Employee Profile → Permissions & Autonomy tab (WireframeSpec §9).

### Goal Progress Ring

A thin circular progress indicator with a hard tick mark at the target and tabular-nums current value in the center — not a horizontal bar. A ring reads as "a target being approached," which is literally what a Goal is (DomainModel.md §2.8); a bar reads as "a task being finished," which is what a Task is. Using the right shape for the right concept is a small thing that consistently reinforces correct mental models. First used on: Goals list, Dashboard goal-progress widget.

### Approval Queue Item

Not a bare "approve/reject" button pair — a compact card showing the Digital Employee's name, what it wants to do, the Decision Trace summary inline (Observability.md §5), and the two actions, so a human can decide without leaving the queue to dig through logs (this is an explicit PRD requirement, OVR-1). Visually flagged with a single Signal-colored left indicator (the one place a colored accent-rail pattern is earned, because it's marking the single most time-sensitive item type in the product — see UXPrinciples.md §3 for why this doesn't contradict the "no decorative accent rails" instinct elsewhere). **On the Workforce Command Center specifically** (UXPrinciples.md §5), this is a docked panel beside the Org Pulse, not a stacked zone above it — positioned where the eye naturally goes once it's scanned the living map, the way an alert light sits at the edge of a radar screen rather than in a separate report above it.

### Decision Trace Timeline

A vertical, monospace-timestamped sequence of what a Digital Employee considered and why, for one Task. Reads like a flight recorder transcript, not a chat log — deliberately, since "why did the AI do that" is a trust question, and trust questions deserve the same precision instrumentation register as everything else in Meridian, not a casual chat-bubble aesthetic.

## 4. Navigation philosophy

**Command-first, not menu-first.** The primary way a returning user gets anywhere in Velora is `⌘K` / `Ctrl+K` — search-and-act, in the tradition of Raycast/Linear/Superhuman — because a workforce-operations console is a tool people return to dozens of times a day, and re-orienting through a nested menu every time is friction a power tool shouldn't have.

The persistent chrome around that is deliberately minimal — a **left icon rail**, not a heavy labeled sidebar: Dashboard, Digital Employees, Goals, Knowledge, Settings (per WireframeSpec §2.1's existing Global Shell spec), collapsible to icons-only, with the org switcher and notification bell anchored at its top. A rail, not a top nav bar — a horizontal top nav reads as a marketing site or a document (Notion), and Velora is neither.

**The shell carries one more permanent fixture, added in the post-review refinement: the Meridian Line** (§3), a full-width strip directly beneath the header, present on every screen the rail is present on. It is chrome in the structural sense (always there, never scrolls away) but not chrome in the "decorative" sense — it's live data, continuously. This is what makes the navigation shell itself part of Velora's visual identity, rather than a neutral frame around whichever page happens to be open.

**What this means concretely for engineering:** the command palette is not a "phase 2 enhancement bolted onto a conventional nav" — it should exist from the first screen that has more than a handful of destinations, because retrofitting keyboard-first navigation onto a mouse-first product later is a rebuild, not an addition.
