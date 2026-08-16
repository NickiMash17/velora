"""Enum type for the departments domain, matching
docs/architecture/Database.md §3.2 exactly — values are the literal
lowercase strings the documented schema specifies, since these back a
native Postgres ENUM type in the Alembic migration."""

from __future__ import annotations

import enum


class FunctionType(enum.StrEnum):
    SALES = "sales"
    SUPPORT = "support"
    FINANCE = "finance"
    MARKETING = "marketing"
    OPS = "ops"
    CUSTOM = "custom"
