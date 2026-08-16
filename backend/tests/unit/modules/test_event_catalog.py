"""Unit tests for the event catalog registry — pure Python, no DB."""

from __future__ import annotations

import pytest

from app.modules.events.domain.catalog import (
    COMPANY_DNA_COMPILED,
    COMPANY_DNA_DRAFT_CREATED,
    COMPANY_DNA_PUBLISHED,
    DEPARTMENT_CREATED,
    EMPLOYEE_ACTIVATED,
    EMPLOYEE_CONFIGURED,
    EMPLOYEE_HIRED,
    EMPLOYEE_PAUSED,
    EMPLOYEE_RETIRED,
    MEMBERSHIP_ACTIVATED,
    ORGANIZATION_CREATED,
    topic_for,
)


def test_organization_created_maps_to_documented_topic() -> None:
    assert topic_for(ORGANIZATION_CREATED) == "organization.created"


def test_membership_activated_maps_to_documented_topic() -> None:
    assert topic_for(MEMBERSHIP_ACTIVATED) == "membership.activated"


def test_department_created_maps_to_documented_topic() -> None:
    assert topic_for(DEPARTMENT_CREATED) == "department.created"


def test_company_dna_draft_created_maps_to_documented_topic() -> None:
    assert topic_for(COMPANY_DNA_DRAFT_CREATED) == "company_dna.draft_created"


def test_company_dna_compiled_maps_to_documented_topic() -> None:
    assert topic_for(COMPANY_DNA_COMPILED) == "company_dna.compiled"


def test_company_dna_published_maps_to_documented_topic() -> None:
    assert topic_for(COMPANY_DNA_PUBLISHED) == "company_dna.published"


def test_employee_hired_maps_to_documented_topic() -> None:
    assert topic_for(EMPLOYEE_HIRED) == "employee.hired"


def test_employee_configured_maps_to_documented_topic() -> None:
    assert topic_for(EMPLOYEE_CONFIGURED) == "employee.configured"


def test_employee_activated_maps_to_documented_topic() -> None:
    assert topic_for(EMPLOYEE_ACTIVATED) == "employee.activated"


def test_employee_paused_maps_to_documented_topic() -> None:
    assert topic_for(EMPLOYEE_PAUSED) == "employee.paused"


def test_employee_retired_maps_to_documented_topic() -> None:
    assert topic_for(EMPLOYEE_RETIRED) == "employee.retired"


def test_uncataloged_event_type_raises() -> None:
    with pytest.raises(ValueError, match="not a cataloged event type"):
        topic_for("SomethingNobodyDocumented")
