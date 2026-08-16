"""Unit tests for the Company DNA domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

from app.modules.company_dna.domain.entities import CompanyDnaVersion
from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus


def test_status_values_match_locked_decision_a2() -> None:
    """Locked decision A2: draft -> finalized -> published -> archived."""
    assert {member.value for member in CompanyDnaVersionStatus} == {
        "draft",
        "finalized",
        "published",
        "archived",
    }


def test_company_dna_version_constructs_with_defaults() -> None:
    dna_version = CompanyDnaVersion(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        version="1.0.0",
        status=CompanyDnaVersionStatus.DRAFT,
    )
    assert dna_version.compiled_summary is None
    assert dna_version.published_at is None
    assert dna_version.created_at is None


def test_company_dna_version_constructs_with_explicit_fields() -> None:
    dna_version = CompanyDnaVersion(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        version="2.1.0",
        status=CompanyDnaVersionStatus.FINALIZED,
        compiled_summary="We are helpful and concise.",
    )
    assert dna_version.compiled_summary == "We are helpful and concise."
    assert dna_version.status == CompanyDnaVersionStatus.FINALIZED
