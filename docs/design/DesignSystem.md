# Design System — "Meridian"

**Status:** v1.0 — Proposed, pending review
**Owner:** Product Design, in collaboration with Frontend Engineering
**Depends on:** [docs/product/PRD.md](../product/PRD.md), [docs/product/WireframeSpec.md](../product/WireframeSpec.md), [docs/architecture/AIEmployees.md](../architecture/AIEmployees.md)

---

## 0. What this document is

This is Velora's design system, named **Meridian**. A meridian is a fixed reference line — the standard everything else is measured against, and the instrument sailors and surveyors historically used to know exactly where they stood. That's the job this system does for Velora: one deliberate, ownable visual language that every screen — built by any engineer, in any milestone — measures itself against, so the product reads as one coherent thing two years and twenty contributors from now, not a collage of whatever each screen's author happened to reach for.

This document covers philosophy, brand personality, visual identity, and the concrete visual tokens (color, typography, spacing, iconography, elevation, motion). Component-level rules live in [ComponentGuidelines.md](./ComponentGuidelines.md); state and interaction philosophy lives in [UXPrinciples.md](./UXPrinciples.md); accessibility and responsive rules live in [Accessibility.md](./Accessibility.md).

**A note on status:** this is a *proposed* system, written for review before implementation begins, per this milestone's explicit instruction not to write application code yet. Where a decision is genuinely a judgment call rather than a derived fact, that's said plainly rather than presented as settled.

---

## 1. Design philosophy

**The one-line version: quiet authority.**

Velora is not a chat window with a company logo on it. It's the console a founder or ops lead uses to run a workforce that happens to be digital. The emotional register that fits that job is the one a well-run control room has — a hospital's operations center, an air-traffic control desk, a private bank's trading floor. Not sterile, not cold, but *composed*. Everything is legible at a glance, nothing is decorative for its own sake, and the person using it never has to wonder whether the system knows what it's doing.

Three commitments follow from that:

1. **Confidence is expressed through restraint, not decoration.** A system that's actually in control doesn't need to shout — gradients, mascots, and bouncy animation are how software *performs* confidence it doesn't have. Meridian earns trust the way a well-made instrument does: tight tolerances, exact alignment, nothing wasted.
2. **Every element states one fact clearly.** A color means one thing. A motion communicates one state change. A number is precise, not "about 40-ish." If a screen can't say plainly what just happened and why, the design failed before the copy did.
3. **The interface shows that work is happening.** Velora's core promise is that digital employees are doing real work, right now, that a human used to have to do. The UI's job is to make that legible and continuously visible — not buried three clicks deep in a report — because "invisible work" and "no work" feel identical to a user, and that's the one thing this product cannot afford to feel like.

### Why not the obvious references

The brief's inspiration list (Apple, Stripe, Vercel, Linear, Arc, Raycast, Figma, Framer, Superhuman, Notion Calendar, Cursor, Warp, Anthropic Console) shares a trait worth naming precisely, because it's the thing to take and the specific look is not: **every one of them says almost nothing with color, and everything with restraint, type discipline, and motion that means something.** None of them is "the purple AI gradient dashboard." Copying any single one of their palettes would just relocate Velora into someone else's category (a Linear clone, a Vercel clone). The move Meridian makes instead is copying the *discipline*, not the palette — see §3 for the specific, ownable color and type decisions that follow from that discipline while staying unmistakably Velora's own.

## 2. Brand personality

If Meridian were a person in the room, they would be:

- **The operator, not the salesperson.** Precise, a little understated, entirely unbothered by needing to impress you — because the work speaks for itself.
- **Warm in substance, cool in surface.** The copy and the moments that matter (a goal completed, a first hire) are genuinely warm and specific. The chrome around them — nav, forms, tables — stays quiet and gets out of the way.
- **Never cute.** No mascot, no "meet your AI buddy!", no exclamation points doing emotional labor the product hasn't earned yet. A Digital Employee is presented as a colleague with a job, not a character.
- **Allergic to filler.** Empty states, error messages, and loading indicators all say something true and specific, every time — see [UXPrinciples.md](./UXPrinciples.md).

**What Meridian is not:** playful (Slack), collaborative-casual (Notion), minimalist-to-the-point-of-blank (a bad Linear clone), or "futuristic" in the neon-purple-gradient sense every generic AI product has already claimed.

## 3. Visual identity

### 3.1 The core idea: instrumentation, not illustration

