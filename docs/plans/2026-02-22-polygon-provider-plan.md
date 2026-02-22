# Polygon.io Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Polygon.io as the primary price data provider with yfinance as fallback, using the official Python SDK.

**Architecture:** New `PolygonProvider` class implements the `DataProvider` ABC, registered in the existing provider infrastructure. Only `fetch_price_history` is active (Free tier); fundamentals/earnings are stubbed. The provider uses `polygon-api-client` SDK for typed responses and pagination.

**Tech Stack:** Python 3.13, polygon-api-client SDK, httpx (transitive), pytest, pydantic

---

### Task 1: Add polygon-api-client dependency

**Files:**
- Modify: `engine/pyproject.toml:6-14`

**Step 1: Add the dependency**

```bash
uv add polygon-api-client --package margin-engine
```

**Step 2: Verify it installed**

```bash
uv run python -c "from polygon import RESTClient; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add engine/pyproject.toml uv.lock
git commit -m "feat(engine): add polygon-api-client dependency"
```

---

### Task 2: PolygonProvider — tests and implementation

**Files:**
- Create: `engine/tests/ingestion/providers/test_polygon_provider.py`
- Create: `engine/src/margin_engine/ingestion/providers/polygon_provider.py`

**Step 1: Write the failing tests**

Create `engine/tests/ingestion/providers/test_polygon_provider.py`:

```python
"""Tests for Polygon.io data provider."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.types import DataCategory


class TestProviderInfo:
    def test_name(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.name == "polygon"

    def test_priority_above_yfinance(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.priority == 20

    def test_requires_api_key(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.requires_api_key is True

    def test_supported_categories_price_only(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.supported_categories == [DataCategory.PRICE]

    def test_rate_limit_free_tier(self):
        provider = PolygonProvider(api_key="test_key")
        assert provider.info.requests_per_minute == 5

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key must not be empty"):
            PolygonProvider(api_key="")


class TestFetchPriceHistory:
    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_success_returns_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Simulate two daily bars
        bar1 = MagicMock()
        bar1.timestamp = 1706140800000  # 2024-01-25 00:00 UTC
        bar1.open = 150.0
        bar1.high = 155.0
        bar1.low = 149.0
        bar1.close = 154.0
        bar1.volume = 1000000
        bar1.vwap = 152.5

        bar2 = MagicMock()
        bar2.timestamp = 1706227200000  # 2024-01-26 00:00 UTC
        bar2.open = 154.0
        bar2.high = 158.0
        bar2.low = 153.0
        bar2.close = 157.0
        bar2.volume = 1200000
        bar2.vwap = 155.5

        mock_client.get_aggs.return_value = [bar1, bar2]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.provider_name == "polygon"
        assert result.category == DataCategory.PRICE
        assert result.ticker == "AAPL"
        assert len(result.raw_data["bars"]) == 2
        assert result.raw_data["bars"][0]["open"] == 150.0
        assert result.raw_data["bars"][0]["close"] == 154.0
        assert result.raw_data["bars"][0]["volume"] == 1000000

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_bar_date_is_iso_format(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        bar = MagicMock()
        bar.timestamp = 1706140800000  # 2024-01-25 00:00 UTC
        bar.open = 150.0
        bar.high = 155.0
        bar.low = 149.0
        bar.close = 154.0
        bar.volume = 1000000
        bar.vwap = 152.5
        mock_client.get_aggs.return_value = [bar]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.raw_data["bars"][0]["date"] == "2024-01-25"

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_adj_close_equals_close_for_adjusted_data(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        bar = MagicMock()
        bar.timestamp = 1706140800000
        bar.open = 150.0
        bar.high = 155.0
        bar.low = 149.0
        bar.close = 154.0
        bar.volume = 1000000
        bar.vwap = 152.5
        mock_client.get_aggs.return_value = [bar]

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.raw_data["bars"][0]["adj_close"] == 154.0

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_days_clamped_to_730(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = []

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=1000)

        # Verify the from_ date is at most 730 days ago
        call_kwargs = mock_client.get_aggs.call_args
        from_date = call_kwargs.kwargs.get("from_") or call_kwargs[1].get("from_")
        expected_from = str(date.today() - timedelta(days=730))
        assert from_date == expected_from

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_empty_response_returns_success_with_no_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = []

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.raw_data["bars"] == []

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_none_response_returns_success_with_no_bars(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.return_value = None

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.raw_data["bars"] == []

    @patch("margin_engine.ingestion.providers.polygon_provider.RESTClient")
    def test_api_error_returns_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_aggs.side_effect = Exception("API rate limit exceeded")

        provider = PolygonProvider(api_key="test_key")
        result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is False
        assert "API rate limit exceeded" in result.error


class TestStubbedMethods:
    def test_fetch_fundamentals_raises(self):
        provider = PolygonProvider(api_key="test_key")
        with pytest.raises(NotImplementedError, match="Starter"):
            provider.fetch_fundamentals("AAPL")

    def test_fetch_earnings_raises(self):
        provider = PolygonProvider(api_key="test_key")
        with pytest.raises(NotImplementedError, match="Starter"):
            provider.fetch_earnings("AAPL")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest engine/tests/ingestion/providers/test_polygon_provider.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ingestion.providers.polygon_provider'`

