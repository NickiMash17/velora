"""AI Employees API endpoints.

Endpoint shapes are the M5 Checkpoint 3 decision — see the M5 Domain
Contract's API plan. `POST /v1/ai-employees` hires (org_admin/
department_manager); `PATCH .../{id}/configure`, `POST .../activate`,
`POST .../pause` (same role scope), and `POST .../retire` (org_admin
only) drive the locked `draft → configured → active ⇄ paused → retired`
state machine; `GET /v1/ai-employees` lists (cursor-paginated, filterable
by department/status); `GET /v1/ai-employee-templates` browses the global
template catalog. No autonomy-only PATCH endpoint (B1, deferred); no
skill-binding endpoint (see application/services.py's module docstring).
"""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_employees.api.errors import (
    AiEmployeeForbiddenHTTPError,
    AiEmployeeNotFoundHTTPError,
    AiEmployeeTemplateNotFoundHTTPError,
    InvalidAiEmployeeTransitionHTTPError,
    InvalidCursorHTTPError,
    MissingConfigurationHTTPError,
)
from app.modules.ai_employees.api.schemas import (
    AiEmployeeListResponse,
    AiEmployeeResponse,
    AiEmployeeTemplateListResponse,
    AiEmployeeTemplateResponse,
    ConfigureAiEmployeeRequest,
    HireAiEmployeeRequest,
)
from app.modules.ai_employees.application.services import (
    activate_ai_employee,
    configure_ai_employee,
    hire_ai_employee,
    pause_ai_employee,
    retire_ai_employee,
)
from app.modules.ai_employees.domain.entities import AiEmployee, AiEmployeeTemplate
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
from app.modules.company_dna.api.errors import CompanyDnaVersionNotFoundHTTPError
from app.modules.company_dna.domain.errors import CompanyDnaVersionNotFoundError
from app.modules.departments.api.errors import DepartmentNotFoundHTTPError
from app.modules.departments.domain.errors import DepartmentNotFoundError
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.organizations.domain.enums import MembershipRole
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["ai-employees"])

_CURSOR_FIELD_SEPARATOR = "|"


def _to_employee_response(employee: AiEmployee) -> AiEmployeeResponse:
    if employee.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in an
        # AiEmployee that was never actually saved.
        raise RuntimeError("Cannot build an AiEmployeeResponse for an unsaved AiEmployee.")
    return AiEmployeeResponse(
        id=employee.id,
        department_id=employee.department_id,
        template_id=employee.template_id,
        name=employee.name,
        role_title=employee.role_title,
        status=employee.status.value,
        company_dna_version_id=employee.company_dna_version_id,
        permission_scope=employee.permission_scope,
        autonomy_defaults=employee.autonomy_defaults,
        created_at=employee.created_at,
    )


def _to_template_response(template: AiEmployeeTemplate) -> AiEmployeeTemplateResponse:
    if template.created_at is None:
        raise RuntimeError(
            "Cannot build an AiEmployeeTemplateResponse for an unsaved AiEmployeeTemplate."
        )
    return AiEmployeeTemplateResponse(
        id=template.id,
        name=template.name,
        default_skills=template.default_skills,
        system_prompt_scaffold=template.system_prompt_scaffold,
        created_at=template.created_at,
    )


def _encode_cursor(created_at: datetime, id_: UUID) -> str:
    raw = f"{created_at.isoformat()}{_CURSOR_FIELD_SEPARATOR}{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_raw, id_raw = raw.split(_CURSOR_FIELD_SEPARATOR)
        return datetime.fromisoformat(created_at_raw), UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorHTTPError(f"'{cursor}' is not a valid pagination cursor.") from exc


def _require_org_admin_or_department_manager(context: OrganizationContext) -> None:
    """Per the M5 authorization matrix: org_admin or department_manager,
    scoped to "own department." **Not enforced here**: no department-
    ownership mechanism exists anywhere in the schema (no
    `department_managers` table, no manager field on `departments`) — see
    this checkpoint's completion report. Only role membership is checked;
    a department_manager can currently act on any department's AI
    Employees, not only their own."""
    allowed_roles = (MembershipRole.ORG_ADMIN.value, MembershipRole.DEPARTMENT_MANAGER.value)
    if context.role not in allowed_roles:
        raise AiEmployeeForbiddenHTTPError(
            "Only an org_admin or department_manager may perform this action."
        )


def _require_org_admin(context: OrganizationContext) -> None:
    if context.role != MembershipRole.ORG_ADMIN.value:
        raise AiEmployeeForbiddenHTTPError("Only an org_admin may perform this action.")


