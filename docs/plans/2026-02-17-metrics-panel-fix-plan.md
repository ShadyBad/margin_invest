# Metrics Panel Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the metrics panel so Sharpe Ratio, Max Drawdown, Volatility, Avg Profit Margin, Allocation, Margin of Safety, and Target display real computed data.

**Architecture:** Fix the Next.js proxy to forward query params (unblocking 3 metrics immediately), surface price target invalid reasons in the UI, then add a backend metrics endpoint that computes all metrics server-side. Frontend transitions from client-side computation to API-fetched metrics.

**Tech Stack:** Python/FastAPI (API), SQLAlchemy/aiosqlite (tests), Next.js 15 (frontend), Vitest (frontend tests), pytest-asyncio (API tests)

---

### Task 1: Fix Next.js Proxy Query Parameter Forwarding

**Files:**
- Modify: `web/src/app/api/v1/scores/[ticker]/route.ts:17-18`

**Step 1: Fix the proxy to forward query string**

In `web/src/app/api/v1/scores/[ticker]/route.ts`, the backend URL is constructed without query parameters. Change line 18 from:

```ts
const response = await fetch(`${API_URL}/api/v1/scores/${ticker}`, {
```

to extract and forward the query string from the incoming request:

```ts
const { search } = new URL(_request.url)
const response = await fetch(`${API_URL}/api/v1/scores/${ticker}${search}`, {
```

Add `const { search } = new URL(_request.url)` right after `const { ticker } = await params` (line 15), and update the fetch URL on the next `fetch()` call.

**Step 2: Verify manually**

Run the dev server and confirm the API receives `?include=price_history,signal_history` when a stock card is expanded. This immediately unblocks Sharpe, Drawdown, Volatility in the KPI grid via the existing client-side computation.

**Step 3: Commit**

```bash
git add web/src/app/api/v1/scores/\[ticker\]/route.ts
git commit -m "fix(web): forward query params in score proxy route"
```

---

### Task 2: Add price_target_invalid_reason to PickSummary

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py:10-37`
- Modify: `api/src/margin_api/routes/dashboard.py:25-69`
- Test: `api/tests/test_dashboard.py`

**Step 1: Write the failing test**

Add to `api/tests/test_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_pick_summary_includes_price_target_invalid_reason(client):
    """PickSummary should include price_target_invalid_reason when targets fail validation."""
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    for pick in data["picks"]:
        assert "price_target_invalid_reason" in pick
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_dashboard.py::test_pick_summary_includes_price_target_invalid_reason -v`
Expected: FAIL — `price_target_invalid_reason` not in pick dict

**Step 3: Add field to PickSummary schema**

In `api/src/margin_api/schemas/dashboard.py`, add after line 36 (`timing_signal`):

```python
    price_target_invalid_reason: str | None = None
```

**Step 4: Populate field in dashboard route**

In `api/src/margin_api/routes/dashboard.py`, inside `_pick_summary_from_row()`, add after the `timing_signal` line (line 57):

```python
        price_target_invalid_reason=invalid_reason,
```

Note: `invalid_reason` is already extracted on line 28.

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_dashboard.py::test_pick_summary_includes_price_target_invalid_reason -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/src/margin_api/routes/dashboard.py api/tests/test_dashboard.py
git commit -m "feat(api): add price_target_invalid_reason to PickSummary"
```

---

### Task 3: Surface Target Invalid Reason in Stock Card UI

**Files:**
- Modify: `web/src/lib/api/types.ts:90-117`
- Modify: `web/src/components/dashboard/stock-card.tsx:198-204`

**Step 1: Add field to frontend PickSummary type**

In `web/src/lib/api/types.ts`, add after line 116 (`sector`):

```ts
  price_target_invalid_reason?: string | null
```

**Step 2: Update Target display in stock card**

In `web/src/components/dashboard/stock-card.tsx`, replace the Target display (lines 198-205):

