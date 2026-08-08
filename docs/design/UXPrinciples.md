# UX Principles

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design
**Depends on:** [DesignSystem.md](./DesignSystem.md), [ComponentGuidelines.md](./ComponentGuidelines.md), [docs/product/WireframeSpec.md](../product/WireframeSpec.md)

---

This document is where Velora's product philosophy — Digital Employees, not software modules (AGENTS.md) — turns into concrete rules for how a screen behaves in every state it can actually be in, not just the happy path a mockup shows.

## 1. Empty state philosophy

**An empty state is a promise, not an apology.** WireframeSpec.md §2.4 already establishes "never a bare 'no data'" as a rule; Meridian's contribution is *how* that promise is rendered: the relevant signature molecule (ComponentGuidelines.md §3) shown in a **dormant** state, not replaced by a generic illustration.

- No Digital Employees hired yet → the roster grid isn't empty, it's a single dormant Digital Employee Card silhouette (Ink-only monogram, no name, no metric) with the hire action where its lifecycle status would be — the shape of the thing you're about to get, at rest.
- No Goals yet → a Goal Progress Ring at 0%, no target tick placed yet, next to the "state a goal" input — the instrument is there, just not reading anything yet.
- This is a deliberate rejection of generic empty-state illustrations (a cartoon magnifying glass, a friendly robot) — they're what every other product does, and they don't teach the user anything about what's about to happen.

## 2. Loading state philosophy

Two categories, visually distinct, because they mean different things:

