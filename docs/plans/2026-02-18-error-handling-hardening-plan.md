# Error Handling Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the dashboard 500 error on card click and ensure no API error ever shows raw JSON to users.

**Architecture:** Add a global FastAPI exception handler with structured `ErrorResponse` model and request ID middleware. Harden `_score_response_from_row()` with try/except fallback. On the frontend, parse structured errors in `apiFetch`, add retry UI in StockCard, and wrap AssetPanel in an error boundary.

**Tech Stack:** FastAPI, Pydantic, Python logging, React error boundaries, TypeScript

---

### Task 1: ErrorResponse Schema

**Files:**
- Create: `api/src/margin_api/schemas/errors.py`
- Test: `api/tests/schemas/test_errors.py`

**Step 1: Write the failing test**

Create `api/tests/schemas/test_errors.py`:

```python
"""Tests for ErrorResponse schema."""

from __future__ import annotations

from margin_api.schemas.errors import ErrorResponse


class TestErrorResponse:
    def test_model_fields(self):
        err = ErrorResponse(
            error_code="SCORE_NOT_FOUND",
            message="No score found for XYZ",
            request_id="abc-123",
            status_code=404,
        )
        assert err.error_code == "SCORE_NOT_FOUND"
        assert err.message == "No score found for XYZ"
        assert err.request_id == "abc-123"
        assert err.status_code == 404

    def test_model_dump(self):
        err = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id="def-456",
            status_code=500,
        )
        d = err.model_dump()
        assert d == {
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": "def-456",
            "status_code": 500,
        }
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'margin_api.schemas.errors'`

**Step 3: Write minimal implementation**

Create `api/src/margin_api/schemas/errors.py`:

```python
"""Structured error response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Structured error returned for all API error responses."""

    error_code: str
    message: str
    request_id: str
    status_code: int
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/schemas/test_errors.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/errors.py api/tests/schemas/test_errors.py
git commit -m "feat(api): add ErrorResponse schema for structured error handling"
```

---

### Task 2: Request ID Middleware + Global Exception Handlers

**Files:**
- Modify: `api/src/margin_api/app.py`
- Test: `api/tests/test_error_handling.py`

**Step 1: Write the failing tests**

Create `api/tests/test_error_handling.py`:

```python
"""Tests for global error handling and request ID middleware."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


class TestRequestIdMiddleware:
    def test_response_has_request_id_header(self, client):
        resp = client.get("/api/v1/health")
        assert "x-request-id" in resp.headers
        # UUID4 format: 8-4-4-4-12 hex chars
        rid = resp.headers["x-request-id"]
        assert len(rid) == 36
        assert rid.count("-") == 4


class TestStructuredErrorResponse:
    def test_404_returns_structured_error(self, client):
        resp = client.get("/api/v1/scores/NONEXISTENT_TICKER_XYZ")
        assert resp.status_code == 404
        body = resp.json()
        assert "error_code" in body
        assert "message" in body
        assert "request_id" in body
        assert "status_code" in body
        assert body["status_code"] == 404

    def test_404_has_request_id_header(self, client):
        resp = client.get("/api/v1/scores/NONEXISTENT_TICKER_XYZ")
        assert "x-request-id" in resp.headers
        body = resp.json()
        assert body["request_id"] == resp.headers["x-request-id"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_error_handling.py -v`
Expected: FAIL — no `x-request-id` header, 404 body is `{"detail": "..."}` not structured

**Step 3: Write the implementation**

Modify `api/src/margin_api/app.py`. Add these imports at the top:

```python
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from margin_api.schemas.errors import ErrorResponse
```

Add the middleware class before `create_app()`:

```python
logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
```

Inside `create_app()`, after CORS middleware and before route registration, add:

```python
    app.add_middleware(RequestIdMiddleware)
```

Still inside `create_app()`, after route registration, add the exception handlers:

```python
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=detail.upper().replace(" ", "_") if exc.status_code == 404 else "HTTP_ERROR",
                message=detail,
                request_id=request_id,
                status_code=exc.status_code,
            ).model_dump(),
            headers={"X-Request-Id": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("[%s] Unhandled exception: %s", request_id, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                request_id=request_id,
                status_code=500,
            ).model_dump(),
            headers={"X-Request-Id": request_id},
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_error_handling.py -v`
Expected: 3 PASSED

**Step 5: Run full API test suite to verify no regressions**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All existing tests pass. Some tests that check `resp.json()["detail"]` may need updating to `resp.json()["message"]`.

