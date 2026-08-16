"""Domain-level AI Employees errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/ai_employees/api/router.py), not here.
"""

from __future__ import annotations


class AiEmployeeNotFoundError(Exception):
    pass


class AiEmployeeTemplateNotFoundError(Exception):
    pass


class InvalidAiEmployeeTransitionError(Exception):
    """Raised when a transition is attempted from a status that doesn't
    permit it — e.g. activating a `draft` employee (must be `configured`
    or `paused` first), or configuring one that isn't `draft`."""


class MissingConfigurationError(Exception):
    """Raised when `configure` is attempted without both a Company DNA
    version and a permission scope. AIEmployees.md §3's hard rule: "A
    Digital Employee cannot skip `configured` — a Digital Employee
    without a bound DNA version and an explicit permission scope cannot
    be activated." Enforced here, at the Provisioning-equivalent service
    layer, not left to UI validation, per that same rule."""
