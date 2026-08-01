"""The organization-scoping dependency identity/api/dependencies.py's own
docstring anticipated: "who is this" (get_current_user) and "what org are
they acting in" are separate, composable concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.identity.api.dependencies import get_current_user
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.tokens import decode_access_token
from app.modules.organizations.api.errors import NoOrganizationContextHTTPError
from app.shared.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class OrganizationContext:
    user: User
    organization_id: UUID
    role: str


async def get_current_org_context(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> OrganizationContext:
    """Composes get_current_user (bearer presence, signature, expiry, and
    token_version are already validated by the time this runs) and reads
    the same token's organization_id/role claims — a second, cheap local
    JWT decode, not a second DB round trip, to avoid duplicating
    get_current_user's validation logic for what's otherwise a one-line
    difference."""
    assert credentials is not None  # guaranteed by get_current_user succeeding above
    claims = decode_access_token(credentials.credentials, secret_key=settings.jwt_secret_key)

    if claims.organization_id is None or claims.role is None:
        raise NoOrganizationContextHTTPError(
            "This session is not scoped to an organization yet."
        )

    return OrganizationContext(
        user=current_user, organization_id=claims.organization_id, role=claims.role
    )
