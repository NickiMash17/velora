"""Async Redis client used for connectivity checks (/readyz) and, from
Milestone 3 onward, auth rate limiting. No caching/business use yet."""

from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis

from app.shared.config import Settings


def create_redis_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis_connection(client: Redis) -> None:
    """Raises if Redis is unreachable. Used by /readyz only."""
    await client.ping()


def get_redis_client(request: Request) -> Redis:
    """FastAPI dependency — mirrors app.shared.db.get_db_session. Routes
    depend on this rather than reaching into request.app.state directly,
    which is also what makes it overridable via app.dependency_overrides
    in tests."""
    return request.app.state.redis_client
