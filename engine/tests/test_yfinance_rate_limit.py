"""Tests for YFinanceProvider rate limiter integration (sync and async)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiter


class TestRateLimiterDuckTyping:
    def test_sync_rate_limiter_works(self):
        """Original sync RateLimiter should still work."""
        limiter = RateLimiter(requests_per_minute=60)
        provider = YFinanceProvider(rate_limiter=limiter)
        # Should not raise
        provider._acquire_rate_limit()

    @pytest.mark.asyncio
    async def test_async_rate_limiter_works(self):
        """An async rate limiter with async wait_and_acquire should work."""
        limiter = AsyncMock()
        limiter.wait_and_acquire = AsyncMock()
        provider = YFinanceProvider(rate_limiter=limiter)
        # Should detect async and await it
        await provider._acquire_rate_limit_async()
        limiter.wait_and_acquire.assert_called_once()
