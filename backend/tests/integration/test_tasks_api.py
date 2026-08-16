"""Integration tests for the M5 Checkpoint 5 Tasks (work-items) API — real
Postgres + Redis via the shared app_client fixture, same pattern
established for departments/company-dna/ai-employees/goals' endpoints in
Checkpoints 1-4.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"task-api-{uuid.uuid4().hex[:10]}@example.com"


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
async def test_create_work_item_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post("/v1/work-items", json={"idempotency_key": "k-1"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_work_item_succeeds_for_any_active_member(
    app_client: httpx.AsyncClient,
) -> None:
    """No role restriction — unlike departments/goals/ai-employees, any
    active member can create a Task (the Claimant Resolution's "humans may
    create tasks")."""
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": "k-2"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["goal_id"] is None
    assert body["assigned_ai_employee_id"] is None
    assert body["assigned_user_id"] is None
    assert body["blocked_reason"] is None
    assert body["retry_count"] == 0


@pytest.mark.asyncio
async def test_create_work_item_with_a_goal(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    goal = await app_client.post(
        "/v1/goals",
        headers=_auth(tokens),
        json={
            "title": "Reduce churn",
            "success_metric": {"metric": "churn_rate", "target": 0.05, "current": 0.08},
        },
    )
    goal_id = goal.json()["id"]

    response = await app_client.post(
        "/v1/work-items",
        headers=_auth(tokens),
        json={"idempotency_key": "k-3", "goal_id": goal_id},
    )

    assert response.status_code == 201
    assert response.json()["goal_id"] == goal_id


@pytest.mark.asyncio
async def test_create_work_item_returns_404_for_unknown_goal(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/work-items",
        headers=_auth(tokens),
        json={"idempotency_key": "k-4", "goal_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "goal_not_found"


@pytest.mark.asyncio
async def test_create_work_item_returns_404_for_unknown_assigned_user(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/work-items",
        headers=_auth(tokens),
        json={"idempotency_key": "k-5", "assigned_user_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "assigned_user_not_found"


@pytest.mark.asyncio
async def test_create_work_item_rejects_a_repeated_idempotency_key(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    first = await app_client.post(
        "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": "dup-key"}
    )
    assert first.status_code == 201

    response = await app_client.post(
        "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": "dup-key"}
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "task_idempotency_conflict"
    assert body["error"]["details"]["task_id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_create_work_item_requires_organization_context(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    response = await app_client.post(
        "/v1/work-items",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"idempotency_key": "k-6"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_organization_context"


@pytest.mark.asyncio
async def test_get_work_item_returns_the_created_task(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": "k-7"}
    )
    task_id = create.json()["id"]

    response = await app_client.get(f"/v1/work-items/{task_id}", headers=_auth(tokens))

    assert response.status_code == 200
    assert response.json()["id"] == task_id


@pytest.mark.asyncio
async def test_get_work_item_returns_404_for_unknown_id(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(f"/v1/work-items/{uuid.uuid4()}", headers=_auth(tokens))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "task_not_found"


@pytest.mark.asyncio
async def test_list_work_items_paginates_with_next_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    for key in ["l-1", "l-2", "l-3"]:
        await app_client.post(
            "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": key}
        )

    first_page = await app_client.get("/v1/work-items?limit=2", headers=_auth(tokens))
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = await app_client.get(
        f"/v1/work-items?limit=2&cursor={first_body['next_cursor']}", headers=_auth(tokens)
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 1
    assert second_body["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_work_items_rejects_invalid_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(
        "/v1/work-items?cursor=not-a-valid-cursor", headers=_auth(tokens)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_cursor"


@pytest.mark.asyncio
async def test_deferred_task_endpoints_do_not_exist(app_client: httpx.AsyncClient) -> None:
    """Regression guard, per instruction: proves Finding 3's deferral
    stays deferred, not silently re-added later. Also guards against
    /v1/tasks (the unrelated generic async-invocation trigger, decision 3)
    ever being confused with the work-items resource."""
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/work-items", headers=_auth(tokens), json={"idempotency_key": "deferred-check"}
    )
    task_id = create.json()["id"]

    for path in [
        f"/v1/work-items/{task_id}/claim",
        f"/v1/work-items/{task_id}/block",
        f"/v1/work-items/{task_id}/complete",
        f"/v1/work-items/{task_id}/fail",
        f"/v1/work-items/{task_id}/approve",
        f"/v1/work-items/{task_id}/reject",
    ]:
        response = await app_client.post(path, headers=_auth(tokens))
        assert response.status_code == 404, f"{path} unexpectedly exists"

    approvals_response = await app_client.get("/v1/approvals", headers=_auth(tokens))
    assert approvals_response.status_code == 404
