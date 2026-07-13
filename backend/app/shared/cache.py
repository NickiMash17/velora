"""Async Redis client used for connectivity checks (/readyz) and, from
Milestone 3 onward, auth rate limiting. No caching/business use yet."""

from __future__ import annotations

from redis.asyncio import Redis

from app.shared.config import Settings


def create_redis_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis_connection(client: Redis) -> None:
    """Raises if Redis is unreachable. Used by /readyz only."""
    await client.ping()
