# Finnhub Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Finnhub as the provider for earnings, news, insider transactions, and institutional holdings, using the official Python SDK.

**Architecture:** New `FinnhubProvider` class implements `DataProvider` ABC with four active fetch methods. Registry updated to support NEWS category (removed from `_NON_TICKER_CATEGORIES`, `fetch_news` added to ABC). Uses `finnhub-python` SDK for typed API access.

**Tech Stack:** Python 3.13, finnhub-python SDK, pytest, pydantic

---

### Task 1: Add finnhub-python dependency

**Files:**
- Modify: `engine/pyproject.toml`

**Step 1: Add the dependency**

```bash
uv add finnhub-python --package margin-engine
```

**Step 2: Verify it installed**

```bash
uv run python -c "import finnhub; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add engine/pyproject.toml uv.lock
git commit -m "feat(engine): add finnhub-python dependency"
```

---

### Task 2: Add fetch_news to DataProvider ABC and enable NEWS in registry

**Files:**
- Modify: `engine/src/margin_engine/ingestion/types.py:95-113`
- Modify: `engine/src/margin_engine/ingestion/registry.py:34,37-43`
- Modify: `engine/tests/ingestion/test_registry.py:534-540`

**Step 1: Write the failing tests**

Add to the existing `FakeProvider` class in `engine/tests/ingestion/test_registry.py` — add this method after `fetch_earnings`:

```python
    def fetch_news(self, ticker: str) -> FetchResult:
        self.calls.append(("fetch_news", ticker, {}))
        return self._make_result(DataCategory.NEWS, ticker)
```

Replace the existing `test_news_fetch_raises_not_implemented` test in `TestUnsupportedCategoryFetch` with:

```python
    def test_news_fetch_dispatches_correctly(self):
        registry = ProviderRegistry()
        provider = FakeProvider("finnhub", [DataCategory.NEWS], priority=10)
        registry.register(provider)

        result = registry.fetch(DataCategory.NEWS, "AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert provider.calls[0] == ("fetch_news", "AAPL", {})
```

Also add a new test class at the bottom of the file:

```python
class TestFetchNewsABC:
    """Verify fetch_news exists on the ABC and raises by default."""

    def test_abc_fetch_news_raises_not_implemented(self):
        from margin_engine.ingestion.types import DataProvider

        class MinimalProvider(DataProvider):
            @property
            def info(self) -> ProviderInfo:
                return ProviderInfo(
                    name="minimal",
                    supported_categories=[],
                    requests_per_minute=1,
                    requires_api_key=False,
                )

        provider = MinimalProvider()
        with pytest.raises(NotImplementedError, match="fetch_news"):
            provider.fetch_news("AAPL")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest engine/tests/ingestion/test_registry.py::TestUnsupportedCategoryFetch::test_news_fetch_dispatches_correctly engine/tests/ingestion/test_registry.py::TestFetchNewsABC -v
```

Expected: FAIL — `AttributeError: 'FakeProvider' object has no attribute 'fetch_news'` and `NotImplementedError: NEWS`

**Step 3: Update the ABC**

In `engine/src/margin_engine/ingestion/types.py`, add after the `fetch_earnings` method (after line 113):

```python
    def fetch_news(self, ticker: str) -> FetchResult:
        """Fetch news articles for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_news")
```

**Step 4: Update the registry**

In `engine/src/margin_engine/ingestion/registry.py`:

Change line 34 from:
```python
_NON_TICKER_CATEGORIES: frozenset[DataCategory] = frozenset({DataCategory.MACRO, DataCategory.NEWS})
```
to:
```python
_NON_TICKER_CATEGORIES: frozenset[DataCategory] = frozenset({DataCategory.MACRO})
```

Add to `_CATEGORY_METHOD_MAP` (after `EARNINGS` entry):
```python
    DataCategory.NEWS: "fetch_news",
```

Update the docstring for `fetch()` — change "MACRO or NEWS" to just "MACRO" in the Raises section (line 126-128).

**Step 5: Run tests to verify they pass**

```bash
uv run pytest engine/tests/ingestion/test_registry.py -v --tb=short
```

