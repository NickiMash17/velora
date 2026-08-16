"""Unit tests for the AI Employees domain layer — pure Python, no DB."""

from __future__ import annotations

import uuid

from app.modules.ai_employees.domain.entities import AiEmployee, AiEmployeeTemplate, Skill
from app.modules.ai_employees.domain.enums import AiEmployeeStatus, AutonomyLevel


def test_ai_employee_status_values_match_state_machine() -> None:
    """StateMachines.md §2: draft -> configured -> active <-> paused -> retired."""
    assert {member.value for member in AiEmployeeStatus} == {
        "draft",
        "configured",
        "active",
        "paused",
        "retired",
    }


def test_autonomy_level_values_match_locked_taxonomy() -> None:
    """AIEmployees.md §6 / locked decision 2 — same three values
    AutonomyDial already uses, unchanged here."""
    assert {member.value for member in AutonomyLevel} == {"autonomous", "notify", "approve"}


def test_ai_employee_constructs_with_defaults() -> None:
    employee = AiEmployee(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        department_id=uuid.uuid4(),
        template_id=uuid.uuid4(),
        name="Riley",
        role_title="Support Agent",
        status=AiEmployeeStatus.DRAFT,
    )
    assert employee.company_dna_version_id is None
    assert employee.permission_scope is None
    assert employee.autonomy_defaults == {}
    assert employee.created_at is None


def test_ai_employee_template_constructs() -> None:
    template = AiEmployeeTemplate(
        id=uuid.uuid4(),
        name="Support Agent",
        default_skills=["send_email", "query_crm"],
        system_prompt_scaffold="You are a helpful support agent.",
    )
    assert template.default_skills == ["send_email", "query_crm"]


def test_skill_constructs() -> None:
    skill = Skill(
        id=uuid.uuid4(),
        key="send_email",
        description="Send an email on the org's behalf",
        input_schema={"type": "object"},
        required_permission_scope={"resource": "email", "access": "write"},
    )
    assert skill.key == "send_email"
