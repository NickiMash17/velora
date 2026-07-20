import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make `app` importable when Alembic is invoked from backend/ (its natural
# working directory) without requiring the project to be pip-installed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.shared.config import get_settings  # noqa: E402
from app.shared.db import Base  # noqa: E402

# Importing each module's ORM classes registers their tables on
# Base.metadata as a side effect — required for `alembic revision
# --autogenerate` to see them. Nothing here is used directly; the imports
# themselves are the point. Add a line whenever a module gains its first
# ORM model.
from app.modules.events.infrastructure.orm import EventORM  # noqa: E402,F401
from app.modules.identity.infrastructure.orm import UserORM  # noqa: E402,F401
from app.modules.organizations.infrastructure.orm import (  # noqa: E402,F401
    OrganizationMembershipORM,
    OrganizationORM,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The real DSN comes from app settings (env-based config,
# docs/architecture/Deployment.md §3) — never hardcoded in alembic.ini.
# Specifically `migrations_database_url`, NOT `database_url`: migrations
# need the table-owning role to run DDL, while the app's own
# `database_url` connects as the non-superuser velora_app role so RLS
# actually applies to it (see Settings' docstring in app/shared/config.py
# and alembic/versions/aa3e8dcefd79_*.py).
#
# This is only applied when the caller hasn't already set a URL. Tests
# (see tests/conftest.py) construct a Config and set sqlalchemy.url to a
# testcontainers-managed Postgres BEFORE invoking alembic.command.upgrade()
# in-process — unconditionally overwriting that here would silently run
# migrations against local dev Postgres instead of the ephemeral test
# database, which is exactly the bug this comment exists to prevent
# reintroducing.
_PLACEHOLDER_URL = "driver://user:pass@localhost/dbname"
if config.get_main_option("sqlalchemy.url") in (None, _PLACEHOLDER_URL):
    config.set_main_option("sqlalchemy.url", get_settings().migrations_database_url)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
