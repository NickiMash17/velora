"""Pydantic request/response models for the identity API.

Every model has a docstring and field descriptions per
docs/architecture/API.md §10 — these flow directly into the generated
OpenAPI schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Create a new user account. Registration creates only an identity —
    no organization, membership, or any other resource."""

    email: EmailStr = Field(..., description="Normalized to lowercase before storage")
    password: str = Field(
        ..., min_length=1, description="Minimum length enforced by policy, not schema"
    )


class UserResponse(BaseModel):
    """Public representation of a user. Never includes password_hash —
    there is no code path that serializes it into a response."""

    id: UUID
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    """Authenticate with email and password."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """An access/refresh token pair, returned by both login and refresh."""

    access_token: str = Field(..., description="Short-lived JWT — see Security.md §3.1")
    refresh_token: str = Field(..., description="Opaque, single-use; rotates on every refresh")
    token_type: str = Field("bearer", description="Always 'bearer'")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshRequest(BaseModel):
    """Exchange a refresh token for a new access/refresh token pair."""

    refresh_token: str
