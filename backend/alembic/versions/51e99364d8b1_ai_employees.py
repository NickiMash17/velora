"""ai employees

M5 Checkpoint 3 — the AI Employees bounded context, per the M5 Domain
Contract (docs/architecture/Database.md §3.3) and the finalized M5
implementation plan. Four tables in FK order, in one file, mirroring
aa3e8dcefd79's own multi-table-per-file precedent:
`ai_employee_templates` -> `skills` -> `ai_employees` -> `ai_employee_skills`.

Two tables are GLOBAL catalogs — `ai_employee_templates` and `skills` —
locked decision A1: no `organization_id`, no RLS statements at all,
matching `users`' precedent exactly (identity/global data, not tenant
data). `ai_employees` and `ai_employee_skills` are tenant-scoped, reusing
the exact `tenant_isolation` policy shape already established in
aa3e8dcefd79/02ed8c1da3b5/75ecf45f5d46.

`ai_employee_skills` uses a direct `organization_id` column (Finding 1,
already resolved in the M5 Step 3 plan) — no join-based RLS policy
anywhere in this migration.

Revision ID: 51e99364d8b1
Revises: 75ecf45f5d46
Create Date: 2026-08-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "51e99364d8b1"
down_revision: str | None = "75ecf45f5d46"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ai_employee_templates — global catalog, no RLS (locked decision A1)
    # ------------------------------------------------------------------
    op.create_table(
        "ai_employee_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("default_skills", postgresql.JSONB(), nullable=False),
        sa.Column("system_prompt_scaffold", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ai_employee_templates TO velora_app")

    # ------------------------------------------------------------------
    # skills — global catalog, no RLS (locked decision A1)
    # ------------------------------------------------------------------
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), nullable=False),
        sa.Column("required_permission_scope", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint("uq_skills_key", "skills", ["key"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON skills TO velora_app")

    # ------------------------------------------------------------------
    # ai_employees — tenant-scoped
    # ------------------------------------------------------------------
    ai_employee_status = postgresql.ENUM(
        "draft",
        "configured",
        "active",
        "paused",
        "retired",
        name="ai_employee_status",
    )

    op.create_table(
        "ai_employees",
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
            nullable=False,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_employee_templates.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role_title", sa.String(), nullable=False),
        sa.Column(
            "company_dna_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_dna_versions.id"),
            nullable=True,
        ),
        sa.Column("status", ai_employee_status, nullable=False),
        sa.Column("permission_scope", postgresql.JSONB(), nullable=True),
        sa.Column("autonomy_defaults", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_ai_employees_organization_id_status", "ai_employees", ["organization_id", "status"]
    )
    op.create_index("ix_ai_employees_department_id", "ai_employees", ["department_id"])

    op.execute("ALTER TABLE ai_employees ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_employees FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON ai_employees
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ai_employees TO velora_app")

    # ------------------------------------------------------------------
    # ai_employee_skills — tenant-scoped join, direct organization_id
    # (Finding 1, already resolved) — no join-based RLS policy.
    # ------------------------------------------------------------------
    op.create_table(
        "ai_employee_skills",
        sa.Column(
            "ai_employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_employees.id"),
            nullable=False,
        ),
        sa.Column(
            "skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id"), nullable=False
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("ai_employee_id", "skill_id"),
    )
    op.create_index("ix_ai_employee_skills_skill_id", "ai_employee_skills", ["skill_id"])
    op.create_index(
        "ix_ai_employee_skills_organization_id", "ai_employee_skills", ["organization_id"]
    )

    op.execute("ALTER TABLE ai_employee_skills ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_employee_skills FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON ai_employee_skills
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ai_employee_skills TO velora_app")


def downgrade() -> None:
    op.drop_table("ai_employee_skills")

    op.drop_table("ai_employees")
    op.execute("DROP TYPE ai_employee_status")

    op.drop_table("skills")

    op.drop_table("ai_employee_templates")
