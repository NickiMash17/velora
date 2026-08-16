"""Use cases: hire, configure, activate, pause, and retire an AI Employee.

No skill-binding path exists in this checkpoint. AIEmployees.md §4 step 2
implies the Provisioning Service "binds the template's default skill set"
at hire time, but the M5 Step 3 implementation plan's locked API surface
never actualized this into a concrete mechanism — no request field takes
skill ids anywhere, and no dedicated endpoint exists. Rather than invent
that mechanism now, `ai_employee_skills` ships as a fully correct,
RLS-verified table with no application code writing to it yet — see this
checkpoint's completion report for the full discrepancy writeup. Adding
the binding step is future work once decided, not a gap invented around
here.

No AI/LLM runtime, no Policy Engine, no Skill Runtime — every transition
below is a plain state change plus an already-cataloged event, matching
`StateMachines.md §2` exactly.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_employees.domain.entities import AiEmployee
from app.modules.ai_employees.domain.enums import AiEmployeeStatus
from app.modules.ai_employees.domain.errors import (
    AiEmployeeNotFoundError,
    AiEmployeeTemplateNotFoundError,
    InvalidAiEmployeeTransitionError,
    MissingConfigurationError,
)
from app.modules.ai_employees.infrastructure.repository import (
    AiEmployeeRepository,
    AiEmployeeTemplateRepository,
)
from app.modules.company_dna.domain.errors import CompanyDnaVersionNotFoundError
from app.modules.company_dna.infrastructure.repository import CompanyDnaVersionRepository
from app.modules.departments.domain.errors import DepartmentNotFoundError
from app.modules.departments.infrastructure.repository import DepartmentRepository
from app.modules.events.domain.catalog import (
    EMPLOYEE_ACTIVATED,
    EMPLOYEE_CONFIGURED,
    EMPLOYEE_HIRED,
    EMPLOYEE_PAUSED,
    EMPLOYEE_RETIRED,
    topic_for,
)
from app.modules.events.infrastructure.outbox import write_event
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "ai_employees"


async def hire_ai_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    department_id: UUID,
    template_id: UUID,
    name: str,
    role_title: str,
    department_repo: DepartmentRepository | None = None,
    template_repo: AiEmployeeTemplateRepository | None = None,
    employee_repo: AiEmployeeRepository | None = None,
) -> AiEmployee:
    department_repo = department_repo or DepartmentRepository()
    template_repo = template_repo or AiEmployeeTemplateRepository()
    employee_repo = employee_repo or AiEmployeeRepository()

    async with tenant_scoped_transaction(session, organization_id):
        department = await department_repo.get_by_id(session, organization_id, department_id)
        if department is None:
            raise DepartmentNotFoundError(f"Department '{department_id}' was not found.")

        template = await template_repo.get_by_id(session, template_id)
        if template is None:
            raise AiEmployeeTemplateNotFoundError(
                f"AI Employee template '{template_id}' was not found."
            )

        employee = AiEmployee(
            id=uuid.uuid4(),
            organization_id=organization_id,
            department_id=department_id,
            template_id=template_id,
            name=name,
            role_title=role_title,
            status=AiEmployeeStatus.DRAFT,
        )
        employee = await employee_repo.create(session, employee)

        await write_event(
            session,
            organization_id=organization_id,
            type=EMPLOYEE_HIRED,
            topic=topic_for(EMPLOYEE_HIRED),
            producer=_PRODUCER,
            payload={
                "ai_employee_id": str(employee.id),
                "department_id": str(department_id),
                "template_id": str(template_id),
            },
            correlation_id=uuid.uuid4(),
        )

    return employee


async def configure_ai_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    employee_id: UUID,
    company_dna_version_id: UUID | None,
    permission_scope: dict[str, Any] | None,
    autonomy_defaults: dict[str, str] | None,
    employee_repo: AiEmployeeRepository | None = None,
    dna_repo: CompanyDnaVersionRepository | None = None,
) -> AiEmployee:
    employee_repo = employee_repo or AiEmployeeRepository()
    dna_repo = dna_repo or CompanyDnaVersionRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await employee_repo.get_by_id(session, organization_id, employee_id)
        if existing is None:
            raise AiEmployeeNotFoundError(f"AI Employee '{employee_id}' was not found.")
        if existing.status != AiEmployeeStatus.DRAFT:
            raise InvalidAiEmployeeTransitionError(
                f"Cannot configure — employee '{employee_id}' is "
                f"'{existing.status.value}', not 'draft'."
            )
        if company_dna_version_id is None or permission_scope is None:
            raise MissingConfigurationError(
                "A Company DNA version and a permission scope are both "
                "required to configure an AI Employee (AIEmployees.md §3)."
            )

        dna_version = await dna_repo.get_by_id(session, organization_id, company_dna_version_id)
        if dna_version is None:
            raise CompanyDnaVersionNotFoundError(
                f"Company DNA version '{company_dna_version_id}' was not found."
            )

        existing.company_dna_version_id = company_dna_version_id
        existing.permission_scope = permission_scope
        existing.autonomy_defaults = autonomy_defaults or {}
        existing.status = AiEmployeeStatus.CONFIGURED
        configured = await employee_repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=EMPLOYEE_CONFIGURED,
            topic=topic_for(EMPLOYEE_CONFIGURED),
            producer=_PRODUCER,
            payload={
                "ai_employee_id": str(configured.id),
                "company_dna_version_id": str(company_dna_version_id),
                "permission_scope": permission_scope,
            },
            correlation_id=uuid.uuid4(),
        )

    return configured


async def activate_ai_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    employee_id: UUID,
    employee_repo: AiEmployeeRepository | None = None,
) -> AiEmployee:
    """Handles both `configured → active` and `paused → active` — both
    reuse `EmployeeActivated`; `StateMachines.md §2` documents no distinct
    "resumed" event."""
    employee_repo = employee_repo or AiEmployeeRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await employee_repo.get_by_id(session, organization_id, employee_id)
        if existing is None:
            raise AiEmployeeNotFoundError(f"AI Employee '{employee_id}' was not found.")
        if existing.status not in (AiEmployeeStatus.CONFIGURED, AiEmployeeStatus.PAUSED):
            raise InvalidAiEmployeeTransitionError(
                f"Cannot activate — employee '{employee_id}' is "
                f"'{existing.status.value}', not 'configured' or 'paused'."
            )

        existing.status = AiEmployeeStatus.ACTIVE
        activated = await employee_repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=EMPLOYEE_ACTIVATED,
            topic=topic_for(EMPLOYEE_ACTIVATED),
            producer=_PRODUCER,
            payload={"ai_employee_id": str(activated.id)},
            correlation_id=uuid.uuid4(),
        )

    return activated


async def pause_ai_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    employee_id: UUID,
    employee_repo: AiEmployeeRepository | None = None,
) -> AiEmployee:
    """Manual pause only — M5 has no Policy Engine, so automatic pausing
    (policy violation, budget exhaustion) is out of scope; `reason` is
    always `"manual"` in this checkpoint."""
    employee_repo = employee_repo or AiEmployeeRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await employee_repo.get_by_id(session, organization_id, employee_id)
        if existing is None:
            raise AiEmployeeNotFoundError(f"AI Employee '{employee_id}' was not found.")
        if existing.status != AiEmployeeStatus.ACTIVE:
            raise InvalidAiEmployeeTransitionError(
                f"Cannot pause — employee '{employee_id}' is "
                f"'{existing.status.value}', not 'active'."
            )

        existing.status = AiEmployeeStatus.PAUSED
        paused = await employee_repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=EMPLOYEE_PAUSED,
            topic=topic_for(EMPLOYEE_PAUSED),
            producer=_PRODUCER,
            payload={"ai_employee_id": str(paused.id), "reason": "manual"},
            correlation_id=uuid.uuid4(),
        )

    return paused


async def retire_ai_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    employee_id: UUID,
    employee_repo: AiEmployeeRepository | None = None,
) -> AiEmployee:
    employee_repo = employee_repo or AiEmployeeRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await employee_repo.get_by_id(session, organization_id, employee_id)
        if existing is None:
            raise AiEmployeeNotFoundError(f"AI Employee '{employee_id}' was not found.")
        if existing.status not in (AiEmployeeStatus.ACTIVE, AiEmployeeStatus.PAUSED):
            raise InvalidAiEmployeeTransitionError(
                f"Cannot retire — employee '{employee_id}' is "
                f"'{existing.status.value}', not 'active' or 'paused'."
            )

        existing.status = AiEmployeeStatus.RETIRED
        retired = await employee_repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=EMPLOYEE_RETIRED,
            topic=topic_for(EMPLOYEE_RETIRED),
            producer=_PRODUCER,
            payload={"ai_employee_id": str(retired.id)},
            correlation_id=uuid.uuid4(),
        )

    return retired
