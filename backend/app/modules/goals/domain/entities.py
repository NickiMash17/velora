"""Pure domain entity for Goal.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.goals.domain.enums import GoalStatus


@dataclass
class Goal:
    id: UUID
    organization_id: UUID
    title: str
    success_metric: dict[str, Any]
    status: GoalStatus
    department_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
