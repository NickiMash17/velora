"""Repository layer for tasks.

Every method takes `organization_id` explicitly, per
docs/architecture/Database.md §2.2 ("no unscoped query method exposed on
tenant-scoped repositories") — though the actual, load-bearing enforcement
is Row-Level Security (see app/shared/tenancy.py); this is defense-in-depth
and call-site clarity, not the guarantee itself.

Only `create`, `get_by_id`, `get_by_idempotency_key`, and
`list_for_organization` exist — no `save()`/update method, since no M5
endpoint ever mutates a Task after creation (Finding 3's cascade: nothing
progresses a Task past `pending`).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.domain.entities import Task
from app.modules.tasks.infrastructure.orm import TaskORM


def _to_domain(row: TaskORM) -> Task:
    return Task(
        id=row.id,
        organization_id=row.organization_id,
        goal_id=row.goal_id,
        assigned_ai_employee_id=row.assigned_ai_employee_id,
        assigned_user_id=row.assigned_user_id,
        status=row.status,
        blocked_reason=row.blocked_reason,
        idempotency_key=row.idempotency_key,
        retry_count=row.retry_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class TaskRepository:
    async def create(self, session: AsyncSession, task: Task) -> Task:
        """Returns the persisted Task with server-generated fields
        (created_at, updated_at) populated — same fix/reason as
        OrganizationRepository.create()'s own docstring."""
        row = TaskORM(
            id=task.id,
            organization_id=task.organization_id,
            goal_id=task.goal_id,
            assigned_ai_employee_id=task.assigned_ai_employee_id,
            assigned_user_id=task.assigned_user_id,
            status=task.status,
            blocked_reason=task.blocked_reason,
            idempotency_key=task.idempotency_key,
            retry_count=task.retry_count,
        )
        session.add(row)
        await session.flush()
        return _to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, organization_id: UUID, task_id: UUID
    ) -> Task | None:
        result = await session.execute(
            select(TaskORM).where(
                TaskORM.organization_id == organization_id, TaskORM.id == task_id
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_by_idempotency_key(
        self, session: AsyncSession, organization_id: UUID, idempotency_key: str
    ) -> Task | None:
        result = await session.execute(
            select(TaskORM).where(
                TaskORM.organization_id == organization_id,
                TaskORM.idempotency_key == idempotency_key,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        goal_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[Task]:
        """Keyset-paginated on `(created_at, id)` — same convention
        established in departments/company_dna/ai_employees/goals."""
        query = select(TaskORM).where(TaskORM.organization_id == organization_id)
        if goal_id is not None:
            query = query.where(TaskORM.goal_id == goal_id)
        if assigned_user_id is not None:
            query = query.where(TaskORM.assigned_user_id == assigned_user_id)
        if cursor is not None:
            query = query.where(tuple_(TaskORM.created_at, TaskORM.id) > cursor)
        query = query.order_by(TaskORM.created_at, TaskORM.id).limit(limit)
        result = await session.execute(query)
        return [_to_domain(row) for row in result.scalars().all()]
