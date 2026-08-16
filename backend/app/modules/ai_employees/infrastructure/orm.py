"""SQLAlchemy models for ai_employee_templates, skills, ai_employees, and
ai_employee_skills.

Shape only. RLS is enabled/forced and the policy created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it
protects, not be inferred from the ORM model at runtime.

`AiEmployeeTemplateORM` and `SkillORM` deliberately have no
`organization_id` column and no RLS of any kind (locked decision A1 —
global catalogs), matching `UserORM`'s precedent exactly.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.ai_employees.domain.enums import AiEmployeeStatus
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "DRAFT") — AIEmployees.md §3 specifies lowercase VALUES
    ("draft"). Passed as `values_callable` so Postgres gets the documented
    lowercase labels."""
    return [member.value for member in python_enum]


class AiEmployeeTemplateORM(Base):
    __tablename__ = "ai_employee_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    default_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    system_prompt_scaffold: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SkillORM(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("key", name="uq_skills_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    required_permission_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AiEmployeeORM(Base):
    __tablename__ = "ai_employees"
    __table_args__ = (
        Index("ix_ai_employees_organization_id_status", "organization_id", "status"),
        Index("ix_ai_employees_department_id", "department_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_employee_templates.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    role_title: Mapped[str] = mapped_column(String, nullable=False)
    company_dna_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_dna_versions.id"), nullable=True
    )
    status: Mapped[AiEmployeeStatus] = mapped_column(
        PgEnum(AiEmployeeStatus, name="ai_employee_status", values_callable=_enum_values),
        nullable=False,
    )
    permission_scope: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    autonomy_defaults: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AiEmployeeSkillORM(Base):
    __tablename__ = "ai_employee_skills"
    __table_args__ = (
        Index("ix_ai_employee_skills_skill_id", "skill_id"),
        Index("ix_ai_employee_skills_organization_id", "organization_id"),
    )

    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_employees.id"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
