"""Tests for live price service."""

from __future__ import annotations

import pytest
import pytest_asyncio


class TestLivePriceService:
    @pytest_asyncio.fixture()
    async def redis_client(self):
        """Create a fake Redis client for testing."""
        try:
            import fakeredis.aioredis

            client = fakeredis.aioredis.FakeRedis()
        except ImportError:
            # Fall back to a simple mock
            from unittest.mock import AsyncMock

            client = AsyncMock()
            store: dict[str, bytes] = {}

            async def mock_get(key):
                return store.get(key)

            async def mock_set(key, value, ex=None):
                store[key] = value

            client.get = mock_get
            client.set = mock_set

        yield client
        try:
            await client.aclose()
        except Exception:
            pass

    @pytest_asyncio.fixture()
    async def service(self, redis_client):
        from margin_api.services.live_prices import LivePriceService

        return LivePriceService(redis_client)

    @pytest.mark.asyncio
    async def test_get_price_returns_none_when_not_cached(self, service):
        result = await service.get_price("AAPL")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_price(self, service):
        await service.set_price("AAPL", 185.50)
        result = await service.get_price("AAPL")
        assert result is not None
        assert result["price"] == 185.50
        assert result["source"] == "live"
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_get_prices_multiple(self, service):
        await service.set_price("AAPL", 185.50)
        await service.set_price("MSFT", 420.00)
        result = await service.get_prices(["AAPL", "MSFT", "NVDA"])
        assert result["AAPL"]["price"] == 185.50
        assert result["MSFT"]["price"] == 420.00
        assert result["NVDA"] is None

    @pytest.mark.asyncio
    async def test_set_prices_batch(self, service):
        await service.set_prices({"AAPL": 185.50, "MSFT": 420.00})
        aapl = await service.get_price("AAPL")
        msft = await service.get_price("MSFT")
        assert aapl["price"] == 185.50
        assert msft["price"] == 420.00

    @pytest.mark.asyncio
    async def test_key_prefix(self, service, redis_client):
        """Verify the Redis key uses the correct prefix."""
        await service.set_price("AAPL", 185.50)
        raw = await redis_client.get("live_price:AAPL")
        assert raw is not None

    @pytest.mark.asyncio
    async def test_ttl_is_set(self, service, redis_client):
        """Verify TTL is set on cached prices."""
        await service.set_price("AAPL", 185.50)
        ttl = await redis_client.ttl("live_price:AAPL")
        assert ttl > 0
        assert ttl <= 600

    @pytest.mark.asyncio
    async def test_get_bar_returns_none_when_not_cached(self, service):
        result = await service.get_bar("AAPL")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_bar(self, service):
        bar = {
            "date": "2026-03-06",
            "open": 188.50,
            "high": 192.30,
            "low": 187.20,
            "close": 191.75,
            "volume": 4523000,
        }
        await service.set_bar("AAPL", bar)
        result = await service.get_bar("AAPL")
        assert result is not None
        assert result["date"] == "2026-03-06"
        assert result["close"] == 191.75
        assert result["volume"] == 4523000
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_bar_key_prefix(self, service, redis_client):
        bar = {"date": "2026-03-06", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
        await service.set_bar("AAPL", bar)
        raw = await redis_client.get("live_bar:AAPL")
        assert raw is not None

    @pytest.mark.asyncio
    async def test_bar_ttl_is_set(self, service, redis_client):
        bar = {"date": "2026-03-06", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
        await service.set_bar("AAPL", bar)
        ttl = await redis_client.ttl("live_bar:AAPL")
        assert ttl > 0
        assert ttl <= 86400
