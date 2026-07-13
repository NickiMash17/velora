"""Async SQLAlchemy engine and declarative base.

No ORM models are defined against `Base` yet — Milestone 1 has no business
logic (docs/architecture/AGENTS.md constraint). `Base` exists now purely as
the registry Alembic's `env.py` needs to point `target_metadata` at; it is
infrastructure wiring, not a placeholder feature. The first real models
land with the identity/organizations migrations in Milestone 2.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import Settings


class Base(DeclarativeBase):
    pass


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def check_database_connection(engine: AsyncEngine) -> None:
    """Raises if the database is unreachable. Used by /readyz only — see
    docs/architecture/Observability.md §7: liveness never checks dependencies,
    readiness does."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
