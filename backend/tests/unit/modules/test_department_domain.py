"""Unit tests for the departments domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

from app.modules.departments.domain.entities import Department
from app.modules.departments.domain.enums import FunctionType


def test_function_type_values_match_database_md() -> None:
    """docs/architecture/Database.md §3.2:
    function_type enum(sales, support, finance, marketing, ops, custom)."""
    assert {member.value for member in FunctionType} == {
        "sales",
        "support",
        "finance",
        "marketing",
        "ops",
        "custom",
    }


def test_department_constructs_with_optional_budget_defaulting_to_none() -> None:
    department = Department(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Support",
        function_type=FunctionType.SUPPORT,
    )
    assert department.budget_cents_monthly is None
    assert department.created_at is None
    assert department.updated_at is None


def test_department_constructs_with_explicit_budget() -> None:
    department = Department(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Sales",
        function_type=FunctionType.SALES,
        budget_cents_monthly=500_000,
    )
    assert department.budget_cents_monthly == 500_000
