"""Integration tests for the AI Employees application services — real,
migrated Postgres throughout. Mirrors test_department_service.py's and
test_company_dna_service.py's pattern.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_employees.application.services import (
    activate_ai_employee,
    configure_ai_employee,
    hire_ai_employee,
    pause_ai_employee,
    retire_ai_employee,
)
from app.modules.ai_employees.domain.entities import AiEmployeeTemplate
from app.modules.ai_employees.domain.enums import AiEmployeeStatus
from app.modules.ai_employees.domain.errors import (
    AiEmployeeNotFoundError,
    AiEmployeeTemplateNotFoundError,
    InvalidAiEmployeeTransitionError,
    MissingConfigurationError,
)
from app.modules.ai_employees.infrastructure.repository import AiEmployeeTemplateRepository
from app.modules.company_dna.application.services import create_draft_version
from app.modules.company_dna.domain.errors import CompanyDnaVersionNotFoundError
from app.modules.departments.application.services import create_department
from app.modules.departments.domain.enums import FunctionType
from app.modules.departments.domain.errors import DepartmentNotFoundError
from app.modules.events.infrastructure.orm import EventORM
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.shared.tenancy import tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"emp-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"emp-tenant-{uuid.uuid4().hex[:10]}"


async def _create_org(db_session: AsyncSession) -> uuid.UUID:
    admin = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(db_session, admin)
    await db_session.commit()

    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=admin.id
    )
    return result.organization.id


async def _create_department(db_session: AsyncSession, organization_id: uuid.UUID) -> uuid.UUID:
    department = await create_department(
        db_session,
        organization_id=organization_id,
        name="Support",
        function_type=FunctionType.SUPPORT,
    )
    return department.id


async def _create_template(db_session: AsyncSession) -> uuid.UUID:
    template = AiEmployeeTemplate(
        id=uuid.uuid4(),
        name="Support Agent",
        default_skills=["send_email"],
        system_prompt_scaffold="You are a helpful support agent.",
    )
    created = await AiEmployeeTemplateRepository().create(db_session, template)
    await db_session.commit()
    return created.id


async def _create_dna_version(db_session: AsyncSession, organization_id: uuid.UUID) -> uuid.UUID:
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )
    return dna_version.id


@pytest.mark.asyncio
async def test_hire_ai_employee_persists_employee_and_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    department_id = await _create_department(db_session, organization_id)
    template_id = await _create_template(db_session)

    employee = await hire_ai_employee(
        db_session,
        organization_id=organization_id,
        department_id=department_id,
        template_id=template_id,
        name="Riley",
        role_title="Support Agent",
    )

    assert employee.status == AiEmployeeStatus.DRAFT
    assert employee.department_id == department_id
    assert employee.template_id == template_id
    assert employee.autonomy_defaults == {}
    assert employee.permission_scope is None

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    hired_events = [e for e in events if e.type == "EmployeeHired"]
    assert len(hired_events) == 1
    assert hired_events[0].topic == "employee.hired"
    assert hired_events[0].producer == "ai_employees"
    assert hired_events[0].payload == {
        "ai_employee_id": str(employee.id),
        "department_id": str(department_id),
        "template_id": str(template_id),
    }


@pytest.mark.asyncio
async def test_hire_ai_employee_rejects_unknown_department(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    template_id = await _create_template(db_session)

    with pytest.raises(DepartmentNotFoundError):
        await hire_ai_employee(
            db_session,
            organization_id=organization_id,
            department_id=uuid.uuid4(),
            template_id=template_id,
            name="Riley",
            role_title="Support Agent",
        )


@pytest.mark.asyncio
async def test_hire_ai_employee_rejects_unknown_template(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    department_id = await _create_department(db_session, organization_id)

    with pytest.raises(AiEmployeeTemplateNotFoundError):
        await hire_ai_employee(
            db_session,
            organization_id=organization_id,
            department_id=department_id,
            template_id=uuid.uuid4(),
            name="Riley",
            role_title="Support Agent",
        )


async def _hire(db_session: AsyncSession, organization_id: uuid.UUID) -> uuid.UUID:
    department_id = await _create_department(db_session, organization_id)
    template_id = await _create_template(db_session)
    employee = await hire_ai_employee(
        db_session,
        organization_id=organization_id,
        department_id=department_id,
        template_id=template_id,
        name="Riley",
        role_title="Support Agent",
    )
    return employee.id


@pytest.mark.asyncio
async def test_configure_requires_dna_version_and_permission_scope(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)

    with pytest.raises(MissingConfigurationError):
        await configure_ai_employee(
            db_session,
            organization_id=organization_id,
            employee_id=employee_id,
            company_dna_version_id=None,
            permission_scope=None,
            autonomy_defaults=None,
        )


@pytest.mark.asyncio
async def test_configure_rejects_unknown_dna_version(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)

    with pytest.raises(CompanyDnaVersionNotFoundError):
        await configure_ai_employee(
            db_session,
            organization_id=organization_id,
            employee_id=employee_id,
            company_dna_version_id=uuid.uuid4(),
            permission_scope={"resource": "email", "access": "write"},
            autonomy_defaults=None,
        )


@pytest.mark.asyncio
async def test_configure_succeeds_and_emits_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)
    dna_version_id = await _create_dna_version(db_session, organization_id)

    configured = await configure_ai_employee(
        db_session,
        organization_id=organization_id,
        employee_id=employee_id,
        company_dna_version_id=dna_version_id,
        permission_scope={"resource": "email", "access": "write"},
        autonomy_defaults={"send_email": "approve"},
    )

    assert configured.status == AiEmployeeStatus.CONFIGURED
    assert configured.company_dna_version_id == dna_version_id
    assert configured.autonomy_defaults == {"send_email": "approve"}

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    configured_events = [e for e in events if e.type == "EmployeeConfigured"]
    assert len(configured_events) == 1
    assert configured_events[0].payload == {
        "ai_employee_id": str(employee_id),
        "company_dna_version_id": str(dna_version_id),
        "permission_scope": {"resource": "email", "access": "write"},
    }


@pytest.mark.asyncio
async def test_configure_rejects_already_configured_employee(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)
    dna_version_id = await _create_dna_version(db_session, organization_id)

    await configure_ai_employee(
        db_session,
        organization_id=organization_id,
        employee_id=employee_id,
        company_dna_version_id=dna_version_id,
        permission_scope={},
        autonomy_defaults=None,
    )

    with pytest.raises(InvalidAiEmployeeTransitionError):
        await configure_ai_employee(
            db_session,
            organization_id=organization_id,
            employee_id=employee_id,
            company_dna_version_id=dna_version_id,
            permission_scope={},
            autonomy_defaults=None,
        )


async def _hire_and_configure(db_session: AsyncSession, organization_id: uuid.UUID) -> uuid.UUID:
    employee_id = await _hire(db_session, organization_id)
    dna_version_id = await _create_dna_version(db_session, organization_id)
    await configure_ai_employee(
        db_session,
        organization_id=organization_id,
        employee_id=employee_id,
        company_dna_version_id=dna_version_id,
        permission_scope={},
        autonomy_defaults=None,
    )
    return employee_id


@pytest.mark.asyncio
async def test_activate_rejects_a_draft_employee(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)

    with pytest.raises(InvalidAiEmployeeTransitionError):
        await activate_ai_employee(
            db_session, organization_id=organization_id, employee_id=employee_id
        )


@pytest.mark.asyncio
async def test_activate_succeeds_from_configured_and_emits_event(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire_and_configure(db_session, organization_id)

    activated = await activate_ai_employee(
        db_session, organization_id=organization_id, employee_id=employee_id
    )

    assert activated.status == AiEmployeeStatus.ACTIVE

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    activated_events = [e for e in events if e.type == "EmployeeActivated"]
    assert len(activated_events) == 1
    assert activated_events[0].payload == {"ai_employee_id": str(employee_id)}


@pytest.mark.asyncio
async def test_pause_requires_active_status(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire_and_configure(db_session, organization_id)

    with pytest.raises(InvalidAiEmployeeTransitionError):
        await pause_ai_employee(
            db_session, organization_id=organization_id, employee_id=employee_id
        )


@pytest.mark.asyncio
async def test_pause_then_activate_reuses_employee_activated(
    db_session: AsyncSession,
) -> None:
    """StateMachines.md §2: paused -> active reuses EmployeeActivated,
    no distinct 'resumed' event exists."""
    organization_id = await _create_org(db_session)
    employee_id = await _hire_and_configure(db_session, organization_id)
    await activate_ai_employee(db_session, organization_id=organization_id, employee_id=employee_id)

    paused = await pause_ai_employee(
        db_session, organization_id=organization_id, employee_id=employee_id
    )
    assert paused.status == AiEmployeeStatus.PAUSED

    resumed = await activate_ai_employee(
        db_session, organization_id=organization_id, employee_id=employee_id
    )
    assert resumed.status == AiEmployeeStatus.ACTIVE

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    assert len([e for e in events if e.type == "EmployeeActivated"]) == 2
    assert len([e for e in events if e.type == "EmployeePaused"]) == 1
    paused_event = next(e for e in events if e.type == "EmployeePaused")
    assert paused_event.payload == {"ai_employee_id": str(employee_id), "reason": "manual"}


@pytest.mark.asyncio
async def test_retire_requires_active_or_paused_status(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire(db_session, organization_id)

    with pytest.raises(InvalidAiEmployeeTransitionError):
        await retire_ai_employee(
            db_session, organization_id=organization_id, employee_id=employee_id
        )


@pytest.mark.asyncio
async def test_retire_succeeds_from_active_and_emits_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire_and_configure(db_session, organization_id)
    await activate_ai_employee(db_session, organization_id=organization_id, employee_id=employee_id)

    retired = await retire_ai_employee(
        db_session, organization_id=organization_id, employee_id=employee_id
    )

    assert retired.status == AiEmployeeStatus.RETIRED

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    retired_events = [e for e in events if e.type == "EmployeeRetired"]
    assert len(retired_events) == 1
    assert retired_events[0].payload == {"ai_employee_id": str(employee_id)}


@pytest.mark.asyncio
async def test_retire_succeeds_from_paused(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    employee_id = await _hire_and_configure(db_session, organization_id)
    await activate_ai_employee(db_session, organization_id=organization_id, employee_id=employee_id)
    await pause_ai_employee(db_session, organization_id=organization_id, employee_id=employee_id)

    retired = await retire_ai_employee(
        db_session, organization_id=organization_id, employee_id=employee_id
    )

    assert retired.status == AiEmployeeStatus.RETIRED


@pytest.mark.asyncio
async def test_operations_on_unknown_employee_raise_not_found(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    with pytest.raises(AiEmployeeNotFoundError):
        await activate_ai_employee(
            db_session, organization_id=organization_id, employee_id=uuid.uuid4()
        )
