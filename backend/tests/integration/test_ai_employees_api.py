"""Integration tests for the M5 Checkpoint 3 AI Employees API — real
Postgres + Redis via the shared app_client fixture, same pattern
established for departments/company-dna's endpoints in Checkpoints 1/2.

Templates have no creation endpoint in M5 (RLS matrix: "not in M5 API") —
tests seed them directly via the repository, using the same underlying
Postgres the `app_client` fixture's session factory is bound to (`db_session`
and `app_client` share `migrated_engine`).
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_employees.domain.entities import AiEmployeeTemplate
from app.modules.ai_employees.infrastructure.repository import AiEmployeeTemplateRepository

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"emp-api-{uuid.uuid4().hex[:10]}@example.com"


async def _register_login_and_create_org(app_client: httpx.AsyncClient) -> dict:
    email = _unique_email()
    password = "a-strong-password"
    await app_client.post("/v1/users", json={"email": email, "password": password})
    login = (
        await app_client.post("/v1/auth/login", json={"email": email, "password": password})
    ).json()

    create = await app_client.post(
        "/v1/organizations",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"name": "Acme Inc.", "refresh_token": login["refresh_token"]},
    )
    return create.json()["tokens"]


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_template(db_session: AsyncSession) -> str:
    template = AiEmployeeTemplate(
        id=uuid.uuid4(),
        name="Support Agent",
        default_skills=["send_email"],
        system_prompt_scaffold="You are a helpful support agent.",
    )
    created = await AiEmployeeTemplateRepository().create(db_session, template)
    await db_session.commit()
    return str(created.id)


async def _create_department(app_client: httpx.AsyncClient, tokens: dict) -> str:
    response = await app_client.post(
        "/v1/departments",
        headers=_auth(tokens),
        json={"name": "Support", "function_type": "support"},
    )
    return response.json()["id"]


async def _create_dna_version(app_client: httpx.AsyncClient, tokens: dict) -> str:
    response = await app_client.post(
        "/v1/company-dna/versions", headers=_auth(tokens), json={"version": "1.0.0"}
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_hire_requires_authentication(app_client: httpx.AsyncClient) -> None:
    response = await app_client.post(
        "/v1/ai-employees",
        json={
            "department_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
            "name": "Riley",
            "role_title": "Support Agent",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hire_succeeds_for_org_admin(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    department_id = await _create_department(app_client, tokens)
    template_id = await _create_template(db_session)

    response = await app_client.post(
        "/v1/ai-employees",
        headers=_auth(tokens),
        json={
            "department_id": department_id,
            "template_id": template_id,
            "name": "Riley",
            "role_title": "Support Agent",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Riley"
    assert body["status"] == "draft"
    assert body["autonomy_defaults"] == {}


@pytest.mark.asyncio
async def test_hire_returns_404_for_unknown_department(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    template_id = await _create_template(db_session)

    response = await app_client.post(
        "/v1/ai-employees",
        headers=_auth(tokens),
        json={
            "department_id": str(uuid.uuid4()),
            "template_id": template_id,
            "name": "Riley",
            "role_title": "Support Agent",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "department_not_found"


@pytest.mark.asyncio
async def test_hire_returns_404_for_unknown_template(
    app_client: httpx.AsyncClient,
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    department_id = await _create_department(app_client, tokens)

    response = await app_client.post(
        "/v1/ai-employees",
        headers=_auth(tokens),
        json={
            "department_id": department_id,
            "template_id": str(uuid.uuid4()),
            "name": "Riley",
            "role_title": "Support Agent",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ai_employee_template_not_found"


async def _hire(app_client: httpx.AsyncClient, tokens: dict, db_session: AsyncSession) -> str:
    department_id = await _create_department(app_client, tokens)
    template_id = await _create_template(db_session)
    create = await app_client.post(
        "/v1/ai-employees",
        headers=_auth(tokens),
        json={
            "department_id": department_id,
            "template_id": template_id,
            "name": "Riley",
            "role_title": "Support Agent",
        },
    )
    assert create.status_code == 201
    return create.json()["id"]


@pytest.mark.asyncio
async def test_configure_requires_dna_version_and_permission_scope(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire(app_client, tokens, db_session)

    response = await app_client.patch(
        f"/v1/ai-employees/{employee_id}/configure",
        headers=_auth(tokens),
        json={"permission_scope": {}},
    )

    assert response.status_code == 422  # company_dna_version_id is a required field


@pytest.mark.asyncio
async def test_configure_succeeds_and_transitions_to_configured(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire(app_client, tokens, db_session)
    dna_version_id = await _create_dna_version(app_client, tokens)

    response = await app_client.patch(
        f"/v1/ai-employees/{employee_id}/configure",
        headers=_auth(tokens),
        json={
            "company_dna_version_id": dna_version_id,
            "permission_scope": {"resource": "email", "access": "write"},
            "autonomy_defaults": {"send_email": "approve"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "configured"
    assert body["autonomy_defaults"] == {"send_email": "approve"}


@pytest.mark.asyncio
async def test_configure_rejects_invalid_autonomy_level(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Autonomy taxonomy is locked to autonomous/notify/approve — the old
    "auto" value must be rejected, not silently accepted."""
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire(app_client, tokens, db_session)
    dna_version_id = await _create_dna_version(app_client, tokens)

    response = await app_client.patch(
        f"/v1/ai-employees/{employee_id}/configure",
        headers=_auth(tokens),
        json={
            "company_dna_version_id": dna_version_id,
            "permission_scope": {},
            "autonomy_defaults": {"send_email": "auto"},
        },
    )

    assert response.status_code == 422


