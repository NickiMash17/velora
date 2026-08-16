"""SQLAlchemy model for company_dna_versions.

Shape only. RLS is enabled/forced and the policy created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it
protects, not be inferred from the ORM model at runtime.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "DRAFT") — Database.md §3.4/locked decision A2 specify lowercase
    VALUES ("draft"). Passed as `values_callable` so Postgres gets the
    documented lowercase labels."""
    return [member.value for member in python_enum]


class CompanyDnaVersionORM(Base):
    __tablename__ = "company_dna_versions"
    __table_args__ = (
        Index("ix_company_dna_versions_organization_id", "organization_id"),
        UniqueConstraint(
            "organization_id", "version", name="uq_company_dna_versions_org_version"
        ),
        Index(
            "ix_company_dna_versions_one_published_per_org",
            "organization_id",
            unique=True,
            postgresql_where=text("status = 'published'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CompanyDnaVersionStatus] = mapped_column(
        PgEnum(
            CompanyDnaVersionStatus, name="company_dna_version_status", values_callable=_enum_values
        ),
        nullable=False,
    )
    compiled_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