Expected: all tests pass (the old NEWS NotImplementedError test is replaced)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/ingestion/types.py engine/src/margin_engine/ingestion/registry.py engine/tests/ingestion/test_registry.py
git commit -m "feat(engine): add fetch_news to ABC and enable NEWS in registry"
```

---

### Task 3: FinnhubProvider — tests and implementation

**Files:**
- Create: `engine/tests/ingestion/providers/test_finnhub_provider.py`
- Create: `engine/src/margin_engine/ingestion/providers/finnhub_provider.py`

**Step 1: Write the failing tests**

Create `engine/tests/ingestion/providers/test_finnhub_provider.py`:

```python
"""Tests for Finnhub data provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider
from margin_engine.ingestion.types import DataCategory


class TestProviderInfo:
    def test_name(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.name == "finnhub"

    def test_priority(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.priority == 5

    def test_requires_api_key(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.requires_api_key is True

    def test_supported_categories(self):
        provider = FinnhubProvider(api_key="test_key")
        assert set(provider.info.supported_categories) == {
            DataCategory.EARNINGS,
            DataCategory.INSIDER,
            DataCategory.INSTITUTIONAL,
            DataCategory.NEWS,
        }

    def test_rate_limit(self):
        provider = FinnhubProvider(api_key="test_key")
        assert provider.info.requests_per_minute == 60

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key must not be empty"):
            FinnhubProvider(api_key="")


class TestFetchEarnings:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.return_value = [
            {
                "actual": 1.88,
                "estimate": 1.97,
                "period": "2023-03-31",
                "quarter": 1,
                "surprise": -0.09,
                "surprisePercent": -4.78,
                "symbol": "AAPL",
                "year": 2023,
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.EARNINGS
        assert result.ticker == "AAPL"
        assert len(result.raw_data["earnings"]) == 1
        assert result.raw_data["earnings"][0]["actual"] == 1.88
        assert result.raw_data["earnings"][0]["period"] == "2023-03-31"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.raw_data["earnings"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_earnings.side_effect = Exception("API error")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_earnings("AAPL")

        assert result.success is False
        assert "API error" in result.error


class TestFetchInsiderTransactions:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.return_value = {
            "data": [
                {
                    "name": "Tim Cook",
                    "share": 100000,
                    "change": -50000,
                    "filingDate": "2023-08-01",
                    "transactionDate": "2023-07-28",
                    "transactionCode": "S",
                    "transactionPrice": 195.5,
                }
            ],
            "symbol": "AAPL",
        }

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.INSIDER
        assert len(result.raw_data["transactions"]) == 1
        assert result.raw_data["transactions"][0]["name"] == "Tim Cook"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_data_key(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.return_value = {
            "data": [],
            "symbol": "AAPL",
        }

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.raw_data["transactions"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.stock_insider_transactions.side_effect = Exception("timeout")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is False
        assert "timeout" in result.error


class TestFetchInstitutionalHoldings:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.return_value = [
            {
                "cik": "0001067983",
                "name": "Berkshire Hathaway",
                "putCall": "",
                "change": 5000,
                "noVoting": 0,
                "percentage": 5.2,
                "share": 890000,
                "value": 170000000,
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.INSTITUTIONAL
        assert len(result.raw_data["holdings"]) == 1
        assert result.raw_data["holdings"][0]["name"] == "Berkshire Hathaway"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.raw_data["holdings"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.institutional_ownership.side_effect = Exception("forbidden")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is False
        assert "forbidden" in result.error


class TestFetchNews:
    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "category": "company news",
                "datetime": 1569550360,
                "headline": "Apple launches new product",
                "id": 25286,
                "image": "https://example.com/img.jpg",
                "related": "AAPL",
                "source": "Reuters",
                "summary": "Apple announced...",
                "url": "https://example.com/article",
            }
        ]

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is True
        assert result.provider_name == "finnhub"
        assert result.category == DataCategory.NEWS
        assert len(result.raw_data["articles"]) == 1
        assert result.raw_data["articles"][0]["headline"] == "Apple launches new product"

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.return_value = []

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is True
        assert result.raw_data["articles"] == []

    @patch("margin_engine.ingestion.providers.finnhub_provider.finnhub.Client")
    def test_api_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.company_news.side_effect = Exception("rate limited")

        provider = FinnhubProvider(api_key="test_key")
        result = provider.fetch_news("AAPL")

        assert result.success is False
        assert "rate limited" in result.error
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest engine/tests/ingestion/providers/test_finnhub_provider.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ingestion.providers.finnhub_provider'`

**Step 3: Write the implementation**

Create `engine/src/margin_engine/ingestion/providers/finnhub_provider.py`:

```python
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

    # ------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Insider transactions
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Institutional holdings
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest engine/tests/ingestion/providers/test_finnhub_provider.py -v
```

Expected: all 18 tests PASS

**Step 5: Commit**

```bash
git add engine/tests/ingestion/providers/test_finnhub_provider.py engine/src/margin_engine/ingestion/providers/finnhub_provider.py
git commit -m "feat(engine): add Finnhub provider for earnings, insider, institutional, news"
```

---

### Task 4: Export FinnhubProvider from package

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/__init__.py`
- Modify: `engine/src/margin_engine/ingestion/__init__.py`

**Step 1: Update providers __init__.py**

Add import and update `__all__` in `engine/src/margin_engine/ingestion/providers/__init__.py`:

```python
"""Concrete data provider implementations."""

from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider
from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

__all__ = ["FinnhubProvider", "FMPProvider", "PolygonProvider", "YFinanceProvider"]
```

**Step 2: Update ingestion __init__.py**

Add to `engine/src/margin_engine/ingestion/__init__.py`:

- Import: `from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider`
- Add `"FinnhubProvider"` to `__all__` list (alphabetical order)

**Step 3: Verify import works**

```bash
uv run python -c "from margin_engine.ingestion import FinnhubProvider; print(FinnhubProvider.__name__)"
```

Expected: `FinnhubProvider`

**Step 4: Run all engine tests**

```bash
uv run pytest engine/tests/ -q --tb=short
```

Expected: all tests pass

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/__init__.py engine/src/margin_engine/ingestion/__init__.py
git commit -m "feat(engine): export FinnhubProvider from ingestion package"
```

---

### Task 5: Add finnhub_api_key to API config

**Files:**
- Modify: `api/src/margin_api/config.py`

**Step 1: Add the config field**

In `api/src/margin_api/config.py`, add `finnhub_api_key` to the "Data providers" section (after `polygon_api_key`):

```python
    # Data providers
    polygon_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
```

**Step 2: Verify it loads from env**

```bash
MARGIN_FINNHUB_API_KEY=test123 uv run python -c "from margin_api.config import Settings; print(Settings().finnhub_api_key)"
```

Expected: `test123`

**Step 3: Commit**

```bash
git add api/src/margin_api/config.py
git commit -m "feat(api): add finnhub_api_key to settings"
```

---

### Task 6: Registry integration tests

**Files:**
- Modify: `engine/tests/ingestion/test_registry.py`

**Step 1: Write the integration tests**

Add a new test class at the bottom of `engine/tests/ingestion/test_registry.py`:

```python
class TestFinnhubInFallbackChain:
    """Verify real FinnhubProvider integrates with registry correctly."""

    def test_finnhub_is_earnings_provider(self):
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.EARNINGS)
        names = [p.info.name for p in chain]
        assert names == ["finnhub"]

    def test_finnhub_is_news_provider(self):
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.NEWS)
        names = [p.info.name for p in chain]
        assert names == ["finnhub"]

    def test_finnhub_in_insider_chain(self):
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.INSIDER)
        names = [p.info.name for p in chain]
        assert names == ["finnhub"]

    def test_finnhub_excluded_without_api_key(self):
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={})
        registry.register(FinnhubProvider(api_key="test_key"))

        for cat in [DataCategory.EARNINGS, DataCategory.NEWS, DataCategory.INSIDER, DataCategory.INSTITUTIONAL]:
            chain = registry.get_fallback_chain(cat)
            assert chain == [], f"Expected empty chain for {cat}"

    def test_finnhub_not_in_price_chain(self):
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 0
```

**Step 2: Run the tests**

```bash
uv run pytest engine/tests/ingestion/test_registry.py::TestFinnhubInFallbackChain -v
```

Expected: all 5 tests PASS

**Step 3: Run full engine test suite**

```bash
uv run pytest engine/tests/ -q --tb=short
```

Expected: all tests pass

**Step 4: Commit**

```bash
git add engine/tests/ingestion/test_registry.py
git commit -m "test(engine): add Finnhub registry integration tests"
```

---

### Task 7: Lint, format, and final verification

**Step 1: Run ruff check and format**

```bash
uv run ruff check engine/ api/ && uv run ruff format engine/ api/
```

Fix any issues that arise.

**Step 2: Run full test suites**

```bash
uv run pytest engine/tests/ -q --tb=short
uv run pytest api/tests/ -q --tb=short
```

Expected: all tests pass

**Step 3: Commit any lint/format fixes**

```bash
git add -A
git commit -m "style: lint and format Finnhub provider"
```
