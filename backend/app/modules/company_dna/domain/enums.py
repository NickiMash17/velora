"""Enum type for the Company DNA domain — locked decision A2 (M5 Step 2
Domain Contract): `draft` → `finalized` → `published` → `archived`."""

from __future__ import annotations

import enum


class CompanyDnaVersionStatus(enum.StrEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    PUBLISHED = "published"
    ARCHIVED = "archived"
