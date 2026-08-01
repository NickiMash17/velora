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
from app.modules.organizations.domain.enums import MembershipStatus
from app.modules.organizations.infrastructure.orm import OrganizationMembershipORM, OrganizationORM
from app.shared.tenancy import tenant_scoped_transaction, user_scoped_transaction


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
    async def create(self, session: AsyncSession, organization: Organization) -> Organization:
        """Returns the persisted Organization with server-generated fields
        (created_at, updated_at) populated — see identity's
        UserRepository.create() for why this is necessary (flush()
        triggers an INSERT with RETURNING that populates the ORM
        instance, but the caller's domain object passed in never sees
        those fields unless read back explicitly). This exact gap was
        flagged as a known latent bug during Milestone 3 and left
        unfixed as out of scope then; Milestone 4 is the first caller
        that actually needs created_at (an API response), which is what
        surfaces it now."""
        row = OrganizationORM(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            plan_tier=organization.plan_tier,
            isolation_tier=organization.isolation_tier,
            region=organization.region,
            status=organization.status,
        )
        session.add(row)
        await session.flush()
        return _to_domain_org(row)

    async def get_by_id(self, session: AsyncSession, organization_id: UUID) -> Organization | None:
        row = await session.get(OrganizationORM, organization_id)
        return _to_domain_org(row) if row else None


class OrganizationMembershipRepository:
    async def create(
        self, session: AsyncSession, membership: OrganizationMembership
    ) -> OrganizationMembership:
        """Same fix as OrganizationRepository.create() above, same reason."""
        row = OrganizationMembershipORM(
            id=membership.id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role,
            status=membership.status,
        )
        session.add(row)
        await session.flush()
        return _to_domain_membership(row)

    async def list_for_organization(
        self, session: AsyncSession, organization_id: UUID
    ) -> list[OrganizationMembership]:
        result = await session.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == organization_id
            )
        )
        return [_to_domain_membership(row) for row in result.scalars().all()]

    async def list_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> list[OrganizationMembership]:
        """The one query this table's `self_visibility` RLS policy exists
        for (ADR 0002): which organization(s) does `user_id` belong to,
        asked before any tenant context is known. Must run inside
        user_scoped_transaction, never tenant_scoped_transaction — there
        is no organization_id to scope to yet, that's the whole point."""
        async with user_scoped_transaction(session, user_id):
            result = await session.execute(
                select(OrganizationMembershipORM).where(
                    OrganizationMembershipORM.user_id == user_id,
                    OrganizationMembershipORM.status == MembershipStatus.ACTIVE,
                )
            )
            return [_to_domain_membership(row) for row in result.scalars().all()]

    async def get_for_user_in_organization(
        self, session: AsyncSession, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        """Verifies `user_id` has an active membership in `organization_id`
        — `organization_id` here is a client-supplied CANDIDATE, not
        trusted for scoping on its own; opening tenant_scoped_transaction
        against it and letting RLS decide what's visible is what actually
        verifies it (same pattern app/modules/organizations/application/
        services.py's create_organization_with_admin already uses for an
        org that doesn't exist yet — here the org already exists, but the
        caller's *membership* in it is what's unverified)."""
        async with tenant_scoped_transaction(session, organization_id):
            result = await session.execute(
                select(OrganizationMembershipORM).where(
                    OrganizationMembershipORM.organization_id == organization_id,
                    OrganizationMembershipORM.user_id == user_id,
                    OrganizationMembershipORM.status == MembershipStatus.ACTIVE,
                )
            )
            row = result.scalar_one_or_none()
            return _to_domain_membership(row) if row else None
