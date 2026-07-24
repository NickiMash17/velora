"""Unit tests for password hashing — pure Python, no DB."""

from __future__ import annotations

import pytest

from app.modules.identity.domain.errors import WeakPasswordError
from app.modules.identity.domain.passwords import (
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_correct_password_authenticates() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash) is True


def test_incorrect_password_fails() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("wrong password entirely", password_hash) is False


def test_hash_is_not_the_plaintext_password() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert password_hash != "correct horse battery staple"
    assert "correct horse battery staple" not in password_hash


def test_hash_uses_argon2id() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert password_hash.startswith("$argon2id$")


def test_same_password_hashes_differently_each_time() -> None:
    """Argon2id salts automatically — two hashes of the same password must
    never be equal, or a database leak would reveal which users share a
    password just by comparing hash strings."""
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert verify_password("correct horse battery staple", second)


@pytest.mark.parametrize("password", ["short", "1234567", ""])
def test_passwords_below_minimum_length_are_rejected(password: str) -> None:
    with pytest.raises(WeakPasswordError):
        validate_password_policy(password)


def test_password_at_minimum_length_is_accepted() -> None:
    validate_password_policy("12345678")  # exactly 8 chars — must not raise
