"""Financial Modeling Prep (FMP) data provider.

Paid/free-tier provider used as fallback for failed yfinance categories.
Requires FMP_API_KEY environment variable.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

_BASE_URL = "https://financialmodelingprep.com/api/v3"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FMPProvider(DataProvider):
    """FMP data provider for fundamentals, earnings, and price history.

    Requires an API key (free tier available).  Priority is higher than
    yfinance so it acts as a preferred fallback.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required for FMPProvider")
        self._api_key = api_key
        self._rate_limiter = rate_limiter
        self._timeout = timeout

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="fmp",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.PRICE,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=300,
            requires_api_key=True,
            priority=20,
        )

    # ------------------------------------------------------------------
    # Fundamentals (income statement)
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch income statement from FMP.

        balance_sheet and cash_flow are returned as empty dicts because
        FMP uses separate endpoints for those statements.
        """
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/income-statement/{ticker}"
            resp = httpx.get(
                url,
                params={"apikey": self._api_key, "limit": 1},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            rows = resp.json()

            income_statement = rows[0] if rows else {}

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={
                    "income_statement": income_statement,
                    "balance_sheet": {},
                    "cash_flow": {},
                },
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
    # Earnings
    # ------------------------------------------------------------------

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch historical earnings calendar from FMP.

        Maps FMP field names to the canonical schema:
            row["eps"]          -> entry["actual_eps"]
            row["epsEstimated"] -> entry["expected_eps"]
            row["date"]         -> entry["quarter"]
        """
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/historical/earning_calendar/{ticker}"
            resp = httpx.get(
                url,
                params={"apikey": self._api_key, "limit": 25},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            rows = resp.json()

            earnings: list[dict] = []
            for row in rows:
                entry: dict = {
                    "quarter": row.get("date", ""),
                    "actual_eps": row.get("eps"),
                    "expected_eps": row.get("epsEstimated"),
                }
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
    # Price history
    # ------------------------------------------------------------------

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        """Fetch historical daily OHLCV bars from FMP.

        Uses the ``historical-price-full`` endpoint with a ``timeseries``
        parameter to limit results to the requested number of days.
        """
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/historical-price-full/{ticker}"
            resp = httpx.get(
                url,
                params={"apikey": self._api_key, "timeseries": days},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_bars = data.get("historical", []) if isinstance(data, dict) else []

            bars = []
            for bar in raw_bars:
                bars.append(
                    {
                        "date": bar.get("date", ""),
                        "open": bar.get("open"),
                        "high": bar.get("high"),
                        "low": bar.get("low"),
                        "close": bar.get("close"),
                        "volume": bar.get("volume"),
                    }
                )

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
