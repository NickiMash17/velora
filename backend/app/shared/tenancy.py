"""Tenant context establishment for Row-Level Security.

Per docs/architecture/Database.md §2.2 and docs/architecture/Security.md
§4, every RLS policy keys on a session-local Postgres variable,
`app.current_org_id`. This module is the ONLY place that variable gets
set — no repository or service should issue its own SET/set_config call,
so there is exactly one implementation to audit for correctness.

Implementation notes:
- Uses `SELECT set_config('app.current_org_id', $1, true)` rather than
  `SET LOCAL app.current_org_id = '...'` — Postgres's `SET` statement does
  not accept bind parameters, so the naive form would require
  string-interpolating the value into SQL. `set_config()` is a normal
  function call and takes a real bind parameter.
- The third argument (`is_local=true`) is what makes this the equivalent
  of `SET LOCAL`: the value reverts automatically at the end of the
  current transaction. This matters specifically because SQLAlchemy's
  async engine pools physical connections — a plain `SET` (session-level,
  not transaction-level) would persist on that physical connection and
  could leak into a *different* tenant's transaction the next time the
  pool hands out the same connection. `is_local=true` makes that
  structurally impossible.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SET_TENANT_CONTEXT = text("SELECT set_config('app.current_org_id', :organization_id, true)")
_SET_USER_CONTEXT = text("SELECT set_config('app.current_user_id', :user_id, true)")


async def set_tenant_context(session: AsyncSession, organization_id: UUID) -> None:
    """Sets app.current_org_id for the remainder of the current transaction
    only. Must be called after a transaction has begun on `session`."""
    await session.execute(_SET_TENANT_CONTEXT, {"organization_id": str(organization_id)})


@asynccontextmanager
async def tenant_scoped_transaction(
    session: AsyncSession, organization_id: UUID
) -> AsyncIterator[AsyncSession]:
    """Opens a transaction on `session` with tenant context established, so
    every query issued inside it is subject to RLS for `organization_id`.

    This is also how a brand-new organization is created (see
    app/modules/organizations/application/services.py): there's no
    pre-existing tenant context for an org that doesn't exist yet, so the
    caller sets context to the org's own about-to-be-created id and lets
    RLS's WITH CHECK validate every insert against it — no elevated or
    RLS-bypassing database role is needed anywhere in this flow.
    """
    async with session.begin():
        await set_tenant_context(session, organization_id)
        yield session


@asynccontextmanager
async def user_scoped_transaction(
    session: AsyncSession, user_id: UUID
) -> AsyncIterator[AsyncSession]:
    """Opens a transaction with `app.current_user_id` set instead of
    `app.current_org_id` — for exactly one purpose: letting a user
    discover which organization(s) they belong to before any tenant
    context exists at all (see
    docs/architecture/decisions/0002-organization-membership-self-visibility.md).

    This must NEVER be used for anything but
    OrganizationMembershipRepository.list_for_user's SELECT. The RLS
    policy this context activates (`self_visibility` on
    `organization_memberships`) is deliberately scoped `FOR SELECT` only
    — it has no `WITH CHECK` and cannot govern INSERT/UPDATE regardless
    of what predicate it's given, so using this helper for a write would
    simply fail closed under `tenant_isolation`, not silently succeed
    against the wrong organization. Still: don't use this for anything
    else. If a future case needs write access, it needs tenant context
    (tenant_scoped_transaction), not user context.
    """
    async with session.begin():
        await session.execute(_SET_USER_CONTEXT, {"user_id": str(user_id)})
        yield session
