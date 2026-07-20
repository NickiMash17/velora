"""Cross-tenant isolation tests — the load-bearing proof that Row-Level
Security, not application-level filtering, is what actually prevents one
organization from reading or writing another's data.

Per docs/architecture/Database.md §2.2 and
docs/engineering/EngineeringStandards.md §4: this is "the one test
category that is never optional or skippable for a passing build." Every
test here deliberately issues queries with NO application-level
organization_id WHERE clause, to prove RLS alone — not a query filter we
wrote — is what's doing the filtering. A real, migrated Postgres is used
throughout; nothing here is mocked, because a mock cannot fail to enforce
a Postgres security policy the way a misconfigured real database can.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.infrastructure.orm import EventORM
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.modules.organizations.infrastructure.orm import OrganizationMembershipORM, OrganizationORM
from app.shared.tenancy import set_tenant_context, tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"tenant-{uuid.uuid4().hex[:10]}"


async def _create_user(session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(session, user)
    await session.commit()
    return user


class TwoTenants:
    """Two fully independent organizations, each with their own founding
    admin, created via the real application service — not raw SQL."""

    def __init__(self, org_a_id: uuid.UUID, org_b_id: uuid.UUID) -> None:
        self.org_a_id = org_a_id
        self.org_b_id = org_b_id


@pytest.fixture
async def two_tenants(db_session: AsyncSession) -> TwoTenants:
    admin_a = await _create_user(db_session)
    admin_b = await _create_user(db_session)

    result_a = await create_organization_with_admin(
        db_session, name="Tenant A Inc", slug=_unique_slug(), admin_user_id=admin_a.id
    )
    result_b = await create_organization_with_admin(
        db_session, name="Tenant B Inc", slug=_unique_slug(), admin_user_id=admin_b.id
    )
    return TwoTenants(org_a_id=result_a.organization.id, org_b_id=result_b.organization.id)


# ---------------------------------------------------------------------
# 0. The precondition every test below silently depends on: the role
#    tests (and the running application) connect as must actually be
#    subject to RLS at all. This is the automated form of the bug that
#    made every test in this file pass for the wrong reason before it
#    was found and fixed — see this milestone's completion report.
#    Postgres superusers, and table owners without FORCE ROW LEVEL
#    SECURITY, bypass RLS unconditionally regardless of how correct the
#    policy SQL is; a future migration change that regresses either
#    property would make this whole file silently meaningless again
#    without this check.
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_role_is_not_superuser_and_cannot_bypass_rls(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )
    row = result.one()

    assert row.rolsuper is False, (
        "the role tests connect as is a superuser — RLS is bypassed unconditionally "
        "and every isolation test in this file passes for the wrong reason"
    )
    assert row.rolbypassrls is False, (
        "the role tests connect as has BYPASSRLS — RLS is bypassed unconditionally "
        "and every isolation test in this file passes for the wrong reason"
    )


@pytest.mark.asyncio
async def test_tenant_tables_have_rls_enabled_and_forced(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname IN ('organizations', 'organization_memberships', 'events')"
        )
    )
    rows = {row.relname: row for row in result.all()}

    assert set(rows) == {"organizations", "organization_memberships", "events"}
    for table_name, row in rows.items():
        assert row.relrowsecurity is True, f"{table_name} does not have RLS enabled"
        assert row.relforcerowsecurity is True, (
            f"{table_name} has RLS enabled but not FORCED — the table-owner exemption "
            "still applies, which is exactly the gap this test exists to catch"
        )


# ---------------------------------------------------------------------
# 1. Organization data
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_organization_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(OrganizationORM))
        visible_ids = {row.id for row in result.scalars().all()}

    assert visible_ids == {two_tenants.org_a_id}
    assert two_tenants.org_b_id not in visible_ids


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_bs_organization_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(
            text("UPDATE organizations SET name = 'hijacked' WHERE id = :id"),
            {"id": str(two_tenants.org_b_id)},
        )
    # RLS silently filters the row out of the UPDATE's target set — zero
    # rows affected, not an error, and Tenant B's row is untouched.
    assert result.rowcount == 0


# ---------------------------------------------------------------------
# 2. Membership data
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_membership_rows(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(select(OrganizationMembershipORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_membership_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Defense-in-depth check: even if application code had a bug and tried
    to write a membership row tagged with Tenant B's organization_id while
    scoped as Tenant A, the WITH CHECK clause must reject the insert at the
    database level."""
    rogue_user = await _create_user(db_session)

    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO organization_memberships "
                    "(id, organization_id, user_id, role, status) "
                    "VALUES (:id, :org_id, :user_id, 'member', 'active')"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "org_id": str(two_tenants.org_b_id),
                    "user_id": str(rogue_user.id),
                },
            )


# ---------------------------------------------------------------------
# 3. Event data
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_events(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(select(EventORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


# ---------------------------------------------------------------------
# 4/5. RLS is enforced by Postgres itself, not application filtering
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_tenant_context_set_hides_everything_fail_closed(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """With app.current_org_id never set at all, current_setting(...,
    true) returns NULL, and `organization_id = NULL` is never true — so
    the fail-closed default is zero visible rows, not every tenant's rows,
    and not a hard error either."""
    async with db_session.begin():
        orgs = (await db_session.execute(select(OrganizationORM))).scalars().all()
        memberships = (
            (await db_session.execute(select(OrganizationMembershipORM))).scalars().all()
        )
        events = (await db_session.execute(select(EventORM))).scalars().all()

    assert orgs == []
    assert memberships == []
    assert events == []


@pytest.mark.asyncio
async def test_rls_survives_a_query_with_no_application_level_filter(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """The decisive test: a bare, unfiltered `SELECT * FROM organizations`
    — the exact query a bug in application code would issue if it forgot
    an organization_id WHERE clause entirely. If this returns only Tenant
    A's row, isolation is coming from Postgres, not from any WHERE clause
    our repository code happened to include."""
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(text("SELECT * FROM organizations"))
        rows = result.fetchall()

    assert len(rows) == 1
    assert str(rows[0].id) == str(two_tenants.org_a_id)


@pytest.mark.asyncio
async def test_switching_tenant_context_switches_visibility(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Same session, sequential transactions, different tenant context each
    time — proves context is transaction-scoped (SET LOCAL semantics via
    set_config(..., true)), not stuck from a previous call."""
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result_a = await db_session.execute(select(OrganizationORM))
        visible_a = {row.id for row in result_a.scalars()}

    async with tenant_scoped_transaction(db_session, two_tenants.org_b_id):
        result_b = await db_session.execute(select(OrganizationORM))
        visible_b = {row.id for row in result_b.scalars()}

    assert visible_a == {two_tenants.org_a_id}
    assert visible_b == {two_tenants.org_b_id}


@pytest.mark.asyncio
async def test_setting_context_without_local_flag_would_leak_is_not_used(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Guards against a regression where someone 'simplifies' tenancy.py to
    use `SET` instead of `set_config(..., true)`: after a tenant-scoped
    transaction commits, a fresh transaction on the SAME session with NO
    context set must see nothing — proving the previous context did not
    persist on the connection."""
    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        await set_tenant_context(db_session, two_tenants.org_a_id)

    async with db_session.begin():
        result = await db_session.execute(select(OrganizationORM))
        rows = result.scalars().all()

    assert rows == []
