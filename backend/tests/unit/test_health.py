"""Unit tests for /healthz and /readyz.

Per docs/architecture/Observability.md §7: liveness must never depend on
downstream services (a transient DB blip shouldn't get a healthy process
killed), while readiness must actually check them. These tests point the
app at unreachable database/redis addresses (closed local ports, no network
call ever completes) specifically to prove that distinction — no real
Postgres/Redis needed here, which is what keeps this a unit test rather
than an integration test.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.shared.config import get_settings


@pytest.fixture
def unreachable_app_client():
    """App configured against closed local ports — no server ever listens
    on port 1, so connection attempts fail fast rather than hanging."""
    env_backup = {
        k: os.environ.get(k)
        for k in ("DATABASE_URL", "REDIS_URL", "ENVIRONMENT", "LOG_LEVEL")
    }
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://x:x@localhost:1/x"
    os.environ["REDIS_URL"] = "redis://localhost:1/0"
    os.environ["ENVIRONMENT"] = "local"
    os.environ["LOG_LEVEL"] = "DEBUG"
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client

    get_settings.cache_clear()
    for key, value in env_backup.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_healthz_ok_even_when_dependencies_are_unreachable(unreachable_app_client):
    response = unreachable_app_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_503_when_dependencies_are_unreachable(unreachable_app_client):
    response = unreachable_app_client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unreachable"
    assert body["checks"]["redis"] == "unreachable"
