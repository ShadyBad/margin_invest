"""Tests for the yfinance data provider.

All tests mock yfinance.Ticker to avoid real network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from margin_engine.ingestion.providers.yfinance_provider import (
    YFinanceProvider,
    _build_periods_from_dfs,
    _df_all_columns_to_dicts,
)
from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import DataCategory, FetchResult


@pytest.fixture
def provider() -> YFinanceProvider:
    return YFinanceProvider()


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


class TestProviderInfo:
    def test_info(self, provider: YFinanceProvider) -> None:
        info = provider.info
        assert info.name == "yfinance"
        assert DataCategory.FUNDAMENTALS in info.supported_categories
        assert DataCategory.PRICE in info.supported_categories
        assert DataCategory.EARNINGS in info.supported_categories
        assert info.requests_per_minute == 60
        assert info.requires_api_key is False
        assert info.priority == 10


# ---------------------------------------------------------------------------
# fetch_fundamentals
# ---------------------------------------------------------------------------


class TestFetchFundamentals:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_fundamentals_success(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """Successful fetch returns income_statement, balance_sheet, cash_flow."""
        # Build sample DataFrames with one column (most recent period)
        income_data = pd.DataFrame(
            {"2024-01-01": [100_000, 50_000, 30_000]},
            index=["Total Revenue", "Operating Income", "Net Income"],
        )
        balance_data = pd.DataFrame(
            {"2024-01-01": [500_000, 200_000]},
            index=["Total Assets", "Total Liabilities"],
        )
        cashflow_data = pd.DataFrame(
            {"2024-01-01": [40_000, -10_000]},
            index=["Operating Cash Flow", "Capital Expenditure"],
        )

        mock_ticker = MagicMock()
        mock_ticker.financials = income_data
        mock_ticker.balance_sheet = balance_data
        mock_ticker.cashflow = cashflow_data
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_fundamentals("AAPL")

        assert isinstance(result, FetchResult)
        assert result.success is True
        assert result.provider_name == "yfinance"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.error is None

        raw = result.raw_data
        assert "income_statement" in raw
        assert "balance_sheet" in raw
        assert "cash_flow" in raw

        assert raw["income_statement"]["Total Revenue"] == 100_000
        assert raw["income_statement"]["Net Income"] == 30_000
        assert raw["balance_sheet"]["Total Assets"] == 500_000
        assert raw["cash_flow"]["Operating Cash Flow"] == 40_000

        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_fundamentals_error(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        """When yfinance raises, return FetchResult with success=False."""
        mock_yf.Ticker.side_effect = RuntimeError("API down")

        result = provider.fetch_fundamentals("BAD")

        assert result.success is False
        assert "API down" in result.error
        assert result.raw_data == {}
        assert result.ticker == "BAD"

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_fundamentals_empty_data(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """Empty DataFrames should still produce a valid FetchResult."""
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_fundamentals("EMPTY")

        assert result.success is True
        assert result.raw_data["income_statement"] == {}
        assert result.raw_data["balance_sheet"] == {}
        assert result.raw_data["cash_flow"] == {}


# ---------------------------------------------------------------------------
# fetch_price_history
# ---------------------------------------------------------------------------


class TestFetchPriceHistory:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_price_history_success(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """Successful price fetch returns bars list."""
        hist_df = pd.DataFrame(
            {
                "Open": [150.0, 151.0],
                "High": [155.0, 156.0],
                "Low": [149.0, 150.0],
                "Close": [154.0, 155.0],
                "Volume": [1_000_000, 1_100_000],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.category == DataCategory.PRICE
        assert result.ticker == "AAPL"

        bars = result.raw_data["bars"]
        assert len(bars) == 2
        assert bars[0]["Open"] == 150.0
        assert bars[1]["Close"] == 155.0

        mock_ticker.history.assert_called_once_with(period="1mo")

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_price_history_maps_days_to_period(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """Verify the days-to-period mapping for all ranges."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        test_cases = [
            (7, "1mo"),
            (30, "1mo"),
            (60, "3mo"),
            (90, "3mo"),
            (120, "6mo"),
            (180, "6mo"),
            (365, "1y"),
            (400, "2y"),
            (730, "2y"),
            (1000, "5y"),
        ]

        for days, expected_period in test_cases:
            mock_ticker.history.reset_mock()
            provider.fetch_price_history("AAPL", days=days)
            mock_ticker.history.assert_called_once_with(period=expected_period)

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_price_history_error(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """When yfinance raises, return FetchResult with success=False."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = RuntimeError("Network error")
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_price_history("BAD")

        assert result.success is False
        assert "Network error" in result.error
        assert result.raw_data == {}


# ---------------------------------------------------------------------------
# fetch_earnings
# ---------------------------------------------------------------------------


class TestFetchEarnings:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_earnings_success(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        """Successful earnings fetch returns list of earnings dicts."""
        earnings_df = pd.DataFrame(
            {
                "Reported EPS": [1.52, 1.46, 1.20],
                "EPS Estimate": [1.50, 1.43, 1.18],
            },
            index=pd.to_datetime(["2024-01-25", "2023-10-26", "2023-07-27"]),
        )

        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = earnings_df
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.category == DataCategory.EARNINGS
        assert result.ticker == "AAPL"

        earnings = result.raw_data["earnings"]
        assert len(earnings) == 3
        assert earnings[0]["actual_eps"] == 1.52
        assert earnings[0]["expected_eps"] == 1.50
        assert "quarter" in earnings[0]

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_earnings_error(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        """When yfinance raises, return FetchResult with success=False."""
        mock_ticker = MagicMock()
        type(mock_ticker).earnings_dates = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("No data"))
        )
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_earnings("BAD")

        assert result.success is False
        assert "No data" in result.error
        assert result.raw_data == {}


# ---------------------------------------------------------------------------
# unsupported categories
# ---------------------------------------------------------------------------


class TestUnsupportedCategories:
    def test_unsupported_categories(self, provider: YFinanceProvider) -> None:
        """Verify NotImplementedError for unsupported fetch methods."""
        with pytest.raises(NotImplementedError, match="yfinance"):
            provider.fetch_insider_transactions("AAPL")

        with pytest.raises(NotImplementedError, match="yfinance"):
            provider.fetch_institutional_holdings("AAPL")


# ---------------------------------------------------------------------------
# fetch_info
# ---------------------------------------------------------------------------


class TestFetchInfo:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_info_success(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        """Successful info fetch returns metadata dict."""
        info_dict = {
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "country": "United States",
            "marketCap": 3_000_000_000_000,
            "industry": "Consumer Electronics",
        }

        mock_ticker = MagicMock()
        mock_ticker.info = info_dict
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_info("AAPL")

        assert isinstance(result, FetchResult)
        assert result.success is True
        assert result.provider_name == "yfinance"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.error is None
        assert result.raw_data == info_dict
        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_info_empty(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        """Empty info dict should still produce success=True with empty data."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_info("EMPTY")

        assert result.success is True
        assert result.raw_data == {}


# ---------------------------------------------------------------------------
# fetch_all
# ---------------------------------------------------------------------------


class TestFetchAll:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_all_returns_all_categories(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """fetch_all returns 4 keys, all success=True, using one Ticker instance."""
        # Set up mock ticker with all data
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame({"2024-01-01": [100_000]}, index=["Total Revenue"])
        mock_ticker.balance_sheet = pd.DataFrame({"2024-01-01": [500_000]}, index=["Total Assets"])
        mock_ticker.cashflow = pd.DataFrame({"2024-01-01": [40_000]}, index=["Operating Cash Flow"])
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [149.0],
                "Close": [154.0],
                "Volume": [1_000_000],
            },
            index=pd.to_datetime(["2024-01-01"]),
        )
        mock_ticker.earnings_dates = pd.DataFrame(
            {"Reported EPS": [1.52], "EPS Estimate": [1.50]},
            index=pd.to_datetime(["2024-01-25"]),
        )
        mock_ticker.info = {
            "shortName": "Apple Inc.",
            "sector": "Technology",
        }
        mock_yf.Ticker.return_value = mock_ticker

        results = provider.fetch_all("AAPL")

        assert set(results.keys()) == {"fundamentals", "price", "earnings", "info"}
        for key, result in results.items():
            assert isinstance(result, FetchResult), f"{key} is not a FetchResult"
            assert result.success is True, f"{key} not success"
            assert result.ticker == "AAPL"

        # Verify yf.Ticker called exactly ONCE
        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_all_partial_failure(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """A failure in earnings does not block fundamentals, price, or info."""
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame({"2024-01-01": [100_000]}, index=["Total Revenue"])
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [149.0],
                "Close": [154.0],
                "Volume": [1_000_000],
            },
            index=pd.to_datetime(["2024-01-01"]),
        )
        # Make earnings_dates raise an exception
        type(mock_ticker).earnings_dates = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Earnings unavailable"))
        )
        mock_ticker.info = {"shortName": "Apple Inc."}
        mock_yf.Ticker.return_value = mock_ticker

        results = provider.fetch_all("AAPL")

        assert results["fundamentals"].success is True
        assert results["price"].success is True
        assert results["info"].success is True
        assert results["earnings"].success is False
        assert "Earnings unavailable" in results["earnings"].error

        # Still only one Ticker call
        mock_yf.Ticker.assert_called_once_with("AAPL")


