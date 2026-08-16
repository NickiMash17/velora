"""Use cases: propose a Goal and activate it.

Only `proposed → active` is implemented — Finding 2 (M5 Step 3 plan,
already resolved): `at_risk`/`achieved`/`abandoned` have zero M5
endpoints, services, or events. `GoalAbandoned` is not introduced.

`success_metric`'s internal shape (`{metric, target, current}`) is
treated as an opaque JSON object throughout this module — its
directionality (higher-vs-lower-is-better) is a known, unresolved gap in
the source documentation (M5 Step 3 plan, Known Gaps) and is deliberately
not invented here.

`GoalProposed`'s cataloged payload includes `proposed_plan`
(EventCatalog.md §5.6), documented for the Goal Engine's automatic
decomposition output — which does not exist in M5 (Domain 4's own scope
note: "the Goal Engine's actual decomposition AI logic" is out of scope).
For a manually-created M5 Goal there is no real plan to attach; this
emits `proposed_plan: {}` as the M5 substitute, the same treatment
already applied to Company DNA's `CompanyDnaCompiled.compiled_summary_hash`
for a pipeline that likewise doesn't exist yet — flagged in this
checkpoint's completion report, not silently assumed.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.domain.catalog import GOAL_ACTIVATED, GOAL_PROPOSED, topic_for
from app.modules.events.infrastructure.outbox import write_event
from app.modules.goals.domain.entities import Goal
from app.modules.goals.domain.enums import GoalStatus
from app.modules.goals.domain.errors import GoalNotFoundError, InvalidGoalTransitionError
from app.modules.goals.infrastructure.repository import GoalRepository
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "goals"


async def propose_goal(
    session: AsyncSession,
    *,
    organization_id: UUID,
    title: str,
    success_metric: dict[str, Any],
    department_id: UUID | None = None,
    goal_repo: GoalRepository | None = None,
) -> Goal:
    goal_repo = goal_repo or GoalRepository()

    goal = Goal(
        id=uuid.uuid4(),
        organization_id=organization_id,
        department_id=department_id,
        title=title,
        success_metric=success_metric,
        status=GoalStatus.PROPOSED,
    )

    async with tenant_scoped_transaction(session, organization_id):
        goal = await goal_repo.create(session, goal)

        await write_event(
            session,
            organization_id=organization_id,
            type=GOAL_PROPOSED,
            topic=topic_for(GOAL_PROPOSED),
            producer=_PRODUCER,
            payload={"goal_id": str(goal.id), "proposed_plan": {}},
            correlation_id=uuid.uuid4(),
        )

    return goal


async def activate_goal(
    session: AsyncSession,
    *,
    organization_id: UUID,
    goal_id: UUID,
    goal_repo: GoalRepository | None = None,
) -> Goal:
    goal_repo = goal_repo or GoalRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await goal_repo.get_by_id(session, organization_id, goal_id)
        if existing is None:
            raise GoalNotFoundError(f"Goal '{goal_id}' was not found.")
        if existing.status != GoalStatus.PROPOSED:
            raise InvalidGoalTransitionError(
                f"Cannot activate — goal '{goal_id}' is "
                f"'{existing.status.value}', not 'proposed'."
            )

        existing.status = GoalStatus.ACTIVE
        activated = await goal_repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=GOAL_ACTIVATED,
            topic=topic_for(GOAL_ACTIVATED),
            producer=_PRODUCER,
            payload={"goal_id": str(activated.id)},
            correlation_id=uuid.uuid4(),
        )

    return activated
