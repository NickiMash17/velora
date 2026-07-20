"""SQLAlchemy models for organizations and organization_memberships.

Shape only. RLS is enabled/forced and policies are created in the Alembic
migration (alembic/versions/), not here — docs/architecture/Database.md §5
requires RLS to live in the same migration as the CREATE TABLE it protects,
not be inferred from the ORM model at runtime.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.organizations.domain.enums import (
    IsolationTier,
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
    PlanTier,
    Region,
)
from app.shared.db import Base


def _enum_values(python_enum: type[enum.Enum]) -> list[str]:
    """SQLAlchemy's Enum type stores Python enum MEMBER NAMES by default
    (e.g. "TRIAL") — Database.md §3.1 specifies lowercase VALUES ("trial").
    Passed as `values_callable` on every PgEnum below so Postgres gets the
    documented lowercase labels."""
    return [member.value for member in python_enum]


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    plan_tier: Mapped[PlanTier] = mapped_column(
        PgEnum(PlanTier, name="plan_tier", values_callable=_enum_values), nullable=False
    )
    isolation_tier: Mapped[IsolationTier] = mapped_column(
        PgEnum(IsolationTier, name="isolation_tier", values_callable=_enum_values), nullable=False
    )
    region: Mapped[Region] = mapped_column(
        PgEnum(Region, name="region", values_callable=_enum_values), nullable=False
    )
    status: Mapped[OrganizationStatus] = mapped_column(
        PgEnum(OrganizationStatus, name="organization_status", values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrganizationMembershipORM(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_membership_org_user"),
        Index("ix_organization_memberships_organization_id", "organization_id"),
        Index("ix_organization_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[MembershipRole] = mapped_column(
        PgEnum(MembershipRole, name="membership_role", values_callable=_enum_values), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        PgEnum(MembershipStatus, name="membership_status", values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
