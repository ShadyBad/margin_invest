"""Tests for per-request rate limiting in YFinanceProvider.fetch_all."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiter


class TestFetchAllRateLimiting:
    def test_fetch_all_acquires_rate_limit_per_section(self):
        """fetch_all should acquire rate limit before each section, not just once."""
        limiter = MagicMock(spec=RateLimiter)
        provider = YFinanceProvider(rate_limiter=limiter)

        with patch("margin_engine.ingestion.providers.yfinance_provider.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.financials = MagicMock(empty=True)
            mock_ticker.balance_sheet = MagicMock(empty=True)
            mock_ticker.cashflow = MagicMock(empty=True)
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_ticker.earnings_dates = None
            mock_ticker.info = {}
            mock_yf.Ticker.return_value = mock_ticker

            provider.fetch_all("AAPL")

        # Should be called 4 times: fundamentals, price, earnings, info
        assert limiter.wait_and_acquire.call_count == 4

    def test_fetch_all_without_limiter_still_works(self):
        """fetch_all with no limiter should work (no gating)."""
        provider = YFinanceProvider(rate_limiter=None)

        with patch("margin_engine.ingestion.providers.yfinance_provider.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.financials = MagicMock(empty=True)
            mock_ticker.balance_sheet = MagicMock(empty=True)
            mock_ticker.cashflow = MagicMock(empty=True)
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_ticker.earnings_dates = None
            mock_ticker.info = {}
            mock_yf.Ticker.return_value = mock_ticker

            results = provider.fetch_all("AAPL")

        assert "fundamentals" in results
        assert "price" in results
        assert "earnings" in results
        assert "info" in results
