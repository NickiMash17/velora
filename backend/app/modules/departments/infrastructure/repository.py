"""Repository layer for departments.

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

from app.modules.departments.domain.entities import Department
from app.modules.departments.infrastructure.orm import DepartmentORM


def _to_domain(row: DepartmentORM) -> Department:
    return Department(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        function_type=row.function_type,
        budget_cents_monthly=row.budget_cents_monthly,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class DepartmentRepository:
    async def create(self, session: AsyncSession, department: Department) -> Department:
        """Returns the persisted Department with server-generated fields
        (created_at, updated_at) populated — same fix/reason as
        OrganizationRepository.create()'s own docstring: flush() triggers
        an INSERT with RETURNING that populates the ORM instance, but the
        caller's domain object never sees those fields unless read back
        explicitly."""
        row = DepartmentORM(
            id=department.id,
            organization_id=department.organization_id,
            name=department.name,
            function_type=department.function_type,
            budget_cents_monthly=department.budget_cents_monthly,
        )
        session.add(row)
        await session.flush()
        return _to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, organization_id: UUID, department_id: UUID
    ) -> Department | None:
        result = await session.execute(
            select(DepartmentORM).where(
                DepartmentORM.organization_id == organization_id,
                DepartmentORM.id == department_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[Department]:
        """Keyset-paginated on `(created_at, id)` — the first real use of
        docs/architecture/API.md §6's documented cursor-pagination
        convention in this codebase, so there is no prior implementation
        to copy; ordering by `(created_at, id)` rather than raw `id`
        (a `uuid4`, unordered) is what makes the cursor stable and the
        page order match creation order."""
        query = select(DepartmentORM).where(DepartmentORM.organization_id == organization_id)
        if cursor is not None:
            query = query.where(
                tuple_(DepartmentORM.created_at, DepartmentORM.id) > cursor
            )
        query = query.order_by(DepartmentORM.created_at, DepartmentORM.id).limit(limit)
        result = await session.execute(query)
        return [_to_domain(row) for row in result.scalars().all()]
