"""Unit tests for the Tasks domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

from app.modules.tasks.domain.entities import Task
from app.modules.tasks.domain.enums import TaskBlockedReason, TaskStatus


def test_task_status_values_match_state_machine() -> None:
    """StateMachines.md §3: pending -> claimed -> in_progress -> blocked
    -> done | failed. Only `pending` is reachable in M5 (Finding 3's
    cascade) — the enum still carries all six for forward compatibility."""
    assert {member.value for member in TaskStatus} == {
        "pending",
        "claimed",
        "in_progress",
        "blocked",
        "done",
        "failed",
    }


def test_task_blocked_reason_values_match_locked_decision_a3() -> None:
    """Locked decision A3 — dormant in M5, `blocked` itself is unreachable."""
    assert {member.value for member in TaskBlockedReason} == {
        "awaiting_dependency",
        "awaiting_approval",
        "awaiting_input",
    }


def test_task_constructs_with_defaults() -> None:
    task = Task(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        idempotency_key="idem-1",
    )
    assert task.goal_id is None
    assert task.assigned_ai_employee_id is None
    assert task.assigned_user_id is None
    assert task.blocked_reason is None
    assert task.retry_count == 0
    assert task.created_at is None


def test_task_constructs_with_explicit_assignment() -> None:
    user_id = uuid.uuid4()
    goal_id = uuid.uuid4()
    task = Task(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        idempotency_key="idem-2",
        goal_id=goal_id,
        assigned_user_id=user_id,
    )
    assert task.goal_id == goal_id
    assert task.assigned_user_id == user_id