Meridian's signature visual device is the **precision indicator** — small, exact, deliberate marks that read like the gauges on a well-made instrument panel rather than illustrations: a single glowing dot for "live," a thin progress ring with a hard-edged tick at the target, a monospaced counter that increments in place rather than a cartoon chart. These recur across the product (see [ComponentGuidelines.md §Signature Molecules](./ComponentGuidelines.md#signature-molecules)) and are what makes a Velora screen recognizable at a glance, the way an amber activity light or a tachometer needle is recognizable regardless of which car it's in.

### 3.2 Why an accent color, and why this one

A near-monochrome interface still needs exactly one color that means "this is the thing that matters right now" — the accent every restrained system in the brief's inspiration list actually has (Linear's violet, Vercel's stark white-on-black, Stripe's indigo). Velora's is **Signal** — a deep antique gold/brass, not the purple every "AI dashboard" defaults to, not the orange Claude already owns, not the teal early OpenAI products used. Gold reads as *earned* rather than decorative — it's the color of a seal, a fine instrument's trim, a rank insignia — which fits a product whose entire value proposition is trust extended to an autonomous employee. It is used the way a control panel uses its one indicator color: rare, and always meaningful (see §4.1).

### 3.3 Wordmark and mark

"Velora" is set in the UI sans (§5.1) at a confident weight, lowercase-lette­r-spacing left alone (no forced letter-spacing games) — the wordmark's distinction comes from restraint and correct kerning, not a custom logotype treatment invented here. A symbol mark (for favicons, the collapsed nav rail) is out of scope for this document — it's a brand-identity deliverable, not a UI design-system one, and shouldn't be improvised as a side effect of this work.

### 3.4 Pervasive identity, not a confined widget

**Added in the post-review refinement.** The original proposal treated the Org Pulse as one signature molecule among several, reachable on the Dashboard. That undersold the idea: a device only recognizable on one page is a widget, not an identity. Meridian's signature device — the live organization, rendered as instrumentation — now exists in two coordinated sizes, and the smaller one is a permanent fixture of the global shell itself, not a page:

