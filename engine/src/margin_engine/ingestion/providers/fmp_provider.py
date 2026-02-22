"""Financial Modeling Prep (FMP) data provider.

Fallback provider for fundamentals and earnings data when yfinance fails.
Uses httpx for synchronous HTTP requests against the FMP REST API.

FMP API docs: https://financialmodelingprep.com/developer/docs
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
    """Concrete data provider backed by Financial Modeling Prep.

    Requires an API key (free tier available).  Supports fundamentals
    (income statement only) and earnings.  Priority is lower than
    yfinance so it acts as a fallback.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("FMP api_key must not be empty")
        self._api_key = api_key
        self._rate_limiter = rate_limiter

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
                DataCategory.EARNINGS,
            ],
            requests_per_minute=300,
            requires_api_key=True,
            priority=5,
        )

    # ------------------------------------------------------------------
    # Fundamentals (income statement only)
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch income statement from FMP.

        balance_sheet and cash_flow are returned as empty dicts because
        FMP uses separate endpoints for those statements.
        """
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/income-statement/{ticker}?apikey={self._api_key}&limit=1"
            resp = httpx.get(url)
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
            url = (
                f"{_BASE_URL}/historical/earning_calendar/{ticker}"
                f"?apikey={self._api_key}&limit=25"
            )
            resp = httpx.get(url)
            resp.raise_for_status()
            rows = resp.json()

            earnings: list[dict] = []
            for row in rows:
                entry: dict = {
                    "quarter": row["date"],
                    "actual_eps": row["eps"],
                    "expected_eps": row["epsEstimated"],
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
