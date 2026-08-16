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

from app.modules.ai_employees.application.services import hire_ai_employee
from app.modules.ai_employees.domain.entities import AiEmployeeTemplate, Skill
from app.modules.ai_employees.infrastructure.orm import AiEmployeeORM, AiEmployeeSkillORM
from app.modules.ai_employees.infrastructure.repository import (
    AiEmployeeSkillRepository,
    AiEmployeeTemplateRepository,
    SkillRepository,
)
from app.modules.company_dna.application.services import create_draft_version
from app.modules.company_dna.infrastructure.orm import CompanyDnaVersionORM
from app.modules.departments.application.services import create_department
from app.modules.departments.domain.enums import FunctionType
from app.modules.departments.infrastructure.orm import DepartmentORM
from app.modules.events.infrastructure.orm import EventORM
from app.modules.goals.application.services import propose_goal
from app.modules.goals.infrastructure.orm import GoalORM
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
            "WHERE relname IN "
            "('organizations', 'organization_memberships', 'events', 'departments', "
            "'company_dna_versions', 'ai_employees', 'ai_employee_skills', 'goals')"
        )
    )
    rows = {row.relname: row for row in result.all()}

    assert set(rows) == {
        "organizations",
        "organization_memberships",
        "events",
        "departments",
        "company_dna_versions",
        "ai_employees",
        "ai_employee_skills",
        "goals",
    }
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
# 3.5. Department data (M5 Checkpoint 1)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_departments(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    await create_department(
        db_session,
        organization_id=two_tenants.org_a_id,
        name="Tenant A Support",
        function_type=FunctionType.SUPPORT,
    )
    await create_department(
        db_session,
        organization_id=two_tenants.org_b_id,
        name="Tenant B Support",
        function_type=FunctionType.SUPPORT,
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(DepartmentORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_bs_department_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    department = await create_department(
        db_session,
        organization_id=two_tenants.org_b_id,
        name="Tenant B Finance",
        function_type=FunctionType.FINANCE,
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(
            text("UPDATE departments SET name = 'hijacked' WHERE id = :id"),
            {"id": str(department.id)},
        )
    # RLS silently filters the row out of the UPDATE's target set — zero
    # rows affected, not an error, and Tenant B's row is untouched.
    assert result.rowcount == 0


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_department_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Same defense-in-depth check as the membership-table equivalent
    above: even if application code had a bug and tried to write a
    department row tagged with Tenant B's organization_id while scoped as
    Tenant A, the WITH CHECK clause must reject the insert at the database
    level."""
    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO departments "
                    "(id, organization_id, name, function_type) "
                    "VALUES (:id, :org_id, 'rogue', 'ops')"
                ),
                {"id": str(uuid.uuid4()), "org_id": str(two_tenants.org_b_id)},
            )


# ---------------------------------------------------------------------
# 3.6. Company DNA data (M5 Checkpoint 2)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_company_dna_versions(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    await create_draft_version(
        db_session, organization_id=two_tenants.org_a_id, version="1.0.0"
    )
    await create_draft_version(
        db_session, organization_id=two_tenants.org_b_id, version="1.0.0"
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(CompanyDnaVersionORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_bs_company_dna_version_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    dna_version = await create_draft_version(
        db_session, organization_id=two_tenants.org_b_id, version="1.0.0"
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(
            text("UPDATE company_dna_versions SET version = 'hijacked' WHERE id = :id"),
            {"id": str(dna_version.id)},
        )
    # RLS silently filters the row out of the UPDATE's target set — zero
    # rows affected, not an error, and Tenant B's row is untouched.
    assert result.rowcount == 0


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_company_dna_version_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Same defense-in-depth check as the department-table equivalent
    above: even if application code had a bug and tried to write a
    Company DNA version row tagged with Tenant B's organization_id while
    scoped as Tenant A, the WITH CHECK clause must reject the insert at
    the database level."""
    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO company_dna_versions "
                    "(id, organization_id, version, status) "
                    "VALUES (:id, :org_id, '1.0.0', 'draft')"
                ),
                {"id": str(uuid.uuid4()), "org_id": str(two_tenants.org_b_id)},
            )


# ---------------------------------------------------------------------
# 3.7. AI Employees data (M5 Checkpoint 3)
# ---------------------------------------------------------------------


async def _create_department_and_template(
    db_session: AsyncSession, organization_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    department = await create_department(
        db_session,
        organization_id=organization_id,
        name="Support",
        function_type=FunctionType.SUPPORT,
    )
    template = await AiEmployeeTemplateRepository().create(
        db_session,
        AiEmployeeTemplate(
            id=uuid.uuid4(),
            name="Support Agent",
            default_skills=["send_email"],
            system_prompt_scaffold="You are a helpful support agent.",
        ),
    )
    # Global-catalog create() has no transaction wrapper of its own (no
    # organization_id to scope), so it leaves an autobegin transaction
    # open on the session — commit explicitly, same as _create_user()
    # above, so the next tenant_scoped_transaction's session.begin()
    # doesn't hit "A transaction is already begun on this Session."
    await db_session.commit()
    return department.id, template.id


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_ai_employees(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    department_a, template_a = await _create_department_and_template(
        db_session, two_tenants.org_a_id
    )
    department_b, template_b = await _create_department_and_template(
        db_session, two_tenants.org_b_id
    )
    await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_a_id,
        department_id=department_a,
        template_id=template_a,
        name="Tenant A Employee",
        role_title="Agent",
    )
    await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_b_id,
        department_id=department_b,
        template_id=template_b,
        name="Tenant B Employee",
        role_title="Agent",
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(AiEmployeeORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_bs_ai_employee_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    department_b, template_b = await _create_department_and_template(
        db_session, two_tenants.org_b_id
    )
    employee = await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_b_id,
        department_id=department_b,
        template_id=template_b,
        name="Tenant B Employee",
        role_title="Agent",
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(
            text("UPDATE ai_employees SET name = 'hijacked' WHERE id = :id"),
            {"id": str(employee.id)},
        )
    # RLS silently filters the row out of the UPDATE's target set — zero
    # rows affected, not an error, and Tenant B's row is untouched.
    assert result.rowcount == 0


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_ai_employee_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    department_a, template_a = await _create_department_and_template(
        db_session, two_tenants.org_a_id
    )

    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO ai_employees "
                    "(id, organization_id, department_id, template_id, name, "
                    "role_title, status, autonomy_defaults) "
                    "VALUES (:id, :org_id, :dept_id, :template_id, 'rogue', "
                    "'Agent', 'draft', '{}')"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "org_id": str(two_tenants.org_b_id),
                    "dept_id": str(department_a),
                    "template_id": str(template_a),
                },
            )


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_ai_employee_skills(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    department_a, template_a = await _create_department_and_template(
        db_session, two_tenants.org_a_id
    )
    department_b, template_b = await _create_department_and_template(
        db_session, two_tenants.org_b_id
    )
    employee_a = await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_a_id,
        department_id=department_a,
        template_id=template_a,
        name="Tenant A Employee",
        role_title="Agent",
    )
    employee_b = await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_b_id,
        department_id=department_b,
        template_id=template_b,
        name="Tenant B Employee",
        role_title="Agent",
    )
    skill = await SkillRepository().create(
        db_session,
        Skill(
            id=uuid.uuid4(),
            key=f"send_email_{uuid.uuid4().hex[:8]}",
            description="Send an email",
            input_schema={},
            required_permission_scope={},
        ),
    )
    await db_session.commit()  # global-catalog create() leaves an autobegin transaction open

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        await AiEmployeeSkillRepository().create(
            db_session,
            organization_id=two_tenants.org_a_id,
            ai_employee_id=employee_a.id,
            skill_id=skill.id,
        )
    async with tenant_scoped_transaction(db_session, two_tenants.org_b_id):
        await AiEmployeeSkillRepository().create(
            db_session,
            organization_id=two_tenants.org_b_id,
            ai_employee_id=employee_b.id,
            skill_id=skill.id,
        )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(AiEmployeeSkillORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_ai_employee_skill_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Confirms the direct-`organization_id`-column RLS policy (Finding 1)
    actually rejects a cross-tenant write — not a join-based policy, which
    this schema deliberately does not use anywhere."""
    department_a, template_a = await _create_department_and_template(
        db_session, two_tenants.org_a_id
    )
    employee_a = await hire_ai_employee(
        db_session,
        organization_id=two_tenants.org_a_id,
        department_id=department_a,
        template_id=template_a,
        name="Tenant A Employee",
        role_title="Agent",
    )
    skill = await SkillRepository().create(
        db_session,
        Skill(
            id=uuid.uuid4(),
            key=f"send_email_{uuid.uuid4().hex[:8]}",
            description="Send an email",
            input_schema={},
            required_permission_scope={},
        ),
    )
    await db_session.commit()  # global-catalog create() leaves an autobegin transaction open

    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO ai_employee_skills "
                    "(ai_employee_id, skill_id, organization_id) "
                    "VALUES (:employee_id, :skill_id, :org_id)"
                ),
                {
                    "employee_id": str(employee_a.id),
                    "skill_id": str(skill.id),
                    "org_id": str(two_tenants.org_b_id),
                },
            )


@pytest.mark.asyncio
async def test_ai_employee_skills_rls_policy_is_not_join_based(db_session: AsyncSession) -> None:
    """Explicit structural check, per instruction: inspect the actual
    policy definition and confirm it references only this table's own
    `organization_id` column — no join/subquery against `ai_employees`
    anywhere."""
    result = await db_session.execute(
        text(
            "SELECT pg_get_expr(polqual, polrelid) AS using_expr "
            "FROM pg_policy WHERE polrelid = 'ai_employee_skills'::regclass "
            "AND polname = 'tenant_isolation'"
        )
    )
    using_expr = result.scalar_one()
    assert using_expr is not None
    assert "ai_employees" not in using_expr
    assert "organization_id" in using_expr


@pytest.mark.asyncio
async def test_global_catalogs_are_visible_identically_regardless_of_tenant_context(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """ai_employee_templates and skills have no RLS at all (locked
    decision A1) — the same rows must be visible under ANY tenant
    context, or none at all, unlike every tenant-scoped table above."""
    template = await AiEmployeeTemplateRepository().create(
        db_session,
        AiEmployeeTemplate(
            id=uuid.uuid4(),
            name="Global Template",
            default_skills=[],
            system_prompt_scaffold="scaffold",
        ),
    )
    skill = await SkillRepository().create(
        db_session,
        Skill(
            id=uuid.uuid4(),
            key=f"global_skill_{uuid.uuid4().hex[:8]}",
            description="A global skill",
            input_schema={},
            required_permission_scope={},
        ),
    )
    await db_session.commit()  # global-catalog create() leaves an autobegin transaction open

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        templates_a = {t.id for t in await AiEmployeeTemplateRepository().list_all(db_session)}
        skills_a = {s.id for s in await SkillRepository().list_all(db_session)}
    async with tenant_scoped_transaction(db_session, two_tenants.org_b_id):
        templates_b = {t.id for t in await AiEmployeeTemplateRepository().list_all(db_session)}
        skills_b = {s.id for s in await SkillRepository().list_all(db_session)}
    # No tenant context set at all — still visible, since there's no RLS to fail closed.
    async with db_session.begin():
        templates_none = {
            t.id for t in await AiEmployeeTemplateRepository().list_all(db_session)
        }
        skills_none = {s.id for s in await SkillRepository().list_all(db_session)}

    assert template.id in templates_a
    assert template.id in templates_b
    assert template.id in templates_none
    assert skill.id in skills_a
    assert skill.id in skills_b
    assert skill.id in skills_none


@pytest.mark.asyncio
async def test_global_catalog_tables_have_no_rls_at_all(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT relname, relrowsecurity FROM pg_class "
            "WHERE relname IN ('ai_employee_templates', 'skills')"
        )
    )
    rows = {row.relname: row.relrowsecurity for row in result.all()}
    assert rows == {"ai_employee_templates": False, "skills": False}


# ---------------------------------------------------------------------
# 3.8. Goals data (M5 Checkpoint 4)
# ---------------------------------------------------------------------

_GOAL_METRIC = {"metric": "churn_rate", "target": 0.05, "current": 0.08}


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_bs_goals(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    await propose_goal(
        db_session,
        organization_id=two_tenants.org_a_id,
        title="Tenant A Goal",
        success_metric=_GOAL_METRIC,
    )
    await propose_goal(
        db_session,
        organization_id=two_tenants.org_b_id,
        title="Tenant B Goal",
        success_metric=_GOAL_METRIC,
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        # No organization_id filter at all — proves RLS, not our WHERE clause.
        result = await db_session.execute(select(GoalORM))
        visible_org_ids = {row.organization_id for row in result.scalars().all()}

    assert visible_org_ids == {two_tenants.org_a_id}


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_bs_goal_row(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    goal = await propose_goal(
        db_session,
        organization_id=two_tenants.org_b_id,
        title="Tenant B Goal",
        success_metric=_GOAL_METRIC,
    )

    async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
        result = await db_session.execute(
            text("UPDATE goals SET title = 'hijacked' WHERE id = :id"),
            {"id": str(goal.id)},
        )
    # RLS silently filters the row out of the UPDATE's target set — zero
    # rows affected, not an error, and Tenant B's row is untouched.
    assert result.rowcount == 0


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_goal_into_tenant_b(
    db_session: AsyncSession, two_tenants: TwoTenants
) -> None:
    """Same defense-in-depth check as the department/AI-employee-table
    equivalents above: even if application code had a bug and tried to
    write a Goal row tagged with Tenant B's organization_id while scoped
    as Tenant A, the WITH CHECK clause must reject the insert at the
    database level."""
    with pytest.raises(DBAPIError):
        async with tenant_scoped_transaction(db_session, two_tenants.org_a_id):
            await db_session.execute(
                text(
                    "INSERT INTO goals "
                    "(id, organization_id, title, success_metric, status) "
                    "VALUES (:id, :org_id, 'rogue', '{}', 'proposed')"
                ),
                {"id": str(uuid.uuid4()), "org_id": str(two_tenants.org_b_id)},
            )


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