```tsx
          <span className="text-text-secondary">
            Target:{" "}
            <span className="text-text-primary font-medium">
              {pick.sell_price != null
                ? `$${pick.sell_price.toFixed(2)}`
                : "N/A"}
            </span>
          </span>
```

with:

```tsx
          <span className="text-text-secondary">
            Target:{" "}
            <span className={`font-medium ${pick.sell_price != null ? "text-text-primary" : "text-text-tertiary"}`}>
              {pick.sell_price != null
                ? `$${pick.sell_price.toFixed(2)}`
                : pick.price_target_invalid_reason === "insufficient_data"
                  ? "Needs data"
                  : pick.price_target_invalid_reason === "single_method"
                    ? "Low confidence"
                    : pick.price_target_invalid_reason === "low_agreement"
                      ? "Methods diverge"
                      : pick.price_target_invalid_reason
                        ? "Unavailable"
                        : "N/A"}
            </span>
          </span>
```

**Step 3: Commit**

```bash
git add web/src/lib/api/types.ts web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): show price target invalid reason instead of N/A"
```

---

### Task 4: Create Backend Metrics Calculation Module

**Files:**
- Create: `api/src/margin_api/services/metrics.py`
- Test: `api/tests/test_metrics_service.py`

**Step 1: Write the failing tests for Sharpe ratio**

Create `api/tests/test_metrics_service.py`:

```python
"""Tests for institutional metrics calculation service."""

from __future__ import annotations

import math
import pytest
from margin_api.services.metrics import (
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_volatility,
    compute_avg_profit_margin,
    classify_risk,
)


class TestSharpeRatio:
    """Golden-value tests for Sharpe ratio."""

    def test_known_series(self):
        """Sharpe for a series with known daily returns."""
        # 10 daily closes with slight upward drift
        closes = [100.0, 101.0, 100.5, 102.0, 101.5, 103.0, 102.5, 104.0, 103.5, 105.0]
        result = compute_sharpe_ratio(closes)
        assert result is not None
        # With positive drift and moderate vol, Sharpe should be positive
        assert result > 0

    def test_flat_series_returns_none(self):
        """Constant price → zero std → None (can't divide by zero)."""
        closes = [100.0] * 20
        result = compute_sharpe_ratio(closes)
        assert result is None

    def test_too_few_bars(self):
        """Fewer than 5 bars → None."""
        closes = [100.0, 101.0, 102.0]
        result = compute_sharpe_ratio(closes)
        assert result is None


class TestMaxDrawdown:
    """Golden-value tests for max drawdown."""

    def test_known_drawdown(self):
        """Peak at 100, trough at 80 → -20% drawdown."""
        closes = [90.0, 100.0, 95.0, 80.0, 85.0, 90.0]
        result = compute_max_drawdown(closes)
        assert result == pytest.approx(-0.20, abs=0.001)

    def test_monotonic_increase(self):
        """Always going up → 0 drawdown."""
        closes = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = compute_max_drawdown(closes)
        assert result == 0.0


class TestVolatility:
    """Golden-value tests for annualized volatility."""

    def test_known_series(self):
        """Volatility for a known series should be positive."""
        closes = [100.0, 101.0, 99.5, 102.0, 98.0, 103.0, 97.5, 104.0, 96.0, 105.0]
        result = compute_volatility(closes)
        assert result is not None
        assert result > 0

    def test_too_few_bars(self):
        """Fewer than 5 bars → None."""
        closes = [100.0, 101.0]
        result = compute_volatility(closes)
        assert result is None


class TestAvgProfitMargin:
    """Tests for average profit margin from income statement data."""

    def test_single_period(self):
        """Single period with net_income=20, total_revenue=100 → 20%."""
        income_data = [{"net_income": 20.0, "total_revenue": 100.0}]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_multi_period(self):
        """Average across multiple periods."""
        income_data = [
            {"net_income": 20.0, "total_revenue": 100.0},   # 20%
            {"net_income": 30.0, "total_revenue": 100.0},   # 30%
            {"net_income": 10.0, "total_revenue": 100.0},   # 10%
            {"net_income": 40.0, "total_revenue": 200.0},   # 20%
        ]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_empty_data(self):
        """No income data → None."""
        result = compute_avg_profit_margin([])
        assert result is None

    def test_zero_revenue_skipped(self):
        """Periods with zero revenue are skipped."""
        income_data = [
            {"net_income": 20.0, "total_revenue": 100.0},  # 20%
            {"net_income": 0.0, "total_revenue": 0.0},      # skip
        ]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_missing_fields(self):
        """Income data missing required fields → None."""
        income_data = [{"operating_income": 50.0}]
        result = compute_avg_profit_margin(income_data)
        assert result is None


class TestRiskClassification:
    """Tests for volatility-based risk classification."""

    def test_conservative(self):
        assert classify_risk(10.0) == "Conservative"

    def test_moderate(self):
        assert classify_risk(20.0) == "Moderate"

    def test_moderate_high(self):
        assert classify_risk(30.0) == "Moderate-High"

    def test_aggressive(self):
        assert classify_risk(50.0) == "Aggressive"

    def test_none_volatility(self):
        assert classify_risk(None) == "Unknown"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_metrics_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.metrics'`

