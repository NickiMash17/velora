"""Integration tests for the Company DNA application services — real,
migrated Postgres throughout. Mirrors test_department_service.py's
pattern for create_department.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company_dna.application.services import (
    create_draft_version,
    finalize_version,
    publish_version,
    update_draft_compiled_summary,
)
from app.modules.company_dna.domain.enums import CompanyDnaVersionStatus
from app.modules.company_dna.domain.errors import (
    CompanyDnaVersionConflictError,
    CompanyDnaVersionNotFoundError,
    EmptyCompiledSummaryError,
    InvalidCompanyDnaTransitionError,
)
from app.modules.company_dna.infrastructure.repository import CompanyDnaVersionRepository
from app.modules.events.infrastructure.orm import EventORM
from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.repository import UserRepository
from app.modules.organizations.application.services import create_organization_with_admin
from app.shared.tenancy import tenant_scoped_transaction

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"dna-{uuid.uuid4().hex[:10]}@example.com"


def _unique_slug() -> str:
    return f"dna-tenant-{uuid.uuid4().hex[:10]}"


async def _create_org(db_session: AsyncSession) -> uuid.UUID:
    admin = User(id=uuid.uuid4(), email=_unique_email(), password_hash=None, mfa_enabled=False)
    await UserRepository().create(db_session, admin)
    await db_session.commit()

    result = await create_organization_with_admin(
        db_session, name="Acme Inc", slug=_unique_slug(), admin_user_id=admin.id
    )
    return result.organization.id


@pytest.mark.asyncio
async def test_create_draft_version_persists_version_and_event(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)

    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )

    assert dna_version.version == "1.0.0"
    assert dna_version.status == CompanyDnaVersionStatus.DRAFT
    assert dna_version.compiled_summary is None
    assert dna_version.created_at is not None

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )

    draft_events = [e for e in events if e.type == "CompanyDnaDraftCreated"]
    assert len(draft_events) == 1
    event = draft_events[0]
    assert event.topic == "company_dna.draft_created"
    assert event.producer == "company_dna"
    assert event.payload == {
        "dna_version_id": str(dna_version.id),
        "organization_id": str(organization_id),
    }


@pytest.mark.asyncio
async def test_create_draft_version_rejects_duplicate_version_string(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    await create_draft_version(db_session, organization_id=organization_id, version="1.0.0")

    with pytest.raises(CompanyDnaVersionConflictError):
        await create_draft_version(db_session, organization_id=organization_id, version="1.0.0")


@pytest.mark.asyncio
async def test_update_draft_compiled_summary_succeeds_while_draft(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )

    updated = await update_draft_compiled_summary(
        db_session,
        organization_id=organization_id,
        version_id=dna_version.id,
        compiled_summary="We are helpful and concise.",
    )

    assert updated.compiled_summary == "We are helpful and concise."
    assert updated.status == CompanyDnaVersionStatus.DRAFT


@pytest.mark.asyncio
async def test_update_draft_compiled_summary_rejects_unknown_version(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)

    with pytest.raises(CompanyDnaVersionNotFoundError):
        await update_draft_compiled_summary(
            db_session,
            organization_id=organization_id,
            version_id=uuid.uuid4(),
            compiled_summary="anything",
        )


@pytest.mark.asyncio
async def test_finalize_version_requires_compiled_summary(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )

    with pytest.raises(EmptyCompiledSummaryError):
        await finalize_version(
            db_session, organization_id=organization_id, version_id=dna_version.id
        )


@pytest.mark.asyncio
async def test_finalize_version_emits_event_with_summary_hash(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )
    await update_draft_compiled_summary(
        db_session,
        organization_id=organization_id,
        version_id=dna_version.id,
        compiled_summary="We are helpful and concise.",
    )

    finalized = await finalize_version(
        db_session, organization_id=organization_id, version_id=dna_version.id
    )

    assert finalized.status == CompanyDnaVersionStatus.FINALIZED

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    compiled_events = [e for e in events if e.type == "CompanyDnaCompiled"]
    assert len(compiled_events) == 1
    expected_hash = hashlib.sha256(b"We are helpful and concise.").hexdigest()
    assert compiled_events[0].payload == {
        "dna_version_id": str(dna_version.id),
        "compiled_summary_hash": expected_hash,
    }


@pytest.mark.asyncio
async def test_finalize_version_rejects_non_draft(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )
    await update_draft_compiled_summary(
        db_session,
        organization_id=organization_id,
        version_id=dna_version.id,
        compiled_summary="content",
    )
    await finalize_version(db_session, organization_id=organization_id, version_id=dna_version.id)

    with pytest.raises(InvalidCompanyDnaTransitionError):
        await finalize_version(
            db_session, organization_id=organization_id, version_id=dna_version.id
        )


@pytest.mark.asyncio
async def test_publish_version_rejects_non_finalized(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version="1.0.0"
    )

    with pytest.raises(InvalidCompanyDnaTransitionError):
        await publish_version(
            db_session, organization_id=organization_id, version_id=dna_version.id
        )


async def _create_finalized_version(
    db_session: AsyncSession, organization_id: uuid.UUID, version: str
) -> uuid.UUID:
    dna_version = await create_draft_version(
        db_session, organization_id=organization_id, version=version
    )
    await update_draft_compiled_summary(
        db_session,
        organization_id=organization_id,
        version_id=dna_version.id,
        compiled_summary=f"content for {version}",
    )
    await finalize_version(db_session, organization_id=organization_id, version_id=dna_version.id)
    return dna_version.id


@pytest.mark.asyncio
async def test_publish_version_succeeds_and_emits_event(db_session: AsyncSession) -> None:
    organization_id = await _create_org(db_session)
    version_id = await _create_finalized_version(db_session, organization_id, "1.0.0")

    published = await publish_version(
        db_session, organization_id=organization_id, version_id=version_id
    )

    assert published.status == CompanyDnaVersionStatus.PUBLISHED
    assert published.published_at is not None

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    published_events = [e for e in events if e.type == "CompanyDnaPublished"]
    assert len(published_events) == 1
    assert published_events[0].payload == {
        "dna_version_id": str(version_id),
        "organization_id": str(organization_id),
        "previous_version_id": None,
    }


@pytest.mark.asyncio
async def test_publish_version_archives_the_previously_published_version(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    first_id = await _create_finalized_version(db_session, organization_id, "1.0.0")
    await publish_version(db_session, organization_id=organization_id, version_id=first_id)

    second_id = await _create_finalized_version(db_session, organization_id, "2.0.0")
    published = await publish_version(
        db_session, organization_id=organization_id, version_id=second_id
    )

    assert published.id == second_id
    assert published.status == CompanyDnaVersionStatus.PUBLISHED

    async with tenant_scoped_transaction(db_session, organization_id):
        first = await CompanyDnaVersionRepository().get_by_id(
            db_session, organization_id, first_id
        )
        current_published = await CompanyDnaVersionRepository().get_current_published(
            db_session, organization_id
        )

    assert first is not None
    assert first.status == CompanyDnaVersionStatus.ARCHIVED
    assert current_published is not None
    assert current_published.id == second_id

    async with tenant_scoped_transaction(db_session, organization_id):
        events = (
            (
                await db_session.execute(
                    select(EventORM).where(EventORM.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        )
    published_events = [e for e in events if e.type == "CompanyDnaPublished"]
    assert len(published_events) == 2
    second_publish_event = next(
        e for e in published_events if e.payload["dna_version_id"] == str(second_id)
    )
    assert second_publish_event.payload["previous_version_id"] == str(first_id)


@pytest.mark.asyncio
async def test_list_for_organization_paginates_by_keyset_cursor(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    for version in ["1.0.0", "1.1.0", "1.2.0"]:
        await create_draft_version(db_session, organization_id=organization_id, version=version)

    async with tenant_scoped_transaction(db_session, organization_id):
        first_page = await CompanyDnaVersionRepository().list_for_organization(
            db_session, organization_id, limit=2
        )
        assert [v.version for v in first_page] == ["1.0.0", "1.1.0"]

        cursor = (first_page[-1].created_at, first_page[-1].id)
        second_page = await CompanyDnaVersionRepository().list_for_organization(
            db_session, organization_id, cursor=cursor, limit=2
        )
        assert [v.version for v in second_page] == ["1.2.0"]


@pytest.mark.asyncio
async def test_get_current_published_returns_none_when_none_published(
    db_session: AsyncSession,
) -> None:
    organization_id = await _create_org(db_session)
    await create_draft_version(db_session, organization_id=organization_id, version="1.0.0")

    async with tenant_scoped_transaction(db_session, organization_id):
        current = await CompanyDnaVersionRepository().get_current_published(
            db_session, organization_id
        )

    assert current is None
