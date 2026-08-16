"""Pure domain entities for the AI Employees domain.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.

No `AiEmployeeSkill` entity here — the join table has no write path in
this checkpoint (see the module's application/services.py docstring for
why) and no independent behavior of its own to model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.ai_employees.domain.enums import AiEmployeeStatus


@dataclass
class AiEmployeeTemplate:
    id: UUID
    name: str
    default_skills: list[str]
    system_prompt_scaffold: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Skill:
    id: UUID
    key: str
    description: str
    input_schema: dict[str, Any]
    required_permission_scope: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class AiEmployee:
    id: UUID
    organization_id: UUID
    department_id: UUID
    template_id: UUID
    name: str
    role_title: str
    status: AiEmployeeStatus
    company_dna_version_id: UUID | None = None
    permission_scope: dict[str, Any] | None = None
    autonomy_defaults: dict[str, str] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
