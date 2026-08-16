"""Domain-level Company DNA errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/company_dna/api/router.py), not here.
"""

from __future__ import annotations


class CompanyDnaVersionNotFoundError(Exception):
    pass


class CompanyDnaVersionConflictError(Exception):
    """Raised when a version string collides with an existing one for the
    same organization (uq_company_dna_versions_org_version)."""


class InvalidCompanyDnaTransitionError(Exception):
    """Raised when a transition is attempted from a status that doesn't
    permit it — e.g. finalizing a version that isn't `draft`, publishing
    one that isn't `finalized`, or editing `compiled_summary` on a version
    that is no longer `draft`."""


class EmptyCompiledSummaryError(Exception):
    """Raised when finalizing a version with no `compiled_summary` set.
    M5's DNA compilation is manual-entry only (CompanyDNA.md §4.2 real
    pipeline is out of scope) — an admin must have actually authored
    content before a version can be locked as `finalized`."""
