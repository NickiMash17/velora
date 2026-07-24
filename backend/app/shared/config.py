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
    # Read by the migration that creates the velora_app role (see
    # alembic/versions/aa3e8dcefd79_*.py) — not used anywhere else. Kept
    # out of version control by living only in .env; the migration reads
    # it via Settings rather than a raw environment variable so it goes
    # through the same fail-fast, single mechanism as every other secret.
    velora_app_db_password: str = Field(
        ...,
        description="Password for the velora_app role — local-dev only, no secrets management yet",
    )
    redis_url: str = Field(..., description="Redis connection URL, e.g. redis://localhost:6379/0")

    # Signs and verifies access tokens (HS256 — symmetric is correct while
    # the issuer and validator are the same process; see
    # docs/architecture/Security.md §3.1 and this milestone's completion
    # report for why RS256 isn't needed yet). Local-dev only, same
    # tracked gap as velora_app_db_password until real secrets management
    # exists (Deployment.md §3.1).
    jwt_secret_key: str = Field(..., description="HS256 signing key for access tokens")
    access_token_ttl_minutes: int = Field(15, description="Security.md §3.1: '~15 min'")
    refresh_token_ttl_days: int = Field(
        30, description="Not specified in Security.md — a documented M3 decision, not a gap"
    )
    login_rate_limit_max_attempts: int = Field(5, description="Per normalized email, per window")
    login_rate_limit_window_seconds: int = Field(60, description="Fixed window for login attempts")

    log_level: str = "INFO"

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — env is read once per process, not per request."""
    return Settings()
