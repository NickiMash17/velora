"""Pure domain entities for User and RefreshToken.

Deliberately have no `organization_id` — neither is tenant-scoped data.
Per docs/architecture/Database.md §3.1, a user may belong to multiple
organizations via separate OrganizationMembership rows; tenancy is a
property of the membership, not the identity, and a refresh token belongs
to the identity that holds it, not to any tenant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str | None
    mfa_enabled: bool
    # Bumped whenever all of a user's outstanding access tokens must be
    # invalidated immediately (e.g. a future password-change flow) —
    # Security.md §3.1 documents this as an access-token claim. Nothing in
    # M3 triggers a bump yet (no such feature exists), but the field, the
    # claim, and the validation path are real and tested: resolving "the
    # authenticated user" already requires loading this row, so comparing
    # token_version costs no extra round-trip.
    token_version: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class RefreshToken:
    id: UUID
    user_id: UUID
    # SHA-256 of the actual opaque token secret — not Argon2id. A refresh
    # token is a high-entropy random value the server itself generated
    # (unlike a password, which is low-entropy and human-chosen), so a
    # fast cryptographic hash is the correct tool here: it protects
    # against exposure if the `refresh_tokens` table is ever dumped,
    # which is the only real threat model for a value with this much
    # entropy — a slow/memory-hard KDF would add cost with no benefit.
    token_hash: str
    # Groups every token produced by a chain of rotations. Reused across
    # rotations so reuse of an already-rotated (dead) token can be
    # detected and the whole family revoked — see
    # app/modules/identity/application/services.py's refresh_session.
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None
    # Points at the token that replaced this one, for audit purposes —
    # not used in any authorization decision.
    replaced_by_id: UUID | None = None
    issued_at: datetime | None = None
