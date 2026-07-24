# API

**Status:** v1.0 — Foundational
**Owner:** Backend / Platform Engineering
**Stack:** FastAPI
**Depends on:** [Security.md](./Security.md), [AIEmployees.md](./AIEmployees.md)

---

## 1. Purpose

This document defines Velora's API design conventions: versioning, request/response shape, error format, the async task pattern for AI Runtime operations, and the auth scheme clients use. It is the contract the frontend (Next.js) and any future partner integrations build against — it should be stable and boring even while the AI Runtime underneath evolves quickly.

## 2. Design Principles

- **REST over the wire, resource-oriented.** Digital Employees, Departments, Goals, Tasks are resources with standard verbs. We do not invent a bespoke RPC style where a REST resource mapping is natural.
- **Two distinct traffic shapes, handled differently:**
  - Human-facing CRUD/read traffic — low latency, synchronous, cacheable.
  - Digital Employee action traffic — often long-running (seconds to minutes), must never block on request lifetime.
- **FastAPI's auto-generated OpenAPI schema is the contract**, not a document maintained by hand — this file describes the *conventions* the generated schema follows, not a hand-written spec that can drift from the implementation.
- **Boring is a feature.** Novel API shapes for novel AI concepts should be resisted where a standard REST/async pattern already covers the need — see §5 for the one deliberate exception (the async task pattern) and why it earns its complexity.

## 3. Versioning

- URL path versioning: `/v1/...`. A breaking change to a resource's shape ships as `/v2/...` for that resource family, not a global version bump across the entire API.
- Additive changes (new optional field, new endpoint) do not require a version bump.
- Deprecation: a deprecated endpoint returns a `Deprecation` and `Sunset` header (per RFC 8594) for at least one full quarter before removal, and deprecation is announced in release notes — never a silent removal.

## 4. Authentication & Tenant Context

