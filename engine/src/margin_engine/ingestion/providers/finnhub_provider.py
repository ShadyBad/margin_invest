"""Finnhub data provider via the official Python SDK.

Provides earnings surprises, insider transactions, institutional
holdings, and company news. Free tier supports 60 API calls/min.

Finnhub docs: https://finnhub.io/docs/api
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

import finnhub

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FinnhubProvider(DataProvider):
    """Concrete data provider backed by Finnhub.

    Requires an API key. Supports earnings, insider transactions,
    institutional holdings, and company news. Priority is 5 — acts
    as primary for earnings/news and fallback for insider/institutional
    (SEC EDGAR will be higher priority when built).
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Finnhub api_key must not be empty")
        self._api_key = api_key
        self._rate_limiter = rate_limiter
        self._client = finnhub.Client(api_key=api_key)

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="finnhub",
            supported_categories=[
                DataCategory.EARNINGS,
                DataCategory.INSIDER,
                DataCategory.INSTITUTIONAL,
                DataCategory.NEWS,
            ],
            requests_per_minute=60,
            requires_api_key=True,
            priority=5,
        )

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch quarterly earnings surprises.

        Requests up to 12 quarters (3 years). Free tier may return
        fewer — we accept whatever comes back.
        """
        self._acquire_rate_limit()
        try:
            data = self._client.company_earnings(symbol=ticker, limit=12)
            earnings = data if data else []

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

    def fetch_insider_transactions(self, ticker: str) -> FetchResult:
        """Fetch insider trading activity for the last year."""
        self._acquire_rate_limit()
        try:
            to_date = date.today()
            from_date = to_date - timedelta(days=365)

            data = self._client.stock_insider_transactions(
                symbol=ticker,
                _from=str(from_date),
                to=str(to_date),
            )
            transactions = data.get("data", []) if data else []

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSIDER,
                ticker=ticker,
                raw_data={"transactions": transactions},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSIDER,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    def fetch_institutional_holdings(self, ticker: str) -> FetchResult:
        """Fetch institutional ownership data for the last year."""
        self._acquire_rate_limit()
        try:
            to_date = date.today()
            from_date = to_date - timedelta(days=365)

            data = self._client.institutional_ownership(
                symbol=ticker,
                _from=str(from_date),
                to=str(to_date),
            )
            holdings = data if data else []

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSTITUTIONAL,
                ticker=ticker,
                raw_data={"holdings": holdings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSTITUTIONAL,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    def fetch_news(self, ticker: str) -> FetchResult:
        """Fetch company news articles for the last 30 days."""
        self._acquire_rate_limit()
        try:
            to_date = date.today()
            from_date = to_date - timedelta(days=30)

            data = self._client.company_news(
                symbol=ticker,
                _from=str(from_date),
                to=str(to_date),
            )
            articles = data if data else []

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.NEWS,
                ticker=ticker,
                raw_data={"articles": articles},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.NEWS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )
