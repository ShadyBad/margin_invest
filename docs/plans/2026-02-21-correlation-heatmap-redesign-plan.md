# Correlation Heatmap Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the dashboard correlation chart and make the landing page heatmap show real Exceptional/High conviction tickers with live-computed, Redis-cached correlation data.

**Architecture:** The existing `/correlations/showcase` endpoint gets enhanced to query the DB for top-conviction tickers and compute correlations on cache miss. The dashboard correlation component and its entire authenticated pipeline get removed. The shared `CorrelationGrid` UI component and engine correlation functions remain untouched.

**Tech Stack:** FastAPI, SQLAlchemy async, Redis (aioredis), Next.js 15, engine `compute_return_correlations()`

---

### Task 1: Remove Dashboard CorrelationHeatmap from Page

**Files:**
- Modify: `web/src/app/dashboard/page.tsx:4,76-85`
- Modify: `web/src/components/dashboard/index.ts:14`

**Step 1: Edit dashboard page to remove CorrelationHeatmap**

In `web/src/app/dashboard/page.tsx`, change the import on line 4 from:
```tsx
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction, CorrelationHeatmap } from "@/components/dashboard"
```
to:
```tsx
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction } from "@/components/dashboard"
```

Remove lines 83-85 (the correlation section):
```tsx
      <section className="mb-10">
        <CorrelationHeatmap />
      </section>
```

**Step 2: Remove export from barrel file**

In `web/src/components/dashboard/index.ts`, delete line 14:
```ts
export { CorrelationHeatmap } from "./correlation-heatmap"
```

**Step 3: Verify the dashboard page builds**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build 2>&1 | head -30`
Expected: Build succeeds (or at least no import errors for CorrelationHeatmap)

**Step 4: Commit**

```bash
git add web/src/app/dashboard/page.tsx web/src/components/dashboard/index.ts
git commit -m "refactor(web): remove CorrelationHeatmap from dashboard page"
```

---

### Task 2: Delete Dashboard Correlation Component and Auth Proxy

**Files:**
- Delete: `web/src/components/dashboard/correlation-heatmap.tsx`
- Delete: `web/src/app/api/v1/correlations/route.ts`

**Step 1: Delete the dashboard correlation component**

Delete file: `web/src/components/dashboard/correlation-heatmap.tsx`

**Step 2: Delete the authenticated proxy route**

Delete file: `web/src/app/api/v1/correlations/route.ts`

**Step 3: Commit**

```bash
git add -A web/src/components/dashboard/correlation-heatmap.tsx web/src/app/api/v1/correlations/route.ts
git commit -m "refactor(web): delete dashboard correlation component and auth proxy route"
```

---

### Task 3: Clean Up Web API Client

**Files:**
- Modify: `web/src/lib/api/correlations.ts`

**Step 1: Remove getCorrelations, keep getShowcaseCorrelations**

Replace the entire contents of `web/src/lib/api/correlations.ts` with:

```ts
import { apiFetch } from './client'
import type { CorrelationResponse } from './types'

