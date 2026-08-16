"""Integration tests for the M5 Checkpoint 1 departments API — real
Postgres + Redis via the shared app_client fixture, same pattern
established for organizations' endpoints in M4.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"dept-api-{uuid.uuid4().hex[:10]}@example.com"


async def _register_login_and_create_org(app_client: httpx.AsyncClient) -> dict:
    """Returns an org_admin-scoped token pair for a brand-new organization."""
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


@pytest.mark.asyncio
async def test_create_department_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/departments", json={"name": "Support", "function_type": "support"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_department_succeeds_for_org_admin(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Support", "function_type": "support", "budget_cents_monthly": 100_000},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Support"
    assert body["function_type"] == "support"
    assert body["budget_cents_monthly"] == 100_000
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_department_omits_optional_budget(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Sales", "function_type": "sales"},
    )

    assert response.status_code == 201
    assert response.json()["budget_cents_monthly"] is None


@pytest.mark.asyncio
async def test_create_department_rejects_invalid_function_type(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Support", "function_type": "not_a_real_function_type"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_department_requires_organization_context(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    response = await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"name": "Support", "function_type": "support"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_organization_context"


@pytest.mark.asyncio
async def test_get_department_returns_the_created_department(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Finance", "function_type": "finance"},
    )
    department_id = create.json()["id"]

    response = await app_client.get(
        f"/v1/departments/{department_id}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == department_id
    assert response.json()["name"] == "Finance"


@pytest.mark.asyncio
async def test_get_department_returns_404_for_unknown_id(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(
        f"/v1/departments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "department_not_found"


@pytest.mark.asyncio
async def test_list_departments_reflects_created_departments(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Ops", "function_type": "ops"},
    )
    await app_client.post(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Marketing", "function_type": "marketing"},
    )

    response = await app_client.get(
        "/v1/departments",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["name"] for item in body["items"]} == {"Ops", "Marketing"}
    assert body["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_departments_paginates_with_next_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    for name in ["Ops", "Finance", "Marketing"]:
        await app_client.post(
            "/v1/departments",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"name": name, "function_type": "ops"},
        )

    first_page = await app_client.get(
        "/v1/departments?limit=2",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = await app_client.get(
        f"/v1/departments?limit=2&cursor={first_body['next_cursor']}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 1
    assert second_body["next_cursor"] is None

    all_names = {item["name"] for item in first_body["items"] + second_body["items"]}
    assert all_names == {"Ops", "Finance", "Marketing"}


@pytest.mark.asyncio
async def test_list_departments_rejects_invalid_cursor(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(
        "/v1/departments?cursor=not-a-valid-cursor",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_cursor"
