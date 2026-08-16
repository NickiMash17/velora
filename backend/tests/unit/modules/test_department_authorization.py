"""Unit test for the departments create-endpoint's role check — pure
Python, no DB, no HTTP.

M4 has no invite/accept-invite flow yet, so no API path exists today to
mint an organization-scoped session with a role other than `org_admin`
(the founding admin is always `org_admin` — see
organizations/application/services.py's create_organization_with_admin).
The positive case (an org_admin session succeeds) is covered end-to-end
in tests/integration/test_departments_api.py; this test exercises the
negative case directly against the router function, since there is no
way to reach it any other way in this milestone.

Deliberately driven via a plain, synchronous `asyncio.run()` rather than
an `async def` test function: this is the only async test anywhere under
tests/unit, and this suite's session-scoped event loop
(`asyncio_default_test_loop_scope = "session"`, pyproject.toml) is
otherwise established by the DB-backed fixtures in tests/integration and
tests/isolation. A no-fixture async unit test picked up by
pytest-asyncio's `asyncio_mode = "auto"` before any of those fixtures run
was found to corrupt that shared loop on Windows
(`WindowsProactorEventLoopPolicy`) — reproduced directly during this
checkpoint's verification. Running this coroutine through its own
throwaway loop instead keeps this test fully decoupled from that shared
session-loop machinery, matching what a "pure Python, no DB" unit test
should need in the first place.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.modules.departments.api.errors import DepartmentForbiddenHTTPError
from app.modules.departments.api.router import create_department_endpoint
from app.modules.departments.api.schemas import CreateDepartmentRequest
from app.modules.departments.domain.enums import FunctionType
from app.modules.organizations.api.dependencies import OrganizationContext
from app.modules.organizations.domain.enums import MembershipRole


def test_non_org_admin_role_is_rejected_before_touching_the_database() -> None:
    context = OrganizationContext(
        user=None,  # type: ignore[arg-type]  # unused before the role check fires
        organization_id=uuid.uuid4(),
        role=MembershipRole.MEMBER.value,
    )
    body = CreateDepartmentRequest(name="Support", function_type=FunctionType.SUPPORT)

    async def _call() -> None:
        await create_department_endpoint(body, session=None, context=context)  # type: ignore[arg-type]

    with pytest.raises(DepartmentForbiddenHTTPError):
        asyncio.run(_call())