**Step 6: Fix any broken tests**

If existing tests assert on `resp.json()["detail"]`, update them to use `resp.json()["message"]` instead. The structured error response replaces `{"detail": "..."}` with `{"error_code": "...", "message": "...", ...}`.

**Step 7: Commit**

```bash
git add api/src/margin_api/app.py api/tests/test_error_handling.py
git commit -m "feat(api): add request ID middleware and global exception handlers"
```

---

### Task 3: Harden _score_response_from_row() with Try/Except Fallback

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:23-97`
- Test: `api/tests/test_scores.py` (add new test)

**Step 1: Write the failing test**

Add to `api/tests/test_scores.py`, a new test in the existing test class that exercises malformed score_detail:

```python
@pytest.mark.asyncio
async def test_get_score_with_malformed_detail_returns_fallback(seeded_session, async_engine):
    """If score_detail JSONB is malformed, endpoint returns degraded response instead of 500."""
    factory, _ = seeded_session

    # Insert asset + score with broken score_detail
    async with factory() as session:
        asset = Asset(ticker="BROKEN", name="Broken Corp")
        session.add(asset)
        await session.flush()
        score = Score(
            asset_id=asset.id,
            composite_percentile=75.0,
            composite_raw_score=0.60,
            conviction_level="high",
            signal="buy",
            quality_percentile=80.0,
            value_percentile=70.0,
            momentum_percentile=75.0,
            data_coverage=0.9,
            score_detail={"garbage": True},  # Missing all required fields
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: _override_get_db(factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/scores/BROKEN")

    assert resp.status_code == 200  # Not 500!
    body = resp.json()
    assert body["ticker"] == "BROKEN"
    assert body["conviction_level"] == "high"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_scores.py::test_get_score_with_malformed_detail_returns_fallback -v`
Expected: FAIL with 500 (or KeyError/ValidationError)

**Step 3: Write the implementation**

In `api/src/margin_api/routes/scores.py`, wrap the JSONB parsing path (lines 55-97) in a try/except that falls through to the summary-column fallback:

```python
def _score_response_from_row(
    row,
    live_price_data: dict | None = None,
) -> ScoreResponse:
    # ... (existing lines 36-53 stay the same)

    detail = score.score_detail
    if detail:
        try:
            # ... (existing lines 56-97: all the detail.setdefault() calls and return ScoreResponse(**detail))
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to parse score_detail for %s, falling back to summary columns",
                ticker,
                exc_info=True,
            )
            # Fall through to summary-column path below

    # Fallback: build from summary columns (existing lines 99-163)
    # ... (unchanged)
```

The key change: wrap lines 56-97 in `try: ... except Exception:` and let it fall through to the existing fallback path on failure.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_scores.py::test_get_score_with_malformed_detail_returns_fallback -v`
Expected: PASS

**Step 5: Run full scores test suite**

Run: `uv run pytest api/tests/test_scores.py -v`
Expected: All PASSED

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/test_scores.py
git commit -m "fix(api): handle malformed score_detail JSONB with fallback to summary columns"
```

---

### Task 4: NaN Filtering in Metrics Service

**Files:**
- Modify: `api/src/margin_api/services/metrics.py:21-26`
- Test: `api/tests/test_metrics_service.py` (add new tests)

**Step 1: Write the failing tests**

Add to `api/tests/test_metrics_service.py`:

```python
class TestNaNHandling:
    def test_sharpe_ratio_with_nan_values(self):
        closes = [100.0, float("nan"), 101.0, 102.0, float("nan"), 103.0, 104.0, 105.0, 106.0, 107.0]
        result = compute_sharpe_ratio(closes)
        # Should not crash — either returns a number or None
        assert result is None or isinstance(result, float)

    def test_max_drawdown_with_nan_values(self):
        closes = [100.0, float("nan"), 95.0, 80.0, 85.0, 90.0]
        result = compute_max_drawdown(closes)
        assert isinstance(result, float)

    def test_volatility_with_nan_values(self):
        closes = [100.0, float("nan"), 101.0, 99.5, 102.0, 98.0, 103.0, 97.5, 104.0, 96.0]
        result = compute_volatility(closes)
        assert result is None or isinstance(result, float)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_metrics_service.py::TestNaNHandling -v`
Expected: FAIL (NaN propagation causes math errors or invalid results)

**Step 3: Write the implementation**

In `api/src/margin_api/services/metrics.py`, add a NaN filter at the top of `_daily_returns()`:

```python
def _daily_returns(closes: list[float]) -> list[float]:
    returns = []
    for i in range(1, len(closes)):
        if math.isnan(closes[i]) or math.isnan(closes[i - 1]):
            continue
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    return returns
```

Also add NaN filtering in `compute_max_drawdown()`:

```python
def compute_max_drawdown(closes: list[float]) -> float:
    peak = -math.inf
    max_dd = 0.0
    for close in closes:
        if math.isnan(close):
            continue
        if close > peak:
            peak = close
        dd = (close - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 4)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_metrics_service.py -v`
Expected: All PASSED (including existing tests — NaN filter doesn't affect clean data)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/metrics.py api/tests/test_metrics_service.py
git commit -m "fix(api): filter NaN values in metrics computation to prevent crashes"
```

---

### Task 5: Defensive Metrics Endpoint

**Files:**
- Modify: `api/src/margin_api/routes/metrics.py:73-93`
- Test: `api/tests/test_metrics_route.py` (add new test)

**Step 1: Write the failing test**

Add to `api/tests/test_metrics_route.py` a test where financial data has no price_history:

```python
@pytest.mark.asyncio
async def test_metrics_with_missing_financial_data_returns_nulls(async_engine):
    """Metrics endpoint returns null metrics when financial data is missing, not 500."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        asset = Asset(ticker="EMPTY", name="Empty Corp")
        session.add(asset)
        await session.flush()
        score = Score(
            asset_id=asset.id,
            composite_percentile=50.0,
            composite_raw_score=0.40,
            conviction_level="none",
            signal="no_action",
            quality_percentile=50.0,
            value_percentile=50.0,
            momentum_percentile=50.0,
            data_coverage=0.5,
            score_detail=_score_detail(),
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        # No FinancialData inserted
        await session.commit()

    app = create_app()

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/scores/EMPTY/metrics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sharpe_ratio"] is None
    assert body["max_drawdown"] is None
    assert body["volatility"] is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_metrics_route.py::test_metrics_with_missing_financial_data_returns_nulls -v`
Expected: Should likely already pass (endpoint handles empty closes). If it does pass, skip to step 5.

**Step 3: (If needed) Wrap compute calls in try/except**

In `api/src/margin_api/routes/metrics.py`, wrap the compute section (lines 73-84):

```python
    # Compute metrics — defensive against bad data
    try:
        sharpe = compute_sharpe_ratio(closes)
    except Exception:
        sharpe = None
    try:
        max_dd = compute_max_drawdown(closes) if closes else None
    except Exception:
        max_dd = None
    try:
        vol = compute_volatility(closes)
    except Exception:
        vol = None
    try:
        avg_pm = compute_avg_profit_margin(income_periods)
    except Exception:
        avg_pm = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_metrics_route.py -v`
Expected: All PASSED

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/metrics.py api/tests/test_metrics_route.py
git commit -m "fix(api): defensive guards on metrics computation to return nulls instead of 500"
```

---

### Task 6: Frontend — Parse Structured Errors in apiFetch

**Files:**
- Modify: `web/src/lib/api/client.ts`

**Step 1: Update ApiError class and apiFetch**

Replace the contents of `web/src/lib/api/client.ts` with:

```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message?: string,
    public requestId?: string,
  ) {
    super(message || `API Error: ${status}`)
    this.name = 'ApiError'
  }
}

