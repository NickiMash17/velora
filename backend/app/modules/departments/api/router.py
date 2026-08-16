"""Departments API endpoints.

Endpoint shapes are the M5 Checkpoint 1 decision — see the M5 Domain
Contract's API plan. `POST /v1/departments` creates a department (org_admin
only); `GET /v1/departments` lists departments in the caller's current
organization, cursor-paginated per docs/architecture/API.md §6 — the first
real implementation of that convention in this codebase; `GET
/v1/departments/{id}` fetches one. Update/archive/status are explicitly
out of scope for M5 (locked decision C1) and are not implemented here.
"""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.departments.api.errors import (
    DepartmentForbiddenHTTPError,
    DepartmentNotFoundHTTPError,
    InvalidCursorHTTPError,
)
from app.modules.departments.api.schemas import (
    CreateDepartmentRequest,
    DepartmentListResponse,
    DepartmentResponse,
)
from app.modules.departments.application.services import create_department
from app.modules.departments.domain.entities import Department
from app.modules.departments.infrastructure.repository import DepartmentRepository
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.organizations.domain.enums import MembershipRole
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["departments"])

_CURSOR_FIELD_SEPARATOR = "|"


def _to_department_response(department: Department) -> DepartmentResponse:
    if department.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in a
        # Department that was never actually saved.
        raise RuntimeError("Cannot build a DepartmentResponse for an unsaved Department.")
    return DepartmentResponse(
        id=department.id,
        name=department.name,
        function_type=department.function_type.value,
        budget_cents_monthly=department.budget_cents_monthly,
        created_at=department.created_at,
    )


def _encode_cursor(department: Department) -> str:
    assert department.created_at is not None  # always true for a persisted row
    raw = f"{department.created_at.isoformat()}{_CURSOR_FIELD_SEPARATOR}{department.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_raw, id_raw = raw.split(_CURSOR_FIELD_SEPARATOR)
        return datetime.fromisoformat(created_at_raw), UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorHTTPError(f"'{cursor}' is not a valid pagination cursor.") from exc


@router.post(
    "/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_department_endpoint(
    body: CreateDepartmentRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> DepartmentResponse:
    if context.role != MembershipRole.ORG_ADMIN.value:
        raise DepartmentForbiddenHTTPError("Only an org_admin may create a department.")

    department = await create_department(
        session,
        organization_id=context.organization_id,
        name=body.name,
        function_type=body.function_type,
        budget_cents_monthly=body.budget_cents_monthly,
    )
    return _to_department_response(department)


@router.get("/departments", response_model=DepartmentListResponse)
async def list_departments(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> DepartmentListResponse:
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    async with tenant_scoped_transaction(session, context.organization_id):
        departments = await DepartmentRepository().list_for_organization(
            session, context.organization_id, cursor=decoded_cursor, limit=limit
        )

    next_cursor = _encode_cursor(departments[-1]) if len(departments) == limit else None
    return DepartmentListResponse(
        items=[_to_department_response(d) for d in departments], next_cursor=next_cursor
    )


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> DepartmentResponse:
    async with tenant_scoped_transaction(session, context.organization_id):
        department = await DepartmentRepository().get_by_id(
            session, context.organization_id, department_id
        )
    if department is None:
        raise DepartmentNotFoundHTTPError(f"Department '{department_id}' was not found.")
    return _to_department_response(department)
