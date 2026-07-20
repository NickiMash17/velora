"""Pure domain entities for Organization and OrganizationMembership.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.organizations.domain.enums import (
    IsolationTier,
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
    PlanTier,
    Region,
)

# Database.md §3.1 documents `slug` as "used for subdomain routing" but
# doesn't specify a format — DNS label rules (lowercase alphanumeric,
# internal hyphens only) are the real-world constraint that fact implies,
# so validating it here isn't inventing a field, it's enforcing the one
# that's already documented against what it actually has to be valid for.
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class InvalidSlugError(ValueError):
    pass


def validate_slug(slug: str) -> str:
    if not _SLUG_PATTERN.match(slug):
        raise InvalidSlugError(
            f"'{slug}' is not a valid organization slug — must be lowercase "
            "alphanumeric with internal hyphens only (DNS label rules), "
            "since it's used for subdomain routing."
        )
    return slug


@dataclass
class Organization:
    id: UUID
    name: str
    slug: str
    plan_tier: PlanTier
    isolation_tier: IsolationTier
    region: Region
    status: OrganizationStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        validate_slug(self.slug)


@dataclass
class OrganizationMembership:
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: MembershipRole
    status: MembershipStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
