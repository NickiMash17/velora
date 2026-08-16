"""Goals API endpoints.

Endpoint shapes are the M5 Checkpoint 4 decision — see the M5 Domain
Contract's API plan. `POST /v1/goals` proposes a Goal (org_admin/
department_manager); `POST /v1/goals/{id}/activate` drives the locked
`proposed → active` transition (the only one implemented — Finding 2);
`GET /v1/goals` lists (cursor-paginated, filterable by department); `GET
/v1/goals/{id}` fetches one. No abandon/at-risk/achieve endpoints.
"""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals.api.errors import (
    GoalForbiddenHTTPError,
    GoalNotFoundHTTPError,
    InvalidCursorHTTPError,
    InvalidGoalTransitionHTTPError,
)
from app.modules.goals.api.schemas import CreateGoalRequest, GoalListResponse, GoalResponse
from app.modules.goals.application.services import activate_goal, propose_goal
from app.modules.goals.domain.entities import Goal
from app.modules.goals.domain.errors import GoalNotFoundError, InvalidGoalTransitionError
from app.modules.goals.infrastructure.repository import GoalRepository
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.organizations.domain.enums import MembershipRole
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["goals"])

_CURSOR_FIELD_SEPARATOR = "|"


def _to_goal_response(goal: Goal) -> GoalResponse:
    if goal.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in a Goal
        # that was never actually saved.
        raise RuntimeError("Cannot build a GoalResponse for an unsaved Goal.")
    return GoalResponse(
        id=goal.id,
        department_id=goal.department_id,
        title=goal.title,
        success_metric=goal.success_metric,
        status=goal.status.value,
        created_at=goal.created_at,
    )


def _encode_cursor(goal: Goal) -> str:
    assert goal.created_at is not None  # always true for a persisted row
    raw = f"{goal.created_at.isoformat()}{_CURSOR_FIELD_SEPARATOR}{goal.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_raw, id_raw = raw.split(_CURSOR_FIELD_SEPARATOR)
        return datetime.fromisoformat(created_at_raw), UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorHTTPError(f"'{cursor}' is not a valid pagination cursor.") from exc


def _require_org_admin_or_department_manager(context: OrganizationContext) -> None:
    """Per the M5 authorization matrix: org_admin or department_manager.
    **Not enforced here**: "own department" scoping, same limitation
    already documented in ai_employees/api/router.py — no department-
    ownership mechanism exists anywhere in the schema."""
    allowed_roles = (MembershipRole.ORG_ADMIN.value, MembershipRole.DEPARTMENT_MANAGER.value)
    if context.role not in allowed_roles:
        raise GoalForbiddenHTTPError(
            "Only an org_admin or department_manager may perform this action."
        )


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def propose_goal_endpoint(
    body: CreateGoalRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> GoalResponse:
    _require_org_admin_or_department_manager(context)

    goal = await propose_goal(
        session,
        organization_id=context.organization_id,
        title=body.title,
        success_metric=body.success_metric,
        department_id=body.department_id,
    )
    return _to_goal_response(goal)


@router.post("/goals/{goal_id}/activate", response_model=GoalResponse)
async def activate_goal_endpoint(
    goal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> GoalResponse:
    _require_org_admin_or_department_manager(context)

    try:
        goal = await activate_goal(
            session, organization_id=context.organization_id, goal_id=goal_id
        )
    except GoalNotFoundError as exc:
        raise GoalNotFoundHTTPError(str(exc)) from exc
    except InvalidGoalTransitionError as exc:
        raise InvalidGoalTransitionHTTPError(str(exc)) from exc
    return _to_goal_response(goal)


@router.get("/goals", response_model=GoalListResponse)
async def list_goals(
    department_id: UUID | None = Query(None),  # noqa: B008 - ruff's safe-default allowlist
    # covers str/int/etc but not UUID; Query(None) has no side effects either way
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> GoalListResponse:
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    async with tenant_scoped_transaction(session, context.organization_id):
        goals = await GoalRepository().list_for_organization(
            session,
            context.organization_id,
            department_id=department_id,
            cursor=decoded_cursor,
            limit=limit,
        )

    next_cursor = _encode_cursor(goals[-1]) if len(goals) == limit else None
    return GoalListResponse(
        items=[_to_goal_response(g) for g in goals], next_cursor=next_cursor
    )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> GoalResponse:
    async with tenant_scoped_transaction(session, context.organization_id):
        goal = await GoalRepository().get_by_id(session, context.organization_id, goal_id)
    if goal is None:
        raise GoalNotFoundHTTPError(f"Goal '{goal_id}' was not found.")
    return _to_goal_response(goal)
