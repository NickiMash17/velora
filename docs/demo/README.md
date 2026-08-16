# Velora — Demo & Showcase System

**Status:** Active
**Owner:** Founding CTO / Engineering
**Depends on:** the actual, running application at the time each asset was captured — nothing in this folder is illustrative or mocked up.

---

## 1. Why this exists

Velora ships in milestones (see `AGENTS.md`'s Sprint Discipline and each milestone's completion report). Engineering documentation (`docs/architecture/`, `docs/product/`) captures *how* and *why* the system is built the way it is — this folder captures *what it actually looked like and did* at each milestone, so that moment doesn't have to be recreated from memory or re-implemented from scratch to show someone.

The audiences this serves are external and non-engineering by default: investors, recruiters, prospective customers, hackathon/competition judges, a LinkedIn post, or a future contributor trying to understand what already exists before reading a line of code. None of those audiences read `docs/architecture/`. This folder is what you actually hand them, or screen-share.

**The one rule everything else here follows:** every asset in this folder is a real capture of the real, running application at a specific commit. Nothing here is a mockup, a Figma export, a placeholder, or an aspirational screenshot of a feature that doesn't exist yet. If a screen hasn't been built, the corresponding milestone folder says so explicitly instead of an image standing in for it. A polished demo folder full of fabricated screens is worse than an honest, sparser one — the entire value of this system is that everything in it is provably real.

## 2. Structure

```
docs/demo/
├── README.md          this file — conventions, standards, how to contribute a new milestone's assets
├── M1/                 per-milestone write-up: what existed, what's captured, what isn't
├── M2/
├── M3/
├── M4/
├── screenshots/        all static screenshots, every milestone, flat — see naming convention below
├── gifs/                short looping captures of one specific flow (10-30s)
├── videos/              longer polished walkthroughs (2-3 min)
└── scripts/              presenter/narration scripts for the videos — what to say, not just what to show
```

Screenshots, GIFs, and videos live in their own top-level folders (not nested per-milestone) so a milestone's assets are trivial to find by filename prefix, and so a later milestone can reference an earlier milestone's asset (e.g. "compare the M2 API-only state to M4's real UI") without a cross-folder path. Each milestone's own folder (`M1/`, `M2/`, ...) holds that milestone's written summary and links to its assets — it's the index and narrative, not a duplicate copy of the files.

## 3. How every milestone gets documented

When a milestone completes (i.e., once its own completion report has been written and approved — this folder documents finished, reviewed work, not work in progress):

1. Create/update `docs/demo/M{N}/README.md` covering: project state, features completed, architecture highlights, security improvements (if any), UI implemented, the user flow, known limitations, and what's next — see `M4/README.md` for a worked example of this shape.
2. Capture real screenshots of every screen that milestone actually shipped, including error/loading/empty states where they exist — never a happy-path-only set. If a requested screen genuinely doesn't exist yet, say so in the milestone README instead of improvising one.
3. Capture short GIFs for the specific flows worth seeing in motion (form submission, a redirect, a transition) — not every screenshot needs a GIF counterpart.
4. For a milestone worth a polished pitch (not every milestone will be), record one walkthrough video and write its presenter script in `scripts/`.
5. Update this file's milestone index below if the set of milestones has changed.

### Milestone index

| Milestone | Status | Folder |
|---|---|---|
| M1 — Platform Foundation | Completed; assets not retroactively captured (predates this system) | [M1/](./M1/README.md) |
| M2 — Identity & Organization Data Layer | Completed; backend/API-only, no UI existed to capture | [M2/](./M2/README.md) |
| M3 — Authentication | Completed; backend/API-only, no frontend auth UI existed yet | [M3/](./M3/README.md) |
| M4 — Organization Experience | Completed; fully documented with real screenshots, GIFs, and a video | [M4/](./M4/README.md) |

## 4. Screenshot naming convention

```
M{N}-{seq}-{screen-name-in-kebab-case}[--{state}].png
```

