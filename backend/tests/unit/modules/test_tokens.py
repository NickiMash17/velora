"""Unit tests for access-token (JWT) encode/decode and refresh-token
helpers — pure Python, no DB."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.modules.identity.infrastructure.tokens import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    decode_access_token,
    generate_refresh_token_secret,
    hash_refresh_token,
    issue_access_token,
)

_SECRET = "unit-test-secret-key-padded-to-at-least-32-bytes-long"


def test_issued_token_decodes_with_matching_claims() -> None:
    user_id = uuid.uuid4()
    token = issue_access_token(
        user_id=user_id, token_version=3, secret_key=_SECRET, ttl_minutes=15
    )

    claims = decode_access_token(token, secret_key=_SECRET)

    assert claims.sub == user_id
    assert claims.token_version == 3


def test_token_signed_with_a_different_secret_is_rejected() -> None:
    token = issue_access_token(
        user_id=uuid.uuid4(), token_version=0, secret_key=_SECRET, ttl_minutes=15
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key="a-completely-different-secret-also-32-bytes-plus")


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token("this-is-not-a-jwt-at-all", secret_key=_SECRET)


def test_expired_token_is_rejected() -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "token_version": 0,
        "iat": now - timedelta(minutes=30),
        "exp": now - timedelta(minutes=15),
    }
    expired_token = jwt.encode(expired_payload, _SECRET, algorithm="HS256")

    with pytest.raises(ExpiredAccessTokenError):
        decode_access_token(expired_token, secret_key=_SECRET)


def test_token_missing_required_claims_is_rejected() -> None:
    # Well-formed, correctly-signed JWT — just missing token_version.
    incomplete_payload = {"sub": str(uuid.uuid4())}
    token = jwt.encode(incomplete_payload, _SECRET, algorithm="HS256")

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key=_SECRET)


def test_refresh_token_secrets_are_unique() -> None:
    first = generate_refresh_token_secret()
    second = generate_refresh_token_secret()
    assert first != second


def test_refresh_token_hash_is_deterministic_and_not_the_secret() -> None:
    secret = generate_refresh_token_secret()
    assert hash_refresh_token(secret) == hash_refresh_token(secret)
    assert hash_refresh_token(secret) != secret