1. **Waiting on a network request** (a page loading, a list fetching) — a skeleton matching the *exact* shape of the real content (already the right instinct in the existing M1 architecture notes: "skeleton cards matching the roster's expected density"). Never a generic spinner for anything that has a known shape.
2. **A Digital Employee actively reasoning** — a distinct, slow Signal-colored pulse (DesignSystem.md §9's one deliberate ambient-motion exception), never the same visual as category 1. Conflating "the network is slow" with "the AI is thinking" erodes the exact trust distinction Velora needs to maintain: one is infrastructure latency, the other is the product's core value actually happening. They should never look the same.

For anything routed through the async task pattern (API.md §5) specifically: the loading state shows *what's happening* — "Velora is planning this out…", "Checking CRM records…" — sourced from real task status, never a bare spinner with no information, per WireframeSpec §2.4's existing rule. A loading state with no information is a loading state that's actively lying about how much it knows.

## 3. Error state philosophy

- **Inline first, banner second, full-page only for catastrophic failure.** A failed field validation lives next to the field. A failed widget on an otherwise-fine dashboard fails only that widget (WireframeSpec §7 already specifies this partial-failure tolerance). A full-page error is reserved for "the app genuinely cannot render anything useful right now."
- **Plain language, never a code.** Every error surfaces `error.message` from the API envelope (API.md §7), never a raw `error.code` or a stack trace — with the `request_id` available on demand behind a "copy details" affordance for support escalation, exactly as WireframeSpec §2.4 already specifies.
- **Calm, not alarmed.** Error states use `--clay-500` (DesignSystem.md §4.3) applied narrowly — an icon, a left rule, the message text — never a full red-filled banner. A product whose core pitch is "trust an autonomous employee" cannot afford its own error UI to look panicked; panic is the one emotional register Meridian never uses, even here.
- **The one earned exception to "no colored accent rail":** the Approval Queue Item (ComponentGuidelines.md §3) uses a Signal-colored rule specifically because it's the single most time-sensitive item type in the product — a human is being asked to make a call an autonomous system couldn't. Errors don't get this treatment; being blocked and being asked to decide are different registers, and only the second earns the emphasis.

## 4. Success state philosophy

- **Quiet confirmation by default** — a toast or inline check, never a modal that requires dismissal (WireframeSpec §2.4's existing rule, kept). Interrupting a user's momentum to congratulate them on a routine save is a cost with no benefit.
- **Genuine milestones get a marked moment, not a generic one.** A Goal reaching `achieved`, a Digital Employee's first completed Task, an organization's first hire — these use the `display` type scale (DesignSystem.md §5.2) and a brief, restrained Signal-colored moment (a ring completing, not confetti). The bar for "this earns a bigger moment" is high and specific — routine CRUD success never clears it, which is exactly what keeps the marked moments meaningful when they do happen.

## 5. Dashboard philosophy — the Workforce Command Center

**Revision note (post-review):** the original proposal treated the Dashboard as three stacked, equally-weighted zones. That was still, structurally, an admin dashboard with better taste. This revision makes a real change, not a cosmetic one: **the living organization is the screen, not a widget on it.**

The Command Center's primary surface is the full Org Pulse (§6) — the same living map described below, at full size, permanently in motion. Everything else is a docked instrument around that one dominant view, the way a radar screen is the center of an operations room and everything else (alert panels, status boards) is arranged at its edges, not stacked above and below it in a scrolling list:

1. **The map is the center.** Full-width, full-height within the content area. This is what's on screen the instant the Command Center loads — not a summary card that links out to it.
2. **Needs You is a docked panel**, anchored to one side of the map (right, in a left-to-right reading language), not a stacked zone above it. It behaves like a ship's console alert light: present and legible at rest, and it's where the eye actually goes the moment something needs a decision — because it sits *beside* the thing generating the work, not in a separate scroll position the user has to remember to check.
3. **Trending is a footer strip**, not a competing zone — a slim, permanently visible band beneath the map (Goal Progress Rings, the cost/savings figure), reviewed at a glance, never competing with the map for primary visual weight.

**Why this is the right call, not just a bolder one:** a dashboard organized as stacked zones is legible one row at a time — a user reads zone 1, then zone 2, then zone 3. A command center organized around one dominant living view is legible *all at once*, the way a real operations room is designed to be scanned in a single glance from the doorway. That's a meaningfully different (and harder-earned) kind of legibility, and it's the one that actually answers "make this instantly recognizable from a single screenshot" — a screenshot of three stacked cards looks like a dashboard; a screenshot of a living map with a docked alert panel looks like nothing else on the market.

**The empty case is still a hard rule:** per WireframeSpec §7, if no Digital Employee has been hired yet, the Command Center is replaced by the hire flow entirely — an empty map with nothing on it is not a softened version of this rule, it's the same rule (UXPrinciples.md §1's dormant-instrument principle: the map's *shape* can be shown at rest, with no nodes yet, but it is never populated with fake activity to avoid looking bare).

## 6. AI Employee visualization philosophy — the Org Pulse, in full

This is the section that most directly answers "make Velora unmistakable." The Org Pulse is no longer one signature molecule among six — it is Velora's central visual identity, and it exists in **two coordinated manifestations**, not one:

1. **The Meridian Line** — a slim, permanently present strip built into the global shell itself (ComponentGuidelines.md's new §3.1), visible on *every* authenticated screen, not only the Command Center. This is the pervasive-activity answer: a user reviewing a single Digital Employee's Permissions tab, or reading Settings, still sees — at the edge of their vision, never demanding attention — that the organization is alive. This is the single strongest lever for "recognizable from one screenshot," because it means *every* screenshot of the product carries the same living signature, not just the one page called "Dashboard."
2. **The full Org Pulse** — the Meridian Line's expanded form, the dominant view on the Workforce Command Center (§5). Departments as fixed nodes, Digital Employees as smaller nodes within them; an animated edge draws from an employee to the Task or Conversation it's engaged in the moment work begins, and fades once it completes. At a glance, before reading a single number, a founder should be able to tell "is anything happening right now" — the exact question a static roster grid cannot answer without making the user read every row.

Both manifestations render the same underlying live-activity data; the Meridian Line is not a separate, simplified feature, it's the same instrument viewed from across the room instead of up close — exactly the relationship a ship's compact bridge repeater has to the full chart table.

**A Digital Employee's identity is a colleague's, not a character's.** Per DesignSystem.md §2's "never cute" rule: no illustrated mascot, no cartoon avatar, no forced personality quirks. A restrained geometric monogram (ComponentGuidelines.md's Digital Employee Card) plus a name and a role title is the entire identity — the same information a real employee directory shows, deliberately, because "trusted colleague" (AGENTS.md's own product framing) is undercut the moment the UI treats the employee as a mascot instead.

**Autonomy is visualized as a physical control, not a settings toggle.** The Autonomy Dial (ComponentGuidelines.md §3) exists because "how much do I trust this employee with this kind of decision" is the single highest-stakes control surface in the product, and it should feel like one to adjust.

**Work-in-progress is always visible, never buried in a log.** The Decision Trace Timeline (ComponentGuidelines.md §3) is one click from any Task, framed as a flight-recorder transcript — because the moment a user has to dig through a database-style log table to understand what an autonomous system did, the trust relationship the entire product depends on starts to erode.

## 7. Company DNA presence

Company DNA (CompanyDNA.md) is the org's actual operating instructions — voice, policy, product knowledge, versioned like code, with every Digital Employee pinned to a specific version until a human explicitly upgrades it (CompanyDNA.md §4.3). None of that is visible anywhere in the original proposal. It should be, and not as a settings page nobody visits — DNA is what every Digital Employee's behavior is *grounded in*, and the interface should make that grounding legible everywhere trust is being built, not just where it's configured.

Three concrete, load-bearing places, not one bolted-on indicator:

1. **The DNA mark, on the Meridian Line itself.** A small, fixed indicator anchored at one end of the pervasive strip (§6) — the org's current published DNA version and status (`v1.3 · published`, or `v1.4 · draft` while a new one is being prepared). This sits in the same always-visible location as the living-activity signal because it answers the same category of question: not "what is happening," but "what is everything that's happening *grounded in*." Clicking it opens DNA settings.
2. **Every Decision Trace opens with its DNA grounding.** The Decision Trace Timeline's (ComponentGuidelines.md §3) first line is never the task itself — it's `Operating on Company DNA v1.3`, before anything else. This is the highest-trust surface in the product (UserJourneys.md Journey 3), and grounding every single autonomous action in a specific, versioned, human-published document, visibly, every time, is a more powerful trust signal than any settings page could be.
3. **DNA drift is visible on the Org Pulse itself.** A Digital Employee node whose bound DNA version (`ai_employees.company_dna_version_id`) is older than the organization's current published version renders with a muted ring instead of full Signal color — not an error, not a warning badge, just a quiet visual note that this employee hasn't been upgraded yet. This is a real, already-modeled state (CompanyDNA.md §4.3 — publishing a new version never silently changes a pinned employee's behavior), and surfacing it on the same living map that shows everything else keeps DNA feeling like part of the organization's nervous system rather than a separate administrative concern.
