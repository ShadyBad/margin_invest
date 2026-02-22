"""Tests for Finnhub data provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider
from margin_engine.ingestion.types import DataCategory


class TestProviderInfo:
    def test_name(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.name == "finnhub"

    def test_priority(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.priority == 5

    def test_requires_api_key(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.requires_api_key is True

    def test_supported_categories(self):
        provider = FinnhubProvider(api_key="test_key")
        assert set(provider.info.supported_categories) == {
            DataCategory.EARNINGS,
            DataCategory.INSIDER,
            DataCategory.INSTITUTIONAL,
            DataCategory.NEWS,
        }

    def test_rate_limit(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.requests_per_minute == 60

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key must not be empty"):
            FinnhubProvider(api_key="")


class TestFetchEarnings:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.return_value = [
            {
                "actual": 1.88,
                "estimate": 1.97,
                "period": "2023-03-31",
                "quarter": 1,
                "surprise": -0.09,
                "surprisePercent": -4.78,
                "symbol": "AAPL",
                "year": 2023,
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.EARNINGS
        assert result.ticker == "AAPL"
        assert len(result.raw_data["earnings"]) == 1
        assert result.raw_data["earnings"][0]["actual"] == 1.88
        assert result.raw_data["earnings"][0]["period"] == "2023-03-31"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.raw_data["earnings"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.side_effect = Exception("API error")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is False
        assert "API error" in result.error


class TestFetchInsiderTransactions:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.return_value = {
            "data": [
                {
                    "name": "Tim Cook",
                    "share": 100000,
                    "change": -50000,
                    "filingDate": "2023-08-01",
                    "transactionDate": "2023-07-28",
                    "transactionCode": "S",
                    "transactionPrice": 195.5,
                }
            ],
            "symbol": "AAPL",
        }

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.INSIDER
        assert len(result.raw_data["transactions"]) == 1
        assert result.raw_data["transactions"][0]["name"] == "Tim Cook"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_data_key(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.return_value = {
            "data": [],
            "symbol": "AAPL",
        }

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.raw_data["transactions"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.side_effect = Exception("timeout")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is False
        assert "timeout" in result.error


class TestFetchInstitutionalHoldings:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.return_value = [
            {
                "cik": "0001067983",
                "name": "Berkshire Hathaway",
                "putCall": "",
                "change": 5000,
                "noVoting": 0,
                "percentage": 5.2,
                "share": 890000,
                "value": 170000000,
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.INSTITUTIONAL
        assert len(result.raw_data["holdings"]) == 1
        assert result.raw_data["holdings"][0]["name"] == "Berkshire Hathaway"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.raw_data["holdings"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.side_effect = Exception("forbidden")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is False
        assert "forbidden" in result.error


class TestFetchNews:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "category": "company news",
                "datetime": 1569550360,
                "headline": "Apple launches new product",
                "id": 25286,
                "image": "https://example.com/img.jpg",
                "related": "AAPL",
                "source": "Reuters",
                "summary": "Apple announced...",
                "url": "https://example.com/article",
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.NEWS
        assert len(result.raw_data["articles"]) == 1
        assert result.raw_data["articles"][0]["headline"] == "Apple launches new product"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is True
        assert result.raw_data["articles"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.side_effect = Exception("rate limited")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is False
        assert "rate limited" in result.error
