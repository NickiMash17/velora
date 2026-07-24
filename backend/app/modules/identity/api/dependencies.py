"""The authenticated-user dependency every future protected endpoint will
depend on.

Deliberately does NOT load or require any organization context — per
this milestone's scope, resolving "who is this" and "what org are they
acting in" are separate concerns (Security.md §3.2: a token is scoped to
at most one organization, but M3 issues tokens with no organization_id
claim at all, since org creation doesn't exist yet). A future milestone
adds an organization-scoping dependency that composes with this one; it
does not replace it.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.api.errors import UnauthorizedHTTPError
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.identity.infrastructure.tokens import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    decode_access_token,
)
from app.shared.config import Settings, get_settings
from app.shared.db import get_db_session

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise UnauthorizedHTTPError("Missing or malformed Authorization header.")

    try:
        claims = decode_access_token(credentials.credentials, secret_key=settings.jwt_secret_key)
    except ExpiredAccessTokenError as exc:
        raise UnauthorizedHTTPError("Access token has expired.") from exc
    except InvalidAccessTokenError as exc:
        raise UnauthorizedHTTPError("Invalid access token.") from exc

    user = await UserRepository().get_by_id(session, claims.sub)
    if user is None:
        raise UnauthorizedHTTPError("Invalid access token.")

    # Costs no extra round-trip: resolving "the authenticated user" already
    # requires this row. See User.token_version's docstring for why this
    # check exists even though nothing bumps the counter yet.
    if user.token_version != claims.token_version:
        raise UnauthorizedHTTPError("Access token has been revoked.")

    return user
