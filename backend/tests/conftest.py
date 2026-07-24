"""Shared fixtures for integration and isolation tests.

Both test categories need a real, freshly-migrated Postgres — this fixture
is factored out so container startup (slow) and migration application
happen once per test session, not once per test module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from alembic.config import Config
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from alembic import command
from app.shared.config import Settings


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


@pytest.fixture(scope="session")
def redis_container() -> RedisContainer:
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest_asyncio.fixture
async def redis_client(redis_container: RedisContainer) -> AsyncIterator[Redis]:
    """Flushes before each test — rate-limit tests rely on a clean counter
    space, and the container itself is session-scoped for speed."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = Redis.from_url(f"redis://{host}:{port}/0", decode_responses=True)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest.fixture
def auth_settings() -> Settings:
    """A Settings instance for exercising the identity/auth code paths in
    isolation from the real local-dev .env — database_url/redis_url are
    present only because Settings requires them, never actually connected
    to (application services take `session`/`redis_client` as explicit
    parameters, not from Settings)."""
    return Settings(
        database_url="postgresql+asyncpg://unused:unused@localhost/unused",
        migrations_database_url="postgresql+asyncpg://unused:unused@localhost/unused",
        velora_app_db_password="unused",
        redis_url="redis://localhost:6379/0",
        jwt_secret_key="test-only-jwt-secret-key-at-least-32-bytes-long",
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        login_rate_limit_max_attempts=5,
        login_rate_limit_window_seconds=60,
    )


@pytest_asyncio.fixture
async def app_client(
    migrated_engine: AsyncEngine,
    redis_client: Redis,
    auth_settings: Settings,
) -> AsyncIterator[httpx.AsyncClient]:
    """The shared app-under-test client for identity/auth integration
    tests. Wires app.dependency_overrides so requests hit the real
    testcontainers Postgres/Redis and a known auth_settings (jwt secret,
    ttls, rate-limit thresholds) — deliberately does NOT run the real
    lifespan (app.main.lifespan), which would connect to local-dev
    .env-configured infrastructure instead of the containers this session
    already started."""
    from app.main import create_app
    from app.shared.cache import get_redis_client
    from app.shared.config import get_settings
    from app.shared.db import get_db_session

    app = create_app()
    session_factory = async_sessionmaker(migrated_engine, expire_on_commit=False)

    async def _override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_settings] = lambda: auth_settings
    app.dependency_overrides[get_redis_client] = lambda: redis_client

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
