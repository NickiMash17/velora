"""Use case: create an Organization and its founding admin membership,
atomically with the OrganizationCreated / MembershipActivated events.

Deliberately does NOT create a User — signup is out of scope for this
milestone (see AGENTS.md constraints). This takes an existing
`admin_user_id`; this milestone's own tests create that user directly via
UserRepository, not through any signup flow.

Milestone 4 adds two orchestration functions on top of the above
(`create_organization_for_user`, `select_organization`) that cross into
`app.modules.identity` to mint an organization-scoped session — a
one-directional dependency (organizations depends on identity; identity
has no knowledge of organizations at all, see
app/modules/identity/infrastructure/tokens.py's docstring). Every
signature crossing that boundary passes `role` as a plain `str`
(`membership.role.value`), never the `MembershipRole` enum.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.domain.catalog import MEMBERSHIP_ACTIVATED, ORGANIZATION_CREATED, topic_for
from app.modules.events.infrastructure.outbox import write_event
from app.modules.identity.application.services import TokenPair, refresh_session
from app.modules.organizations.domain.entities import Organization, OrganizationMembership
from app.modules.organizations.domain.enums import (
    IsolationTier,
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
    PlanTier,
    Region,
)
from app.modules.organizations.domain.errors import (
    MembershipNotFoundError,
    SlugGenerationExhaustedError,
)
from app.modules.organizations.domain.slug import slug_with_suffix, slugify
from app.modules.organizations.infrastructure.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from app.shared.config import Settings
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "organizations"

# Bounded: a real collision after this many high-entropy-suffixed
# candidates would indicate a bug in slug_with_suffix, not genuine
# exhaustion — see SlugGenerationExhaustedError's docstring.
_MAX_SLUG_ATTEMPTS = 5


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
        organization = await organization_repo.create(session, organization)
        membership = await membership_repo.create(session, membership)

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


async def create_organization_for_user(
    session: AsyncSession,
    settings: Settings,
    *,
    name: str,
    admin_user_id: UUID,
    refresh_token: str,
    plan_tier: PlanTier = PlanTier.TRIAL,
    region: Region = Region.US,
    organization_repo: OrganizationRepository | None = None,
    membership_repo: OrganizationMembershipRepository | None = None,
) -> tuple[CreateOrganizationResult, TokenPair]:
    """The API-facing create flow: `name` only — no user-visible slug
    concept at all (docs/product/WireframeSpec.md §5). Generates a
    candidate slug and retries with a new suffixed candidate on a unique-
    constraint collision; `create_organization_with_admin`'s own
    transaction (tenant_scoped_transaction) rolls back cleanly on that
    IntegrityError, so retrying the whole call is safe — no partial state
    survives a failed attempt.

    Also mints a token pair scoped to the new organization by rotating
    the caller's current refresh token (see refresh_session's docstring
    for why this is a rotation-with-override rather than an independent
    second token family)."""
    base_slug = slugify(name)
    candidate = base_slug
    result: CreateOrganizationResult | None = None

    for attempt in range(_MAX_SLUG_ATTEMPTS):
        try:
            result = await create_organization_with_admin(
                session,
                name=name,
                slug=candidate,
                admin_user_id=admin_user_id,
                plan_tier=plan_tier,
                region=region,
                organization_repo=organization_repo,
                membership_repo=membership_repo,
            )
            break
        except IntegrityError:
            if attempt == _MAX_SLUG_ATTEMPTS - 1:
                raise SlugGenerationExhaustedError(
                    f"Could not generate a unique slug for '{name}' after "
                    f"{_MAX_SLUG_ATTEMPTS} attempts."
                ) from None
            candidate = slug_with_suffix(base_slug)

    assert result is not None  # unreachable otherwise: the loop above always breaks or raises

    tokens = await refresh_session(
        session,
        settings,
        refresh_token=refresh_token,
        organization_id=result.organization.id,
        role=result.membership.role.value,
    )
    return result, tokens


async def select_organization(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: UUID,
    organization_id: UUID,
    refresh_token: str,
    membership_repo: OrganizationMembershipRepository | None = None,
) -> TokenPair:
    """Security.md §3.2's "switching organizations issues an entirely new
    scoped token" — `organization_id` is a client-supplied CANDIDATE, not
    trusted for scoping on its own; get_for_user_in_organization verifies
    it by opening tenant_scoped_transaction against it and letting RLS
    decide what's visible, exactly like org-creation already does for an
    org that doesn't exist yet (here the org exists, but the caller's own
    membership in it doesn't yet, until verified)."""
    membership_repo = membership_repo or OrganizationMembershipRepository()

    membership = await membership_repo.get_for_user_in_organization(
        session, organization_id, user_id
    )
    if membership is None:
        raise MembershipNotFoundError(
            f"No active membership for user '{user_id}' in organization '{organization_id}'."
        )

    return await refresh_session(
        session,
        settings,
        refresh_token=refresh_token,
        organization_id=organization_id,
        role=membership.role.value,
    )
