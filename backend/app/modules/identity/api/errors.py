"""Translates identity domain/infrastructure exceptions into the standard
API error envelope (app.shared.errors.AppError). This is the API
boundary's job specifically — domain/ and application/ raise plain
exceptions with no knowledge of HTTP status codes (see
app/modules/identity/domain/errors.py's module docstring).
"""

from __future__ import annotations

from fastapi import status

from app.shared.errors import AppError


class EmailAlreadyRegisteredHTTPError(AppError):
    code = "email_already_registered"
    status_code = status.HTTP_409_CONFLICT


class WeakPasswordHTTPError(AppError):
    code = "weak_password"
    status_code = status.HTTP_400_BAD_REQUEST


class InvalidCredentialsHTTPError(AppError):
    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidRefreshTokenHTTPError(AppError):
    code = "invalid_refresh_token"
    status_code = status.HTTP_401_UNAUTHORIZED


class UnauthorizedHTTPError(AppError):
    """Missing, malformed, expired, or otherwise invalid access token —
    one response shape for all of these, since the client's remedy is
    identical (re-authenticate or refresh)."""

    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED


class RateLimitedHTTPError(AppError):
    code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
