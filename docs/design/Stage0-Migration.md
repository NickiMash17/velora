# Stage 0 — Design Foundation: Migration Summary

**Status:** Complete
**Scope:** `frontend/` only — no backend changes
**Depends on:** [DesignSystem.md](./DesignSystem.md), [ComponentGuidelines.md](./ComponentGuidelines.md),
[UXPrinciples.md](./UXPrinciples.md), [Accessibility.md](./Accessibility.md), [Wireframes.md](./Wireframes.md),
[Roadmap.md](./Roadmap.md)

---

## 1. What this was

Stage 0 builds the production frontend foundation Meridian's approved design
docs describe: design tokens, theme support, the application shell (header,
icon rail, Meridian Line), reusable layout primitives, a small set of core UI
components, motion primitives, and accessibility standards — then refactors
the existing M4 frontend onto them without changing behavior. This is scoped
broader than `Roadmap.md`'s original "tokens only, no visible UI change"
Stage 0 — the user explicitly asked for the shell and primitives too. That
scope expansion is deliberate and is reflected in `Roadmap.md`'s own status
line now (§3 below).

No backend code changed. No new product functionality was added — every
screen does exactly what it did before; only its presentation and internal
structure changed.

## 2. Token layer

`frontend/app/globals.css` gained Meridian's primitives (Ink, Paper, Slate,
Signal — with a distinct dark-mode "lit" value — and the four semantic
colors: Sage/Ochre/Clay/Dusk), then the **existing** semantic aliases
(`--background`, `--foreground`, `--primary`, `--border`, `--destructive`,
`--ring`, etc.) were remapped to point at those primitives instead of the
previous achromatic `oklch(_ 0 0)` values:

| Semantic token | Before | After (light) | After (dark) |
|---|---|---|---|
| `--background` | `oklch(1 0 0)` (white) | Paper `#F6F4EF` | Ink `#0E1013` |
| `--foreground` | `oklch(0.145 0 0)` | Ink `#0E1013` | Paper `#F6F4EF` |
| `--destructive` | generic red | Clay `#A8483D` | Clay `#A8483D` |
| `--ring` (focus) | generic gray | Signal `#C08A2E` | Signal `#D6A44A` |

Because `Button`, `Card`, `Input`, and `Label` already consumed these
semantic tokens (not hardcoded colors), **all four were reskinned to
Meridian with zero component code changes** — this is the mechanism that
satisfies "refactor without changing behavior" at the token layer. The
`shadcn/tailwind.css` import and its own nested theme/custom variants were
left untouched, as planned.

Also added: a type scale (`text-display`/`h1`/`h2`/`h3`/`body`/`small`/`micro`
utilities, `DesignSystem.md` §5.2), motion tokens (`ease-meridian-out`/`-in`
utilities, `--duration-micro/component/structural` custom properties,
`DesignSystem.md` §9), and a global `prefers-reduced-motion` override
(`Accessibility.md` §1). Tailwind's default spacing scale already matched
Meridian's 4px-based scale 1:1 — no spacing tokens were needed.

**Fonts:** Geist (loaded via `next/font/google`) was removed. `--font-sans`/
`--font-mono` are now the literal system-font stacks `DesignSystem.md` §5.1
specifies. This is the one visually obvious, deliberate change beyond
recoloring — already approved in the original design system review.

## 3. New primitives

| File | Purpose | First real consumer |
|---|---|---|
| `components/ui/badge.tsx` | Status pill (Sage/Ochre/Clay/Dusk, never Signal) | Role badge, `DashboardShell` |
| `components/ui/tooltip.tsx` | `@base-ui/react` tooltip wrapper | Icon rail's Dashboard item |
| `components/ui/skeleton.tsx` | Shape-matching loading placeholder | `DashboardShell`'s org card |
| `components/ui/loading-state.tsx` | Neutral "waiting on network" indicator | `AuthGuard`, `SessionResolver` |
| `components/ui/form-error.tsx` | `role="alert"` inline error | 4 forms + `SessionResolver` |
| `components/ui/live-dot.tsx` | idle/live/drift status dot, the one ambient-motion exception | Meridian Line |
| `components/layout/centered-screen.tsx` | Focused single-purpose screen wrapper | root, login, register, onboarding |
| `components/shell/meridian-line.tsx` | The pervasive strip | Dashboard (via `AppShell`) |
| `components/shell/icon-rail.tsx` | Left nav rail | Dashboard (via `AppShell`) |
| `components/shell/header.tsx` | Shell header | Dashboard (via `AppShell`) |
| `components/shell/app-shell.tsx` | Composes the three above | Dashboard |
| `hooks/use-reduced-motion.ts` | JS-level `prefers-reduced-motion` read | reserved for future canvas-based Org Pulse |

