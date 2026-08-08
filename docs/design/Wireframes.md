# Wireframes (Low Fidelity)

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design
**Depends on:** [DesignSystem.md](./DesignSystem.md), [ComponentGuidelines.md](./ComponentGuidelines.md), [UXPrinciples.md](./UXPrinciples.md), [UserJourneys.md](./UserJourneys.md)

---

These are structural layouts, not visual comps — no color, no type treatment, just hierarchy and proportion. A high-fidelity rendering of the Workforce Command Center, Employee Profile, and Org Pulse concepts exists as an interactive artifact accompanying this document (see the delivery summary); this file is the layout logic that artifact implements, kept here as the durable, versioned spec.

**Revision note (post-review):** this file now reflects the Command Center refinement — the Meridian Line added as a permanent shell fixture (§1), and the Dashboard rebuilt around the full Org Pulse as its dominant view rather than three stacked zones (§2). See UXPrinciples.md §5–§7 and ComponentGuidelines.md §3 for the rationale; only the layout logic is restated here.

## 1. Global shell

Every authenticated screen, per WireframeSpec.md §2.1, laid out concretely — now with the Meridian Line (ComponentGuidelines.md §3) as a permanent second header row:

```
┌───┬─────────────────────────────────────────────────────────┐
│ V │  [breadcrumb / page title]              [⌘K] [🔔] [org ▾]│
│ e ├─────────────────────────────────────────────────────────┤
│ l │  ·⚬ ·⚬ ⦿ ·⚬  ·⚬                          DNA v1.3·published│ ← Meridian Line
│ o ├─────────────────────────────────────────────────────────┤
│ r │                                                           │
│ a │                    page content                          │
│   │                                                           │
│ ▤ │                                                           │
│ 👤│                                                           │
│ ⚑ │                                                           │
│ 📚│                                                           │
│ ⚙ │                                                           │
└───┴─────────────────────────────────────────────────────────┘
  ↑ icon rail (Dashboard/Employees/Goals/Knowledge/Settings),
    collapsible, ~64px wide expanded to ~200px on hover/pin
```

The rail is icons-only by default (ComponentGuidelines.md §4) — labels appear on hover or when pinned open. `⌘K` sits in the header, always visible, never hidden behind a menu. The Meridian Line sits directly beneath the header, ~40px tall, on **every** authenticated screen — not just the Command Center: a compressed live read of the organization (small dots = idle, a filled/pulsing dot = actively engaged, same motion language as §3 below at smaller scale) with the DNA mark anchored at its right edge (UXPrinciples.md §7). This is what makes even a Settings or Employee Profile screenshot instantly recognizable as Velora.

## 2. Workforce Command Center (formerly "Dashboard")

**Revision note (post-review):** the prior version of this section showed three stacked, equally-weighted zones. Per UXPrinciples.md §5, that read as "an admin dashboard with better taste." This is the corrected layout — the living organization *is* the screen:

```
┌─────────────────────────────────────────────────────────────┐
│  Acme Inc.                                    trial · org_admin│
├───────────────────────────────────────────────────┬───────────┤
│                                                     │ NEEDS YOU │
│        Sales dept.                                 │┌─────────┐│
│       ┌─────────────┐                              ││▍Riley   ││
│       │  ●  Maya     │                              ││wants to ││
│       │  (idle)      │                              ││send a   ││
│       │              │                              ││refund   ││
│       │  ◉  Riley    │╌╌╌╌╌╌╌╌╌▶ [Task: refund]      ││email    ││
│       │  (active)    │                              ││         ││
│       └─────────────┘                              ││[Reject] ││
│                    Support dept.                    ││[Approve]││
│                   ┌─────────────┐                   │└─────────┘│
│                   │  ●  Jordan   │                   │           │
│                   │  (idle)      │                   │  (docked, │
│                   └─────────────┘                   │  anchored │
│                                                     │  right)   │
│           ↑ the full Org Pulse — dominant,          │           │
│             full-width/full-height view (§3)        │           │
├─────────────────────────────────────────────────────┴───────────┤
│  TRENDING   ◔ Qualified leads +18%   ◕ Response time -30%  $2,140│
│             saved/mo                     (footer strip, slim)    │
└─────────────────────────────────────────────────────────────────┘
```

- **The map is the center** — full-width, full-height within the content area, on screen the instant the Command Center loads.
- **Needs You is a docked panel**, anchored right, not a stacked zone above the map — a console alert light, not a report.
- **Trending is a footer strip**, slim and permanently visible beneath the map, never competing with it for primary visual weight.

Each of the three still loads and fails independently (WireframeSpec §7) — a slow Trending fetch never blocks the map or the docked panel from rendering.

**Empty case** (no Digital Employee hired yet): the entire Command Center — map, docked panel, and footer strip alike — is replaced by the hire flow. UXPrinciples.md §5's rule is explicit that an empty map is not a softened version of this: the map's shape may show at rest with zero nodes, but only once at least one employee exists to make that shape meaningful.

## 3. Org Pulse (the living organization, in full)

