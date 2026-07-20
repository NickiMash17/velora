"""Environment-based application configuration.

Per docs/architecture/Deployment.md §3: every environment-specific value is
injected via environment variables and validated at startup — the app fails
fast on missing/malformed config rather than failing confusingly mid-request.
No environment-specific `if settings.environment == "production"` branches
belong in application code; behavior differences are configuration, not
conditionals.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "velora-backend"
    environment: Environment = "local"

    # Required — no default, so a missing value fails startup immediately
    # rather than surfacing as a confusing error on the first request.
    #
    # database_url is the APPLICATION's runtime DSN — connects as a
    # non-superuser, non-table-owning role (velora_app) so Row-Level
    # Security actually applies to it. migrations_database_url is a
    # SEPARATE, more privileged DSN (the table-owning role) used only by
    # Alembic to run DDL — Postgres superusers/table owners bypass RLS
    # unconditionally, so the app must never connect with those
    # credentials. See alembic/versions/aa3e8dcefd79_*.py for how the
    # velora_app role is created.
    database_url: str = Field(..., description="Async SQLAlchemy DSN, e.g. postgresql+asyncpg://...")
    migrations_database_url: str = Field(
        ...,
        description="Async SQLAlchemy DSN for the table-owning/migration role, Alembic only",
    )
    redis_url: str = Field(..., description="Redis connection URL, e.g. redis://localhost:6379/0")

    log_level: str = "INFO"

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — env is read once per process, not per request."""
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment, not the constructor call
