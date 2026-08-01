"""Unit tests for slug generation — pure Python, no DB."""

from __future__ import annotations

from app.modules.organizations.domain.entities import validate_slug
from app.modules.organizations.domain.slug import slug_with_suffix, slugify


def test_slugify_lowercases_and_hyphenates() -> None:
    assert slugify("Acme Inc.") == "acme-inc"


def test_slugify_strips_leading_and_trailing_punctuation() -> None:
    assert slugify("  --Acme!!--  ") == "acme"


def test_slugify_collapses_multiple_separators() -> None:
    assert slugify("Acme   &   Co.") == "acme-co"


def test_slugify_falls_back_when_no_usable_characters() -> None:
    assert slugify("!!!") == "organization"


def test_slugify_result_is_always_a_valid_slug() -> None:
    validate_slug(slugify("Acme Inc."))
    validate_slug(slugify("!!!"))
    validate_slug(slugify("a" * 200))


def test_slug_with_suffix_is_still_a_valid_slug() -> None:
    base = slugify("Acme Inc.")
    validate_slug(slug_with_suffix(base))


def test_slug_with_suffix_differs_from_base_and_itself() -> None:
    base = slugify("Acme Inc.")
    first = slug_with_suffix(base)
    second = slug_with_suffix(base)
    assert first != base
    assert first != second


def test_slug_with_suffix_stays_within_length_limit_for_long_names() -> None:
    base = slugify("a" * 200)
    validate_slug(slug_with_suffix(base))
