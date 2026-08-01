"""Pydantic request/response models for the organizations API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema. Reuses identity's TokenResponse rather than redefining
an identical shape — organization creation/selection are both, at their
core, session-issuance actions (Security.md §3.2's "switching
organizations issues an entirely new scoped token"), the same kind of
action login/refresh already are.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.identity.api.schemas import TokenResponse


class CreateOrganizationRequest(BaseModel):
    """Create a new organization and become its org_admin. No slug field
    — per docs/product/WireframeSpec.md §5, slugs are never user-visible;
    one is generated from `name` server-side."""

    name: str = Field(..., min_length=1)
    refresh_token: str = Field(
        ...,
        description="The caller's current refresh token, rotated into an organization-scoped one",
    )


class SelectOrganizationRequest(BaseModel):
    """Switch the current session into a specific organization the
    caller is an active member of."""

    refresh_token: str = Field(
        ...,
        description="The caller's current refresh token, rotated into an organization-scoped one",
    )


class OrganizationResponse(BaseModel):
    """Public representation of an organization."""

    id: UUID
    name: str
    slug: str
    plan_tier: str
    status: str
    created_at: datetime


class OrganizationMembershipResponse(BaseModel):
    """An organization the current user belongs to, alongside their role
    in it."""

    organization: OrganizationResponse
    role: str


class OrganizationSessionResponse(BaseModel):
    """Returned by both organization creation and selection — the
    resulting organization plus a token pair newly scoped to it, so the
    client never needs a second round trip to start using the session
    (docs/architecture/API.md's Milestone 4 section)."""

    organization: OrganizationResponse
    tokens: TokenResponse
