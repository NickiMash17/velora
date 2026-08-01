"""Integration tests proving refresh_session correctly carries an
organization/role scope across rotation — the bug flagged during M4
planning: without this, any org-scoped session silently downgrades to
org-less on its very next refresh (~15 minutes), since `refresh_tokens`
previously had nowhere to store that scope at all.

Exercises app.modules.identity.application.services directly (real
Postgres via db_session) rather than through HTTP, since the M4 API
endpoints that call refresh_session with an override (organization
creation/selection) are a separate module built later in this milestone
— this test is about refresh_session's own contract, independent of who
calls it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application.services import authenticate_user, refresh_session
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.passwords import hash_password
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.identity.infrastructure.tokens import decode_access_token
from app.modules.organizations.application.services import create_organization_with_admin
from app.shared.config import Settings

pytestmark = pytest.mark.integration

_PASSWORD = "a-strong-password"


def _unique_email() -> str:
    return f"org-scoped-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"org-scoped-{uuid.uuid4().hex[:10]}"


async def _create_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=_unique_email(),
        password_hash=hash_password(_PASSWORD),
        mfa_enabled=False,
    )
    await UserRepository().create(db_session, user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_login_always_issues_an_organization_less_token(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user = await _create_user(db_session)

    tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )

    claims = decode_access_token(tokens.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id is None
    assert claims.role is None


@pytest.mark.asyncio
async def test_refresh_with_no_override_preserves_organization_less_scope(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user = await _create_user(db_session)
    login_tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )

    refreshed = await refresh_session(
        db_session, auth_settings, refresh_token=login_tokens.refresh_token
    )

    claims = decode_access_token(refreshed.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id is None
    assert claims.role is None


@pytest.mark.asyncio
async def test_refresh_with_an_override_scopes_the_new_token(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user = await _create_user(db_session)
    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=user.id
    )
    login_tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )

    scoped = await refresh_session(
        db_session,
        auth_settings,
        refresh_token=login_tokens.refresh_token,
        organization_id=result.organization.id,
        role="org_admin",
    )

    claims = decode_access_token(scoped.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id == result.organization.id
    assert claims.role == "org_admin"


@pytest.mark.asyncio
async def test_subsequent_refresh_with_no_override_preserves_the_scope_just_set(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    """The regression this whole feature exists to prevent: once a
    session has been scoped to an organization, an ordinary refresh (no
    override — exactly what POST /v1/auth/refresh does) must NOT drop
    back to organization-less."""
    user = await _create_user(db_session)
    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=user.id
    )
    login_tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )
    scoped = await refresh_session(
        db_session,
        auth_settings,
        refresh_token=login_tokens.refresh_token,
        organization_id=result.organization.id,
        role="org_admin",
    )

    rotated_again = await refresh_session(
        db_session, auth_settings, refresh_token=scoped.refresh_token
    )

    claims = decode_access_token(
        rotated_again.access_token, secret_key=auth_settings.jwt_secret_key
    )
    assert claims.organization_id == result.organization.id
    assert claims.role == "org_admin"


@pytest.mark.asyncio
async def test_refresh_can_switch_the_override_to_a_different_organization(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user = await _create_user(db_session)
    first_org = await create_organization_with_admin(
        db_session, name="First Org", slug=_unique_slug(), admin_user_id=user.id
    )
    second_org = await create_organization_with_admin(
        db_session, name="Second Org", slug=_unique_slug(), admin_user_id=user.id
    )
    login_tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )
    scoped_to_first = await refresh_session(
        db_session,
        auth_settings,
        refresh_token=login_tokens.refresh_token,
        organization_id=first_org.organization.id,
        role="org_admin",
    )

    switched = await refresh_session(
        db_session,
        auth_settings,
        refresh_token=scoped_to_first.refresh_token,
        organization_id=second_org.organization.id,
        role="org_admin",
    )

    claims = decode_access_token(switched.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id == second_org.organization.id
