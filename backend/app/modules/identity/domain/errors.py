"""Domain-level authentication errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/identity/api/router.py), not here.
"""

from __future__ import annotations


class EmailAlreadyRegisteredError(Exception):
    pass


class WeakPasswordError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Raised for both 'no such account' and 'wrong password' — the two
    cases must be indistinguishable to the caller (Security.md's login
    requirements: never reveal whether an email exists)."""


class InvalidRefreshTokenError(Exception):
    """Raised for missing, expired, revoked, or replayed refresh tokens —
    the client's remedy is identical in every case (log in again), so
    these aren't distinguished at the exception level either."""
