"""Repository layer for organizations and organization_memberships.

Every method takes `organization_id` explicitly, per
docs/architecture/Database.md §2.2 ("no unscoped query method exposed on
tenant-scoped repositories") — though the actual, load-bearing enforcement
is Row-Level Security (see app/shared/tenancy.py); this is defense-in-depth
and call-site clarity, not the guarantee itself.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.domain.entities import Organization, OrganizationMembership
from app.modules.organizations.infrastructure.orm import OrganizationMembershipORM, OrganizationORM


def _to_domain_org(row: OrganizationORM) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        slug=row.slug,
        plan_tier=row.plan_tier,
        isolation_tier=row.isolation_tier,
        region=row.region,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_domain_membership(row: OrganizationMembershipORM) -> OrganizationMembership:
    return OrganizationMembership(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        role=row.role,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class OrganizationRepository:
    async def create(self, session: AsyncSession, organization: Organization) -> None:
        session.add(
            OrganizationORM(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                plan_tier=organization.plan_tier,
                isolation_tier=organization.isolation_tier,
                region=organization.region,
                status=organization.status,
            )
        )
        await session.flush()

    async def get_by_id(self, session: AsyncSession, organization_id: UUID) -> Organization | None:
        row = await session.get(OrganizationORM, organization_id)
        return _to_domain_org(row) if row else None


class OrganizationMembershipRepository:
    async def create(self, session: AsyncSession, membership: OrganizationMembership) -> None:
        session.add(
            OrganizationMembershipORM(
                id=membership.id,
                organization_id=membership.organization_id,
                user_id=membership.user_id,
                role=membership.role,
                status=membership.status,
            )
        )
        await session.flush()

    async def list_for_organization(
        self, session: AsyncSession, organization_id: UUID
    ) -> list[OrganizationMembership]:
        result = await session.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == organization_id
            )
        )
        return [_to_domain_membership(row) for row in result.scalars().all()]