**Deliberately deferred** (per `Roadmap.md`'s own "build against a real
consumer" principle): `Select`, `Checkbox`/`Switch`, `Dialog`/`Sheet`,
`Table`, `Tabs`, `CommandPalette`, and wiring `sonner`/`Toast`. None has a
consumer in the current M4 screens — building them now would be exactly the
"guessing at values that get thrown away" the roadmap warns against.

## 4. The Meridian Line's honest dormant state

`MeridianLine` accepts real props (`employees`, `dna`) and is genuinely
data-driven. M4 has **zero Digital Employees and no Company DNA feature** —
both explicit, already-documented non-goals of this milestone. Rather than
fabricate activity dots or an invented DNA version (which would violate the
same "never fabricate" standard applied to the earlier demo screenshots),
`DashboardShell` renders it with no props, its real current state: a quiet
"No Digital Employees yet" caption, no DNA mark. A future milestone that adds
Digital Employees or Company DNA passes real data in — no change to this
component is needed then.

## 5. Shell scope

`AppShell` wraps **only the Dashboard**. The icon rail ships with exactly one
real item (Dashboard) — Employees/Goals/Knowledge/Settings don't exist yet,
and rendering icons for them would be chrome pointing at nothing (the M4
plan's own "no fake widgets" rule). The header has no notification bell, no
`⌘K` palette, no org-switcher widget — same reasoning. Login/Register/
Onboarding intentionally stay on `CenteredScreen` (no rail/header) — Journey
1's "momentum matters more than confirmation" argues against full shell
chrome on a single-purpose screen.

## 6. Refactored call sites (behavior-preserving)

- `app/page.tsx`, `app/login/page.tsx`, `app/register/page.tsx`,
  `app/onboarding/page.tsx` — the 4x-duplicated `<main className="flex
  min-h-screen ...">` + literal `<h1>Velora</h1>` replaced by
  `<CenteredScreen>`.
- `app/dashboard/page.tsx` — dropped its ad hoc wrapper (`AppShell` now
  provides shell + `min-h-screen`, applied inside `DashboardShell`).
- `AuthGuard.tsx` — "Loading…" paragraph → `LoadingState`, centered in its own
  `min-h-screen` div (same visual result as before, now self-contained).
- `LoginForm.tsx`, `RegisterForm.tsx`, `CreateOrganizationForm.tsx`,
  `SessionResolver.tsx` — the 4x-duplicated `role="alert" text-sm
  text-destructive` paragraph → `FormError`. Same error-extraction logic,
  same messages, same `ApiError` handling — only the wrapper changed.
- `DashboardShell.tsx` — restructured onto `AppShell` (org name/plan/status
  card and sign-out button unchanged; role now shown as a `Badge` in the
  header instead of inline text; loading state upgraded from a bare "Loading…"
  line to a shape-matching `Skeleton` per `UXPrinciples.md` §2 — same
  `isPending`/`isError` branches, same queries, same mutations, same
  redirects).

No route, redirect, validation rule, or API call changed anywhere in this
refactor — confirmed by reading every diff against the original before
capturing verification screenshots.

## 7. Verification

- `npm run lint` — clean.
- `npm run build` (Next.js 15, strict TypeScript) — clean, all 14 routes
  compiled and pre-rendered successfully.
- End-to-end manual smoke test against a production build
  (`npm run build && npm run start`), backend running against the real
  Postgres/Redis stack: register → onboarding (0 orgs) → create organization
  → dashboard, in both light and dark theme — same redirects, same data, same
  behavior as before Stage 0, confirmed via Playwright driving a real browser
  (not a mock), screenshots captured at each step.

## 8. Screenshots

Real captures from the flow above, `docs/design/screenshots/`:

| File | Screen |
|---|---|
| `Stage0-01-login-{light,dark}.png` | Login |
| `Stage0-02-register-{light,dark}.png` | Register |
| `Stage0-03-onboarding-{light,dark}.png` | Onboarding (create organization) |
| `Stage0-04-dashboard-{light,dark}.png` | Dashboard — full `AppShell`: icon rail, header with role badge + theme toggle, Meridian Line in its dormant state, org card |

## 9. Known simplifications (documented, not silent)

- **Mobile-specific behavior** (`Accessibility.md` §3's notifications/
  approvals-only phone mode) is not built — that feature doesn't exist yet.
  The shell is responsively collapsible (rail stays icon-only, header wraps,
  Meridian Line's secondary text hides below `sm`) but does not attempt the
  documented phone-specific experience.
- **The icon rail has no hover-expand-to-labeled interaction** — with a
  single real item, that affordance has no real destination to distinguish
  yet; it ships icon-only. Add the interaction when a second rail item
  exists.
- **`Company DNA` mark is not clickable** even once `dna` data exists in a
  future milestone, `MeridianLine` renders it as plain text, not a link —
  DNA settings doesn't exist as a destination yet. Wire the click-through
  when it does.

## 11. Extension — molecules, remaining primitives, layout, verification

A follow-up brief asked for a broader Stage 0 than §1–§10 above covered:
the six signature molecules (as presentation-only components), several more
primitives (Avatar, Dropdown/Menu, Dialog, Tabs, Separator, EmptyState,
Toast), layout primitives, layout-dimension/elevation tokens, a mobile
screenshot, and demo artifacts in `docs/demo/`. This section documents that
extension — still Stage 0, no new business functionality, same branch.

### 11.1 New tokens

`--shadow-meridian-raised`/`-overlay` (Level 2/3 elevation, `DesignSystem.md`
§7 — dark mode uses black at higher opacity rather than an Ink-tinted
shadow, since Ink is already the dark-mode ground and would be invisible
against itself; not specified in the design doc, documented here as the
judgment call), a `--scrim` token for `Dialog`'s backdrop (same light/dark
reasoning), and layout-dimension custom properties (`--rail-width`,
`--shell-header-height`, `--meridian-line-height`) — the shell components'
previously-hardcoded `w-16`/`h-14`/`h-10` now reference these so a future
screen can share the exact constants.

### 11.2 New primitives and layout primitives

| File | Purpose | Real consumer now, or demonstrated only |
|---|---|---|
| `components/ui/avatar.tsx` | Ink/Signal monogram, no illustrated character | `AccountMenu` (real) |
| `components/ui/dropdown-menu.tsx` | `@base-ui/react` menu wrapper | `AccountMenu` (real) |
| `components/ui/separator.tsx` | Plain rule | `AccountMenu`, `SplitPanel` (real) |
| `components/ui/dialog.tsx` | Level-3 elevation, scrim backdrop | design-preview only — no destructive-confirm flow exists yet |
| `components/ui/tabs.tsx` | Cross-fade, no slide | design-preview only — Employee Profile's tabs don't exist yet |
| `components/ui/empty-state.tsx` | Generic empty-state fallback | design-preview only |
| `components/ui/toast.tsx` | Typed helper over the already-mounted `sonner` Toaster | design-preview only — see 11.4 |
| `components/layout/stack.tsx`, `cluster.tsx`, `grid.tsx`, `section.tsx`, `content-container.tsx` | Thin flex/grid wrappers | `DashboardShell`, design-preview (real) |
| `components/layout/split-panel.tsx` | Dominant pane + docked pane + `Separator` | design-preview only — the shape a future Workforce Command Center composes from, not built as a named "CommandCenter" component since there's no real content to lay out yet |
| `components/layout/page-header.tsx` | In-content title/description/actions row | design-preview only |

"PageShell" from the brief is already covered by the existing `AppShell`
(authenticated) + `CenteredScreen` (focused) — no third, overlapping shell
primitive was added.

### 11.3 AccountMenu — sign-out relocated, not re-implemented

`components/shell/account-menu.tsx` (Avatar + DropdownMenu + Separator) is
now in the shell header. `DashboardShell` no longer renders its own
"Signed in as…" line and sign-out button in the org card — that action
moved into the header's account menu. The mutation (`useLogoutMutation`)
and its result (clear session, redirect to `/login`) are byte-for-byte
unchanged; only the UI trigger's location moved, confirmed by an end-to-end
Playwright run (register → onboarding → create org → dashboard → open the
real account menu → sign out → lands on `/login`). The org card gained two
previously-unused-but-real fields instead (`organization.slug`,
`organization.created_at`) rather than being left empty.

### 11.4 Signature molecules — presentation-only

`components/molecules/`: `digital-employee-card.tsx`, `autonomy-dial.tsx`,
`goal-progress-ring.tsx`, `approval-queue-item.tsx`,
`decision-trace-timeline.tsx`, `org-pulse.tsx`. All typed, all take plain
props, none fetch or fabricate data internally. `OrgPulse` is a DOM/SVG
foundation (departments and employees as nodes, reusing `LiveDot`), not the
full canvas-based version with animated task edges from the approved
`meridian.html` artifact — that one is genuinely Stage 2 work, once real
Digital Employees and Departments exist to animate. None of the six is
wired into any real M4 screen — no Digital Employee/Goals/Approval/
Department backend exists to back them. They're demonstrated on the new
`app/design-preview/page.tsx` with data clearly labeled as mock, so a
future milestone plugs real data into the same props without redesigning
anything.

`components/ui/toast.tsx` is built and themed but not forced into the
login/register/logout flows — those redirect immediately, and a toast the
user navigates past before reading isn't a genuine improvement. It's
demonstrated on the preview page; its first real consumer is whichever
future action doesn't immediately redirect.

### 11.5 The internal design-preview page

`app/design-preview/page.tsx` — not linked from the icon rail or anywhere
in the product, labeled in its own copy as internal design-review tooling.
This is a stand-in for a proper Storybook setup, tracked as technical debt
(§12), not a permanent fixture. It's also where every new primitive and
molecule got its first real render, which is how the bug in 11.6 was found.

### 11.6 A real bug found and fixed

`DropdownMenuLabel` originally wrapped Base UI's `Menu.GroupLabel`, which
throws (`MenuGroupContext is missing`) unless used inside `Menu.Group` —
not the case here, since this is a plain caption, not an actual group.
Opening any dropdown menu crashed the page. Found via the design-preview
page during manual verification (dev-mode error), before it could have
shipped in the real `AccountMenu`. Fixed by rendering a plain styled `<div>`
instead of the Base UI part — confirmed via a re-run of the same Playwright
click-through with no crash, then verified via the full register → sign-out
flow above.

### 11.7 Mobile responsiveness — a real fix, not just a token

The first mobile screenshot showed the 64px icon rail still reserved on a
390px viewport — exactly the "shrink the desktop layout" anti-pattern
`Accessibility.md` §3 warns against, not a deliberate adaptation. Fixed by
hiding the rail below the `sm` breakpoint (640px, matching that section's
own breakpoint table) — on a phone, a single-item rail addressed via URL
isn't essential chrome, and reclaiming its width matters more. Tablet keeps
the icon-only rail unchanged.

### 11.8 Accessibility spot-check

Playwright's `ariaSnapshot()` against the Dashboard, design-preview page,
and Login, plus a keyboard-only tab walk through the Dashboard header:
every icon-only control resolved a real accessible name (`Account menu`,
`Toggle theme`, `Options`, tab/radio labels, `LiveDot`'s `idle`/`actively
working`/`idle, Company DNA behind current`), focus order was logical
(rail link → account menu → theme toggle), and no unlabeled interactive
element was found. Not a substitute for a full automated audit (no
axe-core or similar was installed) — see §12.

### 11.9 Demo artifacts

`docs/demo/Stage0/` (the location this brief asked for, distinct from
`docs/design/screenshots/` used in §8 — both are kept, cross-referenced
here): root/session-entry screen (honestly labeled — no marketing landing
page exists), login and register in both themes, onboarding, dashboard in
both themes, a Meridian Line/shell close-up crop, a real mobile-viewport
capture (register + dashboard at 390×844), and the design-preview page.
Plus `stage0-demo.gif` — a real Playwright recording (register → onboarding
→ dashboard → theme toggle → account menu), converted with ffmpeg, no
fabricated content.

## 12. Known limitations and technical debt (this extension)

- The design-preview page is a stand-in for a proper component-development
  environment (Storybook or similar) — fine for Stage 0, but it will grow
  unwieldy as more molecules/primitives are added; worth replacing before
  Stage 2 adds real molecule consumers.
- No automated accessibility audit tool (axe-core or similar) is installed;
  §11.8's spot-check is manual and Playwright-driven, not exhaustive.
- `OrgPulse` has no animated task edges yet (DOM/SVG, not canvas) — the
  fuller version already prototyped in `meridian.html` is Stage 2 work.
- `SplitPanel`'s vertical `Separator` relies on flex `align-items: stretch`
  giving it height from its siblings — reasonable in practice, not
  pixel-verified beyond the design-preview page since it has no real page
  consumer yet.

## 13. Next step

Per the user's own instruction, Stage 0 (including this extension) stops
here for review. No Stage 1 (the primitives still deferred — `Select`,
`Checkbox`/`Switch`, `Table`, `CommandPalette` — or real-data wiring for the
molecules built in §11) begins without explicit approval.