- `M{N}` — the milestone the screen belongs to (`M4`), not the date it was captured.
- `{seq}` — two-digit, in the order a viewer would naturally encounter the screens (`01`, `02`, ...) — makes a flat folder sort into a coherent walkthrough on its own.
- `{screen-name}` — what's on screen, kebab-case (`login`, `create-organization`, `dashboard`).
- `--{state}` — optional, only when the same screen has more than one captured state worth distinguishing: `--empty`, `--filled`, `--validation-error`, `--loading`.

Examples actually used in `M4/`: `M4-02-register--empty.png`, `M4-07-register--validation-error.png`, `M4-10-create-organization--loading.png`.

## 5. GIF naming convention

```
M{N}-{flow-name-in-kebab-case}.gif
```

One GIF per end-to-end flow, not per screen — a GIF earns its place by showing something a static screenshot can't (a transition, a redirect, a form submitting). Examples: `M4-register-flow.gif`, `M4-login-flow.gif`, `M4-logout-flow.gif`.

## 6. Video naming convention

```
M{N}-walkthrough.mp4
```

If a milestone is re-recorded later (a real UI change, not a re-take for its own sake), suffix with the capture date rather than overwriting silently: `M4-walkthrough-2026-09-01.mp4`, and note the change in that milestone's README so it's clear which version is current.

## 7. Demo recording standards

- **Resolution:** capture the browser viewport at **1280×800** for screenshots and GIFs — large enough to be legible when embedded in a README or slide, small enough to keep file sizes and GIF frame counts reasonable. Record the polished walkthrough video at **1920×1080** — it's the one asset actually meant for a full-screen presentation, so it earns the higher resolution.
- **Browser:** Chromium (via Playwright or plain Chrome) for every capture — consistent font rendering and scrollbar behavior across every screenshot, so a side-by-side comparison across milestones isn't confounded by "which browser took this one." Don't mix in Firefox/Safari captures for the same milestone.
- **Theme:** capture in **light mode** by default, since that's what a first-time viewer sees (the app's `defaultTheme="system"` falls back to light in a clean recording environment). A milestone that specifically wants to demonstrate dark-mode support is a deliberate exception, noted as such in that milestone's README.
- **Sample data:** use realistic, clean placeholder data — a real-looking name/email like `Acme Inc.` / `founder@acme.example`, never `test123` or `asdf`. Never capture real user data, even your own personal accounts, since these assets are meant to leave the repository's controlled environment (shared with investors, posted publicly).
- **Recording quality (GIF/video):** 30fps minimum, no visible compression artifacting on text (text has to stay legible — this is a product demo, not a meme). Trim dead air: no long pauses waiting for a page load if it isn't the point being demonstrated; if load time itself is the point, say so in the caption rather than making the viewer sit through it silently.
- **No visible dev chrome:** no browser DevTools panel, no localhost port numbers cropped awkwardly mid-frame, no visible OS taskbar/notifications. The address bar itself is fine (`localhost:3000` is expected and honest for a pre-launch product) — anything clearly "someone's messy desktop" is not.

## 8. Repository conventions

- Assets are committed to the repository like any other file — no external hosting/CDN dependency for something this small, and it keeps the whole demo history versioned alongside the code that produced it.
- Keep individual video files reasonably sized (aim under ~30MB for a 2-3 minute walkthrough at 1080p — H.264, reasonable bitrate) so the repository doesn't balloon; re-encode before committing if a raw capture comes out larger.
- Never commit a screenshot/GIF/video containing a real secret, token, or credential visible on screen (an access token pasted into a URL bar, a `.env` file open in another tab, etc.) — treat this the same as the code-level "never expose secrets" rule in `AGENTS.md`.
- A milestone's README in `M{N}/` is the source of truth for *what's in* that milestone's demo set — if an asset is removed or re-captured, update that README in the same change, the same discipline `EngineeringStandards.md` §5 already applies to code and its docs.
