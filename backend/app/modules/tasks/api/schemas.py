"""Pydantic request/response models for the Tasks (work-items) API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema. Path provisional as `/v1/work-items` — B3, not resolved
here per instruction.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateWorkItemRequest(BaseModel):
    """Create a new Task, landing in `pending`. No `title` field — traced
    against Database.md §3.5 and API.md §5 directly, neither establishes
    one (M5 Step 3 plan §0.1)."""

    goal_id: UUID | None = None
    assigned_user_id: UUID | None = None
    idempotency_key: str = Field(
        ..., min_length=1, description="Client-generated key preventing duplicate creation on retry"
    )


class WorkItemResponse(BaseModel):
    """Public representation of a Task."""

    id: UUID
    goal_id: UUID | None
    assigned_ai_employee_id: UUID | None
    assigned_user_id: UUID | None
    status: str
    blocked_reason: str | None
    idempotency_key: str
    retry_count: int
    created_at: datetime


class WorkItemListResponse(BaseModel):
    """A cursor-paginated page of Tasks (docs/architecture/API.md §6).
    `next_cursor` is null once the last page has been returned."""

    items: list[WorkItemResponse]
    next_cursor: str | None
