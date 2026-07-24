"""Unit tests for email normalization — pure Python, no DB."""

from __future__ import annotations

import pytest

from app.modules.identity.domain.email import normalize_email


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Foo@Example.com", "foo@example.com"),
        ("  foo@example.com  ", "foo@example.com"),
        ("FOO@EXAMPLE.COM", "foo@example.com"),
        ("foo@example.com", "foo@example.com"),
        ("\tfoo@example.com\n", "foo@example.com"),
    ],
)
def test_normalize_email(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected
