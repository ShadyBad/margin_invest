# Correlation Heatmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a data-driven portfolio correlation heatmap with engine computation, API endpoint, dashboard component, and landing page update.

**Architecture:** Correlation math in the engine package (pure Python, no numpy). New API endpoint serves NxN matrices. Shared `CorrelationGrid` UI component used by both the dashboard (authenticated, with toggle) and landing page (public, cached showcase). TDD throughout.

**Tech Stack:** Python/Pydantic (engine), FastAPI/SQLAlchemy (API), React/TypeScript/Tailwind 4 (web), Redis (showcase cache), pytest + vitest (tests)

---

## Task 1: Engine — Correlation Models

**Files:**
- Create: `engine/src/margin_engine/correlation.py`
- Test: `engine/tests/test_correlation.py`

**Step 1: Write the failing tests for models**

```python
# engine/tests/test_correlation.py
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from margin_engine.correlation import CorrelationMatrix, ExcludedTicker


class TestCorrelationModels:
    def test_excluded_ticker_fields(self):
        et = ExcludedTicker(ticker="AAPL", reason="insufficient data")
        assert et.ticker == "AAPL"
        assert et.reason == "insufficient data"

    def test_correlation_matrix_valid(self):
        m = CorrelationMatrix(
            tickers=["AAPL", "MSFT"],
            method="returns",
            matrix=[[1.0, 0.5], [0.5, 1.0]],
            sample_sizes=[[252, 250], [250, 252]],
            excluded=[],
            window_days=252,
            computed_at=datetime.now(UTC),
        )
        assert len(m.tickers) == 2
        assert m.matrix[0][1] == 0.5
        assert m.method == "returns"

    def test_correlation_matrix_allows_none_cells(self):
        m = CorrelationMatrix(
            tickers=["AAPL", "MSFT"],
            method="returns",
            matrix=[[1.0, None], [None, 1.0]],
            sample_sizes=[[252, 10], [10, 252]],
            excluded=[],
            window_days=252,
            computed_at=datetime.now(UTC),
        )
        assert m.matrix[0][1] is None

    def test_method_must_be_returns_or_factors(self):
        with pytest.raises(ValidationError):
            CorrelationMatrix(
                tickers=["AAPL"],
                method="invalid",
                matrix=[[1.0]],
                sample_sizes=[[252]],
                excluded=[],
                window_days=252,
                computed_at=datetime.now(UTC),
            )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_correlation.py -v`
Expected: FAIL — `ImportError: cannot import name 'CorrelationMatrix' from 'margin_engine.correlation'`

**Step 3: Write the models**

```python
# engine/src/margin_engine/correlation.py
"""Portfolio correlation computation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ExcludedTicker(BaseModel):
    """A ticker excluded from the correlation matrix with reason."""

    ticker: str
    reason: str


class CorrelationMatrix(BaseModel):
    """NxN correlation matrix for a set of tickers."""

    tickers: list[str]
    method: Literal["returns", "factors"]
    matrix: list[list[float | None]]
    sample_sizes: list[list[int]]
    excluded: list[ExcludedTicker]
    window_days: int
    computed_at: datetime
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_correlation.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/correlation.py engine/tests/test_correlation.py
git commit -m "feat(engine): add correlation matrix models"
```

---

## Task 2: Engine — Pearson Correlation Helper

**Files:**
- Modify: `engine/src/margin_engine/correlation.py`
- Test: `engine/tests/test_correlation.py`

**Step 1: Write the failing tests for the Pearson function**

Add to `engine/tests/test_correlation.py`:

```python
from margin_engine.correlation import _pearson


class TestPearsonCorrelation:
    def test_perfect_positive(self):
        assert _pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_perfect_negative(self):
        assert _pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)

    def test_no_correlation(self):
        # Orthogonal: [1, -1, 1, -1] vs [1, 1, -1, -1]
        r = _pearson([1.0, -1.0, 1.0, -1.0], [1.0, 1.0, -1.0, -1.0])
        assert r == pytest.approx(0.0)

    def test_known_value(self):
        # Hand-computed: x=[10,20,30], y=[12,25,28]
        # r = 45 / sqrt(200 * 148/3... ) ≈ 0.9934
        r = _pearson([10.0, 20.0, 30.0], [12.0, 25.0, 28.0])
        assert r == pytest.approx(0.99344, abs=1e-4)

    def test_constant_series_returns_none(self):
        assert _pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None

    def test_too_short_returns_none(self):
        assert _pearson([1.0], [2.0]) is None

    def test_empty_returns_none(self):
        assert _pearson([], []) is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_correlation.py::TestPearsonCorrelation -v`
Expected: FAIL — `ImportError: cannot import name '_pearson'`

**Step 3: Implement `_pearson`**

Add to `engine/src/margin_engine/correlation.py`:

```python
import math


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Compute Pearson correlation coefficient. Returns None if undefined."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom == 0.0:
        return None
    return cov / denom
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_correlation.py::TestPearsonCorrelation -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/correlation.py engine/tests/test_correlation.py
git commit -m "feat(engine): add Pearson correlation helper"
```

---

## Task 3: Engine — Return Correlation Matrix

