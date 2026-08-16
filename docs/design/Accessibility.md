# Accessibility & Responsive Behavior

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design, in collaboration with Frontend Engineering
**Depends on:** [DesignSystem.md](./DesignSystem.md)

---

## 1. Baseline

**WCAG 2.1 AA is the floor for every screen, not an aspiration for some of them.** This is a testable, non-negotiable bar — same category of requirement as the cross-tenant isolation suite in the backend (EngineeringStandards.md §4): it doesn't get relaxed under deadline pressure, and a screen that doesn't meet it isn't done.

Concretely:

- **Contrast:** body text on both grounds meets AA (4.5:1) at minimum; dark-mode text on `--ink-950` targets AAA (7:1) where the layout allows it, since dark mode is Velora's primary surface (DesignSystem.md §4.4), not a secondary one.
- **Focus is always visible.** Every interactive element gets a real focus ring on keyboard focus (the existing `focus-visible:ring-3 ring-ring/50` pattern in `Button` is the right instinct — formalize it as the standard, don't relax it for visual cleanliness).
- **Keyboard operability is complete, not partial.** Given Meridian's command-first navigation philosophy (ComponentGuidelines.md §4), keyboard support isn't an accessibility add-on bolted onto a mouse-first product — the primary navigation *is* the keyboard path, so this requirement is largely satisfied by the core design, not layered on top of it. Every remaining mouse-only interaction (drag-to-reorder, hover-only reveals) needs a keyboard-operable equivalent before it ships.
- **`prefers-reduced-motion` is respected everywhere** (DesignSystem.md §9), including the one ambient exception (the "live" pulse) — it degrades to a static indicator, never left animating regardless of the user's preference.
- **Screen reader labeling:** icon-only buttons always carry an `aria-label` matching the tooltip text (ComponentGuidelines.md §2's "no icon stands alone" rule extends here); live-updating regions (the Org Pulse, an Approval Queue gaining a new item) use `aria-live="polite"` so a screen-reader user learns about new activity without needing to poll the page.

## 2. Color is never the only signal

Every status this system communicates with color also carries a shape or text cue, so the product remains fully legible for color-blind users and in grayscale:

- Digital Employee lifecycle status: color *and* a text label (`draft`, `active`, `paused`) — never a bare colored dot.
- Approval-needed vs. informational notification: color *and* distinct iconography (ComponentGuidelines.md §2).
- Goal Progress Ring: color *and* the tabular-nums percentage in its center — the ring's fill color is reinforcement, not the only information.

## 3. Responsive behavior

**Desktop-first, deliberately — with a real, not diminished, mobile mode.**

Velora's primary surfaces (Dashboard, Digital Employees roster, Goals board, Employee Profile) are operations-console screens used at a desk for extended sessions, the same category of product as Stripe's dashboard or Linear — and like both of those, the honest design decision is to optimize the complex screens for desktop rather than force-fit a Kanban board and a live org map into a phone viewport at parity with desktop.

That does not mean mobile is an afterthought. Mobile gets its own deliberate, real mode centered on what's actually useful away from a desk:

- **Notifications and approvals** — the single most valuable thing to be able to do from a phone is review and act on an approval-queue item (WireframeSpec §13), and that flow is fully first-class on mobile, not shrunk desktop chrome.
- **Status check-ins** — "is anything on fire," a compressed Org Pulse view, read-only.
- **Everything else** (configuring a Digital Employee's permission scope, editing Company DNA) is explicitly a desktop task, and a mobile visitor is told that plainly rather than handed a broken cramped version of the desktop screen — an honest "this is easier on a larger screen" beats a technically-responsive-but-unusable layout.

Tablet is treated as a secondary citizen: it gets the desktop layout with the same responsive collapse points a desktop window would hit at that width (nav rail collapses to icons-only, multi-column layouts drop to single-column) — not a bespoke tablet-specific design pass.

### Breakpoints

| Name | Width | Behavior |
|---|---|---|
| `mobile` | < 640px | Notifications/approvals + status check-in only, per above |
| `tablet` | 640–1024px | Desktop layout, nav rail auto-collapses, multi-column grids go single-column |
| `desktop` | 1024–1440px | Full layout, the baseline this system is designed against |
| `wide` | > 1440px | Content max-width caps out (per DesignSystem.md §6's "generous, not dense" principle) rather than stretching indefinitely — a 2000px-wide table is not a better table |
