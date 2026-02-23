"""Tests for the FMP (Financial Modeling Prep) data provider.

All tests mock httpx -- no real HTTP calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.types import DataCategory

# ---------------------------------------------------------------------------
# TestProviderInfo
# ---------------------------------------------------------------------------


class TestProviderInfo:
    """Verify provider metadata is correct."""

    def test_info(self) -> None:
        provider = FMPProvider(api_key="test-key")
        info = provider.info

        assert info.name == "fmp"
        assert info.priority == 20  # higher than yfinance (10)
        assert DataCategory.FUNDAMENTALS in info.supported_categories
        assert DataCategory.EARNINGS in info.supported_categories
        assert DataCategory.PRICE in info.supported_categories
        assert info.requires_api_key is True
        assert info.requests_per_minute == 300

    def test_no_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="FMP_API_KEY"):
            FMPProvider(api_key="")


# ---------------------------------------------------------------------------
# TestFetchFundamentals
# ---------------------------------------------------------------------------


class TestFetchFundamentals:
    """Verify fundamentals fetching via FMP income-statement endpoint."""

    def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "revenue": 85777000000,
                "netIncome": 20000000000,
                "grossProfit": 40000000000,
            }
        ]
        mock_response.raise_for_status = MagicMock()

        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_response
            result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.raw_data["income_statement"]["revenue"] == 85777000000

        # Verify correct URL was called
        mock_httpx.get.assert_called_once()
        call_args = mock_httpx.get.call_args
        url = call_args[0][0]
        assert "/income-statement/AAPL" in url
        assert "apikey=test-key" in url

    def test_api_error(self) -> None:
        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("API rate limit exceeded")
            result = provider.fetch_fundamentals("AAPL")

        assert result.success is False
        assert result.error is not None
        assert "API rate limit exceeded" in result.error
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"


# ---------------------------------------------------------------------------
# TestFetchEarnings
# ---------------------------------------------------------------------------


class TestFetchEarnings:
    """Verify earnings fetching via FMP historical earning calendar endpoint."""

    def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "date": "2024-01-25",
                "eps": 2.18,
                "epsEstimated": 2.10,
            }
        ]
        mock_response.raise_for_status = MagicMock()

        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_response
            result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.EARNINGS
        assert result.ticker == "AAPL"

        earnings = result.raw_data["earnings"]
        assert len(earnings) == 1
        assert earnings[0]["actual_eps"] == 2.18
        assert earnings[0]["expected_eps"] == 2.10
        assert earnings[0]["quarter"] == "2024-01-25"

        # Verify correct URL was called
        mock_httpx.get.assert_called_once()
        call_args = mock_httpx.get.call_args
        url = call_args[0][0]
        assert "/historical/earning_calendar/AAPL" in url
        assert "apikey=test-key" in url

    def test_empty_response(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_response
            result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.raw_data["earnings"] == []


# ---------------------------------------------------------------------------
# TestFetchPriceHistory
# ---------------------------------------------------------------------------


class TestFetchPriceHistory:
    """Verify price history fetching via FMP historical-price-full endpoint."""

    def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "historical": [
                {
                    "date": "2024-01-25",
                    "open": 150.0,
                    "high": 155.0,
                    "low": 149.0,
                    "close": 153.0,
                    "volume": 5000000,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_response
            result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.PRICE
        assert result.ticker == "AAPL"

        bars = result.raw_data["bars"]
        assert len(bars) == 1
        assert bars[0]["date"] == "2024-01-25"
        assert bars[0]["open"] == 150.0
        assert bars[0]["close"] == 153.0
        assert bars[0]["volume"] == 5000000

        # Verify correct URL was called
        mock_httpx.get.assert_called_once()
        call_args = mock_httpx.get.call_args
        url = call_args[0][0]
        assert "/historical-price-full/AAPL" in url

    def test_api_error(self) -> None:
        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("Network error")
            result = provider.fetch_price_history("AAPL")

        assert result.success is False
        assert result.error is not None
        assert "Network error" in result.error
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.PRICE

    def test_empty_historical(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"historical": []}
        mock_response.raise_for_status = MagicMock()

        provider = FMPProvider(api_key="test-key")

        with patch("margin_engine.ingestion.providers.fmp_provider.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_response
            result = provider.fetch_price_history("AAPL")

        assert result.success is True
        assert result.raw_data["bars"] == []