export async function getShowcaseCorrelations(): Promise<CorrelationResponse> {
  return apiFetch<CorrelationResponse>('/api/v1/correlations/showcase')
}
```

**Step 2: Verify no remaining imports of getCorrelations**

Run: `grep -r "getCorrelations" web/src/`
Expected: No results (the only consumer was the deleted `correlation-heatmap.tsx`)

**Step 3: Commit**

```bash
git add web/src/lib/api/correlations.ts
git commit -m "refactor(web): remove unused getCorrelations API function"
```

---

### Task 4: Remove Authenticated FastAPI Endpoint

**Files:**
- Modify: `api/src/margin_api/routes/correlations.py`
- Modify: `api/tests/test_correlation_routes.py`

**Step 1: Update tests — remove authenticated endpoint tests, keep showcase tests**

Replace the entire contents of `api/tests/test_correlation_routes.py` with:

```python
"""Tests for correlation endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestShowcaseEndpoint:
    def test_returns_200_without_auth(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200

    def test_response_has_expected_shape(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        data = resp.json()
        assert "tickers" in data
        assert "matrix" in data
        assert "sample_sizes" in data
        assert "method" in data
        n = len(data["tickers"])
        assert len(data["matrix"]) == n
        assert all(len(row) == n for row in data["matrix"])

    def test_fallback_values_present(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        data = resp.json()
        assert data["method"] == "returns"
        assert len(data["tickers"]) >= 2

    def test_showcase_route_registered(self, client: TestClient):
        routes = [r.path for r in client.app.routes]
        assert "/api/v1/correlations/showcase" in routes
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_correlation_routes.py -v`
Expected: 4 tests PASS

**Step 3: Remove authenticated endpoint from route file**

Replace the entire contents of `api/src/margin_api/routes/correlations.py` with:

```python
"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

# Hardcoded fallback for showcase when cache is empty or < 5 tickers scored
_SHOWCASE_FALLBACK = CorrelationResponse(
    tickers=["AAPL", "MSFT", "JNJ", "COST", "V"],
    method="returns",
    matrix=[
        [1.0, 0.82, 0.15, 0.28, 0.45],
        [0.82, 1.0, 0.12, 0.31, 0.51],
        [0.15, 0.12, 1.0, 0.62, 0.22],
        [0.28, 0.31, 0.62, 1.0, 0.35],
        [0.45, 0.51, 0.22, 0.35, 1.0],
    ],
    sample_sizes=[[252] * 5 for _ in range(5)],
    excluded=[],
    window_days=252,
    computed_at=datetime(2026, 1, 1, tzinfo=UTC),
)


@router.get("/showcase", response_model=CorrelationResponse)
async def get_showcase_correlations() -> CorrelationResponse:
    """Public endpoint: pre-computed correlation matrix for landing page."""
    try:
        import redis.asyncio as aioredis

        from margin_api.config import get_settings

        client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        try:
            cached = await client.get("correlation:showcase")
            if cached:
                data = json.loads(cached)
                return CorrelationResponse(**data)
        finally:
            await client.aclose()
    except Exception:
        logger.debug("Redis unavailable for showcase correlations, using fallback")
    return _SHOWCASE_FALLBACK
```

**Step 4: Run tests again**

Run: `uv run pytest api/tests/test_correlation_routes.py -v`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/correlations.py api/tests/test_correlation_routes.py
git commit -m "refactor(api): remove authenticated correlation endpoint, keep showcase"
```

---

### Task 5: Write Test for Live Showcase Computation

**Files:**
- Modify: `api/tests/test_correlation_routes.py`

**Step 1: Write tests for the new live computation behavior**

Append to `api/tests/test_correlation_routes.py`:

```python
from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime


class TestShowcaseLiveComputation:
    """Tests for live correlation computation on cache miss."""

    def _make_price_bars(self, n: int = 30) -> list[dict]:
        """Create fake price bar dicts."""
        import random
        random.seed(42)
        bars = []
        price = 100.0
        for i in range(n):
            price *= 1 + random.uniform(-0.03, 0.03)
            bars.append({
                "Date": f"2026-01-{i + 1:02d}",
                "Open": round(price * 0.99, 2),
                "High": round(price * 1.01, 2),
                "Low": round(price * 0.98, 2),
                "Close": round(price, 2),
                "Volume": 1000000,
            })
        return bars

    @patch("margin_api.routes.correlations._get_redis_cached", new_callable=AsyncMock, return_value=None)
    @patch("margin_api.routes.correlations._cache_to_redis", new_callable=AsyncMock)
    @patch("margin_api.routes.correlations._compute_live_showcase", new_callable=AsyncMock)
    def test_calls_live_computation_on_cache_miss(
        self, mock_compute, mock_cache, mock_redis, client: TestClient
    ):
        """When Redis returns None, endpoint should attempt live computation."""
        mock_compute.return_value = None  # Simulate not enough tickers
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200
        mock_compute.assert_called_once()
        # Falls back to static since live returned None
        data = resp.json()
        assert data["tickers"] == ["AAPL", "MSFT", "JNJ", "COST", "V"]

    @patch("margin_api.routes.correlations._get_redis_cached", new_callable=AsyncMock, return_value=None)
    @patch("margin_api.routes.correlations._cache_to_redis", new_callable=AsyncMock)
    @patch("margin_api.routes.correlations._compute_live_showcase", new_callable=AsyncMock)
    def test_returns_live_data_when_available(
        self, mock_compute, mock_cache, mock_redis, client: TestClient
    ):
        """When live computation succeeds, return that data and cache it."""
        from margin_api.schemas.correlations import CorrelationResponse

        live_result = CorrelationResponse(
            tickers=["NVDA", "AVGO", "PLTR", "APP", "CRWD"],
            method="returns",
            matrix=[
                [1.0, 0.7, 0.3, 0.2, 0.5],
                [0.7, 1.0, 0.4, 0.3, 0.6],
                [0.3, 0.4, 1.0, 0.5, 0.4],
                [0.2, 0.3, 0.5, 1.0, 0.3],
                [0.5, 0.6, 0.4, 0.3, 1.0],
            ],
            sample_sizes=[[252] * 5 for _ in range(5)],
            excluded=[],
            window_days=252,
            computed_at=datetime(2026, 2, 21, tzinfo=UTC),
        )
        mock_compute.return_value = live_result
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tickers"] == ["NVDA", "AVGO", "PLTR", "APP", "CRWD"]
        mock_cache.assert_called_once()
```

**Step 2: Run the new tests to verify they fail**

Run: `uv run pytest api/tests/test_correlation_routes.py::TestShowcaseLiveComputation -v`
Expected: FAIL — `_get_redis_cached`, `_cache_to_redis`, and `_compute_live_showcase` don't exist yet

**Step 3: Commit failing tests**

```bash
git add api/tests/test_correlation_routes.py
git commit -m "test(api): add failing tests for live showcase correlation computation"
```

---

### Task 6: Implement Live Showcase Computation

**Files:**
- Modify: `api/src/margin_api/routes/correlations.py`

**Step 1: Implement the refactored showcase endpoint with helper functions**

Replace the entire contents of `api/src/margin_api/routes/correlations.py` with:

```python
"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

_SHOWCASE_TTL = 3600  # 1 hour

# Hardcoded fallback for showcase when cache is empty or < 5 tickers scored
_SHOWCASE_FALLBACK = CorrelationResponse(
    tickers=["AAPL", "MSFT", "JNJ", "COST", "V"],
    method="returns",
    matrix=[
        [1.0, 0.82, 0.15, 0.28, 0.45],
        [0.82, 1.0, 0.12, 0.31, 0.51],
        [0.15, 0.12, 1.0, 0.62, 0.22],
        [0.28, 0.31, 0.62, 1.0, 0.35],
        [0.45, 0.51, 0.22, 0.35, 1.0],
    ],
    sample_sizes=[[252] * 5 for _ in range(5)],
    excluded=[],
    window_days=252,
    computed_at=datetime(2026, 1, 1, tzinfo=UTC),
)

_HIGH_CONVICTION_THRESHOLD = 72.0
_SHOWCASE_TICKER_COUNT = 5


async def _get_redis_cached() -> CorrelationResponse | None:
    """Try to read showcase correlation from Redis cache."""
    try:
        import redis.asyncio as aioredis

        from margin_api.config import get_settings

        client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        try:
            cached = await client.get("correlation:showcase")
            if cached:
                data = json.loads(cached)
                return CorrelationResponse(**data)
        finally:
            await client.aclose()
    except Exception:
        logger.debug("Redis unavailable for showcase correlations")
    return None


async def _cache_to_redis(response: CorrelationResponse) -> None:
    """Write showcase correlation result to Redis with TTL."""
    try:
        import redis.asyncio as aioredis

        from margin_api.config import get_settings

        client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        try:
            await client.set(
                "correlation:showcase",
                response.model_dump_json(),
                ex=_SHOWCASE_TTL,
            )
        finally:
            await client.aclose()
    except Exception:
        logger.debug("Failed to cache showcase correlations to Redis")


def _parse_bar(raw: dict):
    """Parse a price bar from yfinance-formatted JSONB."""
    from margin_engine.models.financial import PriceBar

    try:
        return PriceBar(
            date=raw.get("Date", raw.get("date", "")),
            open=raw.get("Open", raw.get("open", 0)),
            high=raw.get("High", raw.get("high", 0)),
            low=raw.get("Low", raw.get("low", 0)),
            close=raw.get("Close", raw.get("close", 0)),
            volume=int(raw.get("Volume", raw.get("volume", 0))),
            adj_close=raw.get("Adj Close", raw.get("adj_close")),
        )
    except Exception:
        return None


async def _compute_live_showcase(db: AsyncSession) -> CorrelationResponse | None:
    """Query DB for top conviction tickers and compute correlations.

    Returns None if fewer than 5 qualifying tickers have price data.
    """
    from margin_engine.correlation import compute_return_correlations
    from margin_engine.models.financial import PriceBar

    # Get top tickers by composite_raw_score >= 72.0 (High conviction)
    stmt = (
        select(Score, Asset.ticker)
        .join(Asset, Score.asset_id == Asset.id)
        .where(Score.composite_raw_score >= _HIGH_CONVICTION_THRESHOLD)
        .order_by(Score.composite_raw_score.desc())
        .limit(_SHOWCASE_TICKER_COUNT)
    )
    rows = (await db.execute(stmt)).all()

    if len(rows) < _SHOWCASE_TICKER_COUNT:
        return None

    ticker_list = [r.ticker for r in rows]

    # Load price history for each ticker
    price_data: dict[str, list[PriceBar]] = {}
    for ticker in ticker_list:
        stmt = (
            select(FinancialData)
            .join(Asset, FinancialData.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
            .order_by(FinancialData.period_end.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row and row.price_history:
            price_hist = row.price_history
            bars_raw = price_hist.get("bars", []) if isinstance(price_hist, dict) else []
            if bars_raw:
                bars = [_parse_bar(bar) for bar in bars_raw]
                bars = [b for b in bars if b is not None]
                if bars:
                    price_data[ticker] = bars

    if len(price_data) < _SHOWCASE_TICKER_COUNT:
        return None

    result = compute_return_correlations(price_data, window_days=252)
    return CorrelationResponse(**result.model_dump())


@router.get("/showcase", response_model=CorrelationResponse)
async def get_showcase_correlations(
    db: AsyncSession = Depends(get_db),
) -> CorrelationResponse:
    """Public endpoint: correlation matrix for landing page.

    Checks Redis cache first. On miss, computes live from top-conviction
    tickers and caches for 1 hour. Falls back to static data if fewer
    than 5 qualifying tickers are available.
    """
    # 1. Try Redis cache
    cached = await _get_redis_cached()
    if cached:
        return cached

    # 2. Compute live from DB
    try:
        live = await _compute_live_showcase(db)
        if live:
            await _cache_to_redis(live)
            return live
    except Exception:
        logger.exception("Failed to compute live showcase correlations")

    # 3. Fall back to static data
    return _SHOWCASE_FALLBACK
```

**Step 2: Run all correlation tests**

Run: `uv run pytest api/tests/test_correlation_routes.py -v`
Expected: All 6 tests PASS

**Step 3: Run the full API test suite to check for regressions**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -20`
Expected: No new failures

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/correlations.py
git commit -m "feat(api): compute live showcase correlations from top-conviction tickers"
```

---

### Task 7: Verify End-to-End

**Step 1: Run entire API test suite**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS (including the 6 correlation tests)

**Step 2: Run web build to check for broken imports**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build 2>&1 | tail -20`
Expected: Build succeeds, no import errors

**Step 3: Verify no stale references to removed code**

Run: `grep -r "CorrelationHeatmap" web/src/` — should return nothing
Run: `grep -r "getCorrelations[^S]" web/src/` — should return nothing (getShowcaseCorrelations is OK)
Run: `grep -r "correlations/route" web/src/` — should return nothing

**Step 4: Final commit if any cleanup needed, otherwise done**

```bash
# Only if there were fixes:
git add -A && git commit -m "chore: final cleanup after correlation heatmap redesign"
```
