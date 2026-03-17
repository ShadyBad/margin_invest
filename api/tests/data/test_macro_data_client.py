"""Tests for FRED API client — Shiller CAPE fetching."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from margin_api.data.fred_client import _DEFAULT_CAPE, fetch_shiller_cape


class TestFetchShillerCape:
    @pytest.mark.asyncio
    async def test_returns_float(self):
        """Should return a float CAPE value."""
        with patch("margin_api.data.fred_client._fetch_from_fred", new_callable=AsyncMock) as mock:
            mock.return_value = 30.5
            result = await fetch_shiller_cape()
            assert isinstance(result, float)
            assert result == 30.5

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Returns default CAPE (25.0) if FRED API fails."""
        with patch("margin_api.data.fred_client._fetch_from_fred", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API down")
            result = await fetch_shiller_cape()
            assert result == _DEFAULT_CAPE

    @pytest.mark.asyncio
    async def test_fallback_on_missing_api_key(self):
        """Returns default if no API key configured."""
        with patch("margin_api.data.fred_client._fetch_from_fred", new_callable=AsyncMock) as mock:
            mock.side_effect = ValueError("No API key")
            result = await fetch_shiller_cape()
            assert result == _DEFAULT_CAPE

    @pytest.mark.asyncio
    async def test_caches_result(self):
        """Second call should use cached value, not call FRED again."""
        with patch("margin_api.data.fred_client._fetch_from_fred", new_callable=AsyncMock) as mock:
            mock.return_value = 32.0
            result1 = await fetch_shiller_cape()
            result2 = await fetch_shiller_cape()
            assert result1 == 32.0
            assert result2 == 32.0
            # Should only have been called once due to caching
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_bypass_after_expiry(self):
        """After cache expires, should fetch again."""
        import time

        with patch("margin_api.data.fred_client._fetch_from_fred", new_callable=AsyncMock) as mock:
            mock.return_value = 28.0
            await fetch_shiller_cape()

            # Manually expire the cache
            from margin_api.data import fred_client

            for key in fred_client._cache:
                val, _ = fred_client._cache[key]
                fred_client._cache[key] = (val, time.time() - 1)

            mock.return_value = 29.0
            result = await fetch_shiller_cape()
            assert result == 29.0
            assert mock.call_count == 2

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """Clear the module-level cache before each test."""
        from margin_api.data import fred_client

        fred_client._cache.clear()
        yield
        fred_client._cache.clear()
