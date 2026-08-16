"""Domain-level Goal errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/goals/api/router.py), not here.
"""

from __future__ import annotations


class GoalNotFoundError(Exception):
    pass


class InvalidGoalTransitionError(Exception):
    """Raised when a transition is attempted from a status that doesn't
    permit it — in M5, the only case is activating a Goal that isn't
    `proposed` (Finding 2: no other transition is reachable at all)."""