**Step 3: Implement the metrics service**

Create `api/src/margin_api/services/metrics.py`:

```python
"""Institutional metrics calculation service.

Computes Sharpe ratio, max drawdown, volatility, avg profit margin,
and risk classification from stored financial data.

Constants:
    RISK_FREE_RATE: 5% annualized (conservative; US 10Y ~4.3% as of 2026)
    TRADING_DAYS_PER_YEAR: 252
    MIN_BARS_FOR_STATS: 5 (minimum price bars required)
"""

from __future__ import annotations

import math

RISK_FREE_RATE = 0.05
TRADING_DAYS_PER_YEAR = 252
MIN_BARS_FOR_STATS = 5


def _daily_returns(closes: list[float]) -> list[float]:
    """Compute daily returns from close prices."""
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    return returns


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_sharpe_ratio(closes: list[float]) -> float | None:
    """Annualized Sharpe ratio from daily close prices.

    Formula: ((mean_daily_return - Rf/252) / std_daily_return) * sqrt(252)
    Returns None if < 5 bars or zero standard deviation.
    """
    returns = _daily_returns(closes)
    if len(returns) < MIN_BARS_FOR_STATS:
        return None

    daily_std = _stddev(returns)
    if daily_std == 0:
        return None

    avg_daily_return = _mean(returns)
    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    sharpe = ((avg_daily_return - daily_rf) / daily_std) * math.sqrt(TRADING_DAYS_PER_YEAR)
    return round(sharpe, 2)


def compute_max_drawdown(closes: list[float]) -> float:
    """Maximum peak-to-trough decline as a decimal (e.g., -0.25 for 25% drawdown).

    Returns 0.0 if prices only go up.
    """
    peak = -math.inf
    max_dd = 0.0
    for close in closes:
        if close > peak:
            peak = close
        dd = (close - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 4)


def compute_volatility(closes: list[float]) -> float | None:
    """Annualized volatility as a percentage (e.g., 25.3 for 25.3%).

    Formula: std(daily_returns) * sqrt(252) * 100
    Returns None if < 5 bars.
    """
    returns = _daily_returns(closes)
    if len(returns) < MIN_BARS_FOR_STATS:
        return None

    annualized = _stddev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR) * 100
    return round(annualized, 1)


def compute_avg_profit_margin(income_periods: list[dict]) -> float | None:
    """Average net profit margin across income statement periods.

    Computes net_income / total_revenue for each period, returns the mean as a percentage.
    Skips periods with zero or missing revenue.
    Returns None if no valid periods.
    """
    margins = []
    for period in income_periods:
        net_income = period.get("net_income")
        revenue = period.get("total_revenue")
        if net_income is None or revenue is None or revenue == 0:
            continue
        margins.append((net_income / revenue) * 100)

    if not margins:
        return None
    return round(_mean(margins), 1)


def classify_risk(volatility: float | None) -> str:
    """Classify risk based on annualized volatility percentage."""
    if volatility is None:
        return "Unknown"
    if volatility > 40:
        return "Aggressive"
    if volatility > 25:
        return "Moderate-High"
    if volatility > 15:
        return "Moderate"
    return "Conservative"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_metrics_service.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/metrics.py api/tests/test_metrics_service.py
git commit -m "feat(api): add institutional metrics calculation service"
```

