"""Structured logging per docs/architecture/Observability.md §2.

Every log line is structured JSON with, at minimum: timestamp, level,
request_id (bound per-request by the correlation middleware), module, and
message. DEBUG is clamped to INFO outside `local` — Observability.md is
explicit that DEBUG-level logs are "never shipped to production log
aggregation"; this makes that a structural guarantee, not a convention
someone has to remember to follow when setting an env var.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.shared.config import Settings

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _effective_level(settings: Settings) -> str:
    requested = settings.log_level.upper()
    if requested not in _VALID_LEVELS:
        requested = "INFO"
    if requested == "DEBUG" and not settings.is_local:
        return "INFO"
    return requested


def configure_logging(settings: Settings) -> None:
    """Call once at process startup, before any logger is used."""
    level_name = _effective_level(settings)
    level = getattr(logging, level_name)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    if level_name != settings.log_level.upper():
        structlog.get_logger("app.shared.logging").warning(
            "log_level_clamped",
            requested=settings.log_level.upper(),
            effective=level_name,
            reason="DEBUG is only permitted when environment=local",
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
