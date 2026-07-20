"""Unit tests for the organizations domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

import pytest

from app.modules.organizations.domain.entities import (
    InvalidSlugError,
    Organization,
    validate_slug,
)
from app.modules.organizations.domain.enums import (
    IsolationTier,
    OrganizationStatus,
    PlanTier,
    Region,
)


@pytest.mark.parametrize("slug", ["acme", "acme-inc", "a1", "my-company-123"])
def test_valid_slugs_pass(slug: str) -> None:
    assert validate_slug(slug) == slug


@pytest.mark.parametrize(
    "slug",
    [
        "Acme",  # uppercase
        "acme_inc",  # underscore
        "-acme",  # leading hyphen
        "acme-",  # trailing hyphen
        "",  # empty
        "a" * 64,  # too long
    ],
)
def test_invalid_slugs_are_rejected(slug: str) -> None:
    with pytest.raises(InvalidSlugError):
        validate_slug(slug)


def test_organization_construction_validates_slug() -> None:
    with pytest.raises(InvalidSlugError):
        Organization(
            id=uuid.uuid4(),
            name="Acme",
            slug="Not A Valid Slug",
            plan_tier=PlanTier.TRIAL,
            isolation_tier=IsolationTier.POOL,
            region=Region.US,
            status=OrganizationStatus.TRIAL,
        )
