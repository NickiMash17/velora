"""goals

M5 Checkpoint 4 — the Goals bounded context, per the M5 Domain Contract
(docs/architecture/Database.md §3.5) and the finalized M5 implementation
plan. A `goals` row is a business-level objective, org- or department-
scoped, with an opaque `success_metric` (directionality intentionally not
invented — see Known Gaps in the M5 plan).

Reuses the exact tenant-scoping conventions already established in
aa3e8dcefd79/02ed8c1da3b5/75ecf45f5d46/51e99364d8b1: `organization_id` FK,
RLS `ENABLE`+`FORCE` with a single `tenant_isolation` policy keyed on
`app.current_org_id`, and an explicit `GRANT` to the existing
non-superuser `velora_app` role (created once in aa3e8dcefd79 — not
recreated here).

Only `proposed`/`active` are reachable via any M5 endpoint (Finding 2,
already resolved in the M5 Step 3 plan) — `at_risk`/`achieved`/`abandoned`
remain in the enum for forward compatibility with `StateMachines.md §4`
only; no code in this checkpoint ever writes them.

Revision ID: 51c83f38b7cf
Revises: 51e99364d8b1
Create Date: 2026-08-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "51c83f38b7cf"
down_revision: str | None = "51e99364d8b1"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    goal_status = postgresql.ENUM(
        "proposed",
        "active",
        "at_risk",
        "achieved",
        "abandoned",
        name="goal_status",
    )

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("departments.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("success_metric", postgresql.JSONB(), nullable=False),
        sa.Column("status", goal_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_goals_organization_id", "goals", ["organization_id"])
    op.create_index("ix_goals_department_id", "goals", ["department_id"])

    op.execute("ALTER TABLE goals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE goals FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON goals
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON goals TO velora_app")


def downgrade() -> None:
    op.drop_table("goals")
    op.execute("DROP TYPE goal_status")
