"""Integration tests for the Goals application services — real, migrated
Postgres throughout. Mirrors test_department_service.py's and
test_company_dna_service.py's pattern.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.infrastructure.orm import EventORM
from app.modules.goals.application.services import activate_goal, propose_goal
from app.modules.goals.domain.enums import GoalStatus
from app.modules.goals.domain.errors import GoalNotFoundError, InvalidGoalTransitionError
from app.modules.goals.infrastructure.repository import GoalRepository
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.shared.tenancy import tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"goal-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"goal-tenant-{uuid.uuid4().hex[:10]}"


async def _create_org(db_session: AsyncSession) -> uuid.UUID:
    admin = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(db_session, admin)
    await db_session.commit()

    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=admin.id
    )
    return result.organization.id


_METRIC = {"metric": "churn_rate", "target": 0.05, "current": 0.08}


@pytest.mark.asyncio
async def test_propose_goal_persists_goal_and_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    goal = await propose_goal(
        db_session,
        organization_id=organization_id,
        title="Reduce churn by 10%",
        success_metric=_METRIC,
    )

    assert goal.status == GoalStatus.PROPOSED
    assert goal.department_id is None
    assert goal.success_metric == _METRIC

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
    proposed_events = [e for e in events if e.type == "GoalProposed"]
    assert len(proposed_events) == 1
    assert proposed_events[0].topic == "goal.proposed"
    assert proposed_events[0].producer == "goals"
    assert proposed_events[0].payload == {"goal_id": str(goal.id), "proposed_plan": {}}


@pytest.mark.asyncio
async def test_propose_goal_accepts_an_explicit_department(db_session: AsyncSession) -> None:
    from app.modules.departments.application.services import create_department
    from app.modules.departments.domain.enums import FunctionType

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
        title="Reduce escalations",
        success_metric=_METRIC,
        department_id=department.id,
    )

    assert goal.department_id == department.id


@pytest.mark.asyncio
async def test_activate_goal_succeeds_and_emits_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    goal = await propose_goal(
        db_session, organization_id=organization_id, title="Reduce churn", success_metric=_METRIC
    )

    activated = await activate_goal(db_session, organization_id=organization_id, goal_id=goal.id)

    assert activated.status == GoalStatus.ACTIVE

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
    activated_events = [e for e in events if e.type == "GoalActivated"]
    assert len(activated_events) == 1
    assert activated_events[0].payload == {"goal_id": str(goal.id)}


@pytest.mark.asyncio
async def test_activate_goal_rejects_already_active_goal(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    goal = await propose_goal(
        db_session, organization_id=organization_id, title="Reduce churn", success_metric=_METRIC
    )
    await activate_goal(db_session, organization_id=organization_id, goal_id=goal.id)

    with pytest.raises(InvalidGoalTransitionError):
        await activate_goal(db_session, organization_id=organization_id, goal_id=goal.id)


@pytest.mark.asyncio
async def test_activate_goal_rejects_unknown_goal(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)

    with pytest.raises(GoalNotFoundError):
        await activate_goal(
            db_session, organization_id=organization_id, goal_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_list_for_organization_only_returns_that_organizations_goals(
    db_session: AsyncSession,
) -> None:
    org_a = await _create_org(db_session)
    org_b = await _create_org(db_session)

    await propose_goal(
        db_session, organization_id=org_a, title="Goal A", success_metric=_METRIC
    )
    await propose_goal(
        db_session, organization_id=org_b, title="Goal B", success_metric=_METRIC
    )

    async with tenant_scoped_transaction(db_session, org_a):
        goals_a = await GoalRepository().list_for_organization(db_session, org_a)

    assert [g.title for g in goals_a] == ["Goal A"]


@pytest.mark.asyncio
async def test_list_for_organization_paginates_by_keyset_cursor(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    for title in ["Goal 1", "Goal 2", "Goal 3"]:
        await propose_goal(
            db_session, organization_id=organization_id, title=title, success_metric=_METRIC
        )

    async with tenant_scoped_transaction(db_session, organization_id):
        first_page = await GoalRepository().list_for_organization(
            db_session, organization_id, limit=2
        )
        assert [g.title for g in first_page] == ["Goal 1", "Goal 2"]

        cursor = (first_page[-1].created_at, first_page[-1].id)
        second_page = await GoalRepository().list_for_organization(
            db_session, organization_id, cursor=cursor, limit=2
        )
        assert [g.title for g in second_page] == ["Goal 3"]
