"""Use case: create a Task.

This is the only mutation in the Tasks module in M5 — `/claim`, `/block`,
`/complete`, `/fail`, `/approve`, `/reject` are all deferred (Finding 3's
cascade, M5 Step 3 plan §0.1: none of them has a legitimate M5 entry path
since they transitively depend on machine identity, which doesn't exist).
A Task created here can only ever be observed in `pending`.

`TaskAssigned`'s cataloged payload is `task_id`, `department_id`
(EventCatalog.md §5.6) — but `tasks` has no `department_id` column of its
own (Database.md §3.5); a Task's only path to a department is transitively
through an optional `goal_id`. This derives `department_id` from the
referenced Goal's `department_id` when `goal_id` is provided, and emits
`null` when it isn't (an ad hoc task, or a goal-less task) — a real lookup
of already-linked data, not fabricated content, but flagged here since no
document specifies this derivation explicitly.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.domain.catalog import TASK_ASSIGNED, topic_for
from app.modules.events.infrastructure.outbox import write_event
from app.modules.goals.domain.errors import GoalNotFoundError
from app.modules.goals.infrastructure.repository import GoalRepository
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.tasks.domain.entities import Task
from app.modules.tasks.domain.enums import TaskStatus
from app.modules.tasks.domain.errors import AssignedUserNotFoundError, TaskIdempotencyConflictError
from app.modules.tasks.infrastructure.repository import TaskRepository
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "tasks"


async def create_task(
    session: AsyncSession,
    *,
    organization_id: UUID,
    idempotency_key: str,
    goal_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    task_repo: TaskRepository | None = None,
    goal_repo: GoalRepository | None = None,
    user_repo: UserRepository | None = None,
) -> Task:
    task_repo = task_repo or TaskRepository()
    goal_repo = goal_repo or GoalRepository()
    user_repo = user_repo or UserRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await task_repo.get_by_idempotency_key(
            session, organization_id, idempotency_key
        )
        if existing is not None:
            raise TaskIdempotencyConflictError(existing.id)

        department_id: UUID | None = None
        if goal_id is not None:
            goal = await goal_repo.get_by_id(session, organization_id, goal_id)
            if goal is None:
                raise GoalNotFoundError(f"Goal '{goal_id}' was not found.")
            department_id = goal.department_id

        if assigned_user_id is not None:
            user = await user_repo.get_by_id(session, assigned_user_id)
            if user is None:
                raise AssignedUserNotFoundError(
                    f"User '{assigned_user_id}' was not found."
                )

        task = Task(
            id=uuid.uuid4(),
            organization_id=organization_id,
            goal_id=goal_id,
            assigned_user_id=assigned_user_id,
            status=TaskStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        task = await task_repo.create(session, task)

        await write_event(
            session,
            organization_id=organization_id,
            type=TASK_ASSIGNED,
            topic=topic_for(TASK_ASSIGNED),
            producer=_PRODUCER,
            payload={
                "task_id": str(task.id),
                "department_id": str(department_id) if department_id else None,
            },
            correlation_id=uuid.uuid4(),
        )

    return task
