"""Pure domain entity for CompanyDnaVersion.

No SQLAlchemy, no FastAPI imports — per
docs/engineering/EngineeringStandards.md §2.1, this layer must be testable
without any infrastructure at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus


@dataclass
class CompanyDnaVersion:
    id: UUID
    organization_id: UUID
    version: str
    status: CompanyDnaVersionStatus
    compiled_summary: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
