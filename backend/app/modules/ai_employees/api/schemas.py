"""Pydantic request/response models for the AI Employees API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.ai_employees.domain.enums import AutonomyLevel


class HireAiEmployeeRequest(BaseModel):
    """Hire a new AI Employee into `draft` — AIEmployees.md §4 step 1/2:
    template + department selection, machine identity generation (not
    modeled — no real machine-credential system exists yet)."""

    department_id: UUID
    template_id: UUID
    name: str = Field(..., min_length=1, description='e.g. "Riley"')
    role_title: str = Field(..., min_length=1, description='e.g. "Support Agent"')


class ConfigureAiEmployeeRequest(BaseModel):
    """Bind DNA version + permission scope + autonomy — AIEmployees.md §3's
    hard rule: a Digital Employee cannot skip `configured` without both a
    bound DNA version and an explicit permission scope. `autonomy_defaults`
    is optional (defaults to `{}`); its values must be one of the locked
    taxonomy (`autonomous`/`notify`/`approve` — decision 2), its keys
    (`skill_key`) are not validated against `ai_employee_skills` at any
    level in M5 (an unavoidable consequence of the flat-jsonb decision,
    not an oversight)."""

    company_dna_version_id: UUID
    permission_scope: dict[str, Any]
    autonomy_defaults: dict[str, AutonomyLevel] | None = None


class AiEmployeeResponse(BaseModel):
    """Public representation of an AI Employee."""

    id: UUID
    department_id: UUID
    template_id: UUID
    name: str
    role_title: str
    status: str
    company_dna_version_id: UUID | None
    permission_scope: dict[str, Any] | None
    autonomy_defaults: dict[str, str]
    created_at: datetime


class AiEmployeeListResponse(BaseModel):
    """A cursor-paginated page of AI Employees (docs/architecture/API.md
    §6). `next_cursor` is null once the last page has been returned."""

    items: list[AiEmployeeResponse]
    next_cursor: str | None


class AiEmployeeTemplateResponse(BaseModel):
    """Public representation of an AI Employee template — read-only in
    M5; no endpoint creates or modifies templates (platform-level catalog
    maintenance only)."""

    id: UUID
    name: str
    default_skills: list[str]
    system_prompt_scaffold: str
    created_at: datetime


class AiEmployeeTemplateListResponse(BaseModel):
    """A cursor-paginated page of AI Employee templates — global catalog,
    no organization scoping."""

    items: list[AiEmployeeTemplateResponse]
    next_cursor: str | None
