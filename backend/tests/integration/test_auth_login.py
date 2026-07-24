"""Integration tests for login and the authenticated-user dependency —
real Postgres, real Redis (login rate limiting shares the same fixture,
but attempt volume here always stays under auth_settings' threshold; see
test_auth_rate_limit.py for the limiter itself).
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from app.modules.identity.infrastructure.tokens import issue_access_token
from app.shared.config import Settings

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"login-{uuid.uuid4().hex[:10]}@example.com"


async def _register(app_client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await app_client.post("/v1/users", json={"email": email, "password": password})
    assert response.status_code == 201
    return str(response.json()["id"])


@pytest.mark.asyncio
async def test_successful_login_returns_access_and_refresh_tokens(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    email = _unique_email()
    password = "a-strong-password"
    await _register(app_client, email, password)

    response = await app_client.post("/v1/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == auth_settings.access_token_ttl_minutes * 60


@pytest.mark.asyncio
async def test_wrong_password_is_rejected(app_client: httpx.AsyncClient) -> None:
    email = _unique_email()
    await _register(app_client, email, "the-correct-password")

    response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": "the-wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_nonexistent_account_gets_identical_error_to_wrong_password(
    app_client: httpx.AsyncClient,
) -> None:
    """Login must not reveal whether an email is registered — a
    nonexistent account and a real account with the wrong password have
    to produce the same status code and error body."""
    real_email = _unique_email()
    await _register(app_client, real_email, "the-correct-password")

    wrong_password_response = await app_client.post(
        "/v1/auth/login", json={"email": real_email, "password": "the-wrong-password"}
    )
    nonexistent_response = await app_client.post(
        "/v1/auth/login",
        json={"email": _unique_email(), "password": "whatever-password"},
    )

    assert wrong_password_response.status_code == nonexistent_response.status_code == 401
    assert (
        wrong_password_response.json()["error"]["code"]
        == nonexistent_response.json()["error"]["code"]
        == "invalid_credentials"
    )


@pytest.mark.asyncio
async def test_access_token_resolves_the_authenticated_user(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    password = "a-strong-password"
    user_id = await _register(app_client, email, password)

    login_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    access_token = login_response.json()["access_token"]

    me_response = await app_client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert me_response.status_code == 200
    body = me_response.json()
    assert body["id"] == user_id
    assert body["email"] == email


@pytest.mark.asyncio
async def test_missing_access_token_is_rejected(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_malformed_access_token_is_rejected(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get(
        "/v1/users/me", headers={"Authorization": "Bearer this-is-not-a-jwt"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    email = _unique_email()
    user_id = await _register(app_client, email, "a-strong-password")

    expired_token = issue_access_token(
        user_id=uuid.UUID(user_id),
        token_version=0,
        secret_key=auth_settings.jwt_secret_key,
        ttl_minutes=-1,
    )

    response = await app_client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_access_token_signed_with_a_different_secret_is_rejected(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    user_id = await _register(app_client, email, "a-strong-password")

    forged_token = issue_access_token(
        user_id=uuid.UUID(user_id),
        token_version=0,
        secret_key="a-completely-different-secret-also-32-bytes-plus",
        ttl_minutes=15,
    )

    response = await app_client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {forged_token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
