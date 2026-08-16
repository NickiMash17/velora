"""company dna

M5 Checkpoint 2 — the Company DNA bounded context, per the M5 Domain
Contract (docs/architecture/Database.md §3.4) and the finalized M5
implementation plan. A `company_dna_versions` row is a versioned,
org-authored DNA document; DNA compilation is manual-entry only in M5 —
no compiler pipeline, no AI/LLM generation.

Reuses the exact tenant-scoping conventions already established in
aa3e8dcefd79/02ed8c1da3b5: `organization_id` FK, RLS `ENABLE`+`FORCE` with
a single `tenant_isolation` policy keyed on `app.current_org_id` via
`NULLIF(current_setting(...), '')::uuid`, and an explicit `GRANT` to the
existing non-superuser `velora_app` role (created once in aa3e8dcefd79 —
not recreated here).

Two constraints beyond the basic shape, both flagged [INFERENCE] in the
M5 Step 3 plan since no document states them explicitly:
- `uq_company_dna_versions_org_version`: a version string must be unique
  per organization — duplicate semver strings for the same org would be
  nonsensical.
- `ix_company_dna_versions_one_published_per_org`: a unique partial index
  enforcing "exactly one published version per org at a time"
  (CompanyDNA.md §4.3), extending the existing partial-index technique
  already used for `ix_events_unrelayed` to a UNIQUE partial index.

Revision ID: 75ecf45f5d46
Revises: 02ed8c1da3b5
Create Date: 2026-08-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "75ecf45f5d46"
down_revision: str | None = "02ed8c1da3b5"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    company_dna_version_status = postgresql.ENUM(
        "draft",
        "finalized",
        "published",
        "archived",
        name="company_dna_version_status",
    )

    op.create_table(
        "company_dna_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("status", company_dna_version_status, nullable=False),
        sa.Column("compiled_summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_company_dna_versions_organization_id", "company_dna_versions", ["organization_id"]
    )
    op.create_unique_constraint(
        "uq_company_dna_versions_org_version",
        "company_dna_versions",
        ["organization_id", "version"],
    )
    op.create_index(
        "ix_company_dna_versions_one_published_per_org",
        "company_dna_versions",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    op.execute("ALTER TABLE company_dna_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE company_dna_versions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON company_dna_versions
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON company_dna_versions TO velora_app")


def downgrade() -> None:
    op.drop_table("company_dna_versions")
    op.execute("DROP TYPE company_dna_version_status")
