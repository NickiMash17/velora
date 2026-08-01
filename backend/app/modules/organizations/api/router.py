"""Organizations API endpoints.

Endpoint shapes are a Milestone 4 decision — see this milestone's
completion report and docs/architecture/API.md's Milestone 4 section.
`GET /v1/organizations` (list mine) and `GET /v1/organizations/me`
(current session's org) follow API.md §2's resource-oriented convention;
`POST /v1/organizations` doubles as a session-issuance action (returning
a freshly scoped token pair alongside the created resource) and
`POST /v1/organizations/{id}/select` is the "switching organizations
issues an entirely new scoped token" action Security.md §3.2 already
names — both follow the same reasoning identity's login/refresh actions
already established as the one deliberate exception to pure resource
CRUD.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.api.dependencies import get_current_user
from app.modules.identity.api.errors import InvalidRefreshTokenHTTPError
from app.modules.identity.api.schemas import TokenResponse
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.errors import InvalidRefreshTokenError
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.organizations.api.errors import (
    MembershipNotFoundHTTPError,
    OrganizationNotFoundHTTPError,
)
from app.modules.organizations.api.schemas import (
    CreateOrganizationRequest,
    OrganizationMembershipResponse,
    OrganizationResponse,
    OrganizationSessionResponse,
    SelectOrganizationRequest,
)
from app.modules.organizations.application.services import (
    create_organization_for_user,
    select_organization,
)
from app.modules.organizations.domain.entities import Organization
from app.modules.organizations.domain.errors import MembershipNotFoundError
from app.modules.organizations.infrastructure.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from app.shared.config import Settings, get_settings
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["organizations"])


def _to_organization_response(organization: Organization) -> OrganizationResponse:
    if organization.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in an
        # Organization that was never actually saved.
        raise RuntimeError("Cannot build an OrganizationResponse for an unsaved Organization.")
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        plan_tier=organization.plan_tier.value,
        status=organization.status.value,
        created_at=organization.created_at,
    )


async def _fetch_organization_or_404(
    session: AsyncSession, organization_id: UUID
) -> OrganizationResponse:
    async with tenant_scoped_transaction(session, organization_id):
        organization = await OrganizationRepository().get_by_id(session, organization_id)
    if organization is None:
        raise OrganizationNotFoundHTTPError(f"Organization '{organization_id}' was not found.")
    return _to_organization_response(organization)


@router.get("/organizations", response_model=list[OrganizationMembershipResponse])
async def list_my_organizations(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationMembershipResponse]:
    memberships = await OrganizationMembershipRepository().list_for_user(session, current_user.id)

    responses = []
    for membership in memberships:
        organization = await _fetch_organization_or_404(session, membership.organization_id)
        responses.append(
            OrganizationMembershipResponse(organization=organization, role=membership.role.value)
        )
    return responses


@router.post(
    "/organizations",
    response_model=OrganizationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    body: CreateOrganizationRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> OrganizationSessionResponse:
    try:
        result, tokens = await create_organization_for_user(
            session,
            settings,
            name=body.name,
            admin_user_id=current_user.id,
            refresh_token=body.refresh_token,
        )
    except InvalidRefreshTokenError as exc:
        raise InvalidRefreshTokenHTTPError(str(exc)) from exc
    return OrganizationSessionResponse(
        organization=_to_organization_response(result.organization),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        ),
    )


@router.post("/organizations/{organization_id}/select", response_model=OrganizationSessionResponse)
async def select_organization_endpoint(
    organization_id: UUID,
    body: SelectOrganizationRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> OrganizationSessionResponse:
    try:
        tokens = await select_organization(
            session,
            settings,
            user_id=current_user.id,
            organization_id=organization_id,
            refresh_token=body.refresh_token,
        )
    except MembershipNotFoundError as exc:
        raise MembershipNotFoundHTTPError(str(exc)) from exc
    except InvalidRefreshTokenError as exc:
        raise InvalidRefreshTokenHTTPError(str(exc)) from exc

    organization = await _fetch_organization_or_404(session, organization_id)
    return OrganizationSessionResponse(
        organization=organization,
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        ),
    )


@router.get("/organizations/me", response_model=OrganizationMembershipResponse)
async def get_current_organization(
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> OrganizationMembershipResponse:
    organization = await _fetch_organization_or_404(session, context.organization_id)
    return OrganizationMembershipResponse(organization=organization, role=context.role)
