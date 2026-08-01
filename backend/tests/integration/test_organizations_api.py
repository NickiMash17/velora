"""Integration tests for the M4 organizations API — real Postgres +
Redis via the shared app_client fixture (app.dependency_overrides), same
pattern established for identity's endpoints in M3.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"org-api-{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_login(app_client: httpx.AsyncClient) -> dict:
    email = _unique_email()
    password = "a-strong-password"
    register = await app_client.post("/v1/users", json={"email": email, "password": password})
    assert register.status_code == 201
    login = await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()


@pytest.mark.asyncio
async def test_list_organizations_is_empty_for_a_new_user(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.get(
        "/v1/organizations", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_organizations_me_is_404_before_any_organization_exists(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.get(
        "/v1/organizations/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_organization_context"


@pytest.mark.asyncio
async def test_organizations_me_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/organizations/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_create_organization_returns_the_organization_and_a_scoped_token_pair(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["organization"]["name"] == "Acme Inc."
    assert "slug" in body["organization"]
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_create_organization_never_exposes_a_user_supplied_slug_field(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    # No `slug` field accepted — an extra field is simply ignored, not an
    # error (FastAPI/Pydantic's default), proving the API surface is
    # name-only regardless of what a client sends.
    response = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "name": "Acme Inc.",
            "slug": "attacker-chosen-slug",
            "refresh_token": tokens["refresh_token"],
        },
    )

    assert response.status_code == 201
    assert response.json()["organization"]["slug"] != "attacker-chosen-slug"


@pytest.mark.asyncio
async def test_create_organization_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/organizations", json={"name": "Acme", "refresh_token": "irrelevant"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_organization_rejects_an_invalid_refresh_token(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": "not-a-real-refresh-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_organizations_me_and_list_reflect_the_organization_just_created(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)
    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": tokens["refresh_token"]},
    )
    scoped_access = create.json()["tokens"]["access_token"]
    organization_id = create.json()["organization"]["id"]

    me = await app_client.get(
        "/v1/organizations/me", headers={"Authorization": f"Bearer {scoped_access}"}
    )
    assert me.status_code == 200
    assert me.json()["organization"]["id"] == organization_id
    assert me.json()["role"] == "org_admin"

    listed = await app_client.get(
        "/v1/organizations", headers={"Authorization": f"Bearer {scoped_access}"}
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["organization"]["id"] == organization_id
    assert listed.json()[0]["role"] == "org_admin"


@pytest.mark.asyncio
async def test_refreshing_an_organization_scoped_session_preserves_the_scope(
    app_client: httpx.AsyncClient,
) -> None:
    """The exact regression this milestone's planning flagged: refreshing
    must not silently downgrade an org-scoped session back to org-less."""
    tokens = await _register_and_login(app_client)
    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": tokens["refresh_token"]},
    )
    scoped_refresh = create.json()["tokens"]["refresh_token"]
    organization_id = create.json()["organization"]["id"]

    refreshed = await app_client.post("/v1/auth/refresh", json={"refresh_token": scoped_refresh})
    assert refreshed.status_code == 200

    me = await app_client.get(
        "/v1/organizations/me",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["organization"]["id"] == organization_id


@pytest.mark.asyncio
async def test_select_organization_for_a_returning_user(app_client: httpx.AsyncClient) -> None:
    """The realistic repeat-visit path: login always issues an org-less
    token (unchanged M3 behavior), so a returning user who already has an
    organization must be able to explicitly select back into it."""
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    first_login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()
    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {first_login['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": first_login["refresh_token"]},
    )
    organization_id = create.json()["organization"]["id"]

    # Simulates a brand-new session on a later visit — a fresh, org-less
    # token pair for the same already-a-member user.
    second_login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    response = await app_client.post(
        f"/v1/organizations/{organization_id}/select",
        headers={"Authorization": f"Bearer {second_login['access_token']}"},
        json={"refresh_token": second_login["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["organization"]["id"] == organization_id
    assert body["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_select_organization_rejects_a_non_member(app_client: httpx.AsyncClient) -> None:
    owner_tokens = await _register_and_login(app_client)
    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {owner_tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": owner_tokens["refresh_token"]},
    )
    organization_id = create.json()["organization"]["id"]

    outsider_tokens = await _register_and_login(app_client)

    response = await app_client.post(
        f"/v1/organizations/{organization_id}/select",
        headers={"Authorization": f"Bearer {outsider_tokens['access_token']}"},
        json={"refresh_token": outsider_tokens["refresh_token"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"


@pytest.mark.asyncio
async def test_select_organization_rejects_a_nonexistent_organization(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.post(
        f"/v1/organizations/{uuid.uuid4()}/select",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"


@pytest.mark.asyncio
async def test_replaying_an_already_rotated_refresh_token_against_select_is_rejected(
    app_client: httpx.AsyncClient,
) -> None:
    """Reproduces the exact gap found during manual smoke testing: a
    stale (already-rotated-away) refresh token passed to /select must
    come back as a clean 401 invalid_refresh_token, not an unhandled
    500."""
    tokens = await _register_and_login(app_client)
    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": tokens["refresh_token"]},
    )
    organization_id = create.json()["organization"]["id"]

    # tokens["refresh_token"] was already rotated away by the create call
    # above — replaying it here must be rejected cleanly.
    response = await app_client.post(
        f"/v1/organizations/{organization_id}/select",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"
