"""Unit tests for the AI Employees endpoints' role checks — pure Python,
no DB, no HTTP.

Same reasoning and `asyncio.run()` pattern as
test_department_authorization.py: M4 has no invite/accept-invite flow
yet, so no API path exists today to mint an organization-scoped session
with a role other than `org_admin`; these tests exercise the negative
cases directly against the router functions.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.modules.ai_employees.api.errors import AiEmployeeForbiddenHTTPError
from app.modules.ai_employees.api.router import (
    hire_ai_employee_endpoint,
    retire_ai_employee_endpoint,
)
from app.modules.ai_employees.api.schemas import HireAiEmployeeRequest
from app.modules.organizations.api.dependencies import OrganizationContext
from app.modules.organizations.domain.enums import MembershipRole


def test_viewer_cannot_hire_an_ai_employee() -> None:
    context = OrganizationContext(
        user=None,  # type: ignore[arg-type]
        organization_id=uuid.uuid4(),
        role=MembershipRole.VIEWER.value,
    )
    body = HireAiEmployeeRequest(
        department_id=uuid.uuid4(),
        template_id=uuid.uuid4(),
        name="Riley",
        role_title="Support Agent",
    )

    async def _call() -> None:
        await hire_ai_employee_endpoint(body, session=None, context=context)  # type: ignore[arg-type]

    with pytest.raises(AiEmployeeForbiddenHTTPError):
        asyncio.run(_call())


def test_department_manager_cannot_retire_an_ai_employee() -> None:
    """Retire is org_admin-only — stricter than hire/configure/activate/
    pause, which also allow department_manager."""
    context = OrganizationContext(
        user=None,  # type: ignore[arg-type]
        organization_id=uuid.uuid4(),
        role=MembershipRole.DEPARTMENT_MANAGER.value,
    )

    async def _call() -> None:
        await retire_ai_employee_endpoint(
            uuid.uuid4(), session=None, context=context  # type: ignore[arg-type]
        )

    with pytest.raises(AiEmployeeForbiddenHTTPError):
        asyncio.run(_call())