const BASE_URL = ''

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorCode = 'UNKNOWN'
    let message = `API Error: ${response.status} ${response.statusText}`
    let requestId: string | undefined

    try {
      const body = await response.json()
      errorCode = body.error_code || errorCode
      message = body.message || message
      requestId = body.request_id
    } catch {
      // Non-JSON error response — use status text
      message = response.statusText || message
    }

    throw new ApiError(response.status, errorCode, message, requestId)
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

**Step 2: Verify no type errors**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`

Check for type errors related to `ApiError`. If other files reference `ApiError.statusText`, update them to use `ApiError.errorCode` instead.

**Step 3: Commit**

```bash
git add web/src/lib/api/client.ts
git commit -m "feat(web): parse structured error responses in apiFetch client"
```

---

### Task 7: Frontend — Card Error State with Retry

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Update the error handling in handleClick**

In `stock-card.tsx`, modify the `handleClick` callback to use `Promise.allSettled` and add a retry mechanism:

Replace lines 67-93 with:

```tsx
  const handleClick = useCallback(async () => {
    if (expanded) {
      setExpanded(false)
      return
    }

    setExpanded(true)

    if (!scoreData) {
      await fetchDetails()
    }
  }, [expanded, scoreData, pick.ticker])

  const fetchDetails = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [scoreResult, metricsResult] = await Promise.allSettled([
        getScore(pick.ticker, ["price_history", "signal_history"]),
        getMetrics(pick.ticker),
      ])

      if (scoreResult.status === "fulfilled") {
        setScoreData(scoreResult.value)
      } else {
        const err = scoreResult.reason
        const requestId = err instanceof ApiError ? err.requestId : undefined
        if (requestId) console.error(`[${requestId}] Score fetch failed:`, err)
        setError("Unable to load candidate details")
        return
      }

      if (metricsResult.status === "fulfilled") {
        setMetricsData(metricsResult.value)
      } else {
        // Metrics failure is non-fatal — panel handles null metrics
        console.warn("Metrics fetch failed for", pick.ticker, metricsResult.reason)
        setMetricsData(null)
      }
    } finally {
      setLoading(false)
    }
  }, [pick.ticker])
