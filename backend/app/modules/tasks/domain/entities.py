"""Pure domain entity for Task.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.

No `title` field — traced against `Database.md §3.5` and `API.md §5`
directly; neither establishes a title-like field for Task (M5 Step 3 plan
§0.1). Flagged `[INFERENCE]` if ever added, not locked here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.tasks.domain.enums import TaskBlockedReason, TaskStatus


@dataclass
class Task:
    id: UUID
    organization_id: UUID
    status: TaskStatus
    idempotency_key: str
    goal_id: UUID | None = None
    assigned_ai_employee_id: UUID | None = None
    assigned_user_id: UUID | None = None
    blocked_reason: TaskBlockedReason | None = None
    retry_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
