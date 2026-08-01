# M1 — Platform Foundation (Demo Notes)

**Status:** Completed. Assets not retroactively captured — this milestone predates the demo & showcase system introduced after M4.

## What existed

- Backend: FastAPI application skeleton, health/readiness endpoints (`/healthz`, `/readyz`), structured logging, request ID middleware, the shared error envelope.
- Frontend: Next.js 15 scaffold with Tailwind v4, shadcn/ui, and the theme provider — surfaced through a single foundation-verification page at `/`, whose own docstring stated explicitly it was "not the product Landing Page."
- No user-facing product functionality existed yet — no accounts, no data, nothing to demo to a non-engineering audience.

## Why nothing is captured here

The foundation-verification page (a card confirming Tailwind/shadcn/the theme toggle worked) was superseded and replaced outright in M4, once the root route gained a real job (session resolution). Recreating a screenshot of a page that no longer exists, for a milestone whose entire point was "infrastructure only, nothing to show a user," would not add anything a reader couldn't get from this note.

## If this gap ever needs filling

The exact page still exists in git history (`frontend/app/page.tsx` prior to the M4 commit that replaced it) — checking out that commit and running the frontend locally would reproduce it exactly, if a historical screenshot is ever genuinely needed.
