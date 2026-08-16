"""SQLAlchemy model for departments.

Shape only. RLS is enabled/forced and the policy created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it
protects, not be inferred from the ORM model at runtime.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.departments.domain.enums import FunctionType
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "SALES") — Database.md §3.2 specifies lowercase VALUES ("sales").
    Passed as `values_callable` so Postgres gets the documented lowercase
    labels."""
    return [member.value for member in python_enum]


class DepartmentORM(Base):
    __tablename__ = "departments"
    __table_args__ = (Index("ix_departments_organization_id", "organization_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    function_type: Mapped[FunctionType] = mapped_column(
        PgEnum(FunctionType, name="department_function_type", values_callable=_enum_values),
        nullable=False,
    )
    budget_cents_monthly: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
