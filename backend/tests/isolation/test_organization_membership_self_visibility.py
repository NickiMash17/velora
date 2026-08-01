"""Isolation tests for ADR 0002's self-visibility RLS policy on
`organization_memberships`.

Two things must both be true, proven with no application-level
organization_id/user_id filter doing the real work — Postgres itself
must enforce both:

1. A user can see their OWN membership rows across any number of
   organizations, with no tenant context established at all.
2. That same self-visibility context grants NO write access — the
   specific regression ADR 0002 exists to prevent (a `FOR SELECT`-only
   policy cannot govern INSERT/UPDATE, so a caller inside
   user_scoped_transaction gets exactly the same fail-closed behavior on
   writes as a caller with no context set at all).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.modules.organizations.infrastructure.repository import OrganizationMembershipRepository
from app.shared.tenancy import user_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"self-vis-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"self-vis-{uuid.uuid4().hex[:10]}"


async def _create_user(session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(session, user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_list_for_user_sees_only_its_own_memberships_across_organizations(
    db_session: AsyncSession,
) -> None:
    user_a = await _create_user(db_session)
    user_b = await _create_user(db_session)

    org_1 = await create_organization_with_admin(
        db_session, name="Org One", slug=_unique_slug(), admin_user_id=user_a.id
    )
    org_2 = await create_organization_with_admin(
        db_session, name="Org Two", slug=_unique_slug(), admin_user_id=user_a.id
    )
    # A membership belonging to a different user entirely — must never
    # appear in user_a's results.
    await create_organization_with_admin(
        db_session, name="Org Three", slug=_unique_slug(), admin_user_id=user_b.id
    )

    memberships = await OrganizationMembershipRepository().list_for_user(db_session, user_a.id)

    visible_org_ids = {m.organization_id for m in memberships}
    assert visible_org_ids == {org_1.organization.id, org_2.organization.id}
    assert all(m.user_id == user_a.id for m in memberships)


@pytest.mark.asyncio
async def test_list_for_user_returns_empty_for_a_user_with_no_memberships(
    db_session: AsyncSession,
) -> None:
    lonely_user = await _create_user(db_session)

    memberships = await OrganizationMembershipRepository().list_for_user(
        db_session, lonely_user.id
    )

    assert memberships == []


@pytest.mark.asyncio
async def test_get_for_user_in_organization_confirms_active_membership(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session)
    org = await create_organization_with_admin(
        db_session, name="Acme", slug=_unique_slug(), admin_user_id=user.id
    )

    membership = await OrganizationMembershipRepository().get_for_user_in_organization(
        db_session, org.organization.id, user.id
    )

    assert membership is not None
    assert membership.user_id == user.id
    assert membership.organization_id == org.organization.id


@pytest.mark.asyncio
async def test_get_for_user_in_organization_returns_none_for_a_non_member(
    db_session: AsyncSession,
) -> None:
    admin = await _create_user(db_session)
    outsider = await _create_user(db_session)
    org = await create_organization_with_admin(
        db_session, name="Acme", slug=_unique_slug(), admin_user_id=admin.id
    )

    membership = await OrganizationMembershipRepository().get_for_user_in_organization(
        db_session, org.organization.id, outsider.id
    )

    assert membership is None


@pytest.mark.asyncio
async def test_get_for_user_in_organization_returns_none_for_a_nonexistent_organization(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session)

    membership = await OrganizationMembershipRepository().get_for_user_in_organization(
        db_session, uuid.uuid4(), user.id
    )

    assert membership is None


@pytest.mark.asyncio
async def test_user_scoped_transaction_cannot_be_used_to_insert_a_cross_org_membership(
    db_session: AsyncSession,
) -> None:
    """The regression ADR 0002 exists to prevent: self-visibility context
    must grant SELECT only. Attempting a write inside
    user_scoped_transaction — even one whose user_id matches the caller,
    the one thing the self_visibility predicate checks — must be
    rejected, because that policy has no WITH CHECK and cannot govern
    INSERT at all; only tenant_isolation's WITH CHECK applies, and
    app.current_org_id is unset in this context, so it fails closed."""
    attacker = await _create_user(db_session)
    victim_admin = await _create_user(db_session)
    victim_org = await create_organization_with_admin(
        db_session, name="Victim Org", slug=_unique_slug(), admin_user_id=victim_admin.id
    )

    with pytest.raises(DBAPIError):
        async with user_scoped_transaction(db_session, attacker.id):
            await db_session.execute(
                text(
                    "INSERT INTO organization_memberships "
                    "(id, organization_id, user_id, role, status) "
                    "VALUES (:id, :org_id, :user_id, 'org_admin', 'active')"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "org_id": str(victim_org.organization.id),
                    "user_id": str(attacker.id),
                },
            )
