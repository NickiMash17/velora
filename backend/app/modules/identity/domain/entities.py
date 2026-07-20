"""Pure domain entity for User.

Deliberately has no `organization_id` — a User is not tenant-scoped data.
Per docs/architecture/Database.md §3.1, a user may belong to multiple
organizations via separate OrganizationMembership rows; tenancy is a
property of the membership, not the identity.
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
    created_at: datetime | None = None
    updated_at: datetime | None = None