---

### Task 5: Create Metrics API Schema

**Files:**
- Create: `api/src/margin_api/schemas/metrics.py`

**Step 1: Create the response schema**

Create `api/src/margin_api/schemas/metrics.py`:

```python
"""Institutional metrics API response schema."""

from __future__ import annotations

from pydantic import BaseModel


class InstitutionalMetricsResponse(BaseModel):
    """Pre-computed institutional-grade metrics for a single ticker."""

    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    volatility: float | None = None
    avg_profit_margin: float | None = None
    risk_classification: str = "Unknown"
    allocation_weight: float | None = None
    margin_of_safety: float | None = None
```

**Step 2: Commit**

```bash
git add api/src/margin_api/schemas/metrics.py
git commit -m "feat(api): add InstitutionalMetricsResponse schema"
```

---

### Task 6: Create Metrics API Route

**Files:**
- Create: `api/src/margin_api/routes/metrics.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/test_metrics_route.py`

**Step 1: Write failing tests for the endpoint**

Create `api/tests/test_metrics_route.py`:

```python
"""Tests for GET /api/v1/scores/{ticker}/metrics endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail() -> dict:
    return {
        "ticker": "AAPL",
        "composite_percentile": 95.0,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 90.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 85.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 88.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }


def _make_price_bars(closes: list[float]) -> dict:
    """Create a price_history dict from a list of close prices."""
    bars = []
    for i, close in enumerate(closes):
        bars.append({
            "date": f"2025-01-{i + 1:02d}",
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000000,
        })
    return {"bars": bars}


def _make_income_data() -> dict:
    """Create income_statement data with known profit margins."""
    return {
        "net_income": 25000000000,
        "total_revenue": 100000000000,  # 25% margin
    }


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset)
        await session.flush()

        # Score with price targets and max_position_pct
        score = Score(
            asset_id=asset.id,
            composite_percentile=95.0,
            composite_raw_score=87.5,
            conviction_level="high",
            signal="buy",
            quality_percentile=90.0,
            value_percentile=85.0,
            momentum_percentile=88.0,
            data_coverage=1.0,
            score_detail=_score_detail(),
            intrinsic_value=200.0,
            buy_price=200.0,
            sell_price=250.0,
            actual_price=180.0,
            max_position_pct=8.0,
        )
        session.add(score)
        await session.flush()

        # FinancialData with price_history and income_statement
        closes = [100.0, 101.0, 100.5, 102.0, 101.5, 103.0, 102.5, 104.0, 103.5, 105.0]
        fin_data = FinancialData(
            asset_id=asset.id,
            period_end="2025-01-10",
            filing_date="2025-01-15",
            price_history=_make_price_bars(closes),
            income_statement=_make_income_data(),
        )
        session.add(fin_data)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_returns_all_fields(client):
    """Happy path — all metrics computed from seeded data."""
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sharpe_ratio"] is not None
    assert data["max_drawdown"] is not None
    assert data["volatility"] is not None
    assert data["avg_profit_margin"] is not None
    assert data["risk_classification"] in ("Conservative", "Moderate", "Moderate-High", "Aggressive")
    assert data["allocation_weight"] == 8.0
    assert data["margin_of_safety"] is not None


@pytest.mark.asyncio
async def test_metrics_sharpe_positive(client):
    """With upward-drifting prices, Sharpe should be positive."""
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["sharpe_ratio"] > 0


@pytest.mark.asyncio
async def test_metrics_margin_of_safety(client):
    """MoS = (200 - 180) / 200 = 0.1 (10%)."""
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["margin_of_safety"] == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_metrics_avg_profit_margin(client):
    """25B / 100B = 25% margin."""
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["avg_profit_margin"] == pytest.approx(25.0, abs=0.5)


@pytest.mark.asyncio
async def test_metrics_unknown_ticker(client):
    """Unknown ticker → 404."""
    resp = await client.get("/api/v1/scores/ZZZZZ/metrics")
    assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_metrics_route.py -v`