**Files:**
- Modify: `engine/src/margin_engine/correlation.py`
- Test: `engine/tests/test_correlation.py`

**Context:** Uses `PriceBar` from `engine/src/margin_engine/models/financial.py:165`. Each `PriceBar` has `date: str`, `close: Decimal`, `adj_close: Decimal | None`.

**Step 1: Write the failing tests**

Add to `engine/tests/test_correlation.py`:

```python
import datetime as dt
from decimal import Decimal

from margin_engine.correlation import compute_return_correlations
from margin_engine.models.financial import PriceBar


def _bar(date_str: str, close: float) -> PriceBar:
    """Helper: minimal PriceBar."""
    p = Decimal(str(close))
    return PriceBar(date=date_str, open=p, high=p, low=p, close=p, volume=100_000)


def _daily_bars(start: str, prices: list[float]) -> list[PriceBar]:
    """Generate bars from a list of closing prices, one per business day."""
    base = dt.date.fromisoformat(start)
    bars = []
    d = base
    for price in prices:
        bars.append(_bar(d.isoformat(), price))
        d += dt.timedelta(days=1)
        # skip weekends
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
    return bars


class TestReturnCorrelations:
    def test_two_identical_series_correlation_is_one(self):
        prices = [100.0, 102.0, 101.0, 105.0, 103.0] * 10  # 50 points
        bars_a = _daily_bars("2025-01-02", prices)
        bars_b = _daily_bars("2025-01-02", prices)
        result = compute_return_correlations(
            {"AAPL": bars_a, "COPY": bars_b}, window_days=252
        )
        assert result.tickers == ["AAPL", "COPY"]
        assert result.matrix[0][0] == pytest.approx(1.0)
        assert result.matrix[1][1] == pytest.approx(1.0)
        assert result.matrix[0][1] == pytest.approx(1.0, abs=1e-6)
        assert result.matrix[1][0] == pytest.approx(1.0, abs=1e-6)

    def test_inversely_correlated(self):
        prices_up = [100.0 + i for i in range(50)]
        prices_down = [200.0 - i for i in range(50)]
        bars_a = _daily_bars("2025-01-02", prices_up)
        bars_b = _daily_bars("2025-01-02", prices_down)
        result = compute_return_correlations({"UP": bars_a, "DOWN": bars_b})
        # Log returns of linearly up vs linearly down are strongly negative
        assert result.matrix[0][1] is not None
        assert result.matrix[0][1] < -0.9

    def test_symmetric(self):
        bars_a = _daily_bars("2025-01-02", [100 + i * 0.5 for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i * 0.3 for i in range(50)])
        bars_c = _daily_bars("2025-01-02", [200 - i * 0.2 for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b, "C": bars_c})
        for i in range(3):
            for j in range(3):
                assert result.matrix[i][j] == pytest.approx(
                    result.matrix[j][i], abs=1e-10
                )

    def test_sample_sizes_populated(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b})
        # 50 prices = 49 returns
        assert result.sample_sizes[0][1] == 49

    def test_insufficient_overlap_returns_none(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(10)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(10)])
        result = compute_return_correlations(
            {"A": bars_a, "B": bars_b}, min_overlap=30
        )
        # Only 9 return pairs, below 30 minimum
        assert result.matrix[0][1] is None

    def test_ticker_with_too_few_bars_excluded(self):
        bars_good = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_short = _daily_bars("2025-01-02", [50.0, 51.0])  # only 2 bars
        result = compute_return_correlations(
            {"GOOD": bars_good, "SHORT": bars_short}, min_bars=10
        )
        assert "SHORT" in [e.ticker for e in result.excluded]
        assert result.tickers == ["GOOD"]

    def test_fewer_than_two_valid_tickers_returns_empty(self):
        bars = _daily_bars("2025-01-02", [100.0, 101.0])
        result = compute_return_correlations({"ONLY": bars}, min_bars=10)
        assert result.tickers == []
        assert result.matrix == []

    def test_method_is_returns(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b})
        assert result.method == "returns"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_correlation.py::TestReturnCorrelations -v`
Expected: FAIL — `ImportError: cannot import name 'compute_return_correlations'`

**Step 3: Implement `compute_return_correlations`**

Add to `engine/src/margin_engine/correlation.py`:

