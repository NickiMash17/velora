"""Use case: create an Organization and its founding admin membership,
atomically with the OrganizationCreated / MembershipActivated events.

Deliberately does NOT create a User — signup is out of scope for this
milestone (see AGENTS.md constraints). This takes an existing
`admin_user_id`; this milestone's own tests create that user directly via
UserRepository, not through any signup flow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.domain.catalog import MEMBERSHIP_ACTIVATED, ORGANIZATION_CREATED, topic_for
from app.modules.events.infrastructure.outbox import write_event
from app.modules.organizations.domain.entities import Organization, OrganizationMembership
from app.modules.organizations.domain.enums import (
    IsolationTier,
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
    PlanTier,
    Region,
)
from app.modules.organizations.infrastructure.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "organizations"


@dataclass
class CreateOrganizationResult:
    organization: Organization
    membership: OrganizationMembership


async def create_organization_with_admin(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    admin_user_id: UUID,
    plan_tier: PlanTier = PlanTier.TRIAL,
    region: Region = Region.US,
    organization_repo: OrganizationRepository | None = None,
    membership_repo: OrganizationMembershipRepository | None = None,
) -> CreateOrganizationResult:
    organization_repo = organization_repo or OrganizationRepository()
    membership_repo = membership_repo or OrganizationMembershipRepository()

    organization_id = uuid.uuid4()
    correlation_id = uuid.uuid4()

    organization = Organization(
        id=organization_id,
        name=name,
        slug=slug,
        plan_tier=plan_tier,
        isolation_tier=IsolationTier.POOL,
        region=region,
        status=OrganizationStatus.TRIAL,
    )
    membership = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=admin_user_id,
        role=MembershipRole.ORG_ADMIN,
        status=MembershipStatus.ACTIVE,
    )

    # Tenant context is set to the org being CREATED — see
    # app/shared/tenancy.py's docstring for why this is the correct,
    # bypass-free resolution to there being no pre-existing tenant context
    # for a brand-new organization.
    async with tenant_scoped_transaction(session, organization_id):
        await organization_repo.create(session, organization)
        await membership_repo.create(session, membership)

        org_created_event = await write_event(
            session,
            organization_id=organization_id,
            type=ORGANIZATION_CREATED,
            topic=topic_for(ORGANIZATION_CREATED),
            producer=_PRODUCER,
            payload={
                "organization_id": str(organization_id),
                "plan_tier": plan_tier.value,
                "region": region.value,
            },
            correlation_id=correlation_id,
        )
        await write_event(
            session,
            organization_id=organization_id,
            type=MEMBERSHIP_ACTIVATED,
            topic=topic_for(MEMBERSHIP_ACTIVATED),
            producer=_PRODUCER,
            payload={
                "organization_id": str(organization_id),
                "user_id": str(admin_user_id),
                "role": membership.role.value,
            },
            correlation_id=correlation_id,
            causation_id=org_created_event.id,
        )

    return CreateOrganizationResult(organization=organization, membership=membership)
