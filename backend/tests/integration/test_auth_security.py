"""Security-focused integration tests for the M3 auth flow:

- No credentials/tokens leak into API responses beyond what login/refresh
  are supposed to return.
- No plaintext passwords or issued tokens appear in structured logs.
- The identity/auth code path — which never sets tenant context, since
  neither `users` nor `refresh_tokens` is tenant-scoped — does not weaken
  or bypass RLS on the tables that ARE tenant-scoped (organizations,
  organization_memberships).

Existing M2 tenant-isolation tests (tests/isolation/) are left completely
unmodified; this file does not duplicate them, it only proves the M3
identity code path doesn't regress what they already cover.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.infrastructure.orm import OrganizationORM
from app.shared.config import Settings
from app.shared.logging import configure_logging

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"security-{uuid.uuid4().hex[:10]}@example.com"


@pytest.mark.asyncio
async def test_login_response_never_contains_a_password_field(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    password = "a-strong-password-that-must-never-round-trip"
    await app_client.post("/v1/users", json={"email": email, "password": password})

    response = await app_client.post("/v1/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert password not in response.text


@pytest.mark.asyncio
async def test_no_plaintext_password_or_issued_tokens_appear_in_logs(
    app_client: httpx.AsyncClient,
    auth_settings: Settings,
    capfd: pytest.CaptureFixture[str],
) -> None:
    # capfd, not capsys: structlog's PrintLogger caches the logger object
    # it first writes through (cache_logger_on_first_use) for the rest of
    # the process — capsys replaces the `sys.stdout` *object*, which that
    # cached logger would then hold a now-closed reference to for every
    # later test. capfd instead redirects the underlying OS file
    # descriptor, so the same live `sys.stdout` object structlog cached
    # keeps working after this test ends.
    configure_logging(auth_settings)

    email = _unique_email()
    password = "a-password-that-must-never-appear-in-a-log-line"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    tokens = login_response.json()

    refresh_response = await app_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    rotated_tokens = refresh_response.json()

    captured = capfd.readouterr()
    log_output = captured.out

    assert password not in log_output
    assert tokens["access_token"] not in log_output
    assert tokens["refresh_token"] not in log_output
    assert rotated_tokens["access_token"] not in log_output
    assert rotated_tokens["refresh_token"] not in log_output


@pytest.mark.asyncio
async def test_auth_flow_does_not_weaken_rls_on_tenant_scoped_tables(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Runs a full register/login/refresh cycle (the identity module's
    entire surface area) on the same real Postgres the RLS-protected
    `organizations` table lives in, then confirms an unfiltered,
    no-tenant-context query against it still returns nothing — proving
    the auth code path, which never touches app.current_org_id, has no
    side effect on RLS enforcement for tables it doesn't own."""
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login_response = await app_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    tokens = login_response.json()
    await app_client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    await app_client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    result = await db_session.execute(
        text(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname = 'organizations'"
        )
    )
    row = result.one()
    assert row.relrowsecurity is True
    assert row.relforcerowsecurity is True

    # No app.current_org_id ever set on this connection/transaction —
    # fail-closed RLS means zero visible rows, regardless of how many
    # organizations exist from other tests.
    orgs = (await db_session.execute(select(OrganizationORM))).scalars().all()
    assert orgs == []
