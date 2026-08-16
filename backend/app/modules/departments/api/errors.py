"""Translates departments domain/infrastructure exceptions into the
standard API error envelope (app.shared.errors.AppError) — the API
boundary's job specifically, matching organizations/api/errors.py's own
module docstring for why this translation doesn't happen in domain/ or
application/.
"""

from __future__ import annotations

from fastapi import status

from app.shared.errors import AppError


class DepartmentNotFoundHTTPError(AppError):
    code = "department_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class DepartmentForbiddenHTTPError(AppError):
    """The caller is authenticated and organization-scoped, but their role
    does not permit this action — distinct from unauthorized (401)."""

    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN


class InvalidCursorHTTPError(AppError):
    code = "invalid_cursor"
    status_code = status.HTTP_400_BAD_REQUEST
