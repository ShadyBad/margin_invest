"""Yahoo Finance data provider via the yfinance library.

This is a free, no-API-key provider that supports fundamentals, price
history, and earnings data.  It serves as a low-priority fallback for
paid providers.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import yfinance as yf

from margin_engine.ingestion.rate_limiter import RateLimiter
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
    return {str(k): _safe_scalar(v) for k, v in first_col.items()}


def _safe_scalar(value):
    """Convert numpy/pandas scalar types to native Python types."""
    try:
        # Handle NaN
        if hasattr(value, "item"):
            return value.item()
        return value
    except (ValueError, TypeError):
        return value


def _df_all_columns_to_dicts(df) -> list[tuple[str, dict]]:
    """Extract all columns of a DataFrame as (period_end_iso, row_dict) pairs.

    Each column in a yfinance financials DataFrame represents a fiscal year.
    Returns pairs sorted oldest-first by date.
    """
    if df is None or df.empty:
        return []
    result = []
    for col in df.columns:
        col_data = df[col]
        row_dict = {str(k): _safe_scalar(v) for k, v in col_data.items()}
        # Column header is a Timestamp representing the fiscal year-end
        if hasattr(col, "strftime"):
            period_end = col.strftime("%Y-%m-%d")
        else:
            period_end = str(col)
        result.append((period_end, row_dict))
    # Sort oldest-first
    result.sort(key=lambda x: x[0])
    return result


def _build_periods_from_dfs(financials_df, balance_df, cashflow_df) -> list[dict]:
    """Combine all fiscal years from three statement DataFrames into period dicts.

    Returns a list of dicts sorted oldest-first, each with keys:
        ``period_end``, ``income_statement``, ``balance_sheet``, ``cash_flow``.
    """
    income_by_date = dict(_df_all_columns_to_dicts(financials_df))
    balance_by_date = dict(_df_all_columns_to_dicts(balance_df))
    cashflow_by_date = dict(_df_all_columns_to_dicts(cashflow_df))

    all_dates = sorted(set(income_by_date) | set(balance_by_date) | set(cashflow_by_date))

    periods = []
    for date in all_dates:
        periods.append(
            {
                "period_end": date,
                "income_statement": income_by_date.get(date, {}),
                "balance_sheet": balance_by_date.get(date, {}),
                "cash_flow": cashflow_by_date.get(date, {}),
            }
        )
    return periods


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class YFinanceProvider(DataProvider):
    """Concrete data provider backed by Yahoo Finance (yfinance library).

    Free, no-API-key provider with moderate rate limits.  Used as a
    fallback when premium providers are unavailable.
    """

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    async def _acquire_rate_limit_async(self) -> None:
        """Async version -- awaits if the limiter's wait_and_acquire is a coroutine."""
        if self._rate_limiter is not None:
            result = self._rate_limiter.wait_and_acquire()
            if asyncio.iscoroutine(result):
                await result

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

        Returns the most recent annual period for each statement, plus
        a ``"periods"`` key with all available fiscal years.
        """
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            raw_data = {
                "income_statement": _df_most_recent_column_to_dict(t.financials),
                "balance_sheet": _df_most_recent_column_to_dict(t.balance_sheet),
                "cash_flow": _df_most_recent_column_to_dict(t.cashflow),
                "periods": _build_periods_from_dfs(t.financials, t.balance_sheet, t.cashflow),
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
        self._acquire_rate_limit()
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
        self._acquire_rate_limit()
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

    # ------------------------------------------------------------------
    # Info (asset metadata)
    # ------------------------------------------------------------------

    def fetch_info(self, ticker: str) -> FetchResult:
        """Fetch asset metadata (name, sector, country, market_cap, etc.).

        Uses ``yf.Ticker(ticker).info`` and returns the raw info dict.
        """
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            raw_data = t.info if t.info else {}
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
    # Fetch all categories
    # ------------------------------------------------------------------

    def fetch_all(self, ticker: str, price_days: int = 365) -> dict[str, FetchResult]:
        """Fetch all data categories from a single ``yf.Ticker`` instance.

        Creates ONE Ticker object and fetches fundamentals, price, earnings,
        and info from it.  Each category is independent --- a failure in one
        does not block others.

        Returns:
            Dict keyed by ``"fundamentals"``, ``"price"``, ``"earnings"``,
            ``"info"``, each mapping to a :class:`FetchResult`.
        """
        t = yf.Ticker(ticker)
        results: dict[str, FetchResult] = {}

        # --- fundamentals ---
        self._acquire_rate_limit()
        try:
            raw_fundamentals = {
                "income_statement": _df_most_recent_column_to_dict(t.financials),
                "balance_sheet": _df_most_recent_column_to_dict(t.balance_sheet),
                "cash_flow": _df_most_recent_column_to_dict(t.cashflow),
                "periods": _build_periods_from_dfs(t.financials, t.balance_sheet, t.cashflow),
            }
            results["fundamentals"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=raw_fundamentals,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["fundamentals"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # --- price ---
        self._acquire_rate_limit()
        try:
            period = _days_to_period(price_days)
            hist = t.history(period=period)

            bars: list[dict] = []
            if hist is not None and not hist.empty:
                hist_reset = hist.reset_index()
                bars = hist_reset.to_dict(orient="records")
                for bar in bars:
                    for key, val in bar.items():
                        if hasattr(val, "isoformat"):
                            bar[key] = val.isoformat()
                        elif hasattr(val, "item"):
                            bar[key] = val.item()

            results["price"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={"bars": bars},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["price"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # --- earnings ---
        self._acquire_rate_limit()
        try:
            df = t.earnings_dates

            earnings: list[dict] = []
            if df is not None and not df.empty:
                for date_idx, row in df.iterrows():
                    entry: dict = {"quarter": str(date_idx)}
                    if "Reported EPS" in row:
                        entry["actual_eps"] = _safe_scalar(row["Reported EPS"])
                    if "EPS Estimate" in row:
                        entry["expected_eps"] = _safe_scalar(row["EPS Estimate"])
                    earnings.append(entry)

            results["earnings"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["earnings"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # --- info ---
        self._acquire_rate_limit()
        try:
            raw_info = t.info if t.info else {}
            results["info"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=raw_info,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["info"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        return results
