# User Journeys

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design
**Depends on:** [DesignSystem.md](./DesignSystem.md), [ComponentGuidelines.md](./ComponentGuidelines.md), [UXPrinciples.md](./UXPrinciples.md)

---

## Why journeys, not pages

A page inventory tells you what exists. A journey tells you what someone *feels* while using it, which is the actual design problem — per this exercise's own framing, "don't think about pages, think about experiences." Five journeys below, each covering: what the user is trying to do, the screen hierarchy, primary/secondary actions, the microinteractions and motion, the emotional target, and how the journey degrades gracefully into its empty/error states.

Journeys reference screens already scoped in `docs/product/WireframeSpec.md` and features described in `docs/architecture/AIEmployees.md` / `DomainModel.md` — this document doesn't invent new product scope, it specifies how the already-planned scope should *feel*.

---

## Journey 1 — Creating your first organization

**User goal:** go from "I just signed up" to "I have a workspace that's mine" in under thirty seconds, with zero ambiguity about what happens next.

**Emotional target:** momentum. This is the very first thing a new user does inside the product — WireframeSpec §5 already gets the core instinct right ("momentum matters more than confirmation... no intermediate confirmation screen"). Meridian's job is to make that momentum *feel* like something, not just be fast.

**Screen hierarchy:** Register → Create Organization → (auto) Dashboard. One field that matters (organization name — see M4's actual scope decision to defer industry/team-size until they have a real downstream use). No department suggestions, no plan selection, no "let's set up your workspace" multi-step wizard.

**Primary action:** submit the organization name.
**Secondary actions:** none — this screen has exactly one job, deliberately (WireframeSpec §5: "cannot be reached once an organization already exists... except via the org switcher").

**Microinteractions:**
- The input field has a subtle focus state (Signal-tinted ring, not a full border-color change) — the one moment before submission where Signal appears, marking "this is the one thing that matters on this screen."
- On submit, the button's label transitions to a determinate state ("Creating…") rather than a bare spinner — the async task pattern's "always show what's happening" principle (UXPrinciples.md §2) applies even to a sub-second operation, because consistency of pattern matters more than the exact duration.

**Motion:** the transition from onboarding to dashboard is a 320ms cross-fade with a slight upward settle (DesignSystem.md §9's "ease out, gentle settle" curve) — not a hard cut, not a slide, because this is the single moment the user goes from "setting up" to "in the product," and it should read as arrival, not just a route change.

**Success state:** landing directly on the dashboard, already showing the organization's real name in the `display` type scale (DesignSystem.md §5.2) — the first time that scale appears in the product, deliberately, because this is the first genuinely "this is mine" moment.

**Empty/error states:** a slug collision is invisible to the user entirely (resolved server-side, WireframeSpec §5 — never surfaced as an error the user has to solve). A genuine validation error (empty name) is inline, immediate, plain-language.

---

## Journey 2 — Hiring your first Digital Employee

**User goal:** go from "an empty roster" to "someone is actually working for me" with enough ceremony to feel like a real hire, not enough to feel like a form.

**Emotional target:** significance without friction. Hiring a real employee is a big deal; hiring a *digital* one should feel similarly consequential — proof the product takes the metaphor seriously — while remaining fast enough that it doesn't become the thing standing between a user and value.

**Screen hierarchy:** Digital Employees (empty state) → Hire overlay (template browse or DNA-informed recommendation, AIEmployees.md §4) → Employee Profile in `draft` status, configuration required (DNA binding, permission scope, autonomy level — PRD EMP-2) → Activate.

**Primary action, per step:** pick a template/recommendation → bind DNA + set autonomy → activate.
**Secondary actions:** browse the general catalog instead of a recommendation; adjust default skills before activating.

**Microinteractions:**
- The hire flow opens as an overlay (Sheet, ComponentGuidelines.md §2), not a full navigation away — the roster stays visible underneath, reinforcing "you're adding to something," not "you left to go configure something elsewhere."
- Setting the Autonomy Dial (ComponentGuidelines.md §3) for the first time is the emotional peak of this journey — deliberately given a moment of weight: a real click-stop per position, not a smooth slider, because this is the trust decision the entire product hinges on, and it should feel like one.
- The moment `draft` transitions to `active` is marked with the same restrained Signal moment as a Goal completing (UXPrinciples.md §4) — this is the first Digital-Employee-specific "genuine milestone."

**Motion:** the Employee Profile's tabs (Overview/Permissions/DNA/Activity/Chat) use a 200ms cross-fade between tab content, no slide — tabs are lateral navigation within one screen, not a sequence, so lateral slide motion would incorrectly imply an order that doesn't exist.

**Empty state:** an empty roster shows the dormant Digital Employee Card silhouette (UXPrinciples.md §1) with DNA-informed recommendations surfaced above the general template catalog when DNA exists (AIEmployees.md, tentative EMP-5) — recommendations first, browse-everything second, so the empty state itself starts teaching the product's actual value (this system already knows something about your business) rather than presenting a blank catalog.

**Success state:** the newly active Digital Employee appears in the roster immediately, in its real position, with its live metric already reading (even if it reads "0 tasks yet" — WireframeSpec §8: "a newly hired employee appears immediately... not after a delay").

---

## Journey 3 — Watching a Digital Employee complete work

**User goal:** trust, at a glance, that real work is happening — without having to hunt for proof.

**Emotional target:** quiet confidence. This is the journey that has to prove Velora's entire premise moment-to-moment, so it gets the most instrumentation of any journey in the product.

**Screen hierarchy:** the Workforce Command Center (the Org Pulse shows the employee's node actively connected to a Task — UXPrinciples.md §5) or, from any other screen, the Meridian Line's compressed live-state dots (UXPrinciples.md §6) → click through to Employee Profile → Activity tab → a specific Task's Decision Trace Timeline.

**Primary action:** none required — this is designed to be legible passively, at a glance, which is the point (UXPrinciples.md §6: "before reading a single number, a founder should be able to tell if anything is happening").
**Secondary action:** open the Decision Trace for a specific piece of work, when the user wants the "why," not just the "that."

**Microinteractions:**
- The animated edge on the Org Pulse (ComponentGuidelines.md §3) draws from employee-node to task-node over ~600ms when work begins, and fades over ~800ms when it completes — slightly slower than the standard 320ms structural-motion ceiling (DesignSystem.md §9) because this is the one place motion itself *is* the content, not a transition around content, and needs enough duration to actually be perceived as "ongoing" rather than a blip.
- The Decision Trace Timeline's entries appear in monospace with tabular-nums timestamps, each a discrete step — no typewriter-effect text reveal, no chat-bubble animation. It reads like a transcript being reviewed, not a conversation being had live, which is the correct register per DesignSystem.md §3.1.

**Success state:** a Task reaching `done` is a small, specific confirmation on the Decision Trace ("Completed — see outcome") — not a celebratory moment (that's reserved for Goals, UXPrinciples.md §4); a completed Task is routine, good work, not a milestone, and treating every completed task as an event would cheapen the moments that actually are.

**Error state:** a `TaskFailed` entry surfaces its `error_class` in plain language directly in the timeline (EventCatalog.md §5.6, StateMachines.md §3) with the retry/escalation path immediately visible — never a dead end.

---

## Journey 4 — Reviewing company analytics

**User goal:** understand whether the workforce is actually paying for itself, without needing a BI tool.

**Emotional target:** clarity over comprehensiveness. This is the one journey where the instinct to add more charts is strongest and most wrong — per DesignSystem.md §6, density is achieved by cutting content, not shrinking spacing.

**Screen hierarchy:** the Workforce Command Center's Trending footer strip (UXPrinciples.md §5, item 3) for the daily glance; a dedicated view (Settings → Billing & Plan, or a future Analytics screen) for the deeper look — cost-to-serve per Digital Employee, per Department (PRD BILL-3), sourced from Usage Records / Decision Trace cost telemetry, never a separately-maintained score (AIEmployees.md §9).

**Primary action:** none — this is a read-first screen. The one action available is drilling into a specific number (click a Digital Employee's cost to see its Decision Trace cost breakdown).

**Microinteractions:**
- Every chart gets the same care as body type (per DesignSystem.md's inspiration-list discipline): a faint grid, an emphasized endpoint value in `display`-adjacent weight, tabular-nums axis labels — never a default charting-library theme dropped in unstyled.
- Sparklines, where used, are a single restrained line in Slate, with only the current value marked in Signal — the same "one accent, used once" discipline as everything else in the system (DesignSystem.md §4.1).

**Empty state:** an organization with no usage yet shows the same chart structure at zero, not hidden — the grid, the axis, the shape of what will eventually be there, exactly like the dormant Digital Employee Card (UXPrinciples.md §1's "an empty state is a promise" principle extends to data visualization, not just cards).

---

## Journey 5 — A Digital Employee asks for approval

**User goal:** make a confident yes/no decision in seconds, without digging through logs first.

**Emotional target:** being asked, not interrupted. This is the moment autonomy meets human oversight (AIEmployees.md §6's `approve` level) — it has to feel like a colleague checking in before doing something consequential, not an alert demanding attention.

**Screen hierarchy:** a Notification (bell icon, WireframeSpec §13) → the Approval Queue Item, either in the Workforce Command Center's docked "Needs You" panel beside the Org Pulse (UXPrinciples.md §5) or opened from the notification panel → approve or reject, with the Decision Trace summary visible inline the entire time (PRD OVR-1 — never a bare approve/reject button pair with no context, ComponentGuidelines.md §3).

**Primary actions:** Approve, Reject — both equally weighted visually (this is a genuine decision, not a "confirm the recommended path" pattern where reject is deliberately de-emphasized; de-emphasizing reject would quietly bias the human toward rubber-stamping, which undermines the entire point of the `approve` autonomy level).
**Secondary action:** open the full Decision Trace for more detail before deciding, if the inline summary isn't enough.

**Microinteractions:**
- The Approval Queue Item's Signal-colored left indicator (ComponentGuidelines.md §3) is present from the moment it's created — not animated in with urgency (no shake, no red pulse) — because urgency-through-motion reads as alarm, and this is a considered request, not an emergency.
- Approving or rejecting gives immediate, quiet inline confirmation (UXPrinciples.md §4) and the item leaves the queue with a brief 200ms fade — no modal confirmation step for either action, since both are already deliberate, reviewed decisions by the time the button is pressed; a confirm-your-confirmation dialog would just be friction with no safety benefit.

**Success state:** the queue empties out entirely eventually — and per WireframeSpec §13's existing principle, an empty notification/approval queue gets explicitly positive framing ("You're all caught up"), not a neutral "nothing here," because a fully-reviewed queue is a genuinely good outcome this product should feel good about surfacing.

**Error state:** if approving triggers a downstream failure (the Skill Runtime rejects the now-approved action), that failure is reported back to the same queue location the approval came from, with the Decision Trace still attached — the human should never have to go hunting for what happened to something they just approved.
