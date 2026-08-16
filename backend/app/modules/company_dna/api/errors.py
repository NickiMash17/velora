"""Translates Company DNA domain/infrastructure exceptions into the
standard API error envelope (app.shared.errors.AppError) — the API
boundary's job specifically, matching organizations/api/errors.py's own
module docstring for why this translation doesn't happen in domain/ or
application/.
"""

from __future__ import annotations

from fastapi import status

from app.shared.errors import AppError


class CompanyDnaVersionNotFoundHTTPError(AppError):
    code = "company_dna_version_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class NoPublishedCompanyDnaVersionHTTPError(AppError):
    """Distinct from CompanyDnaVersionNotFoundHTTPError — there's no
    specific id being looked up here, just "this org hasn't published
    anything yet.\""""

    code = "no_published_company_dna_version"
    status_code = status.HTTP_404_NOT_FOUND


class CompanyDnaForbiddenHTTPError(AppError):
    """The caller is authenticated and organization-scoped, but their
    role does not permit this action — CompanyDNA.md §8: "DNA edits
    require org_admin role by default.\""""

    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN


class InvalidCompanyDnaTransitionHTTPError(AppError):
    code = "invalid_company_dna_transition"
    status_code = status.HTTP_409_CONFLICT


class EmptyCompiledSummaryHTTPError(AppError):
    code = "empty_compiled_summary"
    status_code = status.HTTP_409_CONFLICT


class CompanyDnaVersionConflictHTTPError(AppError):
    """A version string that already exists for this organization
    (uq_company_dna_versions_org_version)."""

    code = "company_dna_version_conflict"
    status_code = status.HTTP_409_CONFLICT


class InvalidCursorHTTPError(AppError):
    code = "invalid_cursor"
    status_code = status.HTTP_400_BAD_REQUEST
