"""Unit test for the Company DNA create-endpoint's role check — pure
Python, no DB, no HTTP.

Same reasoning and same `asyncio.run()` pattern as
test_department_authorization.py: M4 has no invite/accept-invite flow
yet, so no API path exists today to mint an organization-scoped session
with a role other than `org_admin`; this test exercises the negative case
directly against the router function. Driven via a plain, synchronous
`asyncio.run()` rather than an `async def` test — see
test_department_authorization.py's docstring for why a no-fixture async
unit test picked up by pytest-asyncio's session-scoped loop is unsafe on
Windows in this suite.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.modules.company_dna.api.errors import CompanyDnaForbiddenHTTPError
from app.modules.company_dna.api.router import create_dna_version
from app.modules.company_dna.api.schemas import CreateDnaVersionRequest
from app.modules.organizations.api.dependencies import OrganizationContext
from app.modules.organizations.domain.enums import MembershipRole


def test_non_org_admin_role_is_rejected_before_touching_the_database() -> None:
    context = OrganizationContext(
        user=None,  # type: ignore[arg-type]  # unused before the role check fires
        organization_id=uuid.uuid4(),
        role=MembershipRole.MEMBER.value,
    )
    body = CreateDnaVersionRequest(version="1.0.0")

    async def _call() -> None:
        await create_dna_version(body, session=None, context=context)  # type: ignore[arg-type]

    with pytest.raises(CompanyDnaForbiddenHTTPError):
        asyncio.run(_call())
