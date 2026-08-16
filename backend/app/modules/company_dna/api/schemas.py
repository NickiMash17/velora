"""Pydantic request/response models for the Company DNA API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateDnaVersionRequest(BaseModel):
    """Open a new draft Company DNA version. `compiled_summary` is not
    set here — it is authored separately via `PATCH .../{id}` (M5's
    manual-entry model; no compiler pipeline exists)."""

    version: str = Field(..., min_length=1, description="Semver string, e.g. '1.0.0'")


class UpdateDnaVersionCompiledSummaryRequest(BaseModel):
    """Edit a draft version's compiled_summary. Only permitted while the
    version is still `draft`."""

    compiled_summary: str = Field(..., min_length=1)


class CompanyDnaVersionResponse(BaseModel):
    """Public representation of a Company DNA version."""

    id: UUID
    version: str
    status: str
    compiled_summary: str | None
    published_at: datetime | None
    created_at: datetime


class CompanyDnaVersionListResponse(BaseModel):
    """A cursor-paginated page of Company DNA versions
    (docs/architecture/API.md §6). `next_cursor` is null once the last
    page has been returned."""

    items: list[CompanyDnaVersionResponse]
    next_cursor: str | None
