"""Integration tests for the Tasks application service — real, migrated
Postgres throughout. Mirrors test_department_service.py's,
test_company_dna_service.py's, and test_goal_service.py's pattern.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.application.services import create_department
from app.modules.departments.domain.enums import FunctionType
from app.modules.events.infrastructure.orm import EventORM
from app.modules.goals.application.services import propose_goal
from app.modules.goals.domain.errors import GoalNotFoundError
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.modules.tasks.application.services import create_task
from app.modules.tasks.domain.enums import TaskStatus
from app.modules.tasks.domain.errors import AssignedUserNotFoundError, TaskIdempotencyConflictError
from app.modules.tasks.infrastructure.repository import TaskRepository
from app.shared.tenancy import tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"task-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"task-tenant-{uuid.uuid4().hex[:10]}"


async def _create_org(db_session: AsyncSession) -> uuid.UUID:
    admin = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(db_session, admin)
    await db_session.commit()

    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=admin.id
    )
    return result.organization.id


@pytest.mark.asyncio
async def test_create_task_persists_task_and_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    task = await create_task(
        db_session, organization_id=organization_id, idempotency_key="idem-1"
    )

    assert task.status == TaskStatus.PENDING
    assert task.goal_id is None
    assert task.assigned_user_id is None
    assert task.assigned_ai_employee_id is None
    assert task.blocked_reason is None
    assert task.retry_count == 0

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
    assigned_events = [e for e in events if e.type == "TaskAssigned"]
    assert len(assigned_events) == 1
    assert assigned_events[0].topic == "task.assigned"
    assert assigned_events[0].producer == "tasks"
    assert assigned_events[0].payload == {"task_id": str(task.id), "department_id": None}


@pytest.mark.asyncio
async def test_create_task_with_a_goal_derives_department_id_for_the_event(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    department = await create_department(
        db_session,
        organization_id=organization_id,
        name="Support",
        function_type=FunctionType.SUPPORT,
    )
    goal = await propose_goal(
        db_session,
        organization_id=organization_id,
        title="Reduce churn",
        success_metric={"metric": "churn_rate", "target": 0.05, "current": 0.08},
        department_id=department.id,
    )

    task = await create_task(
        db_session, organization_id=organization_id, idempotency_key="idem-2", goal_id=goal.id
    )

    assert task.goal_id == goal.id

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
    assigned_event = next(e for e in events if e.type == "TaskAssigned")
    assert assigned_event.payload == {
        "task_id": str(task.id),
        "department_id": str(department.id),
    }


@pytest.mark.asyncio
async def test_create_task_rejects_unknown_goal(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    with pytest.raises(GoalNotFoundError):
        await create_task(
            db_session,
            organization_id=organization_id,
            idempotency_key="idem-3",
            goal_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_task_accepts_an_assigned_user(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    assignee = User(
        id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False
    )
    await UserRepository().create(db_session, assignee)
    await db_session.commit()

    task = await create_task(
        db_session,
        organization_id=organization_id,
        idempotency_key="idem-4",
        assigned_user_id=assignee.id,
    )

    assert task.assigned_user_id == assignee.id


@pytest.mark.asyncio
async def test_create_task_rejects_unknown_assigned_user(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    with pytest.raises(AssignedUserNotFoundError):
        await create_task(
            db_session,
            organization_id=organization_id,
            idempotency_key="idem-5",
            assigned_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_task_rejects_a_repeated_idempotency_key(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    first = await create_task(
        db_session, organization_id=organization_id, idempotency_key="idem-6"
    )

    with pytest.raises(TaskIdempotencyConflictError) as exc_info:
        await create_task(
            db_session, organization_id=organization_id, idempotency_key="idem-6"
        )

    assert exc_info.value.existing_task_id == first.id


@pytest.mark.asyncio
async def test_same_idempotency_key_is_allowed_across_different_organizations(
    db_session: AsyncSession,
) -> None:
    org_a = await _create_org(db_session)
    org_b = await _create_org(db_session)

    task_a = await create_task(db_session, organization_id=org_a, idempotency_key="shared-key")
    task_b = await create_task(db_session, organization_id=org_b, idempotency_key="shared-key")

    assert task_a.id != task_b.id


@pytest.mark.asyncio
async def test_list_for_organization_only_returns_that_organizations_tasks(
    db_session: AsyncSession,
) -> None:
    org_a = await _create_org(db_session)
    org_b = await _create_org(db_session)

    task_a = await create_task(db_session, organization_id=org_a, idempotency_key="a-1")
    await create_task(db_session, organization_id=org_b, idempotency_key="b-1")

    async with tenant_scoped_transaction(db_session, org_a):
        tasks_a = await TaskRepository().list_for_organization(db_session, org_a)

    assert [t.id for t in tasks_a] == [task_a.id]


@pytest.mark.asyncio
async def test_list_for_organization_filters_by_goal_and_assigned_user(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    goal = await propose_goal(
        db_session,
        organization_id=organization_id,
        title="Reduce churn",
        success_metric={"metric": "churn_rate", "target": 0.05, "current": 0.08},
    )
    assignee = User(
        id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False
    )
    await UserRepository().create(db_session, assignee)
    await db_session.commit()

    task_with_goal = await create_task(
        db_session, organization_id=organization_id, idempotency_key="filter-1", goal_id=goal.id
    )
    task_with_user = await create_task(
        db_session,
        organization_id=organization_id,
        idempotency_key="filter-2",
        assigned_user_id=assignee.id,
    )
    await create_task(db_session, organization_id=organization_id, idempotency_key="filter-3")

    async with tenant_scoped_transaction(db_session, organization_id):
        by_goal = await TaskRepository().list_for_organization(
            db_session, organization_id, goal_id=goal.id
        )
        by_user = await TaskRepository().list_for_organization(
            db_session, organization_id, assigned_user_id=assignee.id
        )

    assert [t.id for t in by_goal] == [task_with_goal.id]
    assert [t.id for t in by_user] == [task_with_user.id]


@pytest.mark.asyncio
async def test_list_for_organization_paginates_by_keyset_cursor(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    for key in ["p-1", "p-2", "p-3"]:
        await create_task(db_session, organization_id=organization_id, idempotency_key=key)

    async with tenant_scoped_transaction(db_session, organization_id):
        first_page = await TaskRepository().list_for_organization(
            db_session, organization_id, limit=2
        )
        assert [t.idempotency_key for t in first_page] == ["p-1", "p-2"]

        cursor = (first_page[-1].created_at, first_page[-1].id)
        second_page = await TaskRepository().list_for_organization(
            db_session, organization_id, cursor=cursor, limit=2
        )
        assert [t.idempotency_key for t in second_page] == ["p-3"]