async def _hire_and_configure(
    app_client: httpx.AsyncClient, tokens: dict, db_session: AsyncSession
) -> str:
    employee_id = await _hire(app_client, tokens, db_session)
    dna_version_id = await _create_dna_version(app_client, tokens)
    configure = await app_client.patch(
        f"/v1/ai-employees/{employee_id}/configure",
        headers=_auth(tokens),
        json={"company_dna_version_id": dna_version_id, "permission_scope": {}},
    )
    assert configure.status_code == 200
    return employee_id


@pytest.mark.asyncio
async def test_activate_rejects_a_draft_employee(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire(app_client, tokens, db_session)

    response = await app_client.post(
        f"/v1/ai-employees/{employee_id}/activate", headers=_auth(tokens)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_ai_employee_transition"


@pytest.mark.asyncio
async def test_full_lifecycle_configure_activate_pause_activate_retire(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire_and_configure(app_client, tokens, db_session)

    activate = await app_client.post(
        f"/v1/ai-employees/{employee_id}/activate", headers=_auth(tokens)
    )
    assert activate.status_code == 200
    assert activate.json()["status"] == "active"

    pause = await app_client.post(f"/v1/ai-employees/{employee_id}/pause", headers=_auth(tokens))
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    resume = await app_client.post(
        f"/v1/ai-employees/{employee_id}/activate", headers=_auth(tokens)
    )
    assert resume.status_code == 200
    assert resume.json()["status"] == "active"

    retire = await app_client.post(f"/v1/ai-employees/{employee_id}/retire", headers=_auth(tokens))
    assert retire.status_code == 200
    assert retire.json()["status"] == "retired"


@pytest.mark.asyncio
async def test_retire_rejects_a_draft_employee(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    employee_id = await _hire(app_client, tokens, db_session)

    response = await app_client.post(
        f"/v1/ai-employees/{employee_id}/retire", headers=_auth(tokens)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_ai_employee_transition"


@pytest.mark.asyncio
async def test_get_ai_employee_returns_404_for_unknown_id(app_client: httpx.AsyncClient) -> None:
    tokens = await _register_login_and_create_org(app_client)

    response = await app_client.get(
        f"/v1/ai-employees/{uuid.uuid4()}", headers=_auth(tokens)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ai_employee_not_found"


@pytest.mark.asyncio
async def test_list_ai_employees_filters_by_department_and_status(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = await _register_login_and_create_org(app_client)
    template_id = await _create_template(db_session)
    department_a = await _create_department(app_client, tokens)
    department_b = (
        await app_client.post(
            "/v1/departments",
            headers=_auth(tokens),
            json={"name": "Sales", "function_type": "sales"},
        )
    ).json()["id"]

    for department_id, name in [(department_a, "Riley"), (department_b, "Sam")]:
        await app_client.post(
            "/v1/ai-employees",
            headers=_auth(tokens),
            json={
                "department_id": department_id,
                "template_id": template_id,
                "name": name,
                "role_title": "Agent",
            },
        )

    response = await app_client.get(
        f"/v1/ai-employees?department_id={department_a}", headers=_auth(tokens)
    )
    assert response.status_code == 200
    assert [i["name"] for i in response.json()["items"]] == ["Riley"]

    status_response = await app_client.get(
        "/v1/ai-employees?status=draft", headers=_auth(tokens)
    )
    assert status_response.status_code == 200
    assert {i["name"] for i in status_response.json()["items"]} == {"Riley", "Sam"}


@pytest.mark.asyncio
async def test_list_ai_employee_templates_is_visible_identically_across_organizations(
    app_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Global catalog, no RLS — the same template must be visible
    regardless of which org's token is used."""
    template_id = await _create_template(db_session)

    tokens_a = await _register_login_and_create_org(app_client)
    tokens_b = await _register_login_and_create_org(app_client)

    response_a = await app_client.get("/v1/ai-employee-templates", headers=_auth(tokens_a))
    response_b = await app_client.get("/v1/ai-employee-templates", headers=_auth(tokens_b))

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    ids_a = {t["id"] for t in response_a.json()["items"]}
    ids_b = {t["id"] for t in response_b.json()["items"]}
    assert template_id in ids_a
    assert template_id in ids_b
