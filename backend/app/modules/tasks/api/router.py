"""Tasks (work-items) API endpoints.

Endpoint shapes are the M5 Checkpoint 5 decision — see the M5 Domain
Contract's API plan. `POST /v1/work-items` creates a Task, landing in
`pending` (any active member — no role restriction, matching the
Claimant Resolution's "humans may create tasks" framing); `GET
/v1/work-items` lists (cursor-paginated, filterable by goal/assignee);
`GET /v1/work-items/{id}` fetches one. `/claim`, `/block`, `/complete`,
`/fail`, `/approve`, `/reject`, and `/approvals` are all deferred — not
built, per Finding 3's cascade (M5 Step 3 plan §0.1). The path is
provisional (`work-items`, not `tasks` — B3, not resolved here); `/v1/tasks`
itself stays the unrelated generic async-invocation trigger (decision 3).
"""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals.api.errors import GoalNotFoundHTTPError
from app.modules.goals.domain.errors import GoalNotFoundError
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.tasks.api.errors import (
    AssignedUserNotFoundHTTPError,
    InvalidCursorHTTPError,
    TaskIdempotencyConflictHTTPError,
    TaskNotFoundHTTPError,
)
from app.modules.tasks.api.schemas import (
    CreateWorkItemRequest,
    WorkItemListResponse,
    WorkItemResponse,
)
from app.modules.tasks.application.services import create_task
from app.modules.tasks.domain.entities import Task
from app.modules.tasks.domain.errors import AssignedUserNotFoundError, TaskIdempotencyConflictError
from app.modules.tasks.infrastructure.repository import TaskRepository
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["tasks"])

_CURSOR_FIELD_SEPARATOR = "|"


def _to_work_item_response(task: Task) -> WorkItemResponse:
    if task.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in a Task
        # that was never actually saved.
        raise RuntimeError("Cannot build a WorkItemResponse for an unsaved Task.")
    return WorkItemResponse(
        id=task.id,
        goal_id=task.goal_id,
        assigned_ai_employee_id=task.assigned_ai_employee_id,
        assigned_user_id=task.assigned_user_id,
        status=task.status.value,
        blocked_reason=task.blocked_reason.value if task.blocked_reason else None,
        idempotency_key=task.idempotency_key,
        retry_count=task.retry_count,
        created_at=task.created_at,
    )


def _encode_cursor(task: Task) -> str:
    assert task.created_at is not None  # always true for a persisted row
    raw = f"{task.created_at.isoformat()}{_CURSOR_FIELD_SEPARATOR}{task.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_raw, id_raw = raw.split(_CURSOR_FIELD_SEPARATOR)
        return datetime.fromisoformat(created_at_raw), UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorHTTPError(f"'{cursor}' is not a valid pagination cursor.") from exc


@router.post(
    "/work-items", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED
)
async def create_work_item(
    body: CreateWorkItemRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> WorkItemResponse:
    try:
        task = await create_task(
            session,
            organization_id=context.organization_id,
            idempotency_key=body.idempotency_key,
            goal_id=body.goal_id,
            assigned_user_id=body.assigned_user_id,
        )
    except TaskIdempotencyConflictError as exc:
        raise TaskIdempotencyConflictHTTPError(
            str(exc), details={"task_id": str(exc.existing_task_id)}
        ) from exc
    except GoalNotFoundError as exc:
        raise GoalNotFoundHTTPError(str(exc)) from exc
    except AssignedUserNotFoundError as exc:
        raise AssignedUserNotFoundHTTPError(str(exc)) from exc
    return _to_work_item_response(task)


@router.get("/work-items", response_model=WorkItemListResponse)
async def list_work_items(
    goal_id: UUID | None = Query(None),  # noqa: B008 - ruff's safe-default allowlist
    # covers str/int/etc but not UUID; Query(None) has no side effects either way
    assigned_user_id: UUID | None = Query(None),  # noqa: B008
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> WorkItemListResponse:
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    async with tenant_scoped_transaction(session, context.organization_id):
        tasks = await TaskRepository().list_for_organization(
            session,
            context.organization_id,
            goal_id=goal_id,
            assigned_user_id=assigned_user_id,
            cursor=decoded_cursor,
            limit=limit,
        )

    next_cursor = _encode_cursor(tasks[-1]) if len(tasks) == limit else None
    return WorkItemListResponse(
        items=[_to_work_item_response(t) for t in tasks], next_cursor=next_cursor
    )


@router.get("/work-items/{task_id}", response_model=WorkItemResponse)
async def get_work_item(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> WorkItemResponse:
    async with tenant_scoped_transaction(session, context.organization_id):
        task = await TaskRepository().get_by_id(session, context.organization_id, task_id)
    if task is None:
        raise TaskNotFoundHTTPError(f"Task '{task_id}' was not found.")
    return _to_work_item_response(task)
