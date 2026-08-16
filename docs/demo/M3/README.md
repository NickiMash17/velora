# M3 — Authentication (Demo Notes)

**Status:** Completed. Assets not retroactively captured — no frontend UI was built in this milestone (explicitly out of scope, by design).

## What existed

- Backend-only authentication: `POST /v1/users` (register), `POST /v1/auth/login`, `POST /v1/auth/refresh`, `GET /v1/users/me`.
- Argon2id password hashing, HS256 JWT access tokens (~15 min), rotating opaque refresh tokens with family-based replay detection, Redis-backed login rate limiting.
- Verified end-to-end via `curl`/automated tests only — registration, login, token refresh and rotation, replay-attack family revocation. No screen exists to screenshot; every interaction in this milestone was an HTTP request.

## Why nothing is captured here

M3's own scope explicitly excluded frontend authentication screens — see that milestone's completion report. The first time a human could actually see a login form was M4, which built the login/register screens directly on top of M3's endpoints — see [`../M4/README.md`](../M4/README.md).