# ---------------------------------------------------------------------------
# rate limiting
# ---------------------------------------------------------------------------


class TestProviderRateLimiting:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_rate_limiter_called_per_fetch(self, mock_yf: MagicMock) -> None:
        """When a rate limiter is provided, wait_and_acquire is called for each fetch."""
        mock_limiter = MagicMock(spec=RateLimiter)
        provider = YFinanceProvider(rate_limiter=mock_limiter)

        # Set up minimal mock ticker
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker.earnings_dates = pd.DataFrame()
        mock_ticker.info = {}
        mock_yf.Ticker.return_value = mock_ticker

        provider.fetch_fundamentals("AAPL")
        assert mock_limiter.wait_and_acquire.call_count == 1

        provider.fetch_price_history("AAPL")
        assert mock_limiter.wait_and_acquire.call_count == 2

        provider.fetch_earnings("AAPL")
        assert mock_limiter.wait_and_acquire.call_count == 3

        provider.fetch_info("AAPL")
        assert mock_limiter.wait_and_acquire.call_count == 4

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_no_rate_limiter_by_default(self, mock_yf: MagicMock) -> None:
        """When no rate limiter is provided, fetches work without rate limiting."""
        provider = YFinanceProvider()

        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        # Should not raise
        result = provider.fetch_fundamentals("AAPL")
        assert result.success is True


