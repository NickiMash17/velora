"""SQLAlchemy model for goals.

Shape only. RLS is enabled/forced and the policy created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it
protects, not be inferred from the ORM model at runtime.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.goals.domain.enums import GoalStatus
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "PROPOSED") — Database.md §3.5 specifies lowercase VALUES
    ("proposed"). Passed as `values_callable` so Postgres gets the
    documented lowercase labels."""
    return [member.value for member in python_enum]


class GoalORM(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_organization_id", "organization_id"),
        Index("ix_goals_department_id", "department_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    success_metric: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        PgEnum(GoalStatus, name="goal_status", values_callable=_enum_values), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
