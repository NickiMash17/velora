"""Integration tests for the M5 Checkpoint 2 Company DNA API — real
Postgres + Redis via the shared app_client fixture, same pattern
established for departments' endpoints in Checkpoint 1.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"dna-api-{uuid.uuid4().hex[:10]}@example.com"


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


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_create_dna_version_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post("/v1/company-dna/versions", json={"version": "1.0.0"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_dna_version_succeeds_for_org_admin(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["version"] == "1.0.0"
    assert body["status"] == "draft"
    assert body["compiled_summary"] is None
    assert body["published_at"] is None


@pytest.mark.asyncio
async def test_create_dna_version_rejects_duplicate_version(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )

    response = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "company_dna_version_conflict"


@pytest.mark.asyncio
async def test_update_compiled_summary_succeeds_while_draft(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )
    version_id = create.json()["id"]

    response = await app_client.patch(
        f"/v1/company-dna/versions/{version_id}",
        headers=_auth(tokens),
        json={"compiled_summary": "We are helpful and concise."},
    )

    assert response.status_code == 200
    assert response.json()["compiled_summary"] == "We are helpful and concise."


@pytest.mark.asyncio
async def test_update_compiled_summary_returns_404_for_unknown_id(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.patch(
        f"/v1/company-dna/versions/{uuid.uuid4()}",
        headers=_auth(tokens),
        json={"compiled_summary": "anything"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "company_dna_version_not_found"


async def _create_and_finalize(app_client: httpx.AsyncClient, tokens: dict, version: str) -> str:
    create = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": version}
    )
    version_id = create.json()["id"]
    await app_client.patch(
        f"/v1/company-dna/versions/{version_id}",
        headers=_auth(tokens),
        json={"compiled_summary": f"content for {version}"},
    )
    finalize = await app_client.post(
        f"/v1/company-dna/versions/{version_id}/finalize", headers=_auth(tokens)
    )
    assert finalize.status_code == 200
    return version_id


@pytest.mark.asyncio
async def test_finalize_rejects_empty_compiled_summary(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )
    version_id = create.json()["id"]

    response = await app_client.post(
        f"/v1/company-dna/versions/{version_id}/finalize", headers=_auth(tokens)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "empty_compiled_summary"


@pytest.mark.asyncio
async def test_finalize_succeeds_and_sets_status(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    version_id = await _create_and_finalize(app_client, tokens, "1.0.0")

    detail = await app_client.get("/v1/company-dna/versions", headers=_auth(tokens))
    item = next(i for i in detail.json()["items"] if i["id"] == version_id)
    assert item["status"] == "finalized"


@pytest.mark.asyncio
async def test_finalize_rejects_already_finalized_version(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    version_id = await _create_and_finalize(app_client, tokens, "1.0.0")

    response = await app_client.post(
        f"/v1/company-dna/versions/{version_id}/finalize", headers=_auth(tokens)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_company_dna_transition"


@pytest.mark.asyncio
async def test_publish_rejects_a_draft_version(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    create = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )
    version_id = create.json()["id"]

    response = await app_client.post(
        f"/v1/company-dna/versions/{version_id}/publish", headers=_auth(tokens)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_company_dna_transition"


@pytest.mark.asyncio
async def test_publish_succeeds_for_a_finalized_version(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)
    version_id = await _create_and_finalize(app_client, tokens, "1.0.0")

    response = await app_client.post(
        f"/v1/company-dna/versions/{version_id}/publish", headers=_auth(tokens)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["published_at"] is not None


@pytest.mark.asyncio
async def test_current_returns_404_when_nothing_published(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get("/v1/company-dna/versions/current", headers=_auth(tokens))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_published_company_dna_version"


@pytest.mark.asyncio
async def test_current_returns_the_published_version_after_publish(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    version_id = await _create_and_finalize(app_client, tokens, "1.0.0")
    await app_client.post(
        f"/v1/company-dna/versions/{version_id}/publish", headers=_auth(tokens)
    )

    response = await app_client.get("/v1/company-dna/versions/current", headers=_auth(tokens))

    assert response.status_code == 200
    assert response.json()["id"] == version_id


@pytest.mark.asyncio
async def test_current_reflects_the_newest_publish_after_a_second_one(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    first_id = await _create_and_finalize(app_client, tokens, "1.0.0")
    await app_client.post(f"/v1/company-dna/versions/{first_id}/publish", headers=_auth(tokens))

    second_id = await _create_and_finalize(app_client, tokens, "2.0.0")
    await app_client.post(f"/v1/company-dna/versions/{second_id}/publish", headers=_auth(tokens))

    response = await app_client.get("/v1/company-dna/versions/current", headers=_auth(tokens))
    assert response.json()["id"] == second_id


@pytest.mark.asyncio
async def test_list_dna_versions_paginates_with_next_cursor(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    for version in ["1.0.0", "1.1.0", "1.2.0"]:
        await app_client.post(
            "/v1/company-dna/versions", headers=_auth(tokens), json={"version": version}
        )

    first_page = await app_client.get(
        "/v1/company-dna/versions?limit=2", headers=_auth(tokens)
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = await app_client.get(
        f"/v1/company-dna/versions?limit=2&cursor={first_body['next_cursor']}",
        headers=_auth(tokens),
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 1
    assert second_body["next_cursor"] is None

    all_versions = {i["version"] for i in first_body["items"] + second_body["items"]}
    assert all_versions == {"1.0.0", "1.1.0", "1.2.0"}


@pytest.mark.asyncio
async def test_create_dna_version_requires_organization_context(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    response = await app_client.post(
        "/v1/company-dna/versions",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"version": "1.0.0"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_organization_context"
