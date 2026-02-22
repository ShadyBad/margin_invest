"""Polygon.io data provider via the official Python SDK.

Primary provider for price history data. Supports Free (Basic) tier
with 5 API calls/min and 2-year history limit. Fundamentals and
earnings are stubbed until a Starter+ plan is configured.

Polygon docs: https://polygon.io/docs/stocks
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from polygon import RESTClient

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

logger = logging.getLogger(__name__)

_MAX_FREE_TIER_DAYS = 730


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _timestamp_ms_to_date(ts_ms: int) -> str:
    """Convert a Unix timestamp in milliseconds to an ISO date string."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d")


class PolygonProvider(DataProvider):
    """Concrete data provider backed by Polygon.io.

    Requires an API key. On Free tier, only price history is available.
    Priority is 20 (above yfinance at 10) so it becomes the primary
    price data source with yfinance as fallback.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Polygon api_key must not be empty")
        self._api_key = api_key
        self._rate_limiter = rate_limiter
        self._client = RESTClient(api_key=api_key)

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="polygon",
            supported_categories=[DataCategory.PRICE],
            requests_per_minute=5,
            requires_api_key=True,
            priority=20,
        )

    # ------------------------------------------------------------------
    # Price history (active — Free tier)
    # ------------------------------------------------------------------

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        """Fetch daily OHLCV bars from Polygon aggregates endpoint.

        Free tier limits: 5 calls/min, 2-year max history. Days > 730
        are clamped with a warning.
        """
        self._acquire_rate_limit()
        try:
            if days > _MAX_FREE_TIER_DAYS:
                logger.warning(
                    "Polygon free tier: clamping %d days to %d",
                    days,
                    _MAX_FREE_TIER_DAYS,
                )
                days = _MAX_FREE_TIER_DAYS

            to_date = date.today()
            from_date = to_date - timedelta(days=days)

            aggs = self._client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=str(from_date),
                to=str(to_date),
                adjusted=True,
                sort="asc",
            )

            bars: list[dict] = []
            if aggs:
                for agg in aggs:
                    bars.append(
                        {
                            "date": _timestamp_ms_to_date(agg.timestamp),
                            "open": agg.open,
                            "high": agg.high,
                            "low": agg.low,
                            "close": agg.close,
                            "volume": agg.volume,
                            "adj_close": agg.close,
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

    # ------------------------------------------------------------------
    # Fundamentals (stubbed — requires Starter+ plan)
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Not available on Free tier."""
        raise NotImplementedError(
            "Polygon fundamentals requires Starter+ plan"
        )

    # ------------------------------------------------------------------
    # Earnings (stubbed — requires Starter+ plan)
    # ------------------------------------------------------------------

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Not available on Free tier."""
        raise NotImplementedError(
            "Polygon earnings requires Starter+ plan"
        )
