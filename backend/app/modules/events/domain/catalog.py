"""Registry of event types this codebase is authorized to emit.

Per docs/architecture/EventCatalog.md §1: "If an event isn't listed here,
it doesn't exist." This module mirrors that rule in code — nothing calls
`write_event` with a hand-typed topic string; every emission goes through
`topic_for()`, so a type/topic pair can never drift apart, and an
uncataloged event type fails loudly instead of silently going out with a
made-up topic.

Only events with a real emitter in this codebase are registered here —
see docs/architecture/EventCatalog.md §5.1 for their full producer/
consumer/payload documentation. Do not add speculative future events.
"""

from __future__ import annotations

ORGANIZATION_CREATED = "OrganizationCreated"
MEMBERSHIP_ACTIVATED = "MembershipActivated"
DEPARTMENT_CREATED = "DepartmentCreated"
COMPANY_DNA_DRAFT_CREATED = "CompanyDnaDraftCreated"
COMPANY_DNA_COMPILED = "CompanyDnaCompiled"
COMPANY_DNA_PUBLISHED = "CompanyDnaPublished"
EMPLOYEE_HIRED = "EmployeeHired"
EMPLOYEE_CONFIGURED = "EmployeeConfigured"
EMPLOYEE_ACTIVATED = "EmployeeActivated"
EMPLOYEE_PAUSED = "EmployeePaused"
EMPLOYEE_RETIRED = "EmployeeRetired"

_TOPICS: dict[str, str] = {
    ORGANIZATION_CREATED: "organization.created",
    MEMBERSHIP_ACTIVATED: "membership.activated",
    DEPARTMENT_CREATED: "department.created",
    COMPANY_DNA_DRAFT_CREATED: "company_dna.draft_created",
    COMPANY_DNA_COMPILED: "company_dna.compiled",
    COMPANY_DNA_PUBLISHED: "company_dna.published",
    EMPLOYEE_HIRED: "employee.hired",
    EMPLOYEE_CONFIGURED: "employee.configured",
    EMPLOYEE_ACTIVATED: "employee.activated",
    EMPLOYEE_PAUSED: "employee.paused",
    EMPLOYEE_RETIRED: "employee.retired",
}


def topic_for(event_type: str) -> str:
    try:
        return _TOPICS[event_type]
    except KeyError as exc:
        raise ValueError(
            f"'{event_type}' is not a cataloged event type — add it to "
            "docs/architecture/EventCatalog.md and this registry before emitting it."
        ) from exc
