"""Async SQLAlchemy engine, declarative base, and the per-request session
dependency every API route uses to talk to the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
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


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — a fresh AsyncSession per request, from the
    session factory main.py's lifespan attaches to app.state. Endpoints
    depend on this directly; application-layer services (e.g.
    app.modules.identity.application.services) manage their own
    transaction boundaries on top of the session it yields.
    """
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session


async def check_database_connection(engine: AsyncEngine) -> None:
    """Raises if the database is unreachable. Used by /readyz only — see
    docs/architecture/Observability.md §7: liveness never checks dependencies,
    readiness does."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