Expected: FAIL — route not found (404 on all tests)

**Step 3: Implement the metrics route**

Create `api/src/margin_api/routes/metrics.py`:

```python
"""Institutional metrics endpoint — computes Sharpe, drawdown, volatility, etc."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.metrics import InstitutionalMetricsResponse
from margin_api.services.metrics import (
    classify_risk,
    compute_avg_profit_margin,
    compute_max_drawdown,
    compute_sharpe_ratio,
    compute_volatility,
)

router = APIRouter(prefix="/api/v1/scores", tags=["metrics"])


@router.get("/{ticker}/metrics", response_model=InstitutionalMetricsResponse)
async def get_metrics(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> InstitutionalMetricsResponse:
    """Compute institutional metrics for a ticker from stored financial data."""
    ticker = ticker.upper()

    # Get the latest score for this ticker
    score_query = (
        select(Score, Asset.id.label("asset_id"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    score_result = await db.execute(score_query)
    score_row = score_result.first()
    if score_row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    score = score_row.Score
    asset_id = score.asset_id

    # Get the latest financial data
    fd_query = (
        select(FinancialData)
        .where(FinancialData.asset_id == asset_id)
        .order_by(FinancialData.period_end.desc())
        .limit(1)
    )
    fd_result = await db.execute(fd_query)
    fin_data = fd_result.scalar()

    # Extract close prices from price_history
    closes: list[float] = []
    if fin_data and fin_data.price_history:
        ph = fin_data.price_history
        bars = ph.get("bars", []) if isinstance(ph, dict) else ph
        closes = [bar["close"] for bar in bars if "close" in bar]

    # Extract income statement periods for profit margin
    income_periods: list[dict] = []
    if fin_data and fin_data.income_statement:
        inc = fin_data.income_statement
        # income_statement may be a single period dict or a list of periods
        if isinstance(inc, list):
            income_periods = inc
        elif isinstance(inc, dict):
            income_periods = [inc]

    # Compute metrics
    sharpe = compute_sharpe_ratio(closes)
    max_dd = compute_max_drawdown(closes) if closes else None
    vol = compute_volatility(closes)
    avg_pm = compute_avg_profit_margin(income_periods)

    # Margin of safety
    margin_of_safety: float | None = None
    intrinsic = getattr(score, "intrinsic_value", None)
    actual = getattr(score, "actual_price", None)
    if intrinsic and actual and intrinsic > 0:
        margin_of_safety = round((intrinsic - actual) / intrinsic, 4)

    return InstitutionalMetricsResponse(
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        volatility=vol,
        avg_profit_margin=avg_pm,
        risk_classification=classify_risk(vol),
        allocation_weight=getattr(score, "max_position_pct", None),
        margin_of_safety=margin_of_safety,
    )
```

**Step 4: Register the router in the app**

In `api/src/margin_api/app.py`, find where routers are included and add:

```python
from margin_api.routes.metrics import router as metrics_router
app.include_router(metrics_router)
```

Add this import and `include_router` call alongside the existing score/dashboard routers.

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_metrics_route.py -v`
Expected: All PASS

**Step 6: Run full API test suite to check for regressions**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: All existing tests PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/routes/metrics.py api/src/margin_api/schemas/metrics.py api/src/margin_api/app.py api/tests/test_metrics_route.py
git commit -m "feat(api): add GET /scores/{ticker}/metrics endpoint"
```

