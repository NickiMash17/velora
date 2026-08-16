"""Unit tests for the Goals domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

from app.modules.goals.domain.entities import Goal
from app.modules.goals.domain.enums import GoalStatus


def test_goal_status_values_match_state_machine() -> None:
    """StateMachines.md §4: proposed -> active <-> at_risk -> achieved,
    plus abandoned. Only proposed/active are reachable in M5 (Finding 2)
    — the enum still carries all five for forward compatibility."""
    assert {member.value for member in GoalStatus} == {
        "proposed",
        "active",
        "at_risk",
        "achieved",
        "abandoned",
    }


def test_goal_constructs_with_optional_department_defaulting_to_none() -> None:
    goal = Goal(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="Reduce churn by 10%",
        success_metric={"metric": "churn_rate", "target": 0.05, "current": 0.08},
        status=GoalStatus.PROPOSED,
    )
    assert goal.department_id is None
    assert goal.created_at is None


def test_goal_success_metric_is_stored_opaquely() -> None:
    """No directionality assumption anywhere in the domain layer — the
    dict is stored and returned as-is."""
    metric = {"metric": "response_time_ms", "target": 200, "current": 350}
    goal = Goal(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="Improve response time",
        success_metric=metric,
        status=GoalStatus.PROPOSED,
    )
    assert goal.success_metric == metric
