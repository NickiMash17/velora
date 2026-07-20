"""Unit tests for the event catalog registry — pure Python, no DB."""

from __future__ import annotations

import pytest

from app.modules.events.domain.catalog import (
    MEMBERSHIP_ACTIVATED,
    ORGANIZATION_CREATED,
    topic_for,
)


def test_organization_created_maps_to_documented_topic() -> None:
    assert topic_for(ORGANIZATION_CREATED) == "organization.created"


def test_membership_activated_maps_to_documented_topic() -> None:
    assert topic_for(MEMBERSHIP_ACTIVATED) == "membership.activated"


def test_uncataloged_event_type_raises() -> None:
    with pytest.raises(ValueError, match="not a cataloged event type"):
        topic_for("SomethingNobodyDocumented")