---

### Task 7: Create Next.js Proxy Route for Metrics

**Files:**
- Create: `web/src/app/api/v1/scores/[ticker]/metrics/route.ts`

**Step 1: Create the proxy route**

Create `web/src/app/api/v1/scores/[ticker]/metrics/route.ts`:

```ts
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { ticker } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/scores/${ticker}/metrics`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json(
        { error: text },
        { status: response.status },
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error(`Failed to proxy metrics for ${ticker}:`, error)
    return NextResponse.json(
      { error: "Failed to fetch metrics" },
      { status: 502 },
    )
  }
}
```

**Step 2: Commit**

```bash
git add web/src/app/api/v1/scores/\[ticker\]/metrics/route.ts
git commit -m "feat(web): add Next.js proxy route for metrics endpoint"
```

---

### Task 8: Add Frontend Metrics Types and API Client

**Files:**
- Modify: `web/src/lib/api/types.ts`
- Modify: `web/src/lib/api/scores.ts`
- Modify: `web/src/lib/api/index.ts`

**Step 1: Add InstitutionalMetricsResponse type**

In `web/src/lib/api/types.ts`, add after the `ScoreListResponse` interface (after line 88):

```ts
export interface InstitutionalMetricsResponse {
  sharpe_ratio: number | null
  max_drawdown: number | null
  volatility: number | null
  avg_profit_margin: number | null
  risk_classification: string
  allocation_weight: number | null
  margin_of_safety: number | null
}
```

**Step 2: Add getMetrics function**

In `web/src/lib/api/scores.ts`, add after the `getScore` function:

```ts
export async function getMetrics(
  ticker: string,
): Promise<InstitutionalMetricsResponse> {
  return apiFetch<InstitutionalMetricsResponse>(`/api/v1/scores/${ticker.toUpperCase()}/metrics`)
}
```

Add the import for `InstitutionalMetricsResponse` to the import line at the top:

```ts
import type { ScoreResponse, ScoreListResponse, InstitutionalMetricsResponse } from './types'
```

**Step 3: Export from index**

In `web/src/lib/api/index.ts`, update the scores export to include `getMetrics`:

```ts
export { getScore, getMetrics, listScores, deleteScore } from './scores'
```

**Step 4: Commit**

```bash
git add web/src/lib/api/types.ts web/src/lib/api/scores.ts web/src/lib/api/index.ts
git commit -m "feat(web): add getMetrics API client and types"
```

---

### Task 9: Wire Metrics into StockCard and AssetPanel

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`

**Step 1: Update StockCard to fetch metrics in parallel**

In `web/src/components/dashboard/stock-card.tsx`:

Add import for `getMetrics`:
```ts
import { getScore, getMetrics } from "@/lib/api/scores"
import type { PickSummary, ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"
```

Add state for metrics alongside `scoreData`:
```ts
const [metricsData, setMetricsData] = useState<InstitutionalMetricsResponse | null>(null)
```

Update the `handleClick` callback to fetch both in parallel. Replace the existing try block (lines 77-79):

```ts
        const [score, metrics] = await Promise.all([
          getScore(pick.ticker, ["price_history", "signal_history"]),
          getMetrics(pick.ticker),
        ])
        setScoreData(score)
        setMetricsData(metrics)
```

Pass metrics to AssetPanel (update the `<AssetPanel>` JSX):
```tsx
      <AssetPanel
        isOpen={expanded && !loading}
        onClose={() => setExpanded(false)}
        ticker={pick.ticker}
        scoredResult={scoreData}
        metrics={metricsData}
      />
```

**Step 2: Update AssetPanel to accept and use metrics**

In `web/src/components/dashboard/panel/asset-panel.tsx`:

Add `InstitutionalMetricsResponse` to imports:
```ts
import type { ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"
```

