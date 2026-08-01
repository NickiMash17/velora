# ADR 0002 — Organization Membership Self-Visibility RLS Policy

**Status:** Accepted
**Date:** 2026-07-28

## Context

Milestone 4 needs to answer one question the platform has never had to ask before: "which
organization(s), if any, does the currently authenticated user belong to?" This is exactly
what decides whether a freshly logged-in user sees onboarding (zero organizations) or is
routed into an existing organization's dashboard (one or more).

The existing RLS policy on `organization_memberships` ([Database.md §2.2](../Database.md#22-enforcement-not-convention),
migration `aa3e8dcefd79_identity_and_organization_data_layer.py`) is:

```sql
CREATE POLICY tenant_isolation ON organization_memberships
USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
```

This is correct for every query this platform has needed so far — it fails closed to zero
rows unless a tenant context is already established. But "which orgs am I in" is
structurally different from every other query in the system: it is asked **before** any
tenant context exists, by definition, since discovering that context is the whole point of
the query. Under the existing policy alone, this query always returns zero rows, for every
user, forever — not a bug in the policy, just a case it was never designed to answer.

## Decision

Add a **second, permissive** policy to `organization_memberships`, scoped explicitly to
`FOR SELECT`:

```sql
CREATE POLICY self_visibility ON organization_memberships
FOR SELECT
USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
```

Postgres combines multiple permissive policies for the same command with `OR`, so this
does not touch or weaken `tenant_isolation` — a row is visible if it matches the tenant
context (as before) **or** if its `user_id` matches a new session-local GUC,
`app.current_user_id`, which this policy is the only reason to ever set.

`app.current_user_id` is set by a new, narrowly-scoped helper, `user_scoped_transaction`
(`app/shared/tenancy.py`, mirroring the existing `tenant_scoped_transaction` exactly), used
by exactly one repository method:
`OrganizationMembershipRepository.list_for_user`. Its docstring states plainly that it
exists for that one `SELECT` and nothing else.

**The `FOR SELECT` restriction is the load-bearing part of this decision.** A policy with
no explicit command list applies to `ALL` commands, and — critically — if no `WITH CHECK`
clause is given, Postgres reuses the `USING` expression as the `WITH CHECK` expression too.
Had this policy been written without `FOR SELECT`, it would also govern `INSERT`/`UPDATE`:
any caller inside a `user_scoped_transaction` could then write a membership row into
**any** organization, as long as the row's `user_id` matched their own id — a real
privilege-escalation path, not a theoretical one, and one that would only need a future
contributor to call `OrganizationMembershipRepository.create` inside the wrong transaction
helper to trigger. Scoping to `FOR SELECT` makes that class of mistake structurally
impossible rather than a code-review discipline problem: a `FOR SELECT` policy has no
`WITH CHECK` at all, so it cannot govern writes regardless of what predicate it's given.

## Alternatives Considered

- **A `_system`/`_admin` bypass repository**, per [Database.md §2.2](../Database.md#22-enforcement-not-convention)'s
  own carve-out for genuinely unscoped queries. Rejected: the only way to actually bypass
  RLS is a database role with `BYPASSRLS`, which is precisely the property migration
  `aa3e8dcefd79` went out of its way to deny the application's `velora_app` role
  (`NOSUPERUSER NOBYPASSRLS`) so that "RLS means anything at all." Reintroducing a
  bypass-capable role for this one query would undo that guarantee for every table the role
  can see, not just this one, and would move the actual enforcement into
  hand-written application-layer filtering — exactly the model Database.md §2.2 says RLS
  exists to not depend on.
- **Restructure the existing `tenant_isolation` policy to accept either predicate**,
  instead of adding a second policy. Rejected: it would conflate two genuinely different
  authorization questions ("is this row in my current tenant" vs. "is this row mine,
  regardless of tenant") into one policy, making it harder to reason about which callers
  rely on which guarantee, and harder to remove the self-visibility carve-out later in
  isolation if this design is revisited.
- **Have login itself resolve org context** (so no self-visibility query is ever needed
  outside the identity module). Rejected: Security.md's own Milestone 3 note is explicit
  that a *future milestone's org-creation/switching flow* is what first populates
  org-scoped claims, not login itself, and `identity/api/dependencies.py`'s existing
  docstring already commits to "who is this" and "what org are they acting in" being
  separate, composable concerns. Baking org resolution into login would also require the
  identity module to depend on the organizations module, inverting the dependency
  direction every other part of this milestone otherwise keeps one-way.

## Consequences

- **Easier:** "does this user belong to any organization" becomes a real, RLS-enforced
  query instead of an unanswerable one — this is what onboarding routing in Milestone 4
  depends on.
- **Harder / to watch:** this is the first table in the schema with more than one RLS
  policy, and the first session-local GUC besides `app.current_org_id`. A future
  tenant-scoped table that needs the same kind of self-visibility exception should follow
  this exact pattern (`FOR SELECT`, a dedicated GUC, a narrowly-scoped transaction helper,
  a repository method that is the *only* caller) rather than inventing a new one.
- **Guarded, not just documented:** a dedicated isolation-suite test proves
  `user_scoped_transaction` cannot be used to `INSERT`/`UPDATE` a membership row for an org
  the caller isn't tenant-scoped into — this is a regression test for the specific mistake
  this ADR exists to prevent, not just a description of intent.
