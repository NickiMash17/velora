"""tasks

M5 Checkpoint 5 — the Tasks bounded context, per the M5 Domain Contract
(docs/architecture/Database.md §3.5) and the finalized M5 implementation
plan. Only `tasks` is created here — `task_pending_approvals` is not
built in M5 (§0.1's cascading-consequence analysis: `blocked` has no
legitimate M5 entry path, since it requires `claimed`/`in_progress`,
which require `/claim`, which is deferred pending machine identity —
Finding 3).

Reuses the exact tenant-scoping conventions already established in
aa3e8dcefd79/02ed8c1da3b5/75ecf45f5d46/51e99364d8b1/51c83f38b7cf:
`organization_id` FK, RLS `ENABLE`+`FORCE` with a single `tenant_isolation`
policy keyed on `app.current_org_id`, and an explicit `GRANT` to the
existing non-superuser `velora_app` role (created once in aa3e8dcefd79 —
not recreated here).

`status`/`blocked_reason` ship with their full documented enum values for
forward compatibility with `StateMachines.md §3`, but only `pending` is
ever written by this checkpoint's code — `claimed`/`in_progress`/
`blocked`/`done`/`failed` remain dormant, same treatment as Goals'
`at_risk`/`achieved`/`abandoned` (Finding 2). No `title` column — traced
against `Database.md §3.5` and `API.md §5` directly, neither establishes
one (M5 Step 3 plan §0.1); flagged `[INFERENCE]`, not locked, omitted.

Revision ID: 53a9d927a13a
Revises: 51c83f38b7cf
Create Date: 2026-08-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "53a9d927a13a"
down_revision: str | None = "51c83f38b7cf"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    task_status = postgresql.ENUM(
        "pending",
        "claimed",
        "in_progress",
        "blocked",
        "done",
        "failed",
        name="task_status",
    )
    task_blocked_reason = postgresql.ENUM(
        "awaiting_dependency",
        "awaiting_approval",
        "awaiting_input",
        name="task_blocked_reason",
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("goals.id"), nullable=True),
        sa.Column(
            "assigned_ai_employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_employees.id"),
            nullable=True,
        ),
        sa.Column(
            "assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("status", task_status, nullable=False),
        sa.Column("blocked_reason", task_blocked_reason, nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tasks_organization_id_status", "tasks", ["organization_id", "status"])
    op.create_index("ix_tasks_goal_id", "tasks", ["goal_id"])
    op.create_index("ix_tasks_assigned_ai_employee_id", "tasks", ["assigned_ai_employee_id"])
    op.create_index("ix_tasks_assigned_user_id", "tasks", ["assigned_user_id"])
    op.create_unique_constraint(
        "uq_tasks_org_idempotency_key", "tasks", ["organization_id", "idempotency_key"]
    )

    op.execute("ALTER TABLE tasks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tasks FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON tasks
        USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tasks TO velora_app")


def downgrade() -> None:
    op.drop_table("tasks")
    op.execute("DROP TYPE task_blocked_reason")
    op.execute("DROP TYPE task_status")
