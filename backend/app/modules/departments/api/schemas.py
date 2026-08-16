"""Pydantic request/response models for the departments API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.departments.domain.enums import FunctionType


class CreateDepartmentRequest(BaseModel):
    """Create a new department within the caller's current organization.
    No `status` field — Department lifecycle/archive is out of scope for
    M5 (locked decision C1)."""

    name: str = Field(..., min_length=1)
    function_type: FunctionType
    budget_cents_monthly: int | None = Field(
        None, description="Optional monthly spend cap, in cents"
    )


class DepartmentResponse(BaseModel):
    """Public representation of a department."""

    id: UUID
    name: str
    function_type: str
    budget_cents_monthly: int | None
    created_at: datetime


class DepartmentListResponse(BaseModel):
    """A cursor-paginated page of departments (docs/architecture/API.md §6).
    `next_cursor` is null once the last page has been returned."""

    items: list[DepartmentResponse]
    next_cursor: str | None
