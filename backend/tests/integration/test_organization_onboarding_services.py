"""Integration tests for the M4 organization-onboarding application
services: create-with-slug-retry and select. Real Postgres throughout."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application.services import authenticate_user
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.passwords import hash_password
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.identity.infrastructure.tokens import decode_access_token
from app.modules.organizations.application.services import (
    create_organization_for_user,
    create_organization_with_admin,
    select_organization,
)
from app.modules.organizations.domain.errors import MembershipNotFoundError
from app.modules.organizations.domain.slug import slugify
from app.shared.config import Settings

pytestmark = pytest.mark.integration

_PASSWORD = "a-strong-password"


def _unique_email() -> str:
    return f"onboarding-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"onboarding-{uuid.uuid4().hex[:10]}"


async def _create_user_and_login(
    db_session: AsyncSession, auth_settings: Settings
) -> tuple[User, str]:
    user = User(
        id=uuid.uuid4(), email=_unique_email(), password_hash=hash_password(_PASSWORD),
        mfa_enabled=False,
    )
    await UserRepository().create(db_session, user)
    await db_session.commit()
    tokens = await authenticate_user(
        db_session, auth_settings, email=user.email, password=_PASSWORD
    )
    return user, tokens.refresh_token


@pytest.mark.asyncio
async def test_create_organization_for_user_returns_a_scoped_token_pair(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user, refresh_token = await _create_user_and_login(db_session, auth_settings)

    result, tokens = await create_organization_for_user(
        db_session,
        auth_settings,
        name="Acme Inc",
        admin_user_id=user.id,
        refresh_token=refresh_token,
    )

    assert result.organization.name == "Acme Inc"
    assert result.membership.role.value == "org_admin"
    claims = decode_access_token(tokens.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id == result.organization.id
    assert claims.role == "org_admin"


@pytest.mark.asyncio
async def test_create_organization_for_user_never_exposes_a_slug_to_the_caller(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user, refresh_token = await _create_user_and_login(db_session, auth_settings)

    result, _ = await create_organization_for_user(
        db_session,
        auth_settings,
        name="Some Company",
        admin_user_id=user.id,
        refresh_token=refresh_token,
    )

    assert result.organization.slug == slugify("Some Company")


@pytest.mark.asyncio
async def test_create_organization_for_user_retries_on_slug_collision(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    admin_a = User(
        id=uuid.uuid4(), email=_unique_email(), password_hash=hash_password(_PASSWORD),
        mfa_enabled=False,
    )
    await UserRepository().create(db_session, admin_a)
    await db_session.commit()

    colliding_name = f"Acme {uuid.uuid4().hex[:6]}"
    colliding_slug = slugify(colliding_name)
    # Pre-occupy the slug this name would generate, via the lower-level
    # primitive directly (a legitimate use — see its own docstring).
    await create_organization_with_admin(
        db_session, name=colliding_name, slug=colliding_slug, admin_user_id=admin_a.id
    )

    user, refresh_token = await _create_user_and_login(db_session, auth_settings)

    result, tokens = await create_organization_for_user(
        db_session,
        auth_settings,
        name=colliding_name,
        admin_user_id=user.id,
        refresh_token=refresh_token,
    )

    assert result.organization.slug != colliding_slug
    assert result.organization.slug.startswith(colliding_slug)
    claims = decode_access_token(tokens.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id == result.organization.id


@pytest.mark.asyncio
async def test_select_organization_returns_a_scoped_token_for_an_active_member(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user, refresh_token = await _create_user_and_login(db_session, auth_settings)
    result = await create_organization_with_admin(
        db_session, name="Acme", slug=_unique_slug(), admin_user_id=user.id
    )

    tokens = await select_organization(
        db_session,
        auth_settings,
        user_id=user.id,
        organization_id=result.organization.id,
        refresh_token=refresh_token,
    )

    claims = decode_access_token(tokens.access_token, secret_key=auth_settings.jwt_secret_key)
    assert claims.organization_id == result.organization.id
    assert claims.role == "org_admin"


@pytest.mark.asyncio
async def test_select_organization_rejects_a_non_member(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    admin = User(
        id=uuid.uuid4(), email=_unique_email(), password_hash=hash_password(_PASSWORD),
        mfa_enabled=False,
    )
    await UserRepository().create(db_session, admin)
    await db_session.commit()
    org = await create_organization_with_admin(
        db_session, name="Acme", slug=_unique_slug(), admin_user_id=admin.id
    )

    outsider, outsider_refresh_token = await _create_user_and_login(db_session, auth_settings)

    with pytest.raises(MembershipNotFoundError):
        await select_organization(
            db_session,
            auth_settings,
            user_id=outsider.id,
            organization_id=org.organization.id,
            refresh_token=outsider_refresh_token,
        )


@pytest.mark.asyncio
async def test_select_organization_rejects_a_nonexistent_organization(
    db_session: AsyncSession, auth_settings: Settings
) -> None:
    user, refresh_token = await _create_user_and_login(db_session, auth_settings)

    with pytest.raises(MembershipNotFoundError):
        await select_organization(
            db_session,
            auth_settings,
            user_id=user.id,
            organization_id=uuid.uuid4(),
            refresh_token=refresh_token,
        )
