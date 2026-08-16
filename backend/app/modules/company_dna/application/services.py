"""Use cases: create a draft Company DNA version, edit its
compiled_summary, finalize it, and publish it.

DNA compilation is manual-entry only in M5 (locked decision) — there is
no compiler pipeline and no AI/LLM generation anywhere in this module.
`compiled_summary` is text an org_admin authors directly via `PATCH
/company-dna/versions/{id}`; "finalize" is a human marking that
manually-authored content done and locked, the M5 substitute for
CompanyDNA.md §4.2's (out-of-scope) real compilation pipeline finishing.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company_dna.domain.entities import CompanyDnaVersion
from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus
from app.modules.company_dna.domain.errors import (
    CompanyDnaVersionConflictError,
    CompanyDnaVersionNotFoundError,
    EmptyCompiledSummaryError,
    InvalidCompanyDnaTransitionError,
)
from app.modules.company_dna.infrastructure.repository import CompanyDnaVersionRepository
from app.modules.events.domain.catalog import (
    COMPANY_DNA_COMPILED,
    COMPANY_DNA_DRAFT_CREATED,
    COMPANY_DNA_PUBLISHED,
    topic_for,
)
from app.modules.events.infrastructure.outbox import write_event
from app.shared.tenancy import tenant_scoped_transaction

_PRODUCER = "company_dna"


async def create_draft_version(
    session: AsyncSession,
    *,
    organization_id: UUID,
    version: str,
    repo: CompanyDnaVersionRepository | None = None,
) -> CompanyDnaVersion:
    repo = repo or CompanyDnaVersionRepository()

    dna_version = CompanyDnaVersion(
        id=uuid.uuid4(),
        organization_id=organization_id,
        version=version,
        status=CompanyDnaVersionStatus.DRAFT,
    )

    try:
        async with tenant_scoped_transaction(session, organization_id):
            dna_version = await repo.create(session, dna_version)

            await write_event(
                session,
                organization_id=organization_id,
                type=COMPANY_DNA_DRAFT_CREATED,
                topic=topic_for(COMPANY_DNA_DRAFT_CREATED),
                producer=_PRODUCER,
                payload={
                    "dna_version_id": str(dna_version.id),
                    "organization_id": str(organization_id),
                },
                correlation_id=uuid.uuid4(),
            )
    except IntegrityError as exc:
        raise CompanyDnaVersionConflictError(
            f"Version '{version}' already exists for this organization."
        ) from exc

    return dna_version


async def update_draft_compiled_summary(
    session: AsyncSession,
    *,
    organization_id: UUID,
    version_id: UUID,
    compiled_summary: str,
    repo: CompanyDnaVersionRepository | None = None,
) -> CompanyDnaVersion:
    """No event emitted — editing a draft's content is not a state
    transition (StateMachines.md §1's "every transition emits an event"
    rule governs status changes, not in-place content edits)."""
    repo = repo or CompanyDnaVersionRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await repo.get_by_id(session, organization_id, version_id)
        if existing is None:
            raise CompanyDnaVersionNotFoundError(
                f"Company DNA version '{version_id}' was not found."
            )
        if existing.status != CompanyDnaVersionStatus.DRAFT:
            raise InvalidCompanyDnaTransitionError(
                f"Cannot edit compiled_summary — version '{version_id}' is "
                f"'{existing.status.value}', not 'draft'."
            )
        existing.compiled_summary = compiled_summary
        return await repo.save(session, existing)


async def finalize_version(
    session: AsyncSession,
    *,
    organization_id: UUID,
    version_id: UUID,
    repo: CompanyDnaVersionRepository | None = None,
) -> CompanyDnaVersion:
    repo = repo or CompanyDnaVersionRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await repo.get_by_id(session, organization_id, version_id)
        if existing is None:
            raise CompanyDnaVersionNotFoundError(
                f"Company DNA version '{version_id}' was not found."
            )
        if existing.status != CompanyDnaVersionStatus.DRAFT:
            raise InvalidCompanyDnaTransitionError(
                f"Cannot finalize — version '{version_id}' is "
                f"'{existing.status.value}', not 'draft'."
            )
        if not existing.compiled_summary:
            raise EmptyCompiledSummaryError(
                f"Cannot finalize version '{version_id}' with no compiled_summary."
            )

        existing.status = CompanyDnaVersionStatus.FINALIZED
        finalized = await repo.save(session, existing)

        assert finalized.compiled_summary is not None  # checked above
        compiled_summary_hash = hashlib.sha256(finalized.compiled_summary.encode()).hexdigest()
        await write_event(
            session,
            organization_id=organization_id,
            type=COMPANY_DNA_COMPILED,
            topic=topic_for(COMPANY_DNA_COMPILED),
            producer=_PRODUCER,
            payload={
                "dna_version_id": str(finalized.id),
                "compiled_summary_hash": compiled_summary_hash,
            },
            correlation_id=uuid.uuid4(),
        )

    return finalized


async def publish_version(
    session: AsyncSession,
    *,
    organization_id: UUID,
    version_id: UUID,
    repo: CompanyDnaVersionRepository | None = None,
) -> CompanyDnaVersion:
    """Publishing a version also archives the organization's previously
    published version (if any) in the same transaction — the DB partial
    unique index (`ix_company_dna_versions_one_published_per_org`)
    enforces that at most one row per org can ever be `published`, so this
    archive step isn't optional cleanup, it's what keeps that constraint
    satisfiable. No dedicated event for the archive side-effect —
    `CompanyDnaPublished.previous_version_id` documents it, per the
    already-locked reasoning for this exact side-effect (M5 Step 3 plan
    §4)."""
    repo = repo or CompanyDnaVersionRepository()

    async with tenant_scoped_transaction(session, organization_id):
        existing = await repo.get_by_id(session, organization_id, version_id)
        if existing is None:
            raise CompanyDnaVersionNotFoundError(
                f"Company DNA version '{version_id}' was not found."
            )
        if existing.status != CompanyDnaVersionStatus.FINALIZED:
            raise InvalidCompanyDnaTransitionError(
                f"Cannot publish — version '{version_id}' is "
                f"'{existing.status.value}', not 'finalized'."
            )

        previous = await repo.get_current_published(session, organization_id)
        if previous is not None:
            previous.status = CompanyDnaVersionStatus.ARCHIVED
            await repo.save(session, previous)

        existing.status = CompanyDnaVersionStatus.PUBLISHED
        existing.published_at = datetime.now(UTC)
        published = await repo.save(session, existing)

        await write_event(
            session,
            organization_id=organization_id,
            type=COMPANY_DNA_PUBLISHED,
            topic=topic_for(COMPANY_DNA_PUBLISHED),
            producer=_PRODUCER,
            payload={
                "dna_version_id": str(published.id),
                "organization_id": str(organization_id),
                "previous_version_id": str(previous.id) if previous is not None else None,
            },
            correlation_id=uuid.uuid4(),
        )

    return published