@router.post(
    "/ai-employees", response_model=AiEmployeeResponse, status_code=status.HTTP_201_CREATED
)
async def hire_ai_employee_endpoint(
    body: HireAiEmployeeRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    _require_org_admin_or_department_manager(context)

    try:
        employee = await hire_ai_employee(
            session,
            organization_id=context.organization_id,
            department_id=body.department_id,
            template_id=body.template_id,
            name=body.name,
            role_title=body.role_title,
        )
    except DepartmentNotFoundError as exc:
        raise DepartmentNotFoundHTTPError(str(exc)) from exc
    except AiEmployeeTemplateNotFoundError as exc:
        raise AiEmployeeTemplateNotFoundHTTPError(str(exc)) from exc
    return _to_employee_response(employee)


@router.patch("/ai-employees/{employee_id}/configure", response_model=AiEmployeeResponse)
async def configure_ai_employee_endpoint(
    employee_id: UUID,
    body: ConfigureAiEmployeeRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    _require_org_admin_or_department_manager(context)

    try:
        employee = await configure_ai_employee(
            session,
            organization_id=context.organization_id,
            employee_id=employee_id,
            company_dna_version_id=body.company_dna_version_id,
            permission_scope=body.permission_scope,
            autonomy_defaults=(
                {key: level.value for key, level in body.autonomy_defaults.items()}
                if body.autonomy_defaults is not None
                else None
            ),
        )
    except AiEmployeeNotFoundError as exc:
        raise AiEmployeeNotFoundHTTPError(str(exc)) from exc
    except InvalidAiEmployeeTransitionError as exc:
        raise InvalidAiEmployeeTransitionHTTPError(str(exc)) from exc
    except MissingConfigurationError as exc:
        raise MissingConfigurationHTTPError(str(exc)) from exc
    except CompanyDnaVersionNotFoundError as exc:
        raise CompanyDnaVersionNotFoundHTTPError(str(exc)) from exc
    return _to_employee_response(employee)


@router.post("/ai-employees/{employee_id}/activate", response_model=AiEmployeeResponse)
async def activate_ai_employee_endpoint(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    _require_org_admin_or_department_manager(context)

    try:
        employee = await activate_ai_employee(
            session, organization_id=context.organization_id, employee_id=employee_id
        )
    except AiEmployeeNotFoundError as exc:
        raise AiEmployeeNotFoundHTTPError(str(exc)) from exc
    except InvalidAiEmployeeTransitionError as exc:
        raise InvalidAiEmployeeTransitionHTTPError(str(exc)) from exc
    return _to_employee_response(employee)


@router.post("/ai-employees/{employee_id}/pause", response_model=AiEmployeeResponse)
async def pause_ai_employee_endpoint(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    _require_org_admin_or_department_manager(context)

    try:
        employee = await pause_ai_employee(
            session, organization_id=context.organization_id, employee_id=employee_id
        )
    except AiEmployeeNotFoundError as exc:
        raise AiEmployeeNotFoundHTTPError(str(exc)) from exc
    except InvalidAiEmployeeTransitionError as exc:
        raise InvalidAiEmployeeTransitionHTTPError(str(exc)) from exc
    return _to_employee_response(employee)


@router.post("/ai-employees/{employee_id}/retire", response_model=AiEmployeeResponse)
async def retire_ai_employee_endpoint(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    _require_org_admin(context)

    try:
        employee = await retire_ai_employee(
            session, organization_id=context.organization_id, employee_id=employee_id
        )
    except AiEmployeeNotFoundError as exc:
        raise AiEmployeeNotFoundHTTPError(str(exc)) from exc
    except InvalidAiEmployeeTransitionError as exc:
        raise InvalidAiEmployeeTransitionHTTPError(str(exc)) from exc
    return _to_employee_response(employee)


@router.get("/ai-employees", response_model=AiEmployeeListResponse)
async def list_ai_employees(
    department_id: UUID | None = Query(None),  # noqa: B008 - ruff's safe-default allowlist
    # covers str/int/etc but not UUID/enum types; Query(None) has no side effects either way
    employee_status: AiEmployeeStatus | None = Query(None, alias="status"),  # noqa: B008
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeListResponse:
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    async with tenant_scoped_transaction(session, context.organization_id):
        employees = await AiEmployeeRepository().list_for_organization(
            session,
            context.organization_id,
            department_id=department_id,
            status=employee_status,
            cursor=decoded_cursor,
            limit=limit,
        )

    next_cursor = (
        _encode_cursor(employees[-1].created_at, employees[-1].id)  # type: ignore[arg-type]
        if len(employees) == limit
        else None
    )
    return AiEmployeeListResponse(
        items=[_to_employee_response(e) for e in employees], next_cursor=next_cursor
    )


@router.get("/ai-employees/{employee_id}", response_model=AiEmployeeResponse)
async def get_ai_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeResponse:
    async with tenant_scoped_transaction(session, context.organization_id):
        employee = await AiEmployeeRepository().get_by_id(
            session, context.organization_id, employee_id
        )
    if employee is None:
        raise AiEmployeeNotFoundHTTPError(f"AI Employee '{employee_id}' was not found.")
    return _to_employee_response(employee)


@router.get("/ai-employee-templates", response_model=AiEmployeeTemplateListResponse)
async def list_ai_employee_templates(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> AiEmployeeTemplateListResponse:
    """Global catalog — no tenant scoping, matching locked decision A1;
    `context` is required only to prove the caller is authenticated and
    organization-scoped, not to filter results."""
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    templates = await AiEmployeeTemplateRepository().list_all(
        session, cursor=decoded_cursor, limit=limit
    )

    next_cursor = (
        _encode_cursor(templates[-1].created_at, templates[-1].id)  # type: ignore[arg-type]
        if len(templates) == limit
        else None
    )
    return AiEmployeeTemplateListResponse(
        items=[_to_template_response(t) for t in templates], next_cursor=next_cursor
    )
