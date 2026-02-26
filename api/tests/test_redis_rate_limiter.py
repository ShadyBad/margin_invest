"""Tests for Redis-backed sliding window rate limiter."""

from __future__ import annotations

import time

import fakeredis.aioredis
import pytest
import pytest_asyncio
from margin_api.services.redis_rate_limiter import RedisRateLimiter


@pytest_asyncio.fixture()
async def redis():
    """Create a fake Redis client for testing."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


class TestRedisRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_under_limit(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=10, key_prefix="ratelimit:test")
        acquired = await limiter.acquire()
        assert acquired is True

    @pytest.mark.asyncio
    async def test_acquire_at_limit_returns_false(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=120, key_prefix="ratelimit:test2")
        # 120/60 = 2 per second window
        await limiter.acquire()
        await limiter.acquire()
        # Third call should indicate rate limited
        acquired = await limiter.acquire()
        assert acquired is False

    @pytest.mark.asyncio
    async def test_acquire_low_rate_allows_one_per_window(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=2, key_prefix="ratelimit:test:low")
        # 2/min => window widens so at least 1 request per window
        assert await limiter.acquire() is True
        # Second call in same window should be rejected
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_wait_and_acquire_blocks_then_succeeds(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=60, key_prefix="ratelimit:test3")
        # 60/60 = 1 per second; exhaust the single token in this window
        await limiter.acquire()
        # wait_and_acquire should sleep then succeed
        start = time.monotonic()
        await limiter.wait_and_acquire()
        elapsed = time.monotonic() - start
        # Should have waited some time for the next window.
        # Minimum wait depends on where we are in the current 1s window,
        # but it must be > 0 (at least the 0.05s padding in the sleep).
        assert elapsed >= 0.05

    @pytest.mark.asyncio
    async def test_different_prefixes_are_independent(self, redis):
        limiter_a = RedisRateLimiter(redis, max_per_minute=60, key_prefix="ratelimit:test:a")
        limiter_b = RedisRateLimiter(redis, max_per_minute=60, key_prefix="ratelimit:test:b")
        # Each allows 1 per second
        assert await limiter_a.acquire() is True
        assert await limiter_b.acquire() is True
        # Both exhausted independently
        assert await limiter_a.acquire() is False
        assert await limiter_b.acquire() is False
