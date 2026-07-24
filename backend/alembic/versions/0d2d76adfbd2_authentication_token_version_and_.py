"""authentication: token_version and refresh_tokens

Adds `token_version` to `users` (Security.md §3.1 access-token claim —
see app/modules/identity/domain/entities.py's User.token_version
docstring for why it's real infrastructure now even though nothing
triggers a bump yet) and a `refresh_tokens` table (Security.md §3.1:
refresh tokens are "stored hashed" — that requires somewhere to store
them, which Database.md didn't yet have).

Neither gets an RLS policy — same reasoning as `users` itself: this is
identity data, not tenant-scoped data. Both were absent from Database.md
until this milestone; see this milestone's completion report and the
corresponding Database.md update.

Revision ID: 0d2d76adfbd2
Revises: aa3e8dcefd79
Create Date: 2026-07-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0d2d76adfbd2"
down_revision: str | None = "aa3e8dcefd79"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refresh_tokens.id"),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    # velora_app needs CRUD on the new table too — it's covered by the
    # blanket grant in aa3e8dcefd79 for the four tables that existed then,
    # but that grant doesn't apply retroactively to a table created later.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO velora_app")


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_column("users", "token_version")
