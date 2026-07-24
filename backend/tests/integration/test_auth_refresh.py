"""Integration tests for the refresh-token lifecycle — validation,
expiration, rotation, and replay-detected family revocation. Real
Postgres throughout; expiry is exercised by backdating the persisted
row directly (there's no clock injection point, and there shouldn't be
one just for this)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import update

from app.modules.identity.infrastructure.orm import RefreshTokenORM
from app.modules.identity.infrastructure.tokens import hash_refresh_token

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"refresh-{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_login(app_client: httpx.AsyncClient) -> dict:
    email = _unique_email()
    password = "a-strong-password"
    register_response = await app_client.post(
        "/v1/users", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201

    login_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    assert login_response.status_code == 200
    return login_response.json()


@pytest.mark.asyncio
async def test_valid_refresh_token_issues_a_new_token_pair(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_and_login(app_client)

    response = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_invalid_refresh_token_is_rejected(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected(
    app_client: httpx.AsyncClient, db_session
) -> None:
    tokens = await _register_and_login(app_client)
    token_hash = hash_refresh_token(tokens["refresh_token"])

    await db_session.execute(
        update(RefreshTokenORM)
        .where(RefreshTokenORM.token_hash == token_hash)
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    await db_session.commit()

    response = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_rotation_makes_the_old_refresh_token_unusable(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_and_login(app_client)

    first_refresh = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first_refresh.status_code == 200

    replay_of_old_token = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert replay_of_old_token.status_code == 401
    assert replay_of_old_token.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_replaying_a_rotated_token_revokes_the_whole_family(
    app_client: httpx.AsyncClient,
) -> None:
    """Reusing a token that's already been rotated is treated as theft:
    the entire rotation chain (including the newest, otherwise-still-valid
    token) must be revoked, not just the replayed one."""
    tokens = await _register_and_login(app_client)

    rotated = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert rotated.status_code == 200
    newest_refresh_token = rotated.json()["refresh_token"]

    replay = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401

    newest_token_after_replay = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": newest_refresh_token}
    )

    assert newest_token_after_replay.status_code == 401
    assert newest_token_after_replay.json()["error"]["code"] == "invalid_refresh_token"
