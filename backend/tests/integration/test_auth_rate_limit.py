"""Integration tests for login rate limiting — real Redis. Keyed on
normalized email only (app/shared/rate_limit.py, app.shared.cache), with
no tenant dimension, per this milestone's scope.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from app.shared.config import Settings

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"ratelimit-{uuid.uuid4().hex[:10]}@example.com"


@pytest.mark.asyncio
async def test_login_attempts_are_rate_limited_after_the_configured_max(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    email = _unique_email()

    # No account needs to exist — the limiter increments unconditionally,
    # before any credentials check (see check_and_increment's docstring).
    for _ in range(auth_settings.login_rate_limit_max_attempts):
        response = await app_client.post(
            "/v1/auth/login", json={"email": email, "password": "whatever"}
        )
        assert response.status_code == 401

    limited_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": "whatever"}
    )

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_rate_limit_response_includes_retry_after(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    email = _unique_email()
    for _ in range(auth_settings.login_rate_limit_max_attempts):
        await app_client.post("/v1/auth/login", json={"email": email, "password": "whatever"})

    limited_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": "whatever"}
    )

    assert limited_response.status_code == 429
    details = limited_response.json()["error"]["details"]
    assert details["retry_after_seconds"] > 0


@pytest.mark.asyncio
async def test_rate_limiting_does_not_leak_account_existence(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    """A real account and a nonexistent one must hit the same limit after
    the same number of attempts — the counter can't be shaped by whether
    the email actually corresponds to a user."""
    real_email = _unique_email()
    await app_client.post(
        "/v1/users", json={"email": real_email, "password": "a-strong-password"}
    )
    nonexistent_email = _unique_email()

    for _ in range(auth_settings.login_rate_limit_max_attempts):
        real_response = await app_client.post(
            "/v1/auth/login", json={"email": real_email, "password": "wrong-password"}
        )
        nonexistent_response = await app_client.post(
            "/v1/auth/login", json={"email": nonexistent_email, "password": "wrong-password"}
        )
        assert real_response.status_code == nonexistent_response.status_code == 401

    real_limited = await app_client.post(
        "/v1/auth/login", json={"email": real_email, "password": "wrong-password"}
    )
    nonexistent_limited = await app_client.post(
        "/v1/auth/login", json={"email": nonexistent_email, "password": "wrong-password"}
    )

    assert real_limited.status_code == nonexistent_limited.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_is_scoped_per_email(
    app_client: httpx.AsyncClient, auth_settings: Settings
) -> None:
    exhausted_email = _unique_email()
    for _ in range(auth_settings.login_rate_limit_max_attempts):
        await app_client.post(
            "/v1/auth/login", json={"email": exhausted_email, "password": "whatever"}
        )
    exhausted_response = await app_client.post(
        "/v1/auth/login", json={"email": exhausted_email, "password": "whatever"}
    )
    assert exhausted_response.status_code == 429

    other_email = _unique_email()
    unaffected_response = await app_client.post(
        "/v1/auth/login", json={"email": other_email, "password": "whatever"}
    )
    assert unaffected_response.status_code == 401
