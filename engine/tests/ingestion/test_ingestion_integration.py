"""Integration tests for the ingestion layer.

Verifies that providers, registry, normalizer, and types work together
as a cohesive data ingestion pipeline. All tests mock yfinance to avoid
network calls.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
from margin_engine.ingestion.normalizer import normalize_fundamentals
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.registry import ProviderRegistry
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
)

# ---------------------------------------------------------------------------
# Helper: a provider that always fails
# ---------------------------------------------------------------------------


class MockFailProvider(DataProvider):
    """A provider that always returns success=False for every fetch."""

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="mock_fail",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.PRICE,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=60,
            requires_api_key=False,
            priority=20,
        )

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        return FetchResult(
            provider_name=self.info.name,
            category=DataCategory.FUNDAMENTALS,
            ticker=ticker,
            raw_data={},
            fetched_at=datetime.now(UTC).isoformat(),
            success=False,
            error="MockFailProvider always fails",
        )

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        return FetchResult(
            provider_name=self.info.name,
            category=DataCategory.PRICE,
            ticker=ticker,
            raw_data={},
            fetched_at=datetime.now(UTC).isoformat(),
            success=False,
            error="MockFailProvider always fails",
        )

    def fetch_earnings(self, ticker: str) -> FetchResult:
        return FetchResult(
            provider_name=self.info.name,
            category=DataCategory.EARNINGS,
            ticker=ticker,
            raw_data={},
            fetched_at=datetime.now(UTC).isoformat(),
            success=False,
            error="MockFailProvider always fails",
        )


# ---------------------------------------------------------------------------
# Sample mock DataFrames for yfinance
# ---------------------------------------------------------------------------


def _sample_income_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "2024-09-28": {
                "Total Revenue": 394328000000,
                "Cost Of Revenue": 224000000000,
                "Net Income": 93736000000,
            },
        },
    )


def _sample_balance_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "2024-09-28": {
                "Total Assets": 364980000000,
                "Total Liabilities Net Minority Interest": 308030000000,
            },
        },
    )


def _sample_cashflow_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "2024-09-28": {
                "Operating Cash Flow": 118254000000,
                "Capital Expenditure": -9959000000,
            },
        },
    )


def _normalizer_compatible_income_df() -> pd.DataFrame:
    """Income DataFrame with index names the normalizer recognises."""
    return pd.DataFrame(
        {
            "2024-09-28": {
                "totalRevenue": 394328000000,
                "costOfRevenue": 224000000000,
                "grossProfit": 170328000000,
                "netIncome": 93736000000,
            },
        },
    )


def _normalizer_compatible_balance_df() -> pd.DataFrame:
    """Balance sheet DataFrame with index names the normalizer recognises."""
    return pd.DataFrame(
        {
            "2024-09-28": {
                "totalAssets": 364980000000,
                "totalLiabilities": 308030000000,
                "totalStockholdersEquity": 56950000000,
            },
        },
    )


def _normalizer_compatible_cashflow_df() -> pd.DataFrame:
    """Cash flow DataFrame with index names the normalizer recognises."""
    return pd.DataFrame(
        {
            "2024-09-28": {
                "operatingCashFlow": 118254000000,
                "capitalExpenditure": -9959000000,
            },
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegistryWithYFinanceProvider:
    """Register a YFinanceProvider and verify it appears in fallback chains."""

    def test_registry_with_yfinance_provider(self) -> None:
        registry = ProviderRegistry()
        provider = YFinanceProvider()
        registry.register(provider)

        # YFinanceProvider supports FUNDAMENTALS, PRICE, EARNINGS
        for category in (
            DataCategory.FUNDAMENTALS,
            DataCategory.PRICE,
            DataCategory.EARNINGS,
        ):
            chain = registry.get_fallback_chain(category)
            assert len(chain) == 1
            assert chain[0].info.name == "yfinance"

        # Should NOT appear in chains for unsupported categories
        for category in (
            DataCategory.INSIDER,
            DataCategory.INSTITUTIONAL,
            DataCategory.MACRO,
            DataCategory.NEWS,
        ):
            chain = registry.get_fallback_chain(category)
            assert len(chain) == 0


class TestRegistryFetchFundamentalsWithYFinance:
    """Register YFinanceProvider, mock yfinance, fetch fundamentals."""

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_registry_fetch_fundamentals_with_yfinance(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = _sample_income_df()
        mock_ticker.balance_sheet = _sample_balance_df()
        mock_ticker.cashflow = _sample_cashflow_df()
        mock_yf.Ticker.return_value = mock_ticker

        registry = ProviderRegistry()
        registry.register(YFinanceProvider())

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is True
        assert result.provider_name == "yfinance"
        assert result.ticker == "AAPL"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.error is None

        raw = result.raw_data
        assert "income_statement" in raw
        assert "balance_sheet" in raw
        assert "cash_flow" in raw

        # Verify the raw data contains expected values
        assert raw["income_statement"]["Total Revenue"] == 394328000000
        assert raw["balance_sheet"]["Total Assets"] == 364980000000
        assert raw["cash_flow"]["Operating Cash Flow"] == 118254000000

        mock_yf.Ticker.assert_called_once_with("AAPL")


class TestNormalizerWithYFinanceFetchResult:
    """Fetch fundamentals via provider, then normalize the raw data."""

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_normalizer_with_yfinance_fetch_result(self, mock_yf: MagicMock) -> None:
        # Use normalizer-compatible key names (camelCase) so the
        # normalize_fundamentals function can map them to model fields.
        mock_ticker = MagicMock()
        mock_ticker.financials = _normalizer_compatible_income_df()
        mock_ticker.balance_sheet = _normalizer_compatible_balance_df()
        mock_ticker.cashflow = _normalizer_compatible_cashflow_df()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YFinanceProvider()
        result = provider.fetch_fundamentals("AAPL")
        assert result.success is True

        income, balance, cash_flow = normalize_fundamentals(result.raw_data)

        assert isinstance(income, IncomeStatement)
        assert isinstance(balance, BalanceSheet)
        assert isinstance(cash_flow, CashFlowStatement)

        # Verify key values were normalized correctly
        from decimal import Decimal

        assert income.revenue == Decimal("394328000000")
        assert income.net_income == Decimal("93736000000")
        assert balance.total_assets == Decimal("364980000000")
        assert balance.total_equity == Decimal("56950000000")
        assert cash_flow.operating_cash_flow == Decimal("118254000000")
        assert cash_flow.capital_expenditures == Decimal("-9959000000")


class TestRegistryFallbackOnProviderError:
    """MockFailProvider (priority=20) fails, YFinanceProvider (priority=10) succeeds."""

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_registry_fallback_on_provider_error(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = _sample_income_df()
        mock_ticker.balance_sheet = _sample_balance_df()
        mock_ticker.cashflow = _sample_cashflow_df()
        mock_yf.Ticker.return_value = mock_ticker

        registry = ProviderRegistry()
        registry.register(MockFailProvider())
        registry.register(YFinanceProvider())

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        # The fallback should have succeeded via yfinance
        assert result.success is True
        assert result.provider_name == "yfinance"
        assert "income_statement" in result.raw_data


class TestImportsFromIngestionPackage:
    """Verify all expected names can be imported from margin_engine.ingestion."""

    def test_imports_from_ingestion_package(self) -> None:
        from margin_engine.ingestion import (
            DataCategory,
            DataProvider,
            FetchResult,
            ProviderInfo,
            ProviderRegistry,
            RateLimiter,
            RateLimiterRegistry,
            YFinanceProvider,
            normalize_balance_sheet,
            normalize_cash_flow,
            normalize_fundamentals,
            normalize_income_statement,
            normalize_price_bar,
        )

        # Verify the imports are the correct types
        assert DataCategory.FUNDAMENTALS == "fundamentals"
        assert issubclass(YFinanceProvider, DataProvider)
        assert callable(normalize_fundamentals)
        assert callable(normalize_income_statement)
        assert callable(normalize_balance_sheet)
        assert callable(normalize_cash_flow)
        assert callable(normalize_price_bar)
        assert ProviderRegistry is not None
        assert RateLimiter is not None
        assert RateLimiterRegistry is not None
        assert FetchResult is not None
        assert ProviderInfo is not None
