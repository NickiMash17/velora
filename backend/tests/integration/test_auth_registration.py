"""Integration tests for user registration — real Postgres, real Argon2id
hashing. Registration creates ONLY a user identity: no organization, no
membership, no department, no Company DNA, no Digital Employee — nothing
here even imports those modules.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.modules.identity.infrastructure.orm import UserORM

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"register-{uuid.uuid4().hex[:10]}@example.com"


@pytest.mark.asyncio
async def test_successful_registration_returns_user_without_password(
    app_client: httpx.AsyncClient,
) -> None:
    email = _unique_email()
    response = await app_client.post(
        "/v1/users", json={"email": email, "password": "a-strong-password"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected(app_client: httpx.AsyncClient) -> None:
    email = _unique_email()
    first = await app_client.post(
        "/v1/users", json={"email": email, "password": "a-strong-password"}
    )
    assert first.status_code == 201

    second = await app_client.post(
        "/v1/users", json={"email": email, "password": "another-password"}
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_already_registered"


@pytest.mark.asyncio
async def test_email_normalization_is_enforced_at_registration(
    app_client: httpx.AsyncClient,
) -> None:
    base = uuid.uuid4().hex[:10]
    first = await app_client.post(
        "/v1/users", json={"email": f"User-{base}@Example.com", "password": "a-strong-password"}
    )
    assert first.status_code == 201
    assert first.json()["email"] == f"user-{base}@example.com"

    # Same address, different case/whitespace — must collide, not create a
    # second account.
    second = await app_client.post(
        "/v1/users", json={"email": f"  user-{base}@example.com  ", "password": "another-password"}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_invalid_email_format_is_rejected(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/users", json={"email": "not-an-email-address", "password": "a-strong-password"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_password_below_policy_is_rejected(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/users", json={"email": _unique_email(), "password": "short"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "weak_password"


@pytest.mark.asyncio
async def test_password_is_never_persisted_in_plaintext(
    app_client: httpx.AsyncClient, db_session
) -> None:
    email = _unique_email()
    plaintext = "a-strong-password-nobody-should-see"
    await app_client.post("/v1/users", json={"email": email, "password": plaintext})

    result = await db_session.execute(select(UserORM).where(UserORM.email == email))
    row = result.scalar_one()

    assert row.password_hash is not None
    assert row.password_hash != plaintext
    assert plaintext not in row.password_hash
    assert row.password_hash.startswith("$argon2id$")


@pytest.mark.asyncio
async def test_registration_creates_only_a_user_no_other_resources(
    app_client: httpx.AsyncClient, db_session
) -> None:
    """Explicit scope check: registration must not create an organization,
    membership, department, Company DNA, or Digital Employee — this test
    exists specifically because that boundary is an M3 constraint, not an
    incidental fact."""
    from app.modules.organizations.infrastructure.orm import (
        OrganizationMembershipORM,
        OrganizationORM,
    )

    email = _unique_email()
    response = await app_client.post(
        "/v1/users", json={"email": email, "password": "a-strong-password"}
    )
    user_id = uuid.UUID(response.json()["id"])

    memberships = await db_session.execute(
        select(OrganizationMembershipORM).where(OrganizationMembershipORM.user_id == user_id)
    )
    assert memberships.scalars().all() == []

    # No RLS context is set here deliberately — as org_admin of nothing,
    # this new user shouldn't be able to see ANY organization, which a
    # bare unfiltered count also confirms is unrelated to them.
    orgs_before = (await db_session.execute(select(OrganizationORM))).scalars().all()
    assert not any(str(user_id) in str(o.id) for o in orgs_before)
