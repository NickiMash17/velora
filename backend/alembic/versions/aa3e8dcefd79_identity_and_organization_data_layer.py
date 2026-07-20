"""identity and organization data layer

Creates users, organizations, organization_memberships, and the events
table (transactional outbox / v1 Event Store), with Row-Level Security
enabled and forced on every tenant-scoped table — per
docs/architecture/Database.md §5, RLS lives in the same migration as the
tables it protects, not as a follow-up step.

users is deliberately NOT given an RLS policy — see
app/modules/identity/domain/entities.py's docstring: it isn't tenant-scoped
data, a user's tenancy is a property of organization_memberships, not of
the user row itself.

Every policy predicate wraps current_setting() in NULLIF(..., '') before
casting to uuid: once a custom GUC like app.current_org_id has been set at
all on a connection, a LOCAL-scoped transaction ending resets it to an
empty string, not NULL — so a bare `current_setting(..., true)::uuid`
throws a hard cast error on the very next unscoped query on a reused
pooled connection, rather than safely evaluating to no-match. Discovered
by tests/isolation itself; see this milestone's completion report.

Also creates a non-superuser `velora_app` role and grants it CRUD on all
four tables: Postgres superusers (and table owners, without FORCE)
bypass RLS unconditionally, so the running application — and every
isolation test — must connect as this role, not as the migration-owning
superuser, for RLS to mean anything at all.

Revision ID: aa3e8dcefd79
Revises:
Create Date: 2026-07-20

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "aa3e8dcefd79"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users — not tenant-scoped (see module docstring above); no RLS.
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # ------------------------------------------------------------------
    # organizations — the tenant root. RLS keys on `id` itself, since
    # there is no separate organization_id column on the tenant root.
    # ------------------------------------------------------------------
    plan_tier = postgresql.ENUM(
        "trial", "starter", "growth", "enterprise", name="plan_tier"
    )
    isolation_tier = postgresql.ENUM("pool", "silo", name="isolation_tier")
    region = postgresql.ENUM("us", "eu", "apac", name="region")
    organization_status = postgresql.ENUM(
        "trial", "active", "suspended", "churned", name="organization_status"
    )

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("plan_tier", plan_tier, nullable=False),
        sa.Column("isolation_tier", isolation_tier, nullable=False),
        sa.Column("region", region, nullable=False),
        sa.Column("status", organization_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])

    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organizations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON organizations
        USING (id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    # ------------------------------------------------------------------
    # organization_memberships
    # ------------------------------------------------------------------
    membership_role = postgresql.ENUM(
        "org_admin", "department_manager", "member", "viewer", name="membership_role"
    )
    membership_status = postgresql.ENUM("invited", "active", "suspended", name="membership_status")

    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("status", membership_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_membership_org_user"),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_memberships_user_id", "organization_memberships", ["user_id"]
    )

    op.execute("ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON organization_memberships
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    # ------------------------------------------------------------------
    # events — transactional outbox / v1 Event Store (ADR 0001)
    # ------------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("producer", sa.String(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("relayed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_events_organization_id_occurred_at", "events", ["organization_id", "occurred_at"])
    op.create_index(
        "ix_events_unrelayed",
        "events",
        ["relayed_at"],
        postgresql_where=sa.text("relayed_at IS NULL"),
    )

    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON events
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    # ------------------------------------------------------------------
    # Least-privilege application role.
    #
    # Postgres superusers bypass RLS unconditionally, and FORCE ROW LEVEL
    # SECURITY only removes the *table owner* exemption — not the
    # superuser one. The official postgres Docker image makes
    # POSTGRES_USER a superuser, which is also the role that owns these
    # tables (it ran this migration). So the running application, and
    # every isolation test, must connect as a SEPARATE, non-superuser
    # role for RLS to mean anything at all. Discovered by the isolation
    # tests themselves silently failing (both tenants' rows visible)
    # despite the policies above being correctly defined — see this
    # milestone's completion report.
    #
    # The hardcoded password is a known, flagged limitation: real secrets
    # management (Azure Key Vault, per Deployment.md) is out of scope
    # here, which only needs a real non-superuser role to exist so RLS is
    # actually testable.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'velora_app') THEN
                CREATE ROLE velora_app LOGIN PASSWORD 'velora_app_dev_only'
                    NOSUPERUSER NOBYPASSRLS;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        "users, organizations, organization_memberships, events TO velora_app"
    )


def downgrade() -> None:
    # Tables first — DROP TABLE automatically revokes any grants on them,
    # so there's nothing left for velora_app to hold by the time we get to
    # dropping the role itself (and no REVOKE needed, which would error
    # if this downgrade runs before the role was ever created).
    op.drop_table("events")

    op.drop_table("organization_memberships")
    op.execute("DROP TYPE membership_status")
    op.execute("DROP TYPE membership_role")

    op.drop_table("organizations")
    op.execute("DROP TYPE organization_status")
    op.execute("DROP TYPE region")
    op.execute("DROP TYPE isolation_tier")
    op.execute("DROP TYPE plan_tier")

    op.drop_table("users")

    op.execute("DROP ROLE IF EXISTS velora_app")
