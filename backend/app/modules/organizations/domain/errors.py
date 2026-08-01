"""Domain-level organization errors.

Plain exceptions, not subclasses of app.shared.errors.AppError — that
module imports FastAPI, and importing it here would pull a framework
dependency into domain/ (EngineeringStandards.md §2.1). Translation into
the API error envelope happens at the API boundary
(app/modules/organizations/api/router.py), not here.
"""

from __future__ import annotations


class OrganizationNotFoundError(Exception):
    pass


class MembershipNotFoundError(Exception):
    """Raised for both 'no such organization' and 'not a member of it' —
    the two cases are indistinguishable to the caller, matching the
    identity module's InvalidCredentialsError precedent (never reveal
    whether the resource exists if the caller isn't authorized to know)."""


class SlugGenerationExhaustedError(Exception):
    """Raised if every candidate slug in a bounded retry sequence
    collided — see app/modules/organizations/domain/slug.py. Should be
    exceptionally rare; a real occurrence likely indicates a bug in the
    candidate-generation sequence rather than genuine slug exhaustion."""
