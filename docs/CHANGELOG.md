# Changelog

A concise, narrative history of what shipped each sprint/milestone and why — not a replacement for `git log`, but the version of that history a future reader (or a future us) can actually skim without reconstructing intent from commit diffs.

---

## Sprint 1

### Milestone 1 — Platform Foundation (2026-07-13)

**Completed**

- Backend scaffold: FastAPI modular monolith structure per `EngineeringStandards.md §2.1`
- Environment-based configuration (Pydantic Settings, fails fast on missing config)
- Structured JSON logging, request ID / correlation ID middleware, global exception handling with the standard error envelope (`API.md §7`)
- Health checks: `/healthz` (liveness, no dependency checks) and `/readyz` (readiness, real Postgres + Redis connectivity checks)
- Alembic configured (async), wired to `Settings`, verified against a live Postgres instance
- Docker Compose: Postgres + Redis for local development
- Frontend scaffold: Next.js 15.5.20, Tailwind v4, shadcn/ui, theme/provider stack (React Query, next-themes, Sonner)
- 10 backend tests (7 unit, 1 integration via testcontainers), all passing; ruff and mypy clean
- Root README and `AGENTS.md` engineering charter

**Notes**

- Departments deferred — not part of M1, and not folded into M2's organizations work either; revisit when Company DNA lands, since meaningful department suggestions depend on it (see `PRD.md §10`)
- Next.js pinned to **15.5.20**, not "latest" (which now resolves to Next 16) — a deliberate, flagged decision, not silent drift off the documented stack
- Row-Level Security begins in M2, alongside the first real tenant-scoped tables (organizations, users, memberships)
- The Event Store (Postgres outbox + Redis Streams relay, per `ADR 0001`) also begins in M2 — nothing to write yet with no business logic in M1
- Added an `identity` module to `EngineeringStandards.md`'s backend layout — it had no owner for auth/sessions despite `Security.md` already specifying that behavior
- Two real bugs surfaced by our own tests, fixed rather than worked around: `BaseHTTPMiddleware` not composing reliably with FastAPI's global `Exception` handler (switched both middlewares to pure ASGI), and `X-Request-ID` missing specifically on 500 responses (now set directly in every exception handler, not solely via middleware)
- Local dev note: this machine's native Postgres service already occupies host port 5432 — `docker-compose.yml` maps our container to 5433 instead
- **Process gap, acknowledged:** all of M1 was committed directly to `main`, which conflicts with `EngineeringStandards.md §5`'s own "every change lands via pull request" rule. Not repeated for M2 onward.
