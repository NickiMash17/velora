"""Use case: create a Department, atomically with its DepartmentCreated
event.

Read paths (list/get) have no service-layer wrapper, matching
organizations' own precedent (`OrganizationRepository.get_by_id`/
`list_for_organization` are called directly from the router inside
`tenant_scoped_transaction`, with no `application/services.py` function in
between) — a wrapper would be an abstraction with no behavior to add.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.domain.entities import Department
from app.modules.departments.domain.enums import FunctionType
from app.modules.departments.infrastructure.repository import DepartmentRepository
from app.modules.events.domain.catalog import DEPARTMENT_CREATED, topic_for
from app.modules.events.infrastructure.outbox import write_event
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "departments"


async def create_department(
    session: AsyncSession,
    *,
    organization_id: UUID,
    name: str,
    function_type: FunctionType,
    budget_cents_monthly: int | None = None,
    department_repo: DepartmentRepository | None = None,
) -> Department:
    department_repo = department_repo or DepartmentRepository()

    department = Department(
        id=uuid.uuid4(),
        organization_id=organization_id,
        name=name,
        function_type=function_type,
        budget_cents_monthly=budget_cents_monthly,
    )

    async with tenant_scoped_transaction(session, organization_id):
        department = await department_repo.create(session, department)

        await write_event(
            session,
            organization_id=organization_id,
            type=DEPARTMENT_CREATED,
            topic=topic_for(DEPARTMENT_CREATED),
            producer=_PRODUCER,
            payload={
                "department_id": str(department.id),
                "organization_id": str(organization_id),
                "function_type": function_type.value,
            },
            correlation_id=uuid.uuid4(),
        )

    return department
