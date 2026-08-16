"""Pydantic request/response models for the Goals API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateGoalRequest(BaseModel):
    """Propose a new Goal. `success_metric` is accepted as an opaque
    object (`{metric, target, current}` per Database.md §3.5) — its
    directionality is not validated or interpreted here (known,
    unresolved gap in the source documentation)."""

    title: str = Field(..., min_length=1)
    success_metric: dict[str, Any]
    department_id: UUID | None = None


class GoalResponse(BaseModel):
    """Public representation of a Goal."""

    id: UUID
    department_id: UUID | None
    title: str
    success_metric: dict[str, Any]
    status: str
    created_at: datetime


class GoalListResponse(BaseModel):
    """A cursor-paginated page of Goals (docs/architecture/API.md §6).
    `next_cursor` is null once the last page has been returned."""

    items: list[GoalResponse]
    next_cursor: str | None
