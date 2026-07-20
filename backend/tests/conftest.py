"""Shared fixtures for integration and isolation tests.

Both test categories need a real, freshly-migrated Postgres — this fixture
is factored out so container startup (slow) and migration application
happen once per test session, not once per test module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from alembic import command


def _run_migrations(async_url: str) -> None:
    """Runs the real Alembic migration chain against `async_url` — this
    proves the actual migration file (not a hand-rolled test schema) is
    what's under test, per EngineeringStandards.md §4's integration-test
    convention.

    Must be the asyncpg-scheme URL: alembic/env.py's `run_migrations_online`
    always builds an async engine (`async_engine_from_config`) regardless
    of caller, so a psycopg2-scheme URL fails at the driver-import step,
    not just silently falls back to sync — this bit us once already."""
    alembic_ini_path = str(__file__).rsplit("tests", 1)[0] + "alembic.ini"
    config = Config(alembic_ini_path)
    config.set_main_option("sqlalchemy.url", async_url)
    command.upgrade(config, "head")


def _app_role_url(pg: PostgresContainer) -> str:
    """The migration (aa3e8dcefd79_*.py) creates a non-superuser
    `velora_app` role with a fixed local-dev-only password — this builds
    its connection URL from the container's host/port, swapping in that
    role's credentials in place of the superuser ones testcontainers
    provisions the container with.

    Tests MUST use this, not the superuser URL, for anything exercising
    RLS: Postgres superusers bypass Row-Level Security unconditionally,
    regardless of FORCE ROW LEVEL SECURITY — see this milestone's
    completion report for how that was discovered."""
    host = pg.get_container_host_ip()
    port = pg.get_exposed_port(5432)
    return f"postgresql+asyncpg://velora_app:velora_app_dev_only@{host}:{port}/velora"


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    with PostgresContainer(
        "postgres:16-alpine", username="velora", password="velora", dbname="velora"
    ) as pg:
        admin_url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        _run_migrations(admin_url)  # must be the superuser/table-owning role — it runs DDL
        yield pg


@pytest_asyncio.fixture(scope="session")
async def migrated_engine(postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    """Connects as velora_app (non-superuser) — the role every test query
    actually runs as, so RLS applies exactly as it would for the running
    application."""
    engine = create_async_engine(_app_role_url(postgres_container), pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(migrated_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A fresh AsyncSession per test — no transaction pre-opened, so tests
    are free to manage their own transaction boundaries (e.g. via
    app.shared.tenancy.tenant_scoped_transaction)."""
    session_factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
