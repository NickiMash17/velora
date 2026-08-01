"""Access token (JWT) encode/decode, and opaque refresh token generation.

HS256, not RS256: the issuer and validator are the same process in this
modular monolith (there is no separate Gateway service yet — see
docs/architecture/Deployment.md §4) so a symmetric shared secret is
correct and simpler. RS256 earns its complexity only once a Gateway
needs to verify tokens without holding the signing secret; adopting it
now would be exactly the premature complexity AGENTS.md warns against.

Claims, per docs/architecture/Security.md §3.1: `sub`, `token_version`,
plus standard `iat`/`exp` — always present. `organization_id` and `role`
(singular: a token scopes to exactly one organization, and
`organization_memberships` has a UNIQUE(organization_id, user_id)
constraint, so there is exactly one role per org per user) are present
only once a session has been scoped to an organization (Milestone 4's
organization-creation/selection flow — see
app/modules/identity/application/services.py's `refresh_session`).
Omitted entirely when absent, per Security.md's explicit "claims are
simply absent, not null placeholders."
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

_JWT_ALGORITHM = "HS256"


class InvalidAccessTokenError(Exception):
    pass


class ExpiredAccessTokenError(Exception):
    pass


@dataclass
class AccessTokenClaims:
    sub: UUID
    token_version: int
    issued_at: datetime
    expires_at: datetime
    organization_id: UUID | None = None
    role: str | None = None


def issue_access_token(
    *,
    user_id: UUID,
    token_version: int,
    secret_key: str,
    ttl_minutes: int,
    organization_id: UUID | None = None,
    role: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "token_version": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    # Included only when present — Security.md: "claims are simply
    # absent, not null placeholders." Both are always set together
    # (organization_id implies role and vice versa); see refresh_session's
    # docstring for why they can never independently be None/not-None.
    if organization_id is not None:
        payload["organization_id"] = str(organization_id)
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, secret_key, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, *, secret_key: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessTokenError from exc

    try:
        organization_id_raw = payload.get("organization_id")
        return AccessTokenClaims(
            sub=UUID(payload["sub"]),
            token_version=payload["token_version"],
            issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            organization_id=UUID(organization_id_raw) if organization_id_raw else None,
            role=payload.get("role"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        # Well-formed JWT (valid signature) but missing/malformed claims —
        # treat identically to an invalid token rather than leaking which
        # part of validation failed.
        raise InvalidAccessTokenError from exc


def generate_refresh_token_secret() -> str:
    """A high-entropy opaque value — not a JWT. Nothing needs to inspect a
    refresh token's contents; it's a lookup key into `refresh_tokens`, so
    there's no reason to give it JWT structure."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(secret: str) -> str:
    """SHA-256, not Argon2id — see RefreshToken.token_hash's docstring in
    app/modules/identity/domain/entities.py for why a fast hash is
    correct here."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_family_id() -> UUID:
    return uuid.uuid4()