- **The Meridian Line** (the system's namesake device, made literal): a slim, full-width strip built into the shell, directly beneath the header, present on *every* authenticated screen — Settings, an Employee Profile, the Command Center, all of it. It carries the same live-activity read and the Company DNA mark (§7 of [UXPrinciples.md](./UXPrinciples.md)), compressed.
- **The Org Pulse**: the same instrument, expanded to dominate the Workforce Command Center ([UXPrinciples.md §5](./UXPrinciples.md), [ComponentGuidelines.md §3](./ComponentGuidelines.md)).

This is the concrete, structural answer to "recognizable from a single screenshot": the identity isn't concentrated on one screen a viewer might not see in a given screenshot — it's present in all of them, the way a ship's compass rose appears on every chart regardless of which stretch of coastline the chart happens to show. It costs nothing extra in the token system above — the Meridian Line is built entirely from tokens and motion rules already defined in §4–§9 — it's a placement and information-architecture decision, not a new visual language.

## 4. Color system

### 4.1 Principles

- **One ground, one accent, a small honest set of semantic colors.** Nothing else. If a new screen seems to need a new color, that's a signal the information hierarchy is wrong, not that the palette is incomplete.
- **Neutrals are chosen, not defaulted.** Both the light and dark grounds carry a faint, deliberate warm bias toward Signal, so the whole system feels like one considered material rather than "brand color dropped onto Bootstrap gray."
- **Semantic color is not brand color.** Success/warning/critical/info are a separate, muted family from Signal — see §4.3. Conflating "the accent" with "a status color" is how interfaces end up with success buttons that are the same gold as the primary action, which teaches users to ignore one of them.
- **Dark mode is co-equal, not inverted.** Per-token values for dark mode are chosen for their own contrast and mood, never generated by flipping the light values (see §4.4).

### 4.2 Core tokens

| Token | Hex | Role |
|---|---|---|
| `--ink-950` | `#0E1013` | Dark-mode ground. Near-black with a whisper of warm brown, never pure `#000` — pure black photographs as a hole; this reads as a considered material. |
| `--paper-50` | `#F6F4EF` | Light-mode ground. Warm-neutral off-white — cooler and less yellow than a "latte" cream, closer to uncoated paper or raw linen. |
| `--slate-500` | `#5A6169` | Mid-neutral for secondary text, borders, dividers. Cool-neutral with a faint warm bias so it sits comfortably between Ink and Paper in both modes. |
| `--signal-500` | `#C08A2E` | The one accent. Antique gold/brass. Primary actions, active/live indicators, the one number on a screen that matters most. |

Both `ink-950` and `paper-50` expand into full 9-step ramps (50→950) for surfaces, borders, and text at different elevations — exact intermediate values are a Tailwind config exercise once implementation starts, not something to freeze in prose here.

### 4.3 Semantic colors

Deliberately a *different* hue family from Signal, so a status badge never competes visually with the one accent that means "the primary thing":

| Token | Hex | Meaning |
|---|---|---|
| `--sage-500` | `#5F8567` | Success / completed / healthy |
| `--ochre-500` | `#C46A2C` | Warning / needs attention soon (burnt orange — deliberately more red than Signal's yellow-gold, so the two are never confusable even color-blind) |
| `--clay-500` | `#A8483D` | Critical / failed / blocked |
| `--dusk-500` | `#5B7A93` | Informational / neutral notice |

All four are muted/desaturated versions of their hue, matching Signal's restraint — never a saturated "alert red" or "success green" straight off a default palette.

### 4.4 Dark mode

Dark mode is Meridian's natural home — a workforce operations console is used for long stretches at a desk, and the "instrument panel at night" mood (§3.1) is more legible on Ink than Paper. Concretely:

- Ground is `--ink-950`, not a lighter "dark gray" — depth comes from very subtle elevation steps (§7), not from lightening the base.
- Signal gains a touch of luminance in dark mode (`#D6A44A` rather than `#C08A2E`) so it reads as *lit* against Ink rather than muddy — this is a deliberate per-mode value, not an automatic inversion (per the principle in §4.1).
- Body text on Ink targets AAA contrast where the layout allows it (see [Accessibility.md](./Accessibility.md)); light mode targets AA as the floor, AAA where free.

Light mode is fully supported and gets the same care, not a compliance afterthought — see the same reasoning applied to Paper's warmth (§4.2) and to component-level tokens in [ComponentGuidelines.md](./ComponentGuidelines.md).

## 5. Typography

### 5.1 Faces, and why system stacks

Meridian uses two type roles, both **native system-font stacks**, deliberately:

| Role | Stack | Used for |
|---|---|---|
| UI / Display | `-apple-system, "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif` | Everything: nav, forms, body copy, page titles, large metric callouts |
| Data / Mono | `ui-monospace, "SF Mono", "Cascadia Code", "Consolas", monospace` | IDs, timestamps, code, logs, Decision Trace detail, API keys, anything where digits line up in a column |

**Why not a distinctive custom typeface**, which is the more common "premium" move: a licensed or embedded custom face is a real commitment (licensing, performance, a specific file this document can't respect its own advice — "build with real content, never fabricate" — is exactly why one wasn't invented here without the actual files or license to back it. The honest, still-premium alternative is the one Meridian takes instead: treat each OS's *own* most-refined native face (San Francisco, Segoe UI Variable) as a feature, not a fallback, and make the type **scale and weight discipline** — not typeface novelty — the carrier of personality. This is also, not incidentally, how several of the brief's own reference products actually ship (system-first stacks tuned hard on scale/weight/tracking rather than an exotic face). If Velora later commissions or licenses a proprietary display face, it slots into the "UI / Display" role without disturbing this system — the scale and usage rules below are what matter, not the specific font file.

### 5.2 Scale

A restrained, exact scale — every size on this list, nothing between:

| Token | Size / Line-height | Use |
|---|---|---|
| `display` | 56px / 1.05, weight 650 | The single most important number or statement on a screen (a milestone, a headline metric) — used sparingly, at most once per screen |
| `h1` | 32px / 1.15, weight 600 | Page title |
| `h2` | 22px / 1.25, weight 600 | Section title |
| `h3` | 17px / 1.35, weight 600 | Card / subsection title |
| `body` | 15px / 1.55, weight 400 | Default running text — the workhorse size |
| `small` | 13px / 1.45, weight 400 | Secondary text, metadata, captions |
| `micro` | 11px / 1.3, weight 500, +4% tracking, uppercase | Labels, table headers, status tags |
| `mono` | 13px / 1.5, weight 450 | Data/mono role content at body scale |

Running text (`body`) targets ~65 characters per line at its intended column width — long-form copy (empty-state explanations, onboarding help text) never spans a full wide container edge-to-edge.

### 5.3 Numerals

Anywhere digits appear in a column (metrics, tables, timestamps) uses `font-variant-numeric: tabular-nums`, no exceptions — this is a small detail that separates "looks like a real financial/ops tool" from "looks like a template," and it costs nothing to apply universally.

## 6. Spacing system

A 4px base unit, exposed as a named scale rather than raw pixel values in any component spec:

| Token | Value | Typical use |
|---|---|---|
| `space-1` | 4px | Icon-to-label gaps, tight inline spacing |
| `space-2` | 8px | Default gap between related inline elements |
| `space-3` | 12px | Form field internal padding |
| `space-4` | 16px | Default gap between stacked elements in a component |
| `space-6` | 24px | Gap between distinct components within a section |
| `space-8` | 32px | Section padding |
| `space-12` | 48px | Gap between major page sections |
| `space-16` | 64px | Page-level top/bottom breathing room |

**Principle: generous, not dense.** The default instinct when a screen shows operational data is to cram — resist it. A Velora screen should have the negative space of a well-edited page, not a legacy enterprise-admin grid-of-widgets; density is achieved by *cutting content*, never by shrinking the spacing scale below `space-2`.

## 7. Elevation

No drop shadows as the primary depth cue, and no skeuomorphism. Depth is communicated with borders/rings first, shadow as a light second layer only where a surface truly floats above the page (it needs to be dismissible by clicking outside it):

| Level | Treatment | Used for |
|---|---|---|
| 0 — Page | Flat ground color, no border | The base canvas |
| 1 — Surface | 1px ring, `border-color` at ~10% opacity over the ground | Cards, inputs, static panels — the majority of the UI |
| 2 — Raised | Level 1 ring + a soft, low-opacity shadow (`0 4px 16px rgba(ink, 0.08)`) | Dropdowns, popovers, tooltips |
| 3 — Overlay | Level 2 + a backdrop scrim (`rgba(ink, 0.4)` with light blur) | Modals, the command palette |

This mirrors what's already correctly in place in the current frontend scaffold (`Card` uses `ring-1 ring-foreground/10`, not `box-shadow`) — Meridian formalizes that instinct into an explicit 4-level system rather than introducing a new one.

## 8. Iconography

Velora already depends on `lucide-react`; Meridian keeps it, with discipline rather than a new library:

- **1.5px stroke weight**, standard size 20px inline / 16px in dense contexts (tables, tags) — never mixed within one screen.
- **Icons are never decorative.** Every icon maps to exactly one specific action or state, documented once in [ComponentGuidelines.md](./ComponentGuidelines.md), and reused — never a different icon for the same action on two screens.
- **Outline by default; filled only for a small, fixed set of status dots** (active/paused/error) where a filled shape reads faster than an outline at 8px.
- No icon ever stands alone without a text label the first time it appears in a given flow — an unlabeled icon-only button is a shortcut for a returning user, never the only way to discover what something does.

## 9. Motion principles

- **Motion explains causality, never decorates.** Something moves because the user's action caused a state change — a panel slides because it was opened, a number ticks because it changed — never as ambient flourish.
- **Durations:** 120ms for micro-interactions (hover, focus, toggle), 200ms for component open/close (dropdowns, popovers), 320ms for structural transitions (panel slides, page-level reveals). Nothing in the product should take longer than 320ms to finish animating — if it feels like it needs longer, the motion is doing too much.
- **Easing:** entrances ease out (fast start, gentle settle — `cubic-bezier(0.16, 1, 0.3, 1)`), exits ease in (`cubic-bezier(0.7, 0, 0.84, 0)`). No spring/bounce overshoot anywhere — overshoot reads as playful, which contradicts §1's "quiet authority."
- **`prefers-reduced-motion` is respected everywhere**, by substituting an instant state change or a simple opacity cross-fade — never by leaving an animation running regardless, and never by disabling the feature the motion was communicating (a live indicator still needs to indicate "live" with reduced motion; it just does it without a moving element — see [UXPrinciples.md](./UXPrinciples.md)).
- **The one deliberate exception:** the "live" indicator on an actively-working Digital Employee (§9 of [UXPrinciples.md](./UXPrinciples.md)) uses a slow, continuous pulse — this is the single ambient animation Meridian permits, because its entire job is to communicate "ongoing," which a static state cannot.

## 10. Relationship to the current codebase

This document proposes tokens; it does not change any file in `frontend/`. Concretely, once approved:

- Color/spacing/elevation tokens above map to Tailwind v4 theme extensions (`frontend/app/globals.css`'s existing `@theme` block already has `--font-sans`/`--font-mono`/`--font-heading` — Signal/Ink/Paper/semantic colors slot into that same mechanism).
- `lucide-react`, `class-variance-authority`, `tailwind-merge` — all already dependencies — are kept as-is; nothing here requires a new UI dependency.
- The existing `Button`/`Card` primitives' actual visual output (ring-based elevation, restrained variants) already largely matches Meridian's instincts; the work is formalizing and extending, not discarding.

See [Roadmap.md](./Roadmap.md) for the concrete, staged implementation plan.
