"""Unit test for the Goals create-endpoint's role check — pure Python,
no DB, no HTTP.

Same reasoning and `asyncio.run()` pattern as
test_department_authorization.py/test_ai_employee_authorization.py: M4
has no invite/accept-invite flow yet, so no API path exists today to
mint an organization-scoped session with a role other than `org_admin`;
this test exercises the negative case directly against the router
function.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.modules.goals.api.errors import GoalForbiddenHTTPError
from app.modules.goals.api.router import propose_goal_endpoint
from app.modules.goals.api.schemas import CreateGoalRequest
from app.modules.organizations.api.dependencies import OrganizationContext
from app.modules.organizations.domain.enums import MembershipRole


def test_viewer_cannot_propose_a_goal() -> None:
    context = OrganizationContext(
        user=None,  # type: ignore[arg-type]
        organization_id=uuid.uuid4(),
        role=MembershipRole.VIEWER.value,
    )
    body = CreateGoalRequest(
        title="Reduce churn",
        success_metric={"metric": "churn_rate", "target": 0.05, "current": 0.08},
    )

    async def _call() -> None:
        await propose_goal_endpoint(body, session=None, context=context)  # type: ignore[arg-type]

    with pytest.raises(GoalForbiddenHTTPError):
        asyncio.run(_call())
