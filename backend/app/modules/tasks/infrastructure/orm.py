"""SQLAlchemy model for tasks.

Shape only. RLS is enabled/forced and the policy created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it
protects, not be inferred from the ORM model at runtime.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.tasks.domain.enums import TaskBlockedReason, TaskStatus
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "PENDING") — StateMachines.md §3/decision A3 specify lowercase
    VALUES ("pending"). Passed as `values_callable` so Postgres gets the
    documented lowercase labels."""
    return [member.value for member in python_enum]


class TaskORM(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_organization_id_status", "organization_id", "status"),
        Index("ix_tasks_goal_id", "goal_id"),
        Index("ix_tasks_assigned_ai_employee_id", "assigned_ai_employee_id"),
        Index("ix_tasks_assigned_user_id", "assigned_user_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_tasks_org_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("goals.id"), nullable=True
    )
    assigned_ai_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_employees.id"), nullable=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        PgEnum(TaskStatus, name="task_status", values_callable=_enum_values), nullable=False
    )
    blocked_reason: Mapped[TaskBlockedReason | None] = mapped_column(
        PgEnum(TaskBlockedReason, name="task_blocked_reason", values_callable=_enum_values),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
