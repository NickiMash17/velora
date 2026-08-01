"""Translates organizations domain/infrastructure exceptions into the
standard API error envelope (app.shared.errors.AppError) — the API
boundary's job specifically, matching identity/api/errors.py's own
module docstring for why this translation doesn't happen in domain/ or
application/.
"""

from __future__ import annotations

from fastapi import status

from app.shared.errors import AppError


class OrganizationNotFoundHTTPError(AppError):
    code = "organization_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class MembershipNotFoundHTTPError(AppError):
    """Covers both 'no such organization' and 'not a member of it' —
    deliberately the same response for both, matching
    MembershipNotFoundError's own docstring."""

    code = "organization_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class NoOrganizationContextHTTPError(AppError):
    """The caller's access token is valid but not scoped to any
    organization — distinct from unauthorized (401): the caller IS
    authenticated, they just haven't created or selected an organization
    yet. The frontend uses this specifically to decide whether to show
    onboarding or the org-switch list."""

    code = "no_organization_context"
    status_code = status.HTTP_404_NOT_FOUND
