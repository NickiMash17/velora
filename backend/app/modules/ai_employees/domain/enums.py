"""Enum types for the AI Employees domain.

`AiEmployeeStatus` backs the `ai_employee_status` Postgres ENUM
(`AIEmployees.md §3`: `draft` → `configured` → `active` ⇄ `paused` →
`retired`).

`AutonomyLevel` is **not** a database enum — locked decision 2: autonomy
is a flat jsonb map on `ai_employees.autonomy_defaults`
(`{skill_key: level}`), not a separate table or column type. This enum
exists purely to validate the *values* of that map at the application
layer (`AIEmployees.md §6`: "autonomous" / "notify" / "approve" — the
same three values `AutonomyDial` already uses, unchanged here).
"""

from __future__ import annotations

import enum


class AiEmployeeStatus(enum.StrEnum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class AutonomyLevel(enum.StrEnum):
    AUTONOMOUS = "autonomous"
    NOTIFY = "notify"
    APPROVE = "approve"
