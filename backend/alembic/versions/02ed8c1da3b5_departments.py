"""departments

M5 Checkpoint 1 — the Departments bounded context, per the M5 Domain
Contract (docs/architecture/Database.md §3.2) and the finalized M5
implementation plan. A `departments` row is the primary scope for future
AI Employee/Goal assignment (out of scope for this checkpoint).

Reuses the exact tenant-scoping conventions already established in
aa3e8dcefd79: `organization_id` FK, RLS `ENABLE`+`FORCE` with a single
`tenant_isolation` policy keyed on `app.current_org_id` via
`NULLIF(current_setting(...), '')::uuid`, and an explicit `GRANT` to the
existing non-superuser `velora_app` role (created once in aa3e8dcefd79 —
not recreated here).

No `status` column — Department lifecycle/archive behavior is explicitly
out of scope for M5 (locked decision C1); adding one now would be schema
built ahead of any real need.

Revision ID: 02ed8c1da3b5
Revises: f6ed0954c004
Create Date: 2026-08-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "02ed8c1da3b5"
down_revision: str | None = "f6ed0954c004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    department_function_type = postgresql.ENUM(
        "sales",
        "support",
        "finance",
        "marketing",
        "ops",
        "custom",
        name="department_function_type",
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("function_type", department_function_type, nullable=False),
        sa.Column("budget_cents_monthly", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])

    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE departments FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON departments
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON departments TO velora_app")


def downgrade() -> None:
    op.drop_table("departments")
    op.execute("DROP TYPE department_function_type")