```python
from datetime import UTC, datetime

from margin_engine.models.financial import PriceBar


def _log_returns(bars: list[PriceBar]) -> dict[str, float]:
    """Compute daily log returns keyed by date string."""
    returns: dict[str, float] = {}
    for i in range(1, len(bars)):
        prev_close = float(bars[i - 1].adj_close or bars[i - 1].close)
        curr_close = float(bars[i].adj_close or bars[i].close)
        if prev_close > 0 and curr_close > 0:
            returns[bars[i].date] = math.log(curr_close / prev_close)
    return returns


def compute_return_correlations(
    price_data: dict[str, list[PriceBar]],
    window_days: int = 252,
    min_overlap: int = 30,
    min_bars: int = 10,
) -> CorrelationMatrix:
    """Compute Pearson correlations on daily log returns."""
    excluded: list[ExcludedTicker] = []
    valid_tickers: list[str] = []
    returns_by_ticker: dict[str, dict[str, float]] = {}

    for ticker in sorted(price_data.keys()):
        bars = price_data[ticker][-window_days:]
        if len(bars) < min_bars:
            excluded.append(
                ExcludedTicker(ticker=ticker, reason=f"only {len(bars)} bars (need {min_bars})")
            )
            continue
        returns_by_ticker[ticker] = _log_returns(bars)
        valid_tickers.append(ticker)

    n = len(valid_tickers)
    if n < 2:
        return CorrelationMatrix(
            tickers=valid_tickers,
            method="returns",
            matrix=[[1.0]] if n == 1 else [],
            sample_sizes=[[len(returns_by_ticker.get(valid_tickers[0], {}))]] if n == 1 else [],
            excluded=excluded,
            window_days=window_days,
            computed_at=datetime.now(UTC),
        )

    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    sample_sizes: list[list[int]] = [[0] * n for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 1.0
        ret_i = returns_by_ticker[valid_tickers[i]]
        sample_sizes[i][i] = len(ret_i)
        for j in range(i + 1, n):
            ret_j = returns_by_ticker[valid_tickers[j]]
            common_dates = sorted(set(ret_i.keys()) & set(ret_j.keys()))
            overlap = len(common_dates)
            sample_sizes[i][j] = overlap
            sample_sizes[j][i] = overlap
            if overlap < min_overlap:
                matrix[i][j] = None
                matrix[j][i] = None
            else:
                xs = [ret_i[d] for d in common_dates]
                ys = [ret_j[d] for d in common_dates]
                r = _pearson(xs, ys)
                matrix[i][j] = r
                matrix[j][i] = r

    return CorrelationMatrix(
        tickers=valid_tickers,
        method="returns",
        matrix=matrix,
        sample_sizes=sample_sizes,
        excluded=excluded,
        window_days=window_days,
        computed_at=datetime.now(UTC),
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_correlation.py::TestReturnCorrelations -v`
Expected: 9 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/correlation.py engine/tests/test_correlation.py
git commit -m "feat(engine): add return correlation computation"
```

---

## Task 4: Engine — Factor Score Correlation Matrix

**Files:**
- Modify: `engine/src/margin_engine/correlation.py`
- Test: `engine/tests/test_correlation.py`

**Context:** Uses `FactorBreakdown` from `engine/src/margin_engine/models/scoring.py:85`. Each `FactorBreakdown` has `sub_scores: list[FactorScore]` where `FactorScore` has `percentile_rank: float`.

**Step 1: Write the failing tests**

Add to `engine/tests/test_correlation.py`:

```python
from margin_engine.correlation import compute_factor_correlations
from margin_engine.models.scoring import FactorBreakdown, FactorScore


def _factor(name: str, percentiles: list[float]) -> FactorBreakdown:
    """Helper: build a FactorBreakdown with given sub-score percentiles."""
    return FactorBreakdown(
        factor_name=name,
        weight=1.0,
        sub_scores=[
            FactorScore(name=f"metric_{i}", raw_value=0.0, percentile_rank=p, detail="")
            for i, p in enumerate(percentiles)
        ],
    )


def _factors(quality: list[float], value: list[float], momentum: list[float]) -> dict[str, FactorBreakdown]:
    """Helper: build the 3-factor dict for a ticker."""
    return {
        "quality": _factor("quality", quality),
        "value": _factor("value", value),
        "momentum": _factor("momentum", momentum),
    }


class TestFactorCorrelations:
    def test_identical_profiles_correlation_one(self):
        profiles = {
            "AAPL": _factors([80, 70, 60], [50, 40, 30], [90, 85, 80]),
            "COPY": _factors([80, 70, 60], [50, 40, 30], [90, 85, 80]),
        }
        result = compute_factor_correlations(profiles)
        assert result.method == "factors"
        assert result.matrix[0][1] == pytest.approx(1.0)

    def test_opposite_profiles_negative(self):
        profiles = {
            "HIGH": _factors([90, 90, 90], [90, 90, 90], [90, 90, 90]),
            "LOW": _factors([10, 10, 10], [10, 10, 10], [10, 10, 10]),
        }
        result = compute_factor_correlations(profiles)
        # Constant vectors → None (zero variance)
        assert result.matrix[0][1] is None

    def test_varied_profiles(self):
        profiles = {
            "A": _factors([90, 50, 30], [70, 60, 40], [80, 20, 50]),
            "B": _factors([85, 55, 25], [65, 65, 35], [75, 25, 45]),
        }
        result = compute_factor_correlations(profiles)
        # Similar profiles should be highly correlated
        assert result.matrix[0][1] is not None
        assert result.matrix[0][1] > 0.9

    def test_symmetric(self):
        profiles = {
            "A": _factors([90, 50], [70, 60], [80, 20]),
            "B": _factors([20, 80], [30, 90], [50, 50]),
            "C": _factors([50, 50], [50, 50], [50, 60]),
        }
        result = compute_factor_correlations(profiles)
        for i in range(3):
            for j in range(3):
                assert result.matrix[i][j] == result.matrix[j][i]

    def test_single_ticker_returns_minimal(self):
        profiles = {"ONLY": _factors([80, 70], [50, 40], [90, 85])}
        result = compute_factor_correlations(profiles)
        assert result.tickers == ["ONLY"]
        assert result.matrix == [[1.0]]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_correlation.py::TestFactorCorrelations -v`
Expected: FAIL — `ImportError: cannot import name 'compute_factor_correlations'`

**Step 3: Implement `compute_factor_correlations`**

Add to `engine/src/margin_engine/correlation.py`:

```python
from margin_engine.models.scoring import FactorBreakdown


