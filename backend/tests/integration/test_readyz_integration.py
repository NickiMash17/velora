"""Integration test for /readyz against real Postgres and Redis, per
docs/engineering/EngineeringStandards.md §4 ("Integration tests — real
Postgres/Redis/Qdrant via test containers"). Ephemeral containers, bound to
random free host ports by testcontainers — this deliberately does not rely
on docker-compose.yml's fixed ports, so it stays hermetic and reproducible
in CI regardless of what else is running on the host (see the port-5432
conflict this project's docker-compose hit locally).
"""

from __future__ import annotations

import os

import httpx
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.shared.config import get_settings


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer(
        "postgres:16-alpine", username="velora", password="velora", dbname="velora"
    ) as pg:
        yield pg


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture
def app_client(postgres_container, redis_container):
    async_db_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"

    env_backup = {k: os.environ.get(k) for k in ("DATABASE_URL", "REDIS_URL", "ENVIRONMENT")}
    os.environ["DATABASE_URL"] = async_db_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["ENVIRONMENT"] = "local"
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()

    yield app

    get_settings.cache_clear()
    for key, value in env_backup.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.mark.asyncio
async def test_readyz_reports_ok_against_real_dependencies(app_client):
    transport = httpx.ASGITransport(app=app_client)

    async with app_client.router.lifespan_context(app_client):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"database": "ok", "redis": "ok"}