```

Add the `ApiError` import at the top:

```tsx
import { ApiError } from "@/lib/api/client"
```

**Step 2: Replace the error display (lines 327-331)**

Replace:
```tsx
      {expanded && error && (
        <div className="border-t border-border-primary mt-4 pt-4">
          <p className="text-sm text-bearish">{error}</p>
        </div>
      )}
```

With:
```tsx
      {expanded && error && (
        <div className="border-t border-border-primary mt-4 pt-4">
          <div className="text-center py-4">
            <p className="text-sm font-medium text-text-primary mb-1">
              Unable to load candidate details
            </p>
            <p className="text-xs text-text-secondary mb-3">
              This data is temporarily unavailable.
            </p>
            <button
              type="button"
              className="text-xs text-accent hover:text-accent/80 underline underline-offset-2"
              onClick={(e) => {
                e.stopPropagation()
                setScoreData(null)
                fetchDetails()
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )}
```

**Step 3: Verify no type errors**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): add graceful error state with retry for candidate card detail fetch"
```

---

### Task 8: Frontend — AssetPanel Error Boundary

**Files:**
- Create: `web/src/components/dashboard/panel/panel-error-boundary.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Create the error boundary component**

Create `web/src/components/dashboard/panel/panel-error-boundary.tsx`:

```tsx
"use client"

import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
  onDismiss: () => void
}

interface State {
  hasError: boolean
}

export class PanelErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("AssetPanel render error:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-bg-elevated border border-border-primary rounded-lg p-8 max-w-md text-center">
            <p className="text-sm font-medium text-text-primary mb-1">
              Unable to display details
            </p>
            <p className="text-xs text-text-secondary mb-4">
              Something went wrong rendering the analysis panel.
            </p>
            <button
              type="button"
              className="text-xs text-accent hover:text-accent/80 underline underline-offset-2"
              onClick={() => {
                this.setState({ hasError: false })
                this.props.onDismiss()
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
```

**Step 2: Wrap AssetPanel in the error boundary**

In `stock-card.tsx`, add the import:

```tsx
import { PanelErrorBoundary } from "./panel/panel-error-boundary"
```

Replace the AssetPanel rendering (lines 333-341):

```tsx
    {scoreData && (
      <PanelErrorBoundary onDismiss={() => setExpanded(false)}>
        <AssetPanel
          isOpen={expanded && !loading}
          onClose={() => setExpanded(false)}
          ticker={pick.ticker}
          scoredResult={scoreData}
          metrics={metricsData}
        />
      </PanelErrorBoundary>
    )}
```

**Step 3: Verify no type errors**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add web/src/components/dashboard/panel/panel-error-boundary.tsx web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): add error boundary around AssetPanel to catch render crashes"
```

---

### Task 9: Verify Full Stack

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASSED

**Step 2: Run TypeScript type check**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit`
Expected: No errors

**Step 3: Manual smoke test (if server is running)**

1. Start API: `uvicorn margin_api.app:create_app --factory`
2. Start web: `cd web && npm run dev`
3. Open dashboard, click a card
4. Verify: no raw JSON errors, retry button works if error occurs
5. Check API response headers for `X-Request-Id`

**Step 4: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "fix: address review feedback from error handling hardening"
```
