# M2 — Identity & Organization Data Layer (Demo Notes)

**Status:** Completed. Assets not retroactively captured — no user-facing surface existed to capture.

## What existed

- Backend only: `users`, `organizations`, `organization_memberships`, and `events` tables, with Row-Level Security enforced and forced on every tenant-scoped table.
- `OrganizationRepository`/`OrganizationMembershipRepository` and the `create_organization_with_admin` application service (organization creation + founding admin membership + outbox events, atomically).
- A dedicated cross-tenant isolation test suite (`tests/isolation/`) proving RLS — not application-level filtering — is what actually prevents one organization from reading another's data.
- No API layer and no frontend existed for any of this yet — it was purely a data/domain layer, exercised only by tests.

## Why nothing is captured here

There was nothing to point a browser at. The soonest this milestone's work became visible to an actual user was M4, once `POST /v1/organizations` and the onboarding screen were built on top of it — see [`../M4/README.md`](../M4/README.md).
