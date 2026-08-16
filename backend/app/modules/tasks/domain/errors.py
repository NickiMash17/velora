"""Domain-level Task errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/tasks/api/router.py), not here.
"""

from __future__ import annotations

from uuid import UUID


class TaskNotFoundError(Exception):
    pass


class AssignedUserNotFoundError(Exception):
    """Raised when `assigned_user_id` is provided but no such user
    exists. Checks only that the user row exists (identity.UserRepository),
    not that they're an active member of this organization — the same
    existence-only depth already used for department_id/template_id in
    departments/ai_employees, not a new validation pattern."""


class TaskIdempotencyConflictError(Exception):
    """Raised when the same (organization_id, idempotency_key) pair is
    submitted twice — API.md §5's idempotency guarantee: a network retry
    must not create a duplicate task. Carries the id of the
    already-existing task so the caller can look it up rather than
    silently losing track of it."""

    def __init__(self, existing_task_id: UUID) -> None:
        super().__init__(
            f"A task with this idempotency key already exists: '{existing_task_id}'."
        )
        self.existing_task_id = existing_task_id