- Every request carries a bearer access token (`Authorization: Bearer <jwt>`), validated per [Security.md §3](./Security.md#3-session--token-model).
- Clients never send `organization_id` as a request parameter for tenant scoping — it is derived server-side from the token/subdomain at the Gateway and propagated internally via the signed Tenant Context Token ([Security.md §3.3](./Security.md#33-tenant-context-propagation)). Any endpoint that appears to accept a client-supplied tenant identifier for scoping purposes is a bug, not a feature.
- API keys (for partner/integration use) follow the same tenant-resolution path, scoped at issuance to one organization and a defined permission set.

### 4.1 Authentication Endpoints (Milestone 3)

This document didn't specify auth endpoint shapes precisely enough to implement blind — the decision, so it doesn't get re-litigated per-endpoint later:

| Endpoint | Shape | Why |
|---|---|---|
| `POST /v1/users` | Resource creation (register) | Follows §2's resource-oriented convention directly — creating a user is creating the `users` resource. |
| `GET /v1/users/me` | Resource read, protected | Same convention; `me` resolves via the authenticated-user dependency, not a client-supplied id — proves that dependency end-to-end. |
| `POST /v1/auth/login` | Action, not resource CRUD | Session/token issuance isn't a resource operation. This is the same kind of conventionally-accepted exception §5 already makes for the async task pattern — a standard REST-CRUD shape doesn't fit, and inventing one would be worse than a small, named action endpoint. |
| `POST /v1/auth/refresh` | Action, not resource CRUD | Same reasoning as login. |

No new precedent beyond these four — a future endpoint that doesn't map cleanly to a resource should be justified the same way, not treated as a general license for action-style endpoints.

## 5. The Async Task Pattern

Anything that touches the AI Runtime Plane (Digital Employee invocation, goal decomposition, skill execution with external side effects) does not run synchronously inside the HTTP request. Instead:

```
POST /v1/tasks          → 202 Accepted
                           { "task_id": "...", "status": "pending", "status_url": "/v1/tasks/{task_id}" }
```

The client then either:
- Polls `GET /v1/tasks/{task_id}` for status (`pending → claimed → in_progress → done|failed`), or
- Subscribes via the Realtime Gateway (WebSocket/SSE) for push updates on the same `task_id`.

**Why this earns its complexity:** a synchronous request/response model would force the Gateway to hold a connection open for however long a Digital Employee's reasoning loop takes — seconds to minutes, unpredictable, and directly at odds with horizontal scalability and backpressure. The 202 pattern decouples "the request was accepted" from "the work is done," which is also exactly the shape the underlying system already has (tasks are events, per [Database.md §3.5](./Database.md#35-goals--tasks)) — the API is not inventing new semantics, just exposing the real ones.

Every task creation request accepts (and for AI Runtime actions, requires) an **idempotency key** — a client-generated identifier that ensures a network retry does not create a duplicate task or double-execute a skill (e.g., sending an email twice). See [Database.md §3.5](./Database.md#35-goals--tasks), `tasks.idempotency_key`.

## 6. Request / Response Conventions

- **Content type:** `application/json` for all request/response bodies.
- **Casing:** `snake_case` for all JSON fields — matches Python/Pydantic model field names directly, no serialization-layer translation to maintain.
- **Timestamps:** ISO 8601, UTC, with explicit `Z` suffix.
- **IDs:** UUIDs everywhere, matching the database primary key types ([Database.md §3](./Database.md#3-core-schema)) — no separate public-facing integer ID scheme.
- **Pagination:** cursor-based (`?cursor=...&limit=...`) for all list endpoints, not offset-based — offset pagination degrades badly on high-write tables like `tasks` and `audit_log_entries`, and cursor pagination is the only option that stays correct under concurrent writes.
- **Filtering:** explicit query parameters per filterable field, not a generic query-language parameter, to keep FastAPI's request validation and OpenAPI schema generation doing the work rather than a hand-rolled parser.

## 7. Error Format

A single consistent error shape across every endpoint:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Digital Employee with id '...' was not found.",
    "details": {},
    "request_id": "..."
  }
}
```

- `code` is a stable, machine-readable string (safe to branch on in client code) — never just an HTTP status code repeated as a string.
- `message` is human-readable, safe to display, and never leaks internal implementation detail (stack traces, SQL, internal service names).
- `request_id` ties the error back to a specific trace in the Observability stack ([Deployment.md §6](./Deployment.md#6-observability)) — the first thing support/engineering asks a customer for.
- HTTP status codes are used correctly and consistently (`400` validation, `401`/`403` auth, `404` not found, `409` conflict/idempotency, `429` rate limited, `5xx` server error) — the JSON body is the detail, the status code is the category.

## 8. Rate Limiting

Every response includes standard rate-limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) so clients can self-throttle rather than discover limits via `429`s. Limits are enforced per organization, per API key, and per Digital Employee, per [Security.md §10](./Security.md#10-rate-limiting--abuse-prevention) — this document only specifies how that's surfaced to clients.

## 9. Webhooks (Outbound)

Partner/integration consumers can subscribe to a scoped set of event types (a public-facing subset of the internal Event Bus categories — e.g. `task.completed`, `ai_employee.hired`) via a registered webhook URL. Delivery is at-least-once with a signed payload (HMAC over body, using a per-integration secret) so receivers can verify authenticity; retried with backoff on non-2xx response, with a dead-letter/disable-after-N-failures policy mirroring the internal Event Bus's dead-letter handling.

## 10. Documentation & Discoverability

- FastAPI's generated OpenAPI schema is served at `/v1/openapi.json`, with interactive docs at `/v1/docs` (Swagger UI) gated behind auth in production (not publicly crawlable) until a public partner API is a deliberate product decision.
- Every Pydantic request/response model requires a docstring and field descriptions — these flow directly into the generated schema, so documentation quality is enforced by code review, not a separately maintained spec.

## 11. Non-Goals (v1)

- No GraphQL — the resource shapes here are a good REST fit, and introducing a second query paradigm is not justified by anything in the current domain model.
- No public partner API / marketplace surface in v1 — the versioning and auth conventions above are designed to support one later without a rework, but scoping, quotas, and partner-facing docs for that are a distinct future decision.
- No client SDK generation commitment yet — the OpenAPI schema makes this straightforward to add later (e.g. via `openapi-generator`), but it is not a v1 deliverable.
