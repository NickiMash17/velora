"""Liveness and readiness endpoints.

Per docs/architecture/Observability.md §7:
- /healthz (liveness): process is up and can serve requests at all. No
  dependency checks — a transient DB blip must not get a healthy process
  killed and restarted.
- /readyz (readiness): checks Postgres and Redis connectivity. A container
  fails readiness (pulled from the load balancer) before it fails liveness.

Both are unversioned (no /v1 prefix) — they are infrastructure endpoints,
not part of the versioned public API contract (docs/architecture/API.md §3).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.cache import check_redis_connection
from app.shared.db import check_database_connection

logger = structlog.get_logger("app.health")

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    engine: AsyncEngine = request.app.state.db_engine
    redis_client = request.app.state.redis_client

    checks: dict[str, str] = {}
    healthy = True

    try:
        await check_database_connection(engine)
        checks["database"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", dependency="database")
        checks["database"] = "unreachable"
        healthy = False

    try:
        await check_redis_connection(redis_client)
        checks["redis"] = "ok"
    except Exception:
        logger.warning("readiness_check_failed", dependency="redis")
        checks["redis"] = "unreachable"
        healthy = False

    body = {"status": "ready" if healthy else "not_ready", "checks": checks}
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=body,
    )
