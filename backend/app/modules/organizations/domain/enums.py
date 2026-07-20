"""Enum types for the organizations domain, matching
docs/architecture/Database.md §3.1 exactly — values are the literal lowercase
strings the documented schema specifies, since these back native Postgres
ENUM types in the Alembic migration."""

from __future__ import annotations

import enum


class PlanTier(enum.StrEnum):
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class IsolationTier(enum.StrEnum):
    POOL = "pool"
    SILO = "silo"


class Region(enum.StrEnum):
    US = "us"
    EU = "eu"
    APAC = "apac"


class OrganizationStatus(enum.StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNED = "churned"


class MembershipRole(enum.StrEnum):
    ORG_ADMIN = "org_admin"
    DEPARTMENT_MANAGER = "department_manager"
    MEMBER = "member"
    VIEWER = "viewer"


class MembershipStatus(enum.StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
