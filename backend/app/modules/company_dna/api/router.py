"""Company DNA API endpoints.

Endpoint shapes are the M5 Checkpoint 2 decision — see the M5 Domain
Contract's API plan. `POST /v1/company-dna/versions` opens a draft
(org_admin only); `PATCH .../{id}` edits a draft's compiled_summary;
`POST .../{id}/finalize` and `POST .../{id}/publish` drive the locked
state machine; `GET /v1/company-dna/versions` lists versions
(cursor-paginated, per docs/architecture/API.md §6); `GET .../current`
returns the organization's currently published version. DNA compilation
is manual-entry only in M5 — no compiler pipeline, no AI/LLM generation
anywhere in this module.
"""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company_dna.api.errors import (
    CompanyDnaForbiddenHTTPError,
    CompanyDnaVersionConflictHTTPError,
    CompanyDnaVersionNotFoundHTTPError,
    EmptyCompiledSummaryHTTPError,
    InvalidCompanyDnaTransitionHTTPError,
    InvalidCursorHTTPError,
    NoPublishedCompanyDnaVersionHTTPError,
)
from app.modules.company_dna.api.schemas import (
    CompanyDnaVersionListResponse,
    CompanyDnaVersionResponse,
    CreateDnaVersionRequest,
    UpdateDnaVersionCompiledSummaryRequest,
)
from app.modules.company_dna.application.services import (
    create_draft_version,
    finalize_version,
    publish_version,
    update_draft_compiled_summary,
)
from app.modules.company_dna.domain.entities import CompanyDnaVersion
from app.modules.company_dna.domain.errors import (
    CompanyDnaVersionConflictError,
    CompanyDnaVersionNotFoundError,
    EmptyCompiledSummaryError,
    InvalidCompanyDnaTransitionError,
)
from app.modules.company_dna.infrastructure.repository import CompanyDnaVersionRepository
from app.modules.organizations.api.dependencies import OrganizationContext, get_current_org_context
from app.modules.organizations.domain.enums import MembershipRole
from app.shared.db import get_db_session
from app.shared.tenancy import tenant_scoped_transaction

router = APIRouter(tags=["company-dna"])

_CURSOR_FIELD_SEPARATOR = "|"


def _to_dna_version_response(dna_version: CompanyDnaVersion) -> CompanyDnaVersionResponse:
    if dna_version.created_at is None:
        # Every call site builds this from a row already persisted to the
        # database — reaching this means a future caller passed in a
        # CompanyDnaVersion that was never actually saved.
        raise RuntimeError("Cannot build a CompanyDnaVersionResponse for an unsaved version.")
    return CompanyDnaVersionResponse(
        id=dna_version.id,
        version=dna_version.version,
        status=dna_version.status.value,
        compiled_summary=dna_version.compiled_summary,
        published_at=dna_version.published_at,
        created_at=dna_version.created_at,
    )


def _encode_cursor(dna_version: CompanyDnaVersion) -> str:
    assert dna_version.created_at is not None  # always true for a persisted row
    raw = f"{dna_version.created_at.isoformat()}{_CURSOR_FIELD_SEPARATOR}{dna_version.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_raw, id_raw = raw.split(_CURSOR_FIELD_SEPARATOR)
        return datetime.fromisoformat(created_at_raw), UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorHTTPError(f"'{cursor}' is not a valid pagination cursor.") from exc


def _require_org_admin(context: OrganizationContext) -> None:
    if context.role != MembershipRole.ORG_ADMIN.value:
        raise CompanyDnaForbiddenHTTPError("Only an org_admin may perform this action.")


@router.post(
    "/company-dna/versions",
    response_model=CompanyDnaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dna_version(
    body: CreateDnaVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionResponse:
    _require_org_admin(context)

    try:
        dna_version = await create_draft_version(
            session, organization_id=context.organization_id, version=body.version
        )
    except CompanyDnaVersionConflictError as exc:
        raise CompanyDnaVersionConflictHTTPError(str(exc)) from exc
    return _to_dna_version_response(dna_version)


@router.patch("/company-dna/versions/{version_id}", response_model=CompanyDnaVersionResponse)
async def update_dna_version_compiled_summary(
    version_id: UUID,
    body: UpdateDnaVersionCompiledSummaryRequest,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionResponse:
    _require_org_admin(context)

    try:
        dna_version = await update_draft_compiled_summary(
            session,
            organization_id=context.organization_id,
            version_id=version_id,
            compiled_summary=body.compiled_summary,
        )
    except CompanyDnaVersionNotFoundError as exc:
        raise CompanyDnaVersionNotFoundHTTPError(str(exc)) from exc
    except InvalidCompanyDnaTransitionError as exc:
        raise InvalidCompanyDnaTransitionHTTPError(str(exc)) from exc
    return _to_dna_version_response(dna_version)


@router.post(
    "/company-dna/versions/{version_id}/finalize", response_model=CompanyDnaVersionResponse
)
async def finalize_dna_version(
    version_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionResponse:
    _require_org_admin(context)

    try:
        dna_version = await finalize_version(
            session, organization_id=context.organization_id, version_id=version_id
        )
    except CompanyDnaVersionNotFoundError as exc:
        raise CompanyDnaVersionNotFoundHTTPError(str(exc)) from exc
    except InvalidCompanyDnaTransitionError as exc:
        raise InvalidCompanyDnaTransitionHTTPError(str(exc)) from exc
    except EmptyCompiledSummaryError as exc:
        raise EmptyCompiledSummaryHTTPError(str(exc)) from exc
    return _to_dna_version_response(dna_version)


@router.post(
    "/company-dna/versions/{version_id}/publish", response_model=CompanyDnaVersionResponse
)
async def publish_dna_version(
    version_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionResponse:
    _require_org_admin(context)

    try:
        dna_version = await publish_version(
            session, organization_id=context.organization_id, version_id=version_id
        )
    except CompanyDnaVersionNotFoundError as exc:
        raise CompanyDnaVersionNotFoundHTTPError(str(exc)) from exc
    except InvalidCompanyDnaTransitionError as exc:
        raise InvalidCompanyDnaTransitionHTTPError(str(exc)) from exc
    return _to_dna_version_response(dna_version)


@router.get("/company-dna/versions", response_model=CompanyDnaVersionListResponse)
async def list_dna_versions(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionListResponse:
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    async with tenant_scoped_transaction(session, context.organization_id):
        dna_versions = await CompanyDnaVersionRepository().list_for_organization(
            session, context.organization_id, cursor=decoded_cursor, limit=limit
        )

    next_cursor = _encode_cursor(dna_versions[-1]) if len(dna_versions) == limit else None
    return CompanyDnaVersionListResponse(
        items=[_to_dna_version_response(v) for v in dna_versions], next_cursor=next_cursor
    )


@router.get("/company-dna/versions/current", response_model=CompanyDnaVersionResponse)
async def get_current_dna_version(
    session: AsyncSession = Depends(get_db_session),
    context: OrganizationContext = Depends(get_current_org_context),
) -> CompanyDnaVersionResponse:
    async with tenant_scoped_transaction(session, context.organization_id):
        dna_version = await CompanyDnaVersionRepository().get_current_published(
            session, context.organization_id
        )
    if dna_version is None:
        raise NoPublishedCompanyDnaVersionHTTPError(
            "This organization has not published a Company DNA version yet."
        )
    return _to_dna_version_response(dna_version)
