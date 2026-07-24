"""Repositories for User and RefreshToken.

Deliberately have NO organization_id parameter on any method — neither
table is tenant-scoped data (see
app/modules/identity/domain/entities.py). This is the one place in the
codebase where that's correct by design, not an oversight of
docs/architecture/Database.md §2.2's "every repository method requires
organization_id" rule, which applies to tenant-scoped tables specifically.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities import RefreshToken, User
from app.modules.identity.infrastructure.orm import RefreshTokenORM, UserORM


def _user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        mfa_enabled=row.mfa_enabled,
        token_version=row.token_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _refresh_token_to_domain(row: RefreshTokenORM) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        family_id=row.family_id,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_id=row.replaced_by_id,
        issued_at=row.issued_at,
    )


class UserRepository:
    async def create(self, session: AsyncSession, user: User) -> User:
        """Returns the persisted User with server-generated fields
        (created_at, updated_at) populated — `flush()` triggers an INSERT
        with RETURNING, which SQLAlchemy uses to populate those onto the
        ORM instance automatically, but the caller's *domain* object
        passed in never sees them unless we read them back explicitly."""
        row = UserORM(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            mfa_enabled=user.mfa_enabled,
            token_version=user.token_version,
        )
        session.add(row)
        await session.flush()
        return _user_to_domain(row)

    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        row = await session.get(UserORM, user_id)
        return _user_to_domain(row) if row else None

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(UserORM).where(UserORM.email == email))
        row = result.scalar_one_or_none()
        return _user_to_domain(row) if row else None

    async def increment_token_version(self, session: AsyncSession, user_id: UUID) -> None:
        """Invalidates every access token issued before this call, on
        their next validation (see app/modules/identity/api/dependencies.py).
        Not called by any M3 flow yet — see User.token_version's docstring."""
        await session.execute(
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(token_version=UserORM.token_version + 1)
        )


class RefreshTokenRepository:
    async def create(self, session: AsyncSession, token: RefreshToken) -> None:
        session.add(
            RefreshTokenORM(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                family_id=token.family_id,
                expires_at=token.expires_at,
            )
        )
        await session.flush()

    async def get_by_hash(self, session: AsyncSession, token_hash: str) -> RefreshToken | None:
        result = await session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return _refresh_token_to_domain(row) if row else None

    async def mark_rotated(
        self, session: AsyncSession, token_id: UUID, replaced_by_id: UUID
    ) -> None:
        await session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.id == token_id)
            .values(revoked_at=func.now(), replaced_by_id=replaced_by_id)
        )

    async def revoke_family(self, session: AsyncSession, family_id: UUID) -> None:
        """Replay protection: called when a refresh token that was already
        rotated (revoked_at is set) gets presented again — the entire
        family is revoked, forcing re-authentication, since reuse of a
        dead token is the signal a refresh token has been stolen."""
        await session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.family_id == family_id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
