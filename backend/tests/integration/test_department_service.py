"""Integration tests for create_department — the atomic department +
outbox-event use case — against a real, migrated Postgres. Mirrors
test_organization_service.py's pattern for create_organization_with_admin.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.application.services import create_department
from app.modules.departments.domain.enums import FunctionType
from app.modules.departments.infrastructure.repository import DepartmentRepository
from app.modules.events.infrastructure.orm import EventORM
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.shared.tenancy import tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"dept-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"dept-tenant-{uuid.uuid4().hex[:10]}"


async def _create_org(db_session: AsyncSession) -> uuid.UUID:
    admin = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(db_session, admin)
    await db_session.commit()

    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=admin.id
    )
    return result.organization.id


@pytest.mark.asyncio
async def test_create_department_persists_department_and_event(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)

    department = await create_department(
        db_session,
        organization_id=organization_id,
        name="Support",
        function_type=FunctionType.SUPPORT,
        budget_cents_monthly=250_000,
    )

    assert department.name == "Support"
    assert department.function_type == FunctionType.SUPPORT
    assert department.budget_cents_monthly == 250_000
    assert department.created_at is not None

    async with tenant_scoped_transaction(db_session, organization_id):
        fetched = await DepartmentRepository().get_by_id(
            db_session, organization_id, department.id
        )
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )

    assert fetched is not None
    assert fetched.id == department.id

    department_events = [e for e in events if e.type == "DepartmentCreated"]
    assert len(department_events) == 1
    event = department_events[0]
    assert event.topic == "department.created"
    assert event.producer == "departments"
    assert event.payload == {
        "department_id": str(department.id),
        "organization_id": str(organization_id),
        "function_type": "support",
    }


@pytest.mark.asyncio
async def test_create_department_defaults_budget_to_none(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    department = await create_department(
        db_session,
        organization_id=organization_id,
        name="Sales",
        function_type=FunctionType.SALES,
    )

    assert department.budget_cents_monthly is None


@pytest.mark.asyncio
async def test_list_for_organization_only_returns_that_organizations_departments(
    db_session: AsyncSession,
) -> None:
    org_a = await _create_org(db_session)
    org_b = await _create_org(db_session)

    await create_department(
        db_session, organization_id=org_a, name="Sales A", function_type=FunctionType.SALES
    )
    await create_department(
        db_session, organization_id=org_b, name="Sales B", function_type=FunctionType.SALES
    )

    async with tenant_scoped_transaction(db_session, org_a):
        departments_a = await DepartmentRepository().list_for_organization(db_session, org_a)

    assert [d.name for d in departments_a] == ["Sales A"]


@pytest.mark.asyncio
async def test_list_for_organization_paginates_by_keyset_cursor(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    for name in ["Ops", "Finance", "Marketing"]:
        await create_department(
            db_session,
            organization_id=organization_id,
            name=name,
            function_type=FunctionType.OPS,
        )

    async with tenant_scoped_transaction(db_session, organization_id):
        first_page = await DepartmentRepository().list_for_organization(
            db_session, organization_id, limit=2
        )
        assert [d.name for d in first_page] == ["Ops", "Finance"]

        cursor = (first_page[-1].created_at, first_page[-1].id)
        second_page = await DepartmentRepository().list_for_organization(
            db_session, organization_id, cursor=cursor, limit=2
        )
        assert [d.name for d in second_page] == ["Marketing"]