**Step 3: Write the implementation**

Create `engine/src/margin_engine/ingestion/providers/polygon_provider.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest engine/tests/ingestion/providers/test_polygon_provider.py -v
```

Expected: all 12 tests PASS

**Step 5: Commit**

```bash
git add engine/tests/ingestion/providers/test_polygon_provider.py engine/src/margin_engine/ingestion/providers/polygon_provider.py
git commit -m "feat(engine): add Polygon.io price data provider"
```

---

### Task 3: Export PolygonProvider from package

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/__init__.py`
- Modify: `engine/src/margin_engine/ingestion/__init__.py`

**Step 1: Update providers __init__.py**

Edit `engine/src/margin_engine/ingestion/providers/__init__.py`:

```python
"""Concrete data provider implementations."""

from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

__all__ = ["FMPProvider", "PolygonProvider", "YFinanceProvider"]
```

**Step 2: Update ingestion __init__.py**

Add to `engine/src/margin_engine/ingestion/__init__.py`:

- Import: `from margin_engine.ingestion.providers.polygon_provider import PolygonProvider`
- Add `"PolygonProvider"` to `__all__` list

**Step 3: Verify import works**

```bash
uv run python -c "from margin_engine.ingestion import PolygonProvider; print(PolygonProvider.__name__)"
```

Expected: `PolygonProvider`

**Step 4: Run all engine tests to check nothing broke**

```bash
uv run pytest engine/tests/ -v --tb=short -q
```

Expected: all tests pass

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/__init__.py engine/src/margin_engine/ingestion/__init__.py
git commit -m "feat(engine): export PolygonProvider from ingestion package"
```

---

### Task 4: Add polygon_api_key to API config

**Files:**
- Modify: `api/src/margin_api/config.py:50` (after `api_key_encryption_key`)

**Step 1: Add the config field**

Add after `api_key_encryption_key` in `api/src/margin_api/config.py`:

```python
    # Data providers
    polygon_api_key: str = ""
    fmp_api_key: str = ""
```

Note: `fmp_api_key` may already exist — only add `polygon_api_key` if so. Check first.

**Step 2: Verify it loads from env**

```bash
MARGIN_POLYGON_API_KEY=test123 uv run python -c "from margin_api.config import get_settings; print(get_settings().polygon_api_key)"
```

Expected: `test123`

**Step 3: Commit**

```bash
git add api/src/margin_api/config.py
git commit -m "feat(api): add polygon_api_key to settings"
```

---

### Task 5: Registry integration test

**Files:**
- Modify: `engine/tests/ingestion/test_registry.py`

**Step 1: Write the integration test**

Add a new test class at the bottom of `engine/tests/ingestion/test_registry.py`:

```python
class TestPolygonInFallbackChain:
    """Verify real PolygonProvider integrates with registry correctly."""

    def test_polygon_is_primary_price_provider(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry(api_keys={"polygon": "test_key"})
        registry.register(PolygonProvider(api_key="test_key"))
        registry.register(YFinanceProvider())

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["polygon", "yfinance"]

    def test_polygon_excluded_without_api_key(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry(api_keys={})
        registry.register(PolygonProvider(api_key="test_key"))
        registry.register(YFinanceProvider())

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["yfinance"]

    def test_polygon_not_in_fundamentals_chain(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider

        registry = ProviderRegistry(api_keys={"polygon": "test_key"})
        registry.register(PolygonProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        assert len(chain) == 0
```

**Step 2: Run the test**

```bash
uv run pytest engine/tests/ingestion/test_registry.py::TestPolygonInFallbackChain -v
```

Expected: all 3 tests PASS

**Step 3: Run full engine test suite**

```bash
uv run pytest engine/tests/ -q
```

Expected: all tests pass

**Step 4: Commit**

```bash
git add engine/tests/ingestion/test_registry.py
git commit -m "test(engine): add Polygon registry integration tests"
```

---

### Task 6: Lint, format, and final verification

**Step 1: Run ruff check and format**

```bash
uv run ruff check engine/ api/ && uv run ruff format engine/ api/
```

Fix any issues that arise.

**Step 2: Run full test suites**

```bash
uv run pytest engine/tests/ -v --tb=short -q
uv run pytest api/tests/ -v --tb=short -q
```

Expected: all tests pass

**Step 3: Commit any lint/format fixes**

```bash
git add -A
git commit -m "style: lint and format Polygon provider"
```