Update `AssetPanelProps` interface:
```ts
interface AssetPanelProps {
  isOpen: boolean
  onClose: () => void
  ticker: string
  scoredResult: ScoreResponse
  metrics: InstitutionalMetricsResponse | null
}
```

Update the destructured props:
```ts
export function AssetPanel({ isOpen, onClose, ticker, scoredResult, metrics }: AssetPanelProps) {
```

Remove the `computeInstitutionalMetrics` import and the `useMemo` that calls it (lines 16 and 76-79).

Update the `<KpiGrid>` props to use server-computed metrics:
```tsx
                  <KpiGrid
                    sharpeRatio={metrics?.sharpe_ratio ?? null}
                    maxDrawdown={metrics?.max_drawdown ?? null}
                    volatility={metrics?.volatility ?? null}
                    avgProfitMargin={metrics?.avg_profit_margin ?? null}
                    allocationWeight={metrics?.allocation_weight ?? null}
                    marginOfSafety={metrics?.margin_of_safety != null ? Math.round(metrics.margin_of_safety * 100) : null}
                  />
```

**Step 3: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/dashboard/panel/asset-panel.tsx
git commit -m "feat(web): wire backend metrics into KPI grid"
```

---

### Task 10: Update Frontend Tests

**Files:**
- Modify: `web/src/components/dashboard/__tests__/stock-card.test.tsx`
- Modify: `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`

**Step 1: Update stock-card tests for parallel fetch**

In the stock-card test file, update the mock for `getScore` to also mock `getMetrics`:

```ts
vi.mock("@/lib/api/scores", () => ({
  getScore: vi.fn(),
  getMetrics: vi.fn(),
}))
```

Add a mock metrics response in the test setup:

```ts
const mockMetrics = {
  sharpe_ratio: 1.25,
  max_drawdown: -0.15,
  volatility: 22.5,
  avg_profit_margin: 25.0,
  risk_classification: "Moderate",
  allocation_weight: 8.0,
  margin_of_safety: 0.10,
}
```

Ensure `getMetrics` is configured to return this mock in each test that expands the card.

**Step 2: Update asset-panel tests for metrics prop**

In the asset-panel test file, update `AssetPanel` renders to pass the `metrics` prop:

```tsx
const mockMetrics = {
  sharpe_ratio: 1.25,
  max_drawdown: -0.15,
  volatility: 22.5,
  avg_profit_margin: 25.0,
  risk_classification: "Moderate",
  allocation_weight: 8.0,
  margin_of_safety: 0.10,
}

render(
  <AssetPanel
    isOpen={true}
    onClose={vi.fn()}
    ticker="AAPL"
    scoredResult={mockScore}
    metrics={mockMetrics}
  />
)
```

**Step 3: Run frontend tests**

Run: `cd web && npx vitest run --reporter=verbose`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/dashboard/__tests__/stock-card.test.tsx web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx
git commit -m "test(web): update stock-card and asset-panel tests for metrics endpoint"
```

---

### Task 11: Run Full Test Suites and Final Verification

**Step 1: Run API tests**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: All tests PASS (including new metrics tests)

**Step 2: Run engine tests**

Run: `uv run pytest engine/tests/ -v --timeout=60`
Expected: All tests PASS (no engine changes, regression check only)

**Step 3: Run frontend tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 4: Verify dev server works end-to-end**

1. Start the API: `uv run uvicorn margin_api.app:create_app --factory --port 8000`
2. Start the web app: `cd web && npm run dev`
3. Open dashboard, click a stock card, verify:
   - Sharpe Ratio shows a number (not "—")
   - Max Drawdown shows a percentage (not "—")
   - Volatility shows a percentage (not "—")
   - Avg Profit Margin shows a percentage (not "—")
   - Allocation shows a percentage
   - Margin of Safety shows a percentage
   - Target shows either a dollar amount or a descriptive reason (not "N/A")

**Step 5: Final commit**

If any adjustments were needed, commit them. Then verify git log shows the clean commit history.
