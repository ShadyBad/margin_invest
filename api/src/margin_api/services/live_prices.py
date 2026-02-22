"""Live price service -- Redis-backed real-time price cache."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import redis.asyncio as redis


class LivePriceService:
    """Read and write live prices from Redis."""

    KEY_PREFIX = "live_price:"
    TTL_SECONDS = 600  # 10 minutes

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get_price(self, ticker: str) -> dict | None:
        """Get live price for a ticker. Returns None if not cached."""
        data = await self.redis.get(f"{self.KEY_PREFIX}{ticker}")
        if data is None:
            return None
        return json.loads(data)

    async def set_price(self, ticker: str, price: float) -> None:
        """Cache a live price with TTL."""
        data = json.dumps(
            {
                "price": price,
                "updated_at": datetime.now(UTC).isoformat(),
                "source": "live",
            }
        )
        await self.redis.set(f"{self.KEY_PREFIX}{ticker}", data, ex=self.TTL_SECONDS)

    async def get_prices(self, tickers: list[str]) -> dict[str, dict | None]:
        """Get live prices for multiple tickers."""
        result: dict[str, dict | None] = {}
        for ticker in tickers:
            result[ticker] = await self.get_price(ticker)
        return result

    async def set_prices(self, prices: dict[str, float]) -> None:
        """Cache multiple live prices."""
        for ticker, price in prices.items():
            await self.set_price(ticker, price)
