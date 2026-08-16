"""Repository layer for ai_employee_templates, skills, ai_employees, and
ai_employee_skills.

Tenant-scoped methods (`AiEmployeeRepository`, `AiEmployeeSkillRepository`)
take `organization_id` explicitly, per docs/architecture/Database.md §2.2
("no unscoped query method exposed on tenant-scoped repositories") —
though the actual, load-bearing enforcement is Row-Level Security (see
app/shared/tenancy.py); this is defense-in-depth and call-site clarity,
not the guarantee itself. `AiEmployeeTemplateRepository`/`SkillRepository`
take no `organization_id` at all — they are global catalogs (locked
decision A1), and an "unscoped" method here is correct, not a gap.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_employees.domain.entities import AiEmployee, AiEmployeeTemplate, Skill
from app.modules.ai_employees.infrastructure.orm import (
    AiEmployeeORM,
    AiEmployeeSkillORM,
    AiEmployeeTemplateORM,
    SkillORM,
)


def _template_to_domain(row: AiEmployeeTemplateORM) -> AiEmployeeTemplate:
    return AiEmployeeTemplate(
        id=row.id,
        name=row.name,
        default_skills=list(row.default_skills),
        system_prompt_scaffold=row.system_prompt_scaffold,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _skill_to_domain(row: SkillORM) -> Skill:
    return Skill(
        id=row.id,
        key=row.key,
        description=row.description,
        input_schema=dict(row.input_schema),
        required_permission_scope=dict(row.required_permission_scope),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _employee_to_domain(row: AiEmployeeORM) -> AiEmployee:
    return AiEmployee(
        id=row.id,
        organization_id=row.organization_id,
        department_id=row.department_id,
        template_id=row.template_id,
        name=row.name,
        role_title=row.role_title,
        status=row.status,
        company_dna_version_id=row.company_dna_version_id,
        permission_scope=dict(row.permission_scope) if row.permission_scope else None,
        autonomy_defaults=dict(row.autonomy_defaults),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class AiEmployeeTemplateRepository:
    """No HTTP endpoint creates/modifies templates in M5 (RLS matrix:
    "not in M5 API" — platform-level catalog maintenance only, per the
    locked contract). `create()` exists purely so tests (and, later, an
    out-of-band seeding process) have a way to populate this catalog —
    it is not wired to any router."""

    async def create(
        self, session: AsyncSession, template: AiEmployeeTemplate
    ) -> AiEmployeeTemplate:
        row = AiEmployeeTemplateORM(
            id=template.id,
            name=template.name,
            default_skills=template.default_skills,
            system_prompt_scaffold=template.system_prompt_scaffold,
        )
        session.add(row)
        await session.flush()
        return _template_to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, template_id: UUID
    ) -> AiEmployeeTemplate | None:
        row = await session.get(AiEmployeeTemplateORM, template_id)
        return _template_to_domain(row) if row else None

    async def list_all(
        self,
        session: AsyncSession,
        *,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[AiEmployeeTemplate]:
        """No `organization_id` filter anywhere — global catalog, same
        keyset-pagination convention established in departments/company_dna."""
        query = select(AiEmployeeTemplateORM)
        if cursor is not None:
            query = query.where(
                tuple_(AiEmployeeTemplateORM.created_at, AiEmployeeTemplateORM.id) > cursor
            )
        query = query.order_by(AiEmployeeTemplateORM.created_at, AiEmployeeTemplateORM.id).limit(
            limit
        )
        result = await session.execute(query)
        return [_template_to_domain(row) for row in result.scalars().all()]


class SkillRepository:
    """Same treatment as AiEmployeeTemplateRepository — global catalog,
    no HTTP endpoint in M5, `create()` exists for test/seed use only."""

    async def create(self, session: AsyncSession, skill: Skill) -> Skill:
        row = SkillORM(
            id=skill.id,
            key=skill.key,
            description=skill.description,
            input_schema=skill.input_schema,
            required_permission_scope=skill.required_permission_scope,
        )
        session.add(row)
        await session.flush()
        return _skill_to_domain(row)

    async def get_by_id(self, session: AsyncSession, skill_id: UUID) -> Skill | None:
        row = await session.get(SkillORM, skill_id)
        return _skill_to_domain(row) if row else None

    async def list_all(self, session: AsyncSession) -> list[Skill]:
        result = await session.execute(select(SkillORM))
        return [_skill_to_domain(row) for row in result.scalars().all()]


class AiEmployeeRepository:
    async def create(self, session: AsyncSession, employee: AiEmployee) -> AiEmployee:
        """Returns the persisted AiEmployee with server-generated fields
        (created_at, updated_at) populated — same fix/reason as
        OrganizationRepository.create()'s own docstring."""
        row = AiEmployeeORM(
            id=employee.id,
            organization_id=employee.organization_id,
            department_id=employee.department_id,
            template_id=employee.template_id,
            name=employee.name,
            role_title=employee.role_title,
            company_dna_version_id=employee.company_dna_version_id,
            status=employee.status,
            permission_scope=employee.permission_scope,
            autonomy_defaults=employee.autonomy_defaults,
        )
        session.add(row)
        await session.flush()
        return _employee_to_domain(row)

    async def save(self, session: AsyncSession, employee: AiEmployee) -> AiEmployee:
        """Persists mutations to an already-persisted row (`employee.id`
        must already exist — callers always fetch via `get_by_id` first).

        `flush()` alone does not populate `updated_at` client-side for an
        UPDATE (its `onupdate=func.now()` value stays server-side) —
        `refresh()` makes the re-fetch explicit and awaited, avoiding the
        `MissingGreenlet` failure discovered and fixed in Checkpoint 2's
        `CompanyDnaVersionRepository.save()`."""
        row = await session.get(AiEmployeeORM, employee.id)
        assert row is not None
        row.department_id = employee.department_id
        row.template_id = employee.template_id
        row.name = employee.name
        row.role_title = employee.role_title
        row.company_dna_version_id = employee.company_dna_version_id
        row.status = employee.status
        row.permission_scope = employee.permission_scope
        row.autonomy_defaults = employee.autonomy_defaults
        await session.flush()
        await session.refresh(row)
        return _employee_to_domain(row)

    async def get_by_id(
        self, session: AsyncSession, organization_id: UUID, employee_id: UUID
    ) -> AiEmployee | None:
        result = await session.execute(
            select(AiEmployeeORM).where(
                AiEmployeeORM.organization_id == organization_id,
                AiEmployeeORM.id == employee_id,
            )
        )
        row = result.scalar_one_or_none()
        return _employee_to_domain(row) if row else None

    async def list_for_organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
        *,
        department_id: UUID | None = None,
        status: Any | None = None,
        cursor: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> list[AiEmployee]:
        """Keyset-paginated on `(created_at, id)` — same convention
        established in departments/company_dna. `department_id`/`status`
        filters match WireframeSpec.md §8's documented roster filters."""
        query = select(AiEmployeeORM).where(AiEmployeeORM.organization_id == organization_id)
        if department_id is not None:
            query = query.where(AiEmployeeORM.department_id == department_id)
        if status is not None:
            query = query.where(AiEmployeeORM.status == status)
        if cursor is not None:
            query = query.where(tuple_(AiEmployeeORM.created_at, AiEmployeeORM.id) > cursor)
        query = query.order_by(AiEmployeeORM.created_at, AiEmployeeORM.id).limit(limit)
        result = await session.execute(query)
        return [_employee_to_domain(row) for row in result.scalars().all()]


class AiEmployeeSkillRepository:
    """No HTTP endpoint binds skills to an employee in this checkpoint —
    see application/services.py's module docstring for why. `create()`
    exists so tests can construct valid rows directly against the real
    schema/RLS policy, not wired to any router."""

    async def create(
        self, session: AsyncSession, *, organization_id: UUID, ai_employee_id: UUID, skill_id: UUID
    ) -> None:
        row = AiEmployeeSkillORM(
            ai_employee_id=ai_employee_id, skill_id=skill_id, organization_id=organization_id
        )
        session.add(row)
        await session.flush()

    async def list_for_employee(
        self, session: AsyncSession, organization_id: UUID, ai_employee_id: UUID
    ) -> list[UUID]:
        result = await session.execute(
            select(AiEmployeeSkillORM.skill_id).where(
                AiEmployeeSkillORM.organization_id == organization_id,
                AiEmployeeSkillORM.ai_employee_id == ai_employee_id,
            )
        )
        return list(result.scalars().all())
