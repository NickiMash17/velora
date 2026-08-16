"""Pure domain entity for Department.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.departments.domain.enums import FunctionType


@dataclass
class Department:
    id: UUID
    organization_id: UUID
    name: str
    function_type: FunctionType
    budget_cents_monthly: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
