"""Redis-backed sliding window rate limiter for cross-job API throttling."""

from __future__ import annotations

import asyncio
import math
import time

from redis.asyncio import Redis


class RedisRateLimiter:
    """Sliding window rate limiter backed by Redis.

    Uses fixed-duration window keys with atomic INCR to coordinate rate limiting
    across multiple concurrent ARQ jobs sharing the same Redis instance.

    Window size adapts to the configured rate:
    - For rates >= 60/min (>= 1/sec), uses 1-second windows.
    - For lower rates, widens the window so at least 1 request is allowed per window.

    Implements the same interface as ``margin_engine.ingestion.rate_limiter.RateLimiter``
    so providers can accept either via duck typing.
    """

    def __init__(
        self,
        redis: Redis,
        max_per_minute: int = 36,
        key_prefix: str = "ratelimit:yfinance",
    ) -> None:
        self._redis = redis
        self._max_per_minute = max_per_minute
        self._key_prefix = key_prefix

        # Calculate window size: ensure at least 1 token per window.
        # For max_per_minute=60 → window=1s, tokens_per_window=1
        # For max_per_minute=10 → window=6s, tokens_per_window=1
        # For max_per_minute=120 → window=1s, tokens_per_window=2
        if max_per_minute >= 60:
            self._window_seconds = 1
            self._max_per_window = max_per_minute / 60.0
        else:
            # Widen the window so we get at least 1 token per window
            self._window_seconds = math.ceil(60.0 / max_per_minute)
            self._max_per_window = max(1, (max_per_minute * self._window_seconds) / 60.0)

    def _window_key(self) -> tuple[str, float]:
        """Return (redis_key, seconds_remaining_in_window) for the current window."""
        now = time.time()
        window = int(now // self._window_seconds) * self._window_seconds
        key = f"{self._key_prefix}:{window}"
        elapsed_in_window = now - window
        remaining = self._window_seconds - elapsed_in_window
        return key, remaining

    async def acquire(self) -> bool:
        """Try to acquire a rate limit token.

        Returns True if acquired, False if the current window is exhausted.
        """
        key, remaining = self._window_key()
        count = await self._redis.incr(key)
        if count == 1:
            # Auto-cleanup after the window expires; add padding for safety
            await self._redis.expire(key, self._window_seconds + 5)
        if count <= self._max_per_window:
            return True
        # Over limit — decrement back since we won't use this slot
        await self._redis.decr(key)
        return False

    async def wait_and_acquire(self) -> None:
        """Block (async sleep) until a token is available, then acquire it."""
        while True:
            key, remaining = self._window_key()
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self._window_seconds + 5)
            if count <= self._max_per_window:
                return  # acquired
            # Over limit — decrement and wait for next window
            await self._redis.decr(key)
            await asyncio.sleep(remaining + 0.05)
