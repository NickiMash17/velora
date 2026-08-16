"""Integration tests for the M5 Checkpoint 4 Goals API — real Postgres +
Redis via the shared app_client fixture, same pattern established for
departments/company-dna/ai-employees' endpoints in Checkpoints 1-3.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration

_METRIC = {"metric": "churn_rate", "target": 0.05, "current": 0.08}


def _unique_email() -> str:
    return f"goal-api-{uuid.uuid4().hex[:10]}@example.com"


async def _register_login_and_create_org(app_client: httpx.AsyncClient) -> dict:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": login["refresh_token"]},
    )
    return create.json()["tokens"]


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_propose_goal_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/goals", json={"title": "Reduce churn", "success_metric": _METRIC}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_propose_goal_succeeds_for_org_admin(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/goals",
        headers=_auth(tokens),
        json={"title": "Reduce churn by 10%", "success_metric": _METRIC},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Reduce churn by 10%"
    assert body["status"] == "proposed"
    assert body["success_metric"] == _METRIC
    assert body["department_id"] is None


@pytest.mark.asyncio
async def test_propose_goal_with_a_department(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    department = await app_client.post(
        "/v1/departments",
        headers=_auth(tokens),
        json={"name": "Support", "function_type": "support"},
    )
    department_id = department.json()["id"]

    response = await app_client.post(
        "/v1/goals",
        headers=_auth(tokens),
        json={
            "title": "Reduce escalations",
            "success_metric": _METRIC,
            "department_id": department_id,
        },
    )

    assert response.status_code == 201
    assert response.json()["department_id"] == department_id


@pytest.mark.asyncio
async def test_propose_goal_requires_organization_context(app_client: httpx.AsyncClient) -> None:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    response = await app_client.post(
        "/v1/goals",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"title": "Reduce churn", "success_metric": _METRIC},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_organization_context"


async def _propose(app_client: httpx.AsyncClient, tokens: dict, title: str = "Reduce churn") -> str:
    response = await app_client.post(
        "/v1/goals", headers=_auth(tokens), json={"title": title, "success_metric": _METRIC}
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_activate_goal_succeeds(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    goal_id = await _propose(app_client, tokens)

    response = await app_client.post(f"/v1/goals/{goal_id}/activate", headers=_auth(tokens))

    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_activate_goal_rejects_already_active(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    goal_id = await _propose(app_client, tokens)
    await app_client.post(f"/v1/goals/{goal_id}/activate", headers=_auth(tokens))

    response = await app_client.post(f"/v1/goals/{goal_id}/activate", headers=_auth(tokens))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_goal_transition"


@pytest.mark.asyncio
async def test_activate_goal_returns_404_for_unknown_id(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        f"/v1/goals/{uuid.uuid4()}/activate", headers=_auth(tokens)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "goal_not_found"


@pytest.mark.asyncio
async def test_get_goal_returns_the_created_goal(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    goal_id = await _propose(app_client, tokens, title="Improve NPS")

    response = await app_client.get(f"/v1/goals/{goal_id}", headers=_auth(tokens))

    assert response.status_code == 200
    assert response.json()["title"] == "Improve NPS"


@pytest.mark.asyncio
async def test_get_goal_returns_404_for_unknown_id(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(f"/v1/goals/{uuid.uuid4()}", headers=_auth(tokens))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "goal_not_found"


@pytest.mark.asyncio
async def test_list_goals_filters_by_department(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    department = await app_client.post(
        "/v1/departments",
        headers=_auth(tokens),
        json={"name": "Sales", "function_type": "sales"},
    )
    department_id = department.json()["id"]

    await app_client.post(
        "/v1/goals",
        headers=_auth(tokens),
        json={
            "title": "Dept goal",
            "success_metric": _METRIC,
            "department_id": department_id,
        },
    )
    await _propose(app_client, tokens, title="Org-wide goal")

    response = await app_client.get(
        f"/v1/goals?department_id={department_id}", headers=_auth(tokens)
    )

    assert response.status_code == 200
    assert [i["title"] for i in response.json()["items"]] == ["Dept goal"]


@pytest.mark.asyncio
async def test_list_goals_paginates_with_next_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    for title in ["Goal 1", "Goal 2", "Goal 3"]:
        await _propose(app_client, tokens, title=title)

    first_page = await app_client.get("/v1/goals?limit=2", headers=_auth(tokens))
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = await app_client.get(
        f"/v1/goals?limit=2&cursor={first_body['next_cursor']}", headers=_auth(tokens)
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 1
    assert second_body["next_cursor"] is None

    all_titles = {i["title"] for i in first_body["items"] + second_body["items"]}
    assert all_titles == {"Goal 1", "Goal 2", "Goal 3"}


@pytest.mark.asyncio
async def test_list_goals_rejects_invalid_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(
        "/v1/goals?cursor=not-a-valid-cursor", headers=_auth(tokens)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_cursor"


@pytest.mark.asyncio
async def test_no_abandon_at_risk_or_achieve_endpoints_exist(
    app_client: httpx.AsyncClient,
) -> None:
    """Regression guard, per instruction: proves Finding 2's boundary
    stays exactly `proposed -> active`, not silently widened later."""
    tokens = await _register_login_and_create_org(app_client)
    goal_id = await _propose(app_client, tokens)

    for action in ["abandon", "achieve", "mark-at-risk"]:
        response = await app_client.post(
            f"/v1/goals/{goal_id}/{action}", headers=_auth(tokens)
        )
        assert response.status_code == 404
