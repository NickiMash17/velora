"""organization scoped sessions

Milestone 4 — two independent, co-shipped changes, both required for
organization onboarding to work at all:

1. `refresh_tokens` gains nullable `organization_id`/`role` columns, so
   rotating a refresh token can carry its organization scope forward
   (see app/modules/identity/application/services.py's `refresh_session`)
   instead of silently downgrading every session back to org-less on its
   next refresh. `role` is a plain nullable String, not the
   `membership_role` enum — see identity's RefreshTokenORM docstring for
   why (identity has no import-time knowledge of the organizations
   module's types).

2. A second, `FOR SELECT`-only permissive RLS policy on
   `organization_memberships`, keyed on a new `app.current_user_id`
   session-local GUC, letting a user discover which organization(s) they
   belong to before any tenant context exists — see
   docs/architecture/decisions/0002-organization-membership-self-visibility.md
   for the full reasoning, and why `FOR SELECT` specifically is load-
   bearing (a policy governing all commands would let this context forge
   membership rows into arbitrary organizations). Postgres combines
   multiple permissive policies for the same command with OR, so the
   existing `tenant_isolation` policy on this table is untouched.

Revision ID: f6ed0954c004
Revises: 0d2d76adfbd2
Create Date: 2026-08-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f6ed0954c004"
down_revision: str | None = "0d2d76adfbd2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
    )
    op.add_column("refresh_tokens", sa.Column("role", sa.String(), nullable=True))

    op.execute(
        """
        CREATE POLICY self_visibility ON organization_memberships
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY self_visibility ON organization_memberships")
    op.drop_column("refresh_tokens", "role")
    op.drop_column("refresh_tokens", "organization_id")
