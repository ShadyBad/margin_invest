"""Tests for ARQ worker configuration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from margin_api.workers import WorkerSettings


class TestWorkerSettings:
    def test_has_redis_settings(self):
        assert WorkerSettings.redis_settings is not None

    def test_has_functions(self):
        assert len(WorkerSettings.functions) >= 3

    def test_has_cron_jobs(self):
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_function_names(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "full_ingest" in names
        assert "full_score" in names
        assert "backtest_validate" in names
        assert "live_price_poll" in names
        assert "retry_quarantined" in names


class TestLivePricePoll:
    @pytest.mark.asyncio
    async def test_live_price_poll_no_recommendations(self):
        from margin_api.workers import live_price_poll

        result = await live_price_poll({"recommended_tickers": []})
        assert result["status"] == "no_recommendations"
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_live_price_poll_empty_ctx(self):
        from margin_api.workers import live_price_poll

        result = await live_price_poll({})
        assert result["status"] == "no_recommendations"
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_live_price_poll_with_tickers(self):
        """Test that live_price_poll fetches prices and stores them in Redis."""
        import fakeredis.aioredis

        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        # Mock yfinance Ticker to return a known price
        mock_ticker = MagicMock()
        mock_ticker.fast_info = MagicMock()
        mock_ticker.fast_info.last_price = 185.50

        with (
            patch("margin_api.workers.aioredis.Redis", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", return_value=mock_ticker),
        ):
            result = await live_price_poll({"recommended_tickers": ["AAPL"]})

        assert result["status"] == "completed"
        assert result["updated"] == 1

        # Verify the price was stored in Redis
        from margin_api.services.live_prices import LivePriceService

        service = LivePriceService(fake_redis)
        cached = await service.get_price("AAPL")
        assert cached is not None
        assert cached["price"] == 185.50

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_live_price_poll_skips_failed_tickers(self):
        """Test that a failing ticker is skipped gracefully."""
        import fakeredis.aioredis

        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        call_count = 0

        def mock_ticker_factory(ticker):
            nonlocal call_count
            call_count += 1
            if ticker == "BAD":
                raise Exception("yfinance error")
            mock_t = MagicMock()
            mock_t.fast_info = MagicMock()
            mock_t.fast_info.last_price = 100.0
            return mock_t

        with (
            patch("margin_api.workers.aioredis.Redis", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", side_effect=mock_ticker_factory),
        ):
            result = await live_price_poll({"recommended_tickers": ["AAPL", "BAD"]})

        assert result["status"] == "completed"
        assert result["updated"] == 1

        await fake_redis.aclose()