# ---------------------------------------------------------------------------
# Multi-year period extraction helpers
# ---------------------------------------------------------------------------


class TestDfAllColumnsToDicts:
    def test_extracts_all_columns(self):
        """Each DataFrame column becomes a (period_end, dict) pair."""
        df = pd.DataFrame(
            {"2023-09-24": [100, 200], "2024-09-28": [110, 220]},
            index=["Revenue", "NetIncome"],
        )
        # Convert string column names to Timestamps (like real yfinance data)
        df.columns = pd.to_datetime(df.columns)

        result = _df_all_columns_to_dicts(df)

        assert len(result) == 2
        # Sorted oldest-first
        assert result[0][0] == "2023-09-24"
        assert result[0][1]["Revenue"] == 100
        assert result[0][1]["NetIncome"] == 200
        assert result[1][0] == "2024-09-28"
        assert result[1][1]["Revenue"] == 110

    def test_empty_dataframe_returns_empty(self):
        assert _df_all_columns_to_dicts(pd.DataFrame()) == []

    def test_none_returns_empty(self):
        assert _df_all_columns_to_dicts(None) == []


class TestBuildPeriodsFromDfs:
    def test_merges_three_statements_by_date(self):
        """All three statements for the same date are merged into one period dict."""
        income = pd.DataFrame(
            {"2023-09-24": [1000], "2024-09-28": [1100]},
            index=["Revenue"],
        )
        income.columns = pd.to_datetime(income.columns)

        balance = pd.DataFrame(
            {"2023-09-24": [5000], "2024-09-28": [5500]},
            index=["TotalAssets"],
        )
        balance.columns = pd.to_datetime(balance.columns)

        cashflow = pd.DataFrame(
            {"2023-09-24": [300], "2024-09-28": [350]},
            index=["OperatingCashFlow"],
        )
        cashflow.columns = pd.to_datetime(cashflow.columns)

        periods = _build_periods_from_dfs(income, balance, cashflow)

        assert len(periods) == 2
        assert periods[0]["period_end"] == "2023-09-24"
        assert periods[0]["income_statement"]["Revenue"] == 1000
        assert periods[0]["balance_sheet"]["TotalAssets"] == 5000
        assert periods[0]["cash_flow"]["OperatingCashFlow"] == 300
        assert periods[1]["period_end"] == "2024-09-28"
        assert periods[1]["income_statement"]["Revenue"] == 1100

    def test_handles_mismatched_dates(self):
        """Dates present in one statement but not another get empty dicts."""
        income = pd.DataFrame(
            {"2023-09-24": [1000], "2024-09-28": [1100]},
            index=["Revenue"],
        )
        income.columns = pd.to_datetime(income.columns)

        # Balance sheet only has one date
        balance = pd.DataFrame({"2024-09-28": [5500]}, index=["TotalAssets"])
        balance.columns = pd.to_datetime(balance.columns)

        cashflow = pd.DataFrame()

        periods = _build_periods_from_dfs(income, balance, cashflow)

        assert len(periods) == 2
        # First period: income present, balance/cashflow empty
        assert periods[0]["income_statement"]["Revenue"] == 1000
        assert periods[0]["balance_sheet"] == {}
        assert periods[0]["cash_flow"] == {}

    def test_all_empty_returns_empty(self):
        periods = _build_periods_from_dfs(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        assert periods == []


class TestFetchFundamentalsIncludesPeriods:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fundamentals_includes_periods_key(
        self, mock_yf: MagicMock, provider: YFinanceProvider
    ) -> None:
        """fetch_fundamentals should include a 'periods' key with all fiscal years."""
        income_data = pd.DataFrame(
            {"2023-09-24": [90_000], "2024-09-28": [100_000]},
            index=["Total Revenue"],
        )
        income_data.columns = pd.to_datetime(income_data.columns)

        balance_data = pd.DataFrame(
            {"2023-09-24": [450_000], "2024-09-28": [500_000]},
            index=["Total Assets"],
        )
        balance_data.columns = pd.to_datetime(balance_data.columns)

        cashflow_data = pd.DataFrame(
            {"2023-09-24": [35_000], "2024-09-28": [40_000]},
            index=["Operating Cash Flow"],
        )
        cashflow_data.columns = pd.to_datetime(cashflow_data.columns)

        mock_ticker = MagicMock()
        mock_ticker.financials = income_data
        mock_ticker.balance_sheet = balance_data
        mock_ticker.cashflow = cashflow_data
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        periods = result.raw_data["periods"]
        assert len(periods) == 2
        assert periods[0]["period_end"] == "2023-09-24"
        assert periods[1]["period_end"] == "2024-09-28"
        assert periods[1]["income_statement"]["Total Revenue"] == 100_000
