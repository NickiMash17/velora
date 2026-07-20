"""Repository for User.

Deliberately has NO organization_id parameter on any method — users are
not tenant-scoped data (see app/modules/identity/domain/entities.py). This
is the one repository in the codebase where that's correct by design, not
an oversight of docs/architecture/Database.md §2.2's "every repository
method requires organization_id" rule, which applies to tenant-scoped
tables specifically.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities import User
from app.modules.identity.infrastructure.orm import UserORM


def _to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        mfa_enabled=row.mfa_enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class UserRepository:
    async def create(self, session: AsyncSession, user: User) -> None:
        session.add(
            UserORM(
                id=user.id,
                email=user.email,
                password_hash=user.password_hash,
                mfa_enabled=user.mfa_enabled,
            )
        )
        await session.flush()

    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        row = await session.get(UserORM, user_id)
        return _to_domain(row) if row else None

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(UserORM).where(UserORM.email == email))
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None