def _factor_vector(factors: dict[str, FactorBreakdown]) -> list[float]:
    """Flatten factor breakdowns into a single percentile vector."""
    vector: list[float] = []
    for key in sorted(factors.keys()):
        for sub in factors[key].sub_scores:
            vector.append(sub.percentile_rank)
    return vector


def compute_factor_correlations(
    profiles: dict[str, dict[str, FactorBreakdown]],
) -> CorrelationMatrix:
    """Compute Pearson correlations on factor score vectors."""
    tickers = sorted(profiles.keys())
    vectors = {t: _factor_vector(profiles[t]) for t in tickers}
    n = len(tickers)

    if n < 2:
        return CorrelationMatrix(
            tickers=tickers,
            method="factors",
            matrix=[[1.0]] if n == 1 else [],
            sample_sizes=[[len(vectors[tickers[0]])]] if n == 1 else [],
            excluded=[],
            window_days=0,
            computed_at=datetime.now(UTC),
        )

    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    sample_sizes: list[list[int]] = [[0] * n for _ in range(n)]

    for i in range(n):
        vec_i = vectors[tickers[i]]
        matrix[i][i] = 1.0
        sample_sizes[i][i] = len(vec_i)
        for j in range(i + 1, n):
            vec_j = vectors[tickers[j]]
            size = min(len(vec_i), len(vec_j))
            sample_sizes[i][j] = size
            sample_sizes[j][i] = size
            r = _pearson(vec_i[:size], vec_j[:size])
            matrix[i][j] = r
            matrix[j][i] = r

    return CorrelationMatrix(
        tickers=tickers,
        method="factors",
        matrix=matrix,
        sample_sizes=sample_sizes,
        excluded=[],
        window_days=0,
        computed_at=datetime.now(UTC),
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_correlation.py::TestFactorCorrelations -v`
Expected: 5 passed

**Step 5: Run all engine correlation tests**

Run: `uv run pytest engine/tests/test_correlation.py -v`
Expected: all passed (models + pearson + returns + factors)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/correlation.py engine/tests/test_correlation.py
git commit -m "feat(engine): add factor score correlation computation"
```

---

## Task 5: API — Correlation Schema & Route

**Files:**
- Create: `api/src/margin_api/schemas/correlations.py`
- Create: `api/src/margin_api/routes/correlations.py`
- Modify: `api/src/margin_api/schemas/__init__.py`
- Modify: `api/src/margin_api/app.py:15-33` (imports), `api/src/margin_api/app.py:101-118` (include_router)
- Test: `api/tests/test_correlation_routes.py`

**Step 1: Write the schema**

```python
# api/src/margin_api/schemas/correlations.py
"""Correlation endpoint schemas."""

from datetime import datetime

from pydantic import BaseModel


class ExcludedTickerResponse(BaseModel):
    ticker: str
    reason: str


class CorrelationResponse(BaseModel):
    tickers: list[str]
    method: str
    matrix: list[list[float | None]]
    sample_sizes: list[list[int]]
    excluded: list[ExcludedTickerResponse]
    window_days: int
    computed_at: datetime
```

**Step 2: Write the route**

```python
# api/src/margin_api/routes/correlations.py
"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

# Hardcoded fallback for showcase when cache is empty
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

        client = aioredis.Redis(host="localhost", port=6379, socket_connect_timeout=1)
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


@router.get("", response_model=CorrelationResponse)
async def get_correlations(
    request: Request,
    method: str = Query(..., pattern="^(returns|factors)$"),
    tickers: str | None = Query(None),
    window: int = Query(252, ge=30, le=504),
    db: AsyncSession = Depends(get_db),
) -> CorrelationResponse:
    """Compute correlation matrix for user's tickers."""
    from margin_engine.correlation import (
        compute_factor_correlations,
        compute_return_correlations,
    )
    from margin_engine.models.financial import PriceBar
    from margin_engine.models.scoring import FactorBreakdown, FactorScore

    # Resolve ticker list
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")][:10]
    else:
        # Default: user's top picks (buy/strong_buy signals)
        user_id = getattr(request.state, "user_id", None)
        stmt = (
            select(Score)
            .where(Score.signal.in_(["buy", "strong_buy"]))
            .order_by(Score.composite_raw_score.desc())
            .limit(10)
        )
        if user_id:
            stmt = stmt.where(Score.user_id == user_id)
        rows = (await db.execute(stmt)).scalars().all()
        ticker_list = [r.ticker for r in rows]

    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers for correlation")

    if method == "returns":
        # Fetch price history for each ticker
        price_data: dict[str, list[PriceBar]] = {}
        for ticker in ticker_list:
            stmt = select(FinancialData).where(
                FinancialData.ticker == ticker,
                FinancialData.data_type == "price_history",
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.data:
                bars = [PriceBar(**bar) for bar in row.data]
                price_data[ticker] = bars

        if len(price_data) < 2:
            raise HTTPException(
                status_code=404,
                detail="No qualifying picks found. Score some tickers first.",
            )

        result = compute_return_correlations(price_data, window_days=window)

    else:  # factors
        # Fetch latest scores for each ticker
        factor_profiles: dict[str, dict[str, FactorBreakdown]] = {}
        for ticker in ticker_list:
            stmt = (
                select(Score)
                .where(Score.ticker == ticker)
                .order_by(Score.scored_at.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.quality and row.value and row.momentum:
                factor_profiles[ticker] = {
                    "quality": _rebuild_factor(row.quality),
                    "value": _rebuild_factor(row.value),
                    "momentum": _rebuild_factor(row.momentum),
                }

        if len(factor_profiles) < 2:
            raise HTTPException(
                status_code=404,
                detail="No qualifying picks found. Score some tickers first.",
            )

        result = compute_factor_correlations(factor_profiles)

    return CorrelationResponse(**result.model_dump())


def _rebuild_factor(data: dict) -> FactorBreakdown:
    """Rebuild FactorBreakdown from JSONB dict."""
    from margin_engine.models.scoring import FactorBreakdown, FactorScore

    sub_scores = [FactorScore(**s) for s in data.get("sub_scores", [])]
    return FactorBreakdown(
        factor_name=data["factor_name"],
        weight=data["weight"],
        sub_scores=sub_scores,
    )
```

**Step 3: Register the router**

Add to `api/src/margin_api/app.py`:
- Line ~33 area (imports): `from margin_api.routes.correlations import router as correlations_router`
- Line ~118 area (after `app.include_router(universe_router)`): `app.include_router(correlations_router)`

**Step 4: Update schema exports**

Add to `api/src/margin_api/schemas/__init__.py`:
```python
from margin_api.schemas.correlations import CorrelationResponse, ExcludedTickerResponse
```
And add both to `__all__`.

**Step 5: Write API tests**

```python
# api/tests/test_correlation_routes.py
"""Tests for correlation endpoints."""

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


class TestCorrelationEndpoint:
    def test_invalid_method_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/correlations?method=invalid")
        assert resp.status_code == 422

    def test_method_required(self, client: TestClient):
        resp = client.get("/api/v1/correlations")
        assert resp.status_code == 422

    def test_window_bounds(self, client: TestClient):
        resp = client.get("/api/v1/correlations?method=returns&window=5")
        assert resp.status_code == 422
        resp = client.get("/api/v1/correlations?method=returns&window=1000")
        assert resp.status_code == 422

    def test_route_registered(self, client: TestClient):
        routes = [r.path for r in client.app.routes]
        assert "/api/v1/correlations" in routes
        assert "/api/v1/correlations/showcase" in routes
```

**Step 6: Run tests**

Run: `uv run pytest api/tests/test_correlation_routes.py -v`
Expected: all passed

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/correlations.py api/src/margin_api/routes/correlations.py \
  api/src/margin_api/schemas/__init__.py api/src/margin_api/app.py \
  api/tests/test_correlation_routes.py
git commit -m "feat(api): add correlation matrix endpoints"
```

---

## Task 6: Frontend — TypeScript Types & API Client

**Files:**
- Modify: `web/src/lib/api/types.ts`
- Create: `web/src/lib/api/correlations.ts`
- Modify: `web/src/lib/api/index.ts`

**Step 1: Add TypeScript interfaces**

Add to end of `web/src/lib/api/types.ts`:

```typescript
export interface ExcludedTickerResponse {
  ticker: string
  reason: string
}

export interface CorrelationResponse {
  tickers: string[]
  method: string
  matrix: (number | null)[][]
  sample_sizes: number[][]
  excluded: ExcludedTickerResponse[]
  window_days: number
  computed_at: string
}
```

**Step 2: Create API client functions**

```typescript
// web/src/lib/api/correlations.ts
import { apiFetch } from './client'
import type { CorrelationResponse } from './types'

export async function getCorrelations(
  method: 'returns' | 'factors',
  tickers?: string[],
  window?: number,
): Promise<CorrelationResponse> {
  const params = new URLSearchParams({ method })
  if (tickers?.length) params.set('tickers', tickers.join(','))
  if (window !== undefined) params.set('window', String(window))
  return apiFetch<CorrelationResponse>(`/api/v1/correlations?${params}`)
}

export async function getShowcaseCorrelations(): Promise<CorrelationResponse> {
  return apiFetch<CorrelationResponse>('/api/v1/correlations/showcase')
}
```

**Step 3: Export from index**

Add to `web/src/lib/api/index.ts`:

```typescript
export { getCorrelations, getShowcaseCorrelations } from './correlations'
```

And add to the type exports:
```typescript
export type { CorrelationResponse, ExcludedTickerResponse } from './types'
```

**Step 4: Commit**

```bash
git add web/src/lib/api/types.ts web/src/lib/api/correlations.ts web/src/lib/api/index.ts
git commit -m "feat(web): add correlation API types and client functions"
```

---

## Task 7: Frontend — Shared CorrelationGrid Component

**Files:**
- Create: `web/src/components/ui/correlation-grid.tsx`
- Test: `web/src/components/ui/__tests__/correlation-grid.test.tsx`

**Step 1: Write the failing tests**

```typescript
// web/src/components/ui/__tests__/correlation-grid.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { CorrelationGrid } from '../correlation-grid'

const TICKERS = ['AAPL', 'MSFT', 'JNJ']
const MATRIX: (number | null)[][] = [
  [1.0, 0.82, 0.15],
  [0.82, 1.0, null],
  [0.15, null, 1.0],
]
const SAMPLE_SIZES = [
  [252, 250, 248],
  [250, 252, 10],
  [248, 10, 252],
]

describe('CorrelationGrid', () => {
  it('renders all ticker labels', () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    // Each ticker appears twice: once as column header, once as row header
    for (const ticker of TICKERS) {
      const elements = screen.getAllByText(ticker)
      expect(elements.length).toBe(2)
    }
  })

  it('renders numeric values for non-null cells', () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    expect(screen.getAllByText('0.82').length).toBe(2) // symmetric pair
    expect(screen.getAllByText('0.15').length).toBe(2) // symmetric pair
  })

  it('renders dash for null cells', () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBe(2) // two null cells
  })

  it('renders diagonal as 1.00', () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    const ones = screen.getAllByText('1.00')
    expect(ones.length).toBe(3) // 3 diagonal cells
  })

  it('shows tooltip on hover when enabled', async () => {
    const user = userEvent.setup()
    render(
      <CorrelationGrid
        tickers={TICKERS}
        matrix={MATRIX}
        sampleSizes={SAMPLE_SIZES}
        showTooltip
      />
    )
    // Find a cell with value 0.82 and hover it
    const cells = screen.getAllByText('0.82')
    await user.hover(cells[0])
    expect(screen.getByText(/AAPL/)).toBeDefined()
    expect(screen.getByText(/MSFT/)).toBeDefined()
    expect(screen.getByText(/250/)).toBeDefined()
  })

  it('does not show tooltip when disabled', async () => {
    const user = userEvent.setup()
    render(
      <CorrelationGrid
        tickers={TICKERS}
        matrix={MATRIX}
        sampleSizes={SAMPLE_SIZES}
        showTooltip={false}
      />
    )
    const cells = screen.getAllByText('0.82')
    await user.hover(cells[0])
    // Tooltip content should not appear
    expect(screen.queryByText(/N =/)).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/ui/__tests__/correlation-grid.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement CorrelationGrid**

```tsx
// web/src/components/ui/correlation-grid.tsx
"use client"

import { Fragment, useState } from "react"

interface CorrelationGridProps {
  tickers: string[]
  matrix: (number | null)[][]
  sampleSizes?: number[][]
  showTooltip?: boolean
  className?: string
}

function cellBackground(value: number | null): string {
  if (value === null) return "var(--color-bg-primary)"
  const abs = Math.abs(value)
  if (value >= 0) {
    if (abs >= 0.6) return `color-mix(in srgb, var(--color-accent) ${15 + abs * 25}%, transparent)`
    if (abs >= 0.3) return `color-mix(in srgb, var(--color-accent) ${abs * 25}%, transparent)`
    return "transparent"
  }
  if (abs >= 0.6) return `color-mix(in srgb, var(--color-danger) ${15 + abs * 25}%, transparent)`
  if (abs >= 0.3) return `color-mix(in srgb, var(--color-danger) ${abs * 25}%, transparent)`
  return "transparent"
}

function textClass(value: number | null, isDiagonal: boolean): string {
  if (value === null) return "text-text-tertiary"
  if (isDiagonal) return "text-text-tertiary"
  return Math.abs(value) >= 0.5 ? "text-text-primary" : "text-text-secondary"
}

function formatValue(value: number | null): string {
  if (value === null) return "—"
  return value.toFixed(2)
}

export function CorrelationGrid({
  tickers,
  matrix,
  sampleSizes,
  showTooltip = false,
  className = "",
}: CorrelationGridProps) {
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null)
  const n = tickers.length

  return (
    <div className={className}>
      <div
        className="grid gap-px"
        style={{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }}
      >
        {/* Empty top-left corner */}
        <div />
        {/* Column headers */}
        {tickers.map((ticker) => (
          <div
            key={`col-${ticker}`}
            className="text-[9px] font-mono text-text-tertiary text-center py-1 -rotate-45 origin-bottom-left translate-x-2"
          >
            {ticker}
          </div>
        ))}
        {/* Rows */}
        {matrix.map((row, i) => (
          <Fragment key={`row-${tickers[i]}`}>
            {/* Row label */}
            <div className="text-[9px] font-mono text-text-tertiary flex items-center justify-end pr-2">
              {tickers[i]}
            </div>
            {/* Cells */}
            {row.map((value, j) => {
              const isDiag = i === j
              return (
                <div
                  key={`${i}-${j}`}
                  className="aspect-square flex items-center justify-center rounded-sm relative cursor-default"
                  style={{ background: cellBackground(value) }}
                  onMouseEnter={() => showTooltip && setHover({ i, j })}
                  onMouseLeave={() => setHover(null)}
                >
                  <span className={`text-[10px] font-mono ${textClass(value, isDiag)} hidden md:inline`}>
                    {formatValue(value)}
                  </span>
                  {/* Mobile: only show color, no text for grids > 5 */}
                  {n <= 5 && (
                    <span className={`text-[9px] font-mono ${textClass(value, isDiag)} md:hidden`}>
                      {formatValue(value)}
                    </span>
                  )}
                  {/* Tooltip */}
                  {showTooltip && hover?.i === i && hover?.j === j && !isDiag && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-10 bg-bg-elevated border border-border-primary rounded px-2 py-1 shadow-card whitespace-nowrap pointer-events-none">
                      <div className="text-[10px] font-mono text-text-primary">
                        {tickers[i]} &times; {tickers[j]}
                      </div>
                      <div className="text-[10px] font-mono text-text-secondary">
                        &rho; = {formatValue(value)}
                      </div>
                      {sampleSizes && (
                        <div className="text-[10px] font-mono text-text-tertiary">
                          N = {sampleSizes[i][j]} days
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>
      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-4">
        <span className="text-[9px] text-text-tertiary">-1.0</span>
        <div
          className="h-2 w-32 rounded-full"
          style={{
            background:
              "linear-gradient(to right, color-mix(in srgb, var(--color-danger) 40%, transparent), transparent 50%, color-mix(in srgb, var(--color-accent) 40%, transparent))",
          }}
        />
        <span className="text-[9px] text-text-tertiary">+1.0</span>
      </div>
    </div>
  )
}
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/ui/__tests__/correlation-grid.test.tsx`
Expected: all passed

**Step 5: Commit**

```bash
git add web/src/components/ui/correlation-grid.tsx \
  web/src/components/ui/__tests__/correlation-grid.test.tsx
git commit -m "feat(web): add shared CorrelationGrid component"
```

---

## Task 8: Frontend — Dashboard CorrelationHeatmap

**Files:**
- Create: `web/src/components/dashboard/correlation-heatmap.tsx`
- Modify: `web/src/components/dashboard/index.ts`
- Modify: `web/src/app/dashboard/page.tsx`

**Step 1: Create the dashboard wrapper component**

```tsx
// web/src/components/dashboard/correlation-heatmap.tsx
"use client"

import { useCallback, useEffect, useState } from "react"

import { getCorrelations } from "@/lib/api/correlations"
import type { CorrelationResponse } from "@/lib/api/types"
import { CorrelationGrid } from "@/components/ui/correlation-grid"

type Method = "returns" | "factors"

export function CorrelationHeatmap() {
  const [method, setMethod] = useState<Method>("returns")
  const [data, setData] = useState<CorrelationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async (m: Method) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getCorrelations(m)
      setData(result)
    } catch (err) {
      if (err instanceof Error && err.message.includes("400")) {
        setError("Score at least 2 tickers to see portfolio correlations.")
      } else {
        setError("Unable to load correlations.")
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(method)
  }, [method, fetchData])

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary">
          Portfolio Correlations
        </div>
        {/* Toggle */}
        <div className="flex gap-1 bg-bg-primary rounded-full p-0.5">
          {(["returns", "factors"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMethod(m)}
              className={`text-[10px] font-mono px-3 py-1 rounded-full transition-colors ${
                method === m
                  ? "bg-bg-elevated text-text-primary shadow-sm"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              {m === "returns" ? "Returns" : "Factors"}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="text-[11px] text-text-tertiary font-mono animate-pulse">
            Computing correlations...
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="text-[11px] text-text-tertiary font-mono">{error}</div>
        </div>
      )}

      {data && !loading && !error && (
        <CorrelationGrid
          tickers={data.tickers}
          matrix={data.matrix}
          sampleSizes={data.sample_sizes}
          showTooltip
        />
      )}

      {data && data.excluded.length > 0 && !loading && (
        <div className="mt-3 text-[9px] text-text-tertiary font-mono">
          Excluded: {data.excluded.map((e) => `${e.ticker} (${e.reason})`).join(", ")}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Export from dashboard index**

Add to `web/src/components/dashboard/index.ts`:

```typescript
export { CorrelationHeatmap } from "./correlation-heatmap"
```

**Step 3: Add to dashboard page**

In `web/src/app/dashboard/page.tsx`, add the import and render the component after the Top Picks section (after the `</section>` that wraps `<PicksGrid>`):

Import: `import { CorrelationHeatmap } from "@/components/dashboard"`
(or add to existing destructured import from `"@/components/dashboard"`)

Add section:
```tsx
<section className="mb-10">
  <CorrelationHeatmap />
</section>
```

Place it between the Top Picks section and the Watchlist section.

**Step 4: Commit**

```bash
git add web/src/components/dashboard/correlation-heatmap.tsx \
  web/src/components/dashboard/index.ts \
  web/src/app/dashboard/page.tsx
git commit -m "feat(web): add correlation heatmap to dashboard"
```

---

## Task 9: Frontend — Update Landing Page ProofHeatmap

**Files:**
- Modify: `web/src/components/landing/proof-heatmap.tsx`

**Step 1: Rewrite ProofHeatmap to use CorrelationGrid with API fallback**

Replace the entire content of `web/src/components/landing/proof-heatmap.tsx`:

```tsx
// web/src/components/landing/proof-heatmap.tsx
"use client"

import { useEffect, useState } from "react"

import { CorrelationGrid } from "@/components/ui/correlation-grid"

// Fallback data when API is unavailable
const FALLBACK_TICKERS = ["AAPL", "MSFT", "JNJ", "COST", "V"]
const FALLBACK_MATRIX: (number | null)[][] = [
  [1.0, 0.82, 0.15, 0.28, 0.45],
  [0.82, 1.0, 0.12, 0.31, 0.51],
  [0.15, 0.12, 1.0, 0.62, 0.22],
  [0.28, 0.31, 0.62, 1.0, 0.35],
  [0.45, 0.51, 0.22, 0.35, 1.0],
]

interface ShowcaseData {
  tickers: string[]
  matrix: (number | null)[][]
}

export function ProofHeatmap() {
  const [data, setData] = useState<ShowcaseData>({
    tickers: FALLBACK_TICKERS,
    matrix: FALLBACK_MATRIX,
  })

  useEffect(() => {
    async function fetchShowcase() {
      try {
        const resp = await fetch("/api/v1/correlations/showcase")
        if (resp.ok) {
          const json = await resp.json()
          setData({ tickers: json.tickers, matrix: json.matrix })
        }
      } catch {
        // Keep fallback
      }
    }
    fetchShowcase()
  }, [])

  return (
    <CorrelationGrid
      tickers={data.tickers}
      matrix={data.matrix}
      showTooltip={false}
    />
  )
}
```

**Step 2: Verify landing page still renders**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build`
Expected: builds without errors

**Step 3: Commit**

```bash
git add web/src/components/landing/proof-heatmap.tsx
git commit -m "feat(web): update landing page heatmap to use shared grid with API fallback"
```

---

## Task 10: CLI — Showcase Cache Command

**Files:**
- Modify: `api/src/margin_api/cli.py`

**Step 1: Add `correlations --showcase` subcommand**

Add to the CLI's argument parser and main function in `api/src/margin_api/cli.py`:

Parser addition:
```python
corr_parser = subparsers.add_parser("correlations", help="Compute and cache correlations")
corr_parser.add_argument("--showcase", action="store_true", help="Compute and cache showcase matrix")
corr_parser.add_argument(
    "--tickers",
    nargs="+",
    default=["AAPL", "MSFT", "JNJ", "COST", "V", "JPM", "XOM", "PG"],
    help="Tickers for showcase",
)
```

Handler:
```python
async def _handle_correlations(args):
    """Compute and cache showcase correlation matrix."""
    import json
    import redis.asyncio as aioredis
    from margin_engine.correlation import compute_return_correlations
    from margin_engine.models.financial import PriceBar

    session_factory = get_session_factory()
    async with session_factory() as db:
        price_data = {}
        for ticker in args.tickers:
            stmt = select(FinancialData).where(
                FinancialData.ticker == ticker,
                FinancialData.data_type == "price_history",
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.data:
                bars = [PriceBar(**bar) for bar in row.data]
                price_data[ticker] = bars
                logger.info("Loaded %d bars for %s", len(bars), ticker)
            else:
                logger.warning("No price data for %s", ticker)

    if len(price_data) < 2:
        logger.error("Need at least 2 tickers with price data")
        return

    result = compute_return_correlations(price_data)
    logger.info("Computed %dx%d correlation matrix", len(result.tickers), len(result.tickers))

    client = aioredis.Redis(host="localhost", port=6379)
    try:
        payload = json.dumps(result.model_dump(), default=str)
        await client.set("correlation:showcase", payload, ex=86400)  # 24h TTL
        logger.info("Cached showcase correlations in Redis (24h TTL)")
    finally:
        await client.aclose()
```

Wire it into the main dispatch:
```python
elif args.command == "correlations":
    asyncio.run(_handle_correlations(args))
```

**Step 2: Commit**

```bash
git add api/src/margin_api/cli.py
git commit -m "feat(api): add CLI command to compute and cache showcase correlations"
```

---

## Task 11: Run Full Test Suite & Verify

**Step 1: Run engine tests**

Run: `uv run pytest engine/tests/test_correlation.py -v`
Expected: all tests pass

**Step 2: Run API tests**

Run: `uv run pytest api/tests/test_correlation_routes.py -v`
Expected: all tests pass

**Step 3: Run full engine suite (regression check)**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ~784+ tests pass, no regressions

**Step 4: Run full API suite (regression check)**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: ~294+ tests pass, no regressions

**Step 5: Run frontend tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: all tests pass

**Step 6: Commit any test fixes if needed, then final commit**

```bash
git add -A && git commit -m "test: verify full test suite passes with correlation feature"
```
