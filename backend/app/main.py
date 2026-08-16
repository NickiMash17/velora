"""FastAPI application assembly — wires routers and middleware, not business
logic (docs/engineering/EngineeringStandards.md §2.1). Health checks are
deliberately unversioned (docs/architecture/API.md §3); business endpoints
(Milestone 3 onward) live under /v1."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.modules.company_dna.api.router import router as company_dna_router
from app.modules.departments.api.router import router as departments_router
from app.modules.identity.api.router import router as identity_router
from app.modules.organizations.api.router import router as organizations_router
from app.shared.cache import create_redis_client
from app.shared.config import get_settings
from app.shared.db import create_engine, create_session_factory
from app.shared.errors import register_exception_handlers
from app.shared.health import router as health_router
from app.shared.logging import configure_logging, get_logger
from app.shared.middleware import RequestIDMiddleware, RequestLoggingMiddleware

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)

    app.state.db_engine = create_engine(settings)
    app.state.db_session_factory = create_session_factory(app.state.db_engine)
    app.state.redis_client = create_redis_client(settings)

    logger.info("app_startup", environment=settings.environment)
    try:
        yield
    finally:
        await app.state.db_engine.dispose()
        await app.state.redis_client.aclose()
        logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Order matters: outermost-added middleware runs first on the request,
    # last on the response — RequestIDMiddleware must bind the id before
    # RequestLoggingMiddleware logs it.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(identity_router, prefix="/v1")
    app.include_router(organizations_router, prefix="/v1")
    app.include_router(departments_router, prefix="/v1")
    app.include_router(company_dna_router, prefix="/v1")

    return app


app = create_app()
