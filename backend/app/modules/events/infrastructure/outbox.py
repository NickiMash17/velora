"""Transactional outbox write path — the ONLY way any module writes to the
events table.

Per docs/architecture/decisions/0001-event-store-implementation.md and
docs/architecture/Database.md §3.11: the event insert must use the SAME
session/transaction as the domain state change it accompanies, so both
commit or both roll back together — this function only ever `flush()`es,
never `commit()`s, so the caller's transaction boundary (typically
app.shared.tenancy.tenant_scoped_transaction) is what actually makes it
atomic.

No relay process and no Redis Streams publishing here — per this
milestone's explicit scope, and per ADR 0001, those are deferred until a
real consumer exists to read from them.
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.infrastructure.orm import EventORM


async def write_event(
    session: AsyncSession,
    *,
    organization_id: UUID | None,
    type: str,
    topic: str,
    producer: str,
    payload: dict[str, Any],
    correlation_id: UUID,
    causation_id: UUID | None = None,
) -> EventORM:
    event = EventORM(
        id=uuid.uuid4(),
        organization_id=organization_id,
        type=type,
        topic=topic,
        producer=producer,
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event
