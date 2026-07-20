"""SQLAlchemy model for the events table (the v1 Event Store / transactional
outbox — see docs/architecture/decisions/0001-event-store-implementation.md).

Shape only, matching docs/architecture/Database.md §3.11 exactly. RLS is
enabled/forced and the policy created in the Alembic migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class EventORM(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_organization_id_occurred_at", "organization_id", "occurred_at"),
        Index(
            "ix_events_unrelayed",
            "relayed_at",
            postgresql_where=text("relayed_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    producer: Mapped[str] = mapped_column(String, nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    relayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
