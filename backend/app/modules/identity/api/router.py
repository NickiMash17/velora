"""Identity API endpoints.

Endpoint shapes are an M3 decision, not something docs/architecture/API.md
specifies precisely enough to follow verbatim — see this milestone's
completion report. `POST /v1/users` (registration) and `GET /v1/users/me`
follow API.md's resource-oriented convention (creating/reading the users
resource); `POST /v1/auth/login` and `POST /v1/auth/refresh` are the one
conventionally-accepted exception to that (session/token actions, not
resource CRUD) — API.md §5 already accepts exactly one such exception
(the async task pattern) for the same reason: a standard REST-CRUD shape
doesn't fit, and inventing one would be worse than the established
convention of a small, named action endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.api.dependencies import get_current_user
from app.modules.identity.api.errors import (
    EmailAlreadyRegisteredHTTPError,
    InvalidCredentialsHTTPError,
    InvalidRefreshTokenHTTPError,
    RateLimitedHTTPError,
    WeakPasswordHTTPError,
)
from app.modules.identity.api.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.identity.application.services import (
    authenticate_user,
    refresh_session,
    register_user,
)
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    WeakPasswordError,
)
from app.shared.cache import get_redis_client
from app.shared.config import Settings, get_settings
from app.shared.db import get_db_session
from app.shared.rate_limit import RateLimitExceededError, check_and_increment

router = APIRouter(tags=["identity"])


def _to_user_response(user: User) -> UserResponse:
    # Explicit field-by-field construction, not response_model's implicit
    # attribute-reading conversion — User is a plain dataclass, not a
    # Pydantic model configured with from_attributes=True, and being
    # explicit here is also what makes "password_hash is never returned"
    # visibly true by inspection rather than by omission.
    if user.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database (register_user returns the post-flush entity;
        # get_current_user loads by id) — reaching this means a future
        # caller passed in a User that was never actually saved.
        raise RuntimeError("Cannot build a UserResponse for a User with no created_at.")
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    try:
        user = await register_user(session, email=body.email, password=body.password)
    except EmailAlreadyRegisteredError as exc:
        raise EmailAlreadyRegisteredHTTPError(str(exc)) from exc
    except WeakPasswordError as exc:
        raise WeakPasswordHTTPError(str(exc)) from exc
    return _to_user_response(user)


@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _to_user_response(current_user)


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
) -> TokenResponse:
    # Incremented before the credentials check, unconditionally, so
    # behavior is identical whether or not body.email corresponds to a
    # real account — see app/shared/rate_limit.py's module docstring.
    try:
        await check_and_increment(
            redis_client,
            key=f"ratelimit:login:{body.email.lower().strip()}",
            max_attempts=settings.login_rate_limit_max_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
    except RateLimitExceededError as exc:
        raise RateLimitedHTTPError(
            "Too many login attempts. Try again later.",
            details={"retry_after_seconds": exc.retry_after_seconds},
        ) from exc

    try:
        token_pair = await authenticate_user(
            session, settings, email=body.email, password=body.password
        )
    except InvalidCredentialsError as exc:
        raise InvalidCredentialsHTTPError(str(exc)) from exc

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        token_pair = await refresh_session(session, settings, refresh_token=body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise InvalidRefreshTokenHTTPError(str(exc)) from exc

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )
