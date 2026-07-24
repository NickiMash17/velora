"""Authentication use cases: register, login (issue tokens), refresh.

Each function owns its own transaction boundary (`async with
session.begin():`), consistent with
app/modules/organizations/application/services.py's pattern from
Milestone 2 — neither `users` nor `refresh_tokens` is tenant-scoped, so
no tenant context needs establishing here, unlike that module's use of
tenant_scoped_transaction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.email import normalize_email
from app.modules.identity.domain.entities import RefreshToken, User
from app.modules.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.identity.domain.passwords import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.modules.identity.infrastructure.repository import RefreshTokenRepository, UserRepository
from app.modules.identity.infrastructure.tokens import (
    generate_refresh_token_secret,
    hash_refresh_token,
    issue_access_token,
    new_family_id,
)
from app.shared.config import Settings


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    user_repo: UserRepository | None = None,
) -> User:
    user_repo = user_repo or UserRepository()
    normalized = normalize_email(email)

    validate_password_policy(password)

    async with session.begin():
        existing = await user_repo.get_by_email(session, normalized)
        if existing is not None:
            raise EmailAlreadyRegisteredError(f"'{normalized}' is already registered.")

        user = User(
            id=uuid.uuid4(),
            email=normalized,
            password_hash=hash_password(password),
            mfa_enabled=False,
            token_version=0,
        )
        return await user_repo.create(session, user)


async def _issue_token_pair_for_user(
    session: AsyncSession,
    settings: Settings,
    user: User,
    refresh_token_repo: RefreshTokenRepository,
    *,
    family_id: uuid.UUID,
) -> tuple[TokenPair, uuid.UUID]:
    """Returns the token pair alongside the new refresh token row's id —
    callers rotating an existing token need that id to record what it was
    replaced by (see refresh_session); a fresh login has no prior token
    to link, so it just discards the second element."""
    access_token = issue_access_token(
        user_id=user.id,
        token_version=user.token_version,
        secret_key=settings.jwt_secret_key,
        ttl_minutes=settings.access_token_ttl_minutes,
    )

    refresh_secret = generate_refresh_token_secret()
    new_token_id = uuid.uuid4()
    refresh_token = RefreshToken(
        id=new_token_id,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_secret),
        family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
    )
    await refresh_token_repo.create(session, refresh_token)

    token_pair = TokenPair(
        access_token=access_token,
        refresh_token=refresh_secret,
        expires_in=settings.access_token_ttl_minutes * 60,
    )
    return token_pair, new_token_id


async def authenticate_user(
    session: AsyncSession,
    settings: Settings,
    *,
    email: str,
    password: str,
    user_repo: UserRepository | None = None,
    refresh_token_repo: RefreshTokenRepository | None = None,
) -> TokenPair:
    """Rate limiting happens at the API boundary (before this is called),
    per app/shared/rate_limit.py — that's what keeps its behavior
    identical regardless of whether `email` corresponds to a real
    account. This function's own job is only "do the credentials check
    ever reveal existence" — and it doesn't: both a missing user and a
    wrong password raise the identical InvalidCredentialsError."""
    user_repo = user_repo or UserRepository()
    refresh_token_repo = refresh_token_repo or RefreshTokenRepository()
    normalized = normalize_email(email)

    async with session.begin():
        user = await user_repo.get_by_email(session, normalized)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password.")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        token_pair, _ = await _issue_token_pair_for_user(
            session, settings, user, refresh_token_repo, family_id=new_family_id()
        )
        return token_pair


async def refresh_session(
    session: AsyncSession,
    settings: Settings,
    *,
    refresh_token: str,
    user_repo: UserRepository | None = None,
    refresh_token_repo: RefreshTokenRepository | None = None,
) -> TokenPair:
    """Rotation + replay protection: presenting a token that was already
    rotated (revoked_at set) revokes its entire family and rejects the
    request — reuse of a dead token is the signal a refresh token has
    been stolen, per this milestone's documented decision (Security.md
    doesn't specify a lifecycle precisely enough to leave this unstated).
    """
    user_repo = user_repo or UserRepository()
    refresh_token_repo = refresh_token_repo or RefreshTokenRepository()
    token_hash = hash_refresh_token(refresh_token)

    # Replay detection needs its revocation to actually persist even
    # though the request is then rejected — raising *inside* the same
    # `session.begin()` block that performed the revoke would roll the
    # revoke back too, since an exception exiting that block is exactly
    # what triggers its rollback. So the replayed-token case sets a flag
    # and lets the block commit normally; the error is only raised once
    # that commit has already happened.
    replay_detected = False

    async with session.begin():
        existing = await refresh_token_repo.get_by_hash(session, token_hash)
        if existing is None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if existing.revoked_at is not None:
            await refresh_token_repo.revoke_family(session, existing.family_id)
            replay_detected = True
        else:
            if existing.expires_at < datetime.now(UTC):
                raise InvalidRefreshTokenError("Refresh token has expired.")

            user = await user_repo.get_by_id(session, existing.user_id)
            if user is None:
                raise InvalidRefreshTokenError("Invalid refresh token.")

            token_pair, new_token_id = await _issue_token_pair_for_user(
                session,
                settings,
                user,
                refresh_token_repo,
                family_id=existing.family_id,
            )
            await refresh_token_repo.mark_rotated(session, existing.id, new_token_id)

    if replay_detected:
        raise InvalidRefreshTokenError("Refresh token has already been used.")

    return token_pair
