"""Yahoo Finance data provider via the yfinance library.

This is a free, no-API-key provider that supports fundamentals, price
history, and earnings data.  It serves as a low-priority fallback for
paid providers.
"""

from __future__ import annotations

from datetime import UTC, datetime

import yfinance as yf

from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

_DAYS_TO_PERIOD: list[tuple[int, str]] = [
    (30, "1mo"),
    (90, "3mo"),
    (180, "6mo"),
    (365, "1y"),
    (730, "2y"),
]
"""Mapping thresholds: if *days* <= threshold, use the corresponding yfinance period string."""


def _days_to_period(days: int) -> str:
    """Convert a requested number of days to a yfinance ``period`` parameter."""
    for threshold, period in _DAYS_TO_PERIOD:
        if days <= threshold:
            return period
    return "5y"


def _df_most_recent_column_to_dict(df) -> dict:
    """Extract the first (most recent) column of a DataFrame as a flat dict.

    Returns an empty dict when the DataFrame is empty.
    """
    if df is None or df.empty:
        return {}
    first_col = df.iloc[:, 0]
    return {
        str(k): _safe_scalar(v)
        for k, v in first_col.items()
    }


def _safe_scalar(value):
    """Convert numpy/pandas scalar types to native Python types."""
    try:
        # Handle NaN
        if hasattr(value, "item"):
            return value.item()
        return value
    except (ValueError, TypeError):
        return value


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class YFinanceProvider(DataProvider):
    """Concrete data provider backed by Yahoo Finance (yfinance library).

    Free, no-API-key provider with moderate rate limits.  Used as a
    fallback when premium providers are unavailable.
    """

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="yfinance",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.PRICE,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=60,
            requires_api_key=False,
            priority=10,
        )

    # ------------------------------------------------------------------
    # Fundamentals
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch income statement, balance sheet, and cash flow.

        Returns the most recent annual period for each statement.
        """
        try:
            t = yf.Ticker(ticker)
            raw_data = {
                "income_statement": _df_most_recent_column_to_dict(t.financials),
                "balance_sheet": _df_most_recent_column_to_dict(t.balance_sheet),
                "cash_flow": _df_most_recent_column_to_dict(t.cashflow),
            }
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=raw_data,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Price history
    # ------------------------------------------------------------------

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        """Fetch OHLCV price bars for the requested look-back window."""
        try:
            t = yf.Ticker(ticker)
            period = _days_to_period(days)
            hist = t.history(period=period)

            bars: list[dict] = []
            if hist is not None and not hist.empty:
                # Reset index so date becomes a column
                hist_reset = hist.reset_index()
                bars = hist_reset.to_dict(orient="records")
                # Convert Timestamps and numpy types to JSON-friendly values
                for bar in bars:
                    for key, val in bar.items():
                        if hasattr(val, "isoformat"):
                            bar[key] = val.isoformat()
                        elif hasattr(val, "item"):
                            bar[key] = val.item()

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={"bars": bars},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch historical earnings dates with actual/estimated EPS."""
        try:
            t = yf.Ticker(ticker)
            df = t.earnings_dates

            earnings: list[dict] = []
            if df is not None and not df.empty:
                for date_idx, row in df.iterrows():
                    entry: dict = {
                        "quarter": str(date_idx),
                    }
                    if "Reported EPS" in row:
                        entry["actual_eps"] = _safe_scalar(row["Reported EPS"])
                    if "EPS Estimate" in row:
                        entry["expected_eps"] = _safe_scalar(row["EPS Estimate"])
                    earnings.append(entry)

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )
