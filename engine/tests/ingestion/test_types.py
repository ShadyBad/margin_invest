"""Tests for data provider protocol and types."""

from __future__ import annotations

import pytest
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)


class TestDataCategory:
    def test_has_all_expected_values(self):
        expected = {
            "FUNDAMENTALS",
            "PRICE",
            "INSIDER",
            "INSTITUTIONAL",
            "MACRO",
            "NEWS",
            "EARNINGS",
            "SHORT_INTEREST",
            "ANALYST",
        }
        actual = {member.name for member in DataCategory}
        assert actual == expected

    def test_values_are_lowercase_strings(self):
        for member in DataCategory:
            assert member.value == member.name.lower()

    def test_is_str_subclass(self):
        assert isinstance(DataCategory.FUNDAMENTALS, str)


class TestProviderInfo:
    def test_create_provider_info(self):
        info = ProviderInfo(
            name="yfinance",
            supported_categories=[DataCategory.FUNDAMENTALS, DataCategory.PRICE],
            requests_per_minute=100,
            requires_api_key=False,
        )
        assert info.name == "yfinance"
        assert DataCategory.FUNDAMENTALS in info.supported_categories
        assert DataCategory.PRICE in info.supported_categories
        assert info.requests_per_minute == 100
        assert info.requires_api_key is False

    def test_default_priority_is_zero(self):
        info = ProviderInfo(
            name="fred",
            supported_categories=[DataCategory.MACRO],
            requests_per_minute=120,
            requires_api_key=True,
        )
        assert info.priority == 0

    def test_custom_priority(self):
        info = ProviderInfo(
            name="polygon",
            supported_categories=[DataCategory.PRICE],
            requests_per_minute=5,
            requires_api_key=True,
            priority=10,
        )
        assert info.priority == 10

    def test_empty_supported_categories(self):
        info = ProviderInfo(
            name="dummy",
            supported_categories=[],
            requests_per_minute=0,
            requires_api_key=False,
        )
        assert info.supported_categories == []


class TestFetchResult:
    def test_create_success_result(self):
        result = FetchResult(
            provider_name="yfinance",
            category=DataCategory.FUNDAMENTALS,
            ticker="AAPL",
            raw_data={"revenue": 394328000000},
            fetched_at="2026-02-12T10:30:00Z",
        )
        assert result.provider_name == "yfinance"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.raw_data == {"revenue": 394328000000}
        assert result.fetched_at == "2026-02-12T10:30:00Z"
        assert result.success is True
        assert result.error is None

    def test_create_error_result(self):
        result = FetchResult(
            provider_name="polygon",
            category=DataCategory.PRICE,
            ticker="XYZ",
            raw_data={},
            fetched_at="2026-02-12T10:30:00Z",
            success=False,
            error="API rate limit exceeded",
        )
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.raw_data == {}

    def test_default_success_is_true(self):
        result = FetchResult(
            provider_name="finnhub",
            category=DataCategory.EARNINGS,
            ticker="MSFT",
            raw_data={"eps": 2.50},
            fetched_at="2026-02-12T11:00:00Z",
        )
        assert result.success is True

    def test_default_error_is_none(self):
        result = FetchResult(
            provider_name="finnhub",
            category=DataCategory.NEWS,
            ticker="TSLA",
            raw_data={"headlines": []},
            fetched_at="2026-02-12T11:00:00Z",
        )
        assert result.error is None


class TestDataProviderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            DataProvider()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        class DummyProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="dummy",
                    supported_categories=[DataCategory.FUNDAMENTALS],
                    requests_per_minute=60,
                    requires_api_key=False,
                    priority=1,
                )

        provider = DummyProvider()
        assert provider.info.name == "dummy"
        assert provider.info.priority == 1

    def test_default_fetch_fundamentals_raises(self):
        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=0,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="minimal.*fundamentals"):
            provider.fetch_fundamentals("AAPL")

    def test_default_fetch_price_history_raises(self):
        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=0,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="minimal.*price_history"):
            provider.fetch_price_history("AAPL")

    def test_default_fetch_insider_transactions_raises(self):
        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=0,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="minimal.*insider_transactions"):
            provider.fetch_insider_transactions("AAPL")

    def test_default_fetch_institutional_holdings_raises(self):
        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=0,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="minimal.*institutional_holdings"):
            provider.fetch_institutional_holdings("AAPL")

    def test_default_fetch_earnings_raises(self):
        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=0,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="minimal.*earnings"):
            provider.fetch_earnings("AAPL")

    def test_subclass_can_override_method(self):
        class PriceOnlyProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="price_only",
                    supported_categories=[DataCategory.PRICE],
                    requests_per_minute=10,
                    requires_api_key=True,
                )

            def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
                return FetchResult(
                    provider_name=self.info.name,
                    category=DataCategory.PRICE,
                    ticker=ticker,
                    raw_data={"prices": [100, 101, 102]},
                    fetched_at="2026-02-12T12:00:00Z",
                )

        provider = PriceOnlyProvider()
        result = provider.fetch_price_history("AAPL", days=30)
        assert result.success is True
        assert result.ticker == "AAPL"
        assert result.category == DataCategory.PRICE

        # Other methods should still raise NotImplementedError
        with pytest.raises(NotImplementedError):
            provider.fetch_fundamentals("AAPL")
