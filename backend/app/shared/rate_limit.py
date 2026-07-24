"""Generic Redis fixed-window rate limiter.

Not identity-specific — usable by anything that needs a simple per-key
attempt counter. Deliberately has no organization_id/tenant concept: per
docs/architecture/Security.md, rate limiting is documented per
organization/API-key/Digital-Employee for AI Runtime resource abuse
(§10) — a different problem from this milestone's login-brute-force
protection, which by definition happens before any tenant context
exists. Keying this on anything tenant-related would be a real
architectural mistake, not just an unnecessary one.

Fixed window (INCR + EXPIRE), not a sliding window or token bucket —
simple, no Lua scripting needed, and correct enough for login-attempt
throttling where the exact boundary behavior at a window edge doesn't
matter much. A token bucket would be worth the extra complexity for
smooth, sustained-rate limiting (e.g. Model Gateway calls); a fixed
window is not worse for "block after N attempts in M seconds."
"""

from __future__ import annotations

from redis.asyncio import Redis


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


async def check_and_increment(
    redis_client: Redis,
    *,
    key: str,
    max_attempts: int,
    window_seconds: int,
) -> None:
    """Raises RateLimitExceededError if `key` has already hit
    `max_attempts` within the current window; otherwise increments and
    returns. The increment happens unconditionally, before any caller-side
    check of whether the underlying resource (e.g. an email/account)
    exists — this is what keeps rate-limit behavior from leaking whether
    a given key corresponds to something real.
    """
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)

    if current > max_attempts:
        ttl = await redis_client.ttl(key)
        raise RateLimitExceededError(retry_after_seconds=max(ttl, 1))