The Command Center's dominant view at higher fidelity — the concrete answer to "living organization map," and, via the Meridian Line (§1), the same data compressed onto every other screen:

```
   Sales department            Support department
  ┌─────────────┐             ┌─────────────┐
  │   ●  Maya    │             │   ◐  Jordan  │  ◐ = muted ring:
  │   (idle)     │             │   (idle,     │    DNA drift —
  │              │             │   DNA stale) │    pinned to an
  │   ◉  Riley   │╌╌╌╌╌╌╌╌╌╌╌▶ [Task]         │    older Company
  │   (active)   │  animated edge, fades on    │    DNA version
  └─────────────┘  completion (~800ms)         └─────────────┘
```

- Solid dot = idle/available. Filled ring with motion = actively engaged (the one ambient-motion exception, DesignSystem.md §9).
- Muted ring (◐) = DNA drift — this employee's bound Company DNA version is behind the org's current published one (UXPrinciples.md §7). Not an error state, just a quiet note visible on the same map as everything else.
- Edges only exist while work is in flight — an idle organization shows a calm, static set of nodes, which is itself informative ("nothing urgent right now"), not a degraded/empty version of the view.
- Clicking a node opens that Digital Employee's Profile; clicking an edge's task-end opens that Task's Decision Trace directly.
- Scales by *filtering*, not shrinking, once an organization has dozens of employees — department nodes collapse to a single summary node (count active / count idle / count drifted) until expanded, rather than rendering every node at a size too small to read.
- This same live-activity stream, compressed, is what the Meridian Line (§1) renders on every other screen — two sizes of one instrument, never two separate features (ComponentGuidelines.md §3).

## 4. Digital Employee Profile

```
┌─────────────────────────────────────────────────────────────┐
│  ◉  Riley — Support Agent · Support dept.      [active ▾]     │
├─────────────────────────────────────────────────────────────┤
│  Overview │ Permissions & Autonomy │ DNA │ Activity │ Chat     │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│   (tab content — e.g. Permissions & Autonomy:)                │
│                                                                 │
│   Send email to customer          [ auto ─●─ notify ─ approve]│
│   Issue refund ≤ $50               [auto ─ notify ─●─ approve]│
│   Issue refund > $50               [auto ─ notify ─ approve ─●]│
│                                                                 │
│                                        ↑ Autonomy Dial,        │
│                                          one row per action     │
│                                          type (AIEmployees §6)  │
└─────────────────────────────────────────────────────────────┘
```

Tabs cross-fade (200ms, no slide — UserJourneys.md's Journey 2 rationale). Activity tab surfaces the Decision Trace Timeline (§5 below) scoped to this employee.

## 5. Decision Trace Timeline

```
  10:42:03  Task received: "Refund request from customer #4821"
  10:42:04  Checked refund policy — limit $50/no-approval
  10:42:04  Requested amount ($120) exceeds limit
  10:42:05  ▍ Routed to approval queue → awaiting human decision
  10:44:51  ✓ Approved by Nicolette
  10:44:52  Refund issued — confirmation #RF-88213
```

Monospace, tabular-nums timestamps, one line per step — a transcript, not a chat thread (DesignSystem.md §3.1, UserJourneys.md Journey 3).

## 6. Goals board

```
┌─────────────────────────────────────────────────────────────┐
│  Goals                                    [+ New Goal]        │
├─────────────────────────────────────────────────────────────┤
│  ◔ Increase qualified leads 20%     ████████░░  62% · active  │
│  ◕ Cut response time 30%            █████████░  88% · active  │
│  ○ Launch referral program           ░░░░░░░░░░   0% · proposed│
├─────────────────────────────────────────────────────────────┤
│  pending │ claimed │ in_progress │ blocked │ done │ failed     │
│  ┌────┐  ┌────┐    ┌────┐        ┌────┐    ┌────┐ ┌────┐      │
│  │task│  │task│    │task│        │task│    │task│ │    │      │
│  └────┘  └────┘    └────┘        └────┘    └────┘ └────┘      │
└─────────────────────────────────────────────────────────────┘
    ↑ Goal Progress Rings, list form            ↑ Task Kanban board
```

**Empty case:** the "New Goal" input is front-and-center with a real example placeholder ("e.g. Increase qualified leads by 20%"), not a bare empty board (WireframeSpec §10, UXPrinciples.md §1's dormant-instrument principle applied to the Goal Progress Ring — shown at 0%, no target tick yet, rather than omitted).

## 7. Notes on fidelity

These layouts fix hierarchy and proportion, not final spacing/type/color values — those are governed by DesignSystem.md and are free to be tuned during implementation as long as the hierarchy above is preserved (the Org Pulse map dominant, Needs You docked beside it, Trending as a footer strip beneath — never re-stacked into three equal zones; tabs before content; timeline entries in strict chronological order). Where this document and the accompanying high-fidelity artifact ever disagree on a visual detail, the artifact is illustrative and this document's *hierarchy* wins — the artifact is a snapshot of one way to render this spec, not a second spec.
