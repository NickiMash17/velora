"""Repository layer for company_dna_versions.

Every method takes `organization_id` explicitly, per
docs/architecture/Database.md §2.2 ("no unscoped query method exposed on
tenant-scoped repositories") — though the actual, load-bearing enforcement
is Row-Level Security (see app/shared/tenancy.py); this is defense-in-depth
and call-site clarity, not the guarantee itself.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company_dna.domain.entities import CompanyDnaVersion
from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus
from app.modules.company_dna.infrastructure.orm import CompanyDnaVersionORM


def _to_domain(row: CompanyDnaVersionORM) -> CompanyDnaVersion:
    return CompanyDnaVersion(
        id=row.id,
        organization_id=row.organization_id,
        version=row.version,
        status=row.status,
        compiled_summary=row.compiled_summary,
        published_at=row.published_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class CompanyDnaVersionRepository:
    async def create(
        self, session: AsyncSession, dna_version: CompanyDnaVersion
    ) -> CompanyDnaVersion:
        """Returns the persisted CompanyDnaVersion with server-generated
        fields (created_at, updated_at) populated — same fix/reason as
        OrganizationRepository.create()'s own docstring: flush() triggers
        an INSERT with RETURNING that populates the ORM instance, but the
        caller's domain object never sees those fields unless read back
        explicitly."""
        row = CompanyDnaVersionORM(
            id=dna_version.id,
            organization_id=dna_version.organization_id,
            version=dna_version.version,
            status=dna_version.status,
            compiled_summary=dna_version.compiled_summary,
            published_at=dna_version.published_at,
        )
        session.add(row)
        await session.flush()
        return _to_domain(row)

    async def save(
        self, session: AsyncSession, dna_version: CompanyDnaVersion
    ) -> CompanyDnaVersion:
        """Persists mutations to an already-persisted row (`version.id`
        must already exist — callers always fetch via `get_by_id` first,
        so this never has to guard against a missing row itself).

        `flush()` alone does not populate `updated_at` client-side for an
        UPDATE (unlike an INSERT's server_default, which flush's RETURNING
        does capture) — `updated_at`'s `onupdate=func.now()` value stays
        server-side, and the attribute is left expired. Reading it back
        immediately afterward would otherwise trigger an implicit lazy-load
        SELECT outside of an awaited context, which asyncpg's async
        SQLAlchemy dialect cannot do (`MissingGreenlet`) — `refresh()`
        makes that re-fetch explicit and awaited instead."""
        row = await session.get(CompanyDnaVersionORM, dna_version.id)
        assert row is not None
        row.version = dna_version.version
        row.status = dna_version.status
        row.compiled_summary = dna_version.compiled_summary
        row.published_at = dna_version.published_at
        await session.flush()
        await session.refresh(row)
        return _to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, organization_id: UUID, version_id: UUID
    ) -> CompanyDnaVersion | None:
        result = await session.execute(
            select(CompanyDnaVersionORM).where(
                CompanyDnaVersionORM.organization_id == organization_id,
                CompanyDnaVersionORM.id == version_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_current_published(
        self, session: AsyncSession, organization_id: UUID
    ) -> CompanyDnaVersion | None:
        result = await session.execute(
            select(CompanyDnaVersionORM).where(
                CompanyDnaVersionORM.organization_id == organization_id,
                CompanyDnaVersionORM.status == CompanyDnaVersionStatus.PUBLISHED,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[CompanyDnaVersion]:
        """Keyset-paginated on `(created_at, id)` — same convention
        established in departments/infrastructure/repository.py, the
        first real use of docs/architecture/API.md §6's cursor-pagination
        convention in this codebase."""
        query = select(CompanyDnaVersionORM).where(
            CompanyDnaVersionORM.organization_id == organization_id
        )
        if cursor is not None:
            query = query.where(
                tuple_(CompanyDnaVersionORM.created_at, CompanyDnaVersionORM.id) > cursor
            )
        query = query.order_by(
            CompanyDnaVersionORM.created_at, CompanyDnaVersionORM.id
        ).limit(limit)
        result = await session.execute(query)
        return [_to_domain(row) for row in result.scalars().all()]
