"""Repository layer for goals.

Every method takes `organization_id` explicitly, per
docs/architecture/Database.md §2.2 ("no unscoped query method exposed on
tenant-scoped repositories") — though the actual, load-bearing enforcement
is Row-Level Security (see app/shared/tenancy.py); this is defense-in-depth
and call-site clarity, not the guarantee itself.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals.domain.entities import Goal
from app.modules.goals.infrastructure.orm import GoalORM


def _to_domain(row: GoalORM) -> Goal:
    return Goal(
        id=row.id,
        organization_id=row.organization_id,
        department_id=row.department_id,
        title=row.title,
        success_metric=dict(row.success_metric),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class GoalRepository:
    async def create(self, session: AsyncSession, goal: Goal) -> Goal:
        """Returns the persisted Goal with server-generated fields
        (created_at, updated_at) populated — same fix/reason as
        OrganizationRepository.create()'s own docstring."""
        row = GoalORM(
            id=goal.id,
            organization_id=goal.organization_id,
            department_id=goal.department_id,
            title=goal.title,
            success_metric=goal.success_metric,
            status=goal.status,
        )
        session.add(row)
        await session.flush()
        return _to_domain(row)

    async def save(self, session: AsyncSession, goal: Goal) -> Goal:
        """Persists mutations to an already-persisted row (`goal.id` must
        already exist — callers always fetch via `get_by_id` first).

        `flush()` alone does not populate `updated_at` client-side for an
        UPDATE (its `onupdate=func.now()` value stays server-side) —
        `refresh()` makes the re-fetch explicit and awaited, avoiding the
        `MissingGreenlet` failure discovered and fixed in Checkpoint 2's
        `CompanyDnaVersionRepository.save()`."""
        row = await session.get(GoalORM, goal.id)
        assert row is not None
        row.department_id = goal.department_id
        row.title = goal.title
        row.success_metric = goal.success_metric
        row.status = goal.status
        await session.flush()
        await session.refresh(row)
        return _to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, organization_id: UUID, goal_id: UUID
    ) -> Goal | None:
        result = await session.execute(
            select(GoalORM).where(
                GoalORM.organization_id == organization_id, GoalORM.id == goal_id
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        department_id: UUID | None = None,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[Goal]:
        """Keyset-paginated on `(created_at, id)` — same convention
        established in departments/company_dna/ai_employees."""
        query = select(GoalORM).where(GoalORM.organization_id == organization_id)
        if department_id is not None:
            query = query.where(GoalORM.department_id == department_id)
        if cursor is not None:
            query = query.where(tuple_(GoalORM.created_at, GoalORM.id) > cursor)
        query = query.order_by(GoalORM.created_at, GoalORM.id).limit(limit)
        result = await session.execute(query)
        return [_to_domain(row) for row in result.scalars().all()]
