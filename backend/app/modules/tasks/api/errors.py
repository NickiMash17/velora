"""Translates Tasks domain/infrastructure exceptions into the standard
API error envelope (app.shared.errors.AppError) — the API boundary's job
specifically, matching organizations/api/errors.py's own module
docstring for why this translation doesn't happen in domain/ or
application/.
"""

from __future__ import annotations

from fastapi import status

from app.shared.errors import AppError


class TaskNotFoundHTTPError(AppError):
    code = "task_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class AssignedUserNotFoundHTTPError(AppError):
    code = "assigned_user_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class TaskIdempotencyConflictHTTPError(AppError):
    """API.md §5's idempotency guarantee: a network retry must not create
    a duplicate task. The conflicting task's id is included in `details`
    so the caller can look it up via `GET /work-items/{id}` — the
    response follows this codebase's uniform error envelope rather than
    returning the original resource's body directly on a 4xx status,
    which no other endpoint here does either."""

    code = "task_idempotency_conflict"
    status_code = status.HTTP_409_CONFLICT


class InvalidCursorHTTPError(AppError):
    code = "invalid_cursor"
    status_code = status.HTTP_400_BAD_REQUEST
