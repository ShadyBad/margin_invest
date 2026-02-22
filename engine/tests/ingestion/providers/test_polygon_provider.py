"""Tests for Polygon.io data provider."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.types import DataCategory


class TestProviderInfo:
    def test_name(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.name == "polygon"

    def test_priority_above_yfinance(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.priority == 20

    def test_requires_api_key(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.requires_api_key is True

    def test_supported_categories_price_only(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.supported_categories == [DataCategory.PRICE]

    def test_rate_limit_free_tier(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.requests_per_minute == 5

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key must not be empty"):
            PolygonProvider(api_key="")


class TestFetchPriceHistory:
    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_success_returns_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Simulate two daily bars
        bar1 = MagicMock()
        bar1.timestamp = 1706140800000  # 2024-01-25 00:00 UTC
        bar1.open = 150.0
        bar1.high = 155.0
        bar1.low = 149.0
        bar1.close = 154.0
        bar1.volume = 1000000
        bar1.vwap = 152.5

        bar2 = MagicMock()
        bar2.timestamp = 1706227200000  # 2024-01-26 00:00 UTC
        bar2.open = 154.0
        bar2.high = 158.0
        bar2.low = 153.0
        bar2.close = 157.0
        bar2.volume = 1200000
        bar2.vwap = 155.5

        mock_client.get_aggs.return_value = [bar1, bar2]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.provider_name == "polygon"
        assert result.category == DataCategory.PRICE
        assert result.ticker == "AAPL"
        assert len(result.raw_data["bars"]) == 2
        assert result.raw_data["bars"][0]["open"] == 150.0
        assert result.raw_data["bars"][0]["close"] == 154.0
        assert result.raw_data["bars"][0]["volume"] == 1000000

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_bar_date_is_iso_format(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        bar = MagicMock()
        bar.timestamp = 1706140800000  # 2024-01-25 00:00 UTC
        bar.open = 150.0
        bar.high = 155.0
        bar.low = 149.0
        bar.close = 154.0
        bar.volume = 1000000
        bar.vwap = 152.5
        mock_client.get_aggs.return_value = [bar]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.raw_data["bars"][0]["date"] == "2024-01-25"

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_adj_close_equals_close_for_adjusted_data(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        bar = MagicMock()
        bar.timestamp = 1706140800000
        bar.open = 150.0
        bar.high = 155.0
        bar.low = 149.0
        bar.close = 154.0
        bar.volume = 1000000
        bar.vwap = 152.5
        mock_client.get_aggs.return_value = [bar]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.raw_data["bars"][0]["adj_close"] == 154.0

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_days_clamped_to_730(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = []

        provider = PolygonProvider(api_key="test_key")
        provider.fetch_price_history("AAPL", days=1000)

        # Verify the from_ date is at most 730 days ago
        call_kwargs = mock_client.get_aggs.call_args
        from_date = call_kwargs.kwargs.get("from_") or call_kwargs[1].get("from_")
        expected_from = str(date.today() - timedelta(days=730))
        assert from_date == expected_from

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_empty_response_returns_success_with_no_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = []

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.raw_data["bars"] == []

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_none_response_returns_success_with_no_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = None

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.raw_data["bars"] == []

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_api_error_returns_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.side_effect = Exception("API rate limit exceeded")

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is False
        assert "API rate limit exceeded" in result.error


class TestStubbedMethods:
    def test_fetch_fundamentals_raises(self):
        provider = PolygonProvider(api_key="test_key")
        with pytest.raises(NotImplementedError, match="Starter"):
            provider.fetch_fundamentals("AAPL")

    def test_fetch_earnings_raises(self):
        provider = PolygonProvider(api_key="test_key")
        with pytest.raises(NotImplementedError, match="Starter"):
            provider.fetch_earnings("AAPL")
