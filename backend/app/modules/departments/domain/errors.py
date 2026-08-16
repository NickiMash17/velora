"""Domain-level department errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/departments/api/router.py), not here.
"""

from __future__ import annotations


class DepartmentNotFoundError(Exception):
    pass
