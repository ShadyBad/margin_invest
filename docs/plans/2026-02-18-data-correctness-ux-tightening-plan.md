# Data Correctness & UX Tightening Implementation Plan (v2)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix filter logic (multi-window liquidity, multi-year health checks, INCONCLUSIVE verdicts), implement risk metrics (Sharpe/Drawdown/Vol), add valuation audit trail, accumulate score history, and consolidate the UX.

**Architecture:** Data-up — engine calculations first (pure Python), then API layer (FastAPI + SQLAlchemy), then frontend (Next.js + Recharts). Implementation order: A → B → C → D → F → E → G per design doc.

**Tech Stack:** Python 3.13 / Pydantic / pytest / SQLAlchemy 2.0 / asyncpg / aiosqlite (tests) / FastAPI / Next.js 15 / TypeScript / Recharts

**Design Doc:** `docs/plans/2026-02-18-data-correctness-ux-tightening-design.md`

---

## Phase 1: Engine — Liquidity Filter Redesign (Section A)

### Task 1: LiquidityProfile Model + Multi-Window Computation

**Files:**
- Create: `engine/src/margin_engine/models/liquidity.py`
- Create: `engine/tests/models/test_liquidity_profile.py`

**Step 1: Write failing test for LiquidityProfile**

```python
"""Tests for LiquidityProfile model and multi-window computation."""

import pytest
from decimal import Decimal
from margin_engine.models.liquidity import LiquidityProfile, compute_liquidity_profile
from margin_engine.models.financial import PriceBar


class TestLiquidityProfile:
    def test_profile_from_price_bars(self):
        """Compute median dollar volumes across 20/60/90 day windows."""
        bars = _make_bars(n=100, avg_close=150.0, avg_volume=1_000_000)
        profile = compute_liquidity_profile(
            bars=bars,
            listing_venue="NYSE",
            country_code="US",
        )
        assert profile.median_dollar_volume_20d > 0
        assert profile.median_dollar_volume_60d > 0
        assert profile.median_dollar_volume_90d > 0

    def test_profile_insufficient_bars(self):
        """Fewer than 20 bars should still compute available windows."""
        bars = _make_bars(n=15, avg_close=100.0, avg_volume=500_000)
        profile = compute_liquidity_profile(bars=bars)
        assert profile.median_dollar_volume_20d is None  # not enough
        assert profile.median_dollar_volume_60d is None
        assert profile.median_dollar_volume_90d is None

    def test_median_not_mean(self):
        """Median should resist outlier days with abnormal volume."""
        bars = _make_bars(n=25, avg_close=100.0, avg_volume=1_000_000)
        # Inject 3 extreme outlier days
        for i in range(3):
            bars[i] = PriceBar(
                date=bars[i].date,
                close=Decimal("100"),
                volume=100_000_000,  # 100x normal
            )
        profile = compute_liquidity_profile(bars=bars)
        # Median should be close to normal, not pulled by outliers
        assert profile.median_dollar_volume_20d < Decimal("200_000_000")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/models/test_liquidity_profile.py -v`
Expected: FAIL — module does not exist.

**Step 3: Implement LiquidityProfile model and compute function**

```python
"""Liquidity profile model with multi-window dollar volume computation."""

from __future__ import annotations
from decimal import Decimal
from statistics import median
from pydantic import BaseModel
from margin_engine.models.financial import PriceBar


class LiquidityProfile(BaseModel):
    median_dollar_volume_20d: Decimal | None = None
    median_dollar_volume_60d: Decimal | None = None
    median_dollar_volume_90d: Decimal | None = None
    listing_venue: str | None = None
    country_code: str | None = None
    avg_spread_bps: float | None = None


def compute_liquidity_profile(
    bars: list[PriceBar],
    listing_venue: str | None = None,
    country_code: str | None = None,
) -> LiquidityProfile:
    """Compute multi-window median dollar volumes from daily price bars."""
    # Sort bars by date descending (most recent first)
    sorted_bars = sorted(bars, key=lambda b: b.date, reverse=True)

    def _median_dollar_vol(n: int) -> Decimal | None:
        if len(sorted_bars) < n:
            return None
        window = sorted_bars[:n]
        dollar_vols = [b.close * Decimal(str(b.volume)) for b in window]
        return Decimal(str(median(dollar_vols)))

    return LiquidityProfile(
        median_dollar_volume_20d=_median_dollar_vol(20),
        median_dollar_volume_60d=_median_dollar_vol(60),
        median_dollar_volume_90d=_median_dollar_vol(90),
        listing_venue=listing_venue,
        country_code=country_code,
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/models/test_liquidity_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/liquidity.py engine/tests/models/test_liquidity_profile.py
git commit -m "feat(engine): add LiquidityProfile model with multi-window median dollar volume"
```

---

### Task 2: Position-Sizing Simulation

**Files:**
- Modify: `engine/src/margin_engine/models/liquidity.py`
- Modify: `engine/tests/models/test_liquidity_profile.py`

**Step 1: Write failing tests**

```python
class TestPositionSizing:
    def test_days_to_fill_normal(self):
        """$500K position at 5% participation of $10M daily vol = 1 day."""
        result = days_to_fill(
            position_size=500_000,
            participation_rate=0.05,
            median_dollar_volume=Decimal("10_000_000"),
        )
        assert result == pytest.approx(1.0)

    def test_days_to_fill_illiquid(self):
        """$500K position at 5% of $500K daily vol = 20 days."""
        result = days_to_fill(
            position_size=500_000,
            participation_rate=0.05,
            median_dollar_volume=Decimal("500_000"),
        )
        assert result == pytest.approx(20.0)

    def test_market_impact_estimate(self):
        """Impact at 5% participation ≈ 2.2 bps."""
        impact = market_impact_estimate(0.05)
        assert impact == pytest.approx(2.236, abs=0.1)  # 10 * sqrt(0.05)

    def test_divergence_ratio(self):
        """20d/90d ratio > 3 means liquidity evaporating."""
        ratio = liquidity_divergence_ratio(
            vol_20d=Decimal("500_000"),
            vol_90d=Decimal("2_000_000"),
        )
        assert ratio == pytest.approx(4.0)
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/models/test_liquidity_profile.py::TestPositionSizing -v`

**Step 3: Implement helper functions**

Add to `liquidity.py`:

```python
from math import sqrt

def days_to_fill(
    position_size: float,
    participation_rate: float,
    median_dollar_volume: Decimal,
) -> float:
    """How many days to build a position at given participation rate."""
    daily_capacity = float(median_dollar_volume) * participation_rate
    if daily_capacity <= 0:
        return float("inf")
    return position_size / daily_capacity

def market_impact_estimate(participation_rate: float) -> float:
    """Simplified Almgren-Chriss market impact in basis points."""
    return 10.0 * sqrt(participation_rate)

def liquidity_divergence_ratio(
    vol_20d: Decimal | None,
    vol_90d: Decimal | None,
) -> float | None:
    """Ratio of 90d to 20d volume. >3 = liquidity evaporating."""
    if vol_20d is None or vol_90d is None or vol_20d <= 0:
        return None
    return float(vol_90d / vol_20d)
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/models/test_liquidity_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/liquidity.py engine/tests/models/test_liquidity_profile.py
git commit -m "feat(engine): add position-sizing simulation and liquidity divergence detection"
```

---

### Task 3: Liquidity Filter Rewrite

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/liquidity.py`
- Modify: `engine/src/margin_engine/config/filter_config.py` (update LiquidityConfig)
- Modify: `engine/tests/scoring/filters/test_liquidity.py`

**Step 1: Update LiquidityConfig with new fields**

In `filter_config.py`, update `LiquidityConfig` to include:

```python
class PositionSizingConfig(BaseModel):
    target_position: int = 500_000
    max_participation_rate: float = 0.05
    max_days_to_fill: int = 5
    max_impact_bps: float = 50.0

class LiquidityConfig(BaseModel):
    # ... existing fields ...
    windows: list[int] = Field(default_factory=lambda: [20, 60, 90])
    divergence_max_ratio: float = 3.0
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
```

**Step 2: Write failing tests for the redesigned filter**

```python
def test_liquidity_position_sizing_fail(self):
    """Asset where position can't be filled in 5 days should FAIL."""
    # $500K position at 5% of $1M daily vol = 10 days > 5 max
    profile = _make_profile(market_cap=Decimal("5_000_000_000"))
    bars = _make_bars(n=100, avg_close=50.0, avg_volume=20_000)  # $1M daily
    config = LiquidityConfig()
    result = liquidity_check_v2(profile, bars, config=config)
    assert not result.passed
    assert "days_to_fill" in result.detail.lower()

def test_liquidity_divergence_fail(self):
    """20d vol < 90d vol / 3 → liquidity evaporating → FAIL."""
    profile = _make_profile(market_cap=Decimal("5_000_000_000"))
    bars = _make_divergent_bars(vol_90d=5_000_000, vol_20d=1_000_000)
    config = LiquidityConfig()
    result = liquidity_check_v2(profile, bars, config=config)
    assert not result.passed
    assert "divergence" in result.detail.lower()

def test_liquidity_all_criteria_pass(self):
    """Asset meeting all criteria should PASS with full metrics."""
    profile = _make_profile(market_cap=Decimal("50_000_000_000"))
    bars = _make_bars(n=100, avg_close=200.0, avg_volume=500_000)
    config = LiquidityConfig()
    result = liquidity_check_v2(profile, bars, config=config)
    assert result.passed
    assert result.computed_metrics is not None
    assert "median_dollar_volume_90d" in result.computed_metrics
```

**Step 3: Implement liquidity_check_v2**

Rewrite `liquidity.py` with the new function that:
1. Computes `LiquidityProfile` from bars
2. Checks market cap threshold (existing tiered logic)
3. Checks 90d median dollar volume vs tier threshold
4. Checks position sizing (days_to_fill ≤ max)
5. Checks divergence ratio (20d/90d ≤ max)
6. Checks sector eligibility and history
7. Returns `FilterResult` with all computed metrics

Keep the old `liquidity_check()` function as deprecated alias for backward compat.

**Step 4: Update pipeline to pass price bars to liquidity filter**

The pipeline function needs to accept `price_bars: list[PriceBar] | None` and pass them to the new liquidity check.

**Step 5: Run full filter test suite**

Run: `uv run pytest engine/tests/scoring/filters/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/liquidity.py engine/src/margin_engine/config/filter_config.py engine/tests/scoring/filters/test_liquidity.py engine/src/margin_engine/scoring/filters/pipeline.py
git commit -m "feat(engine): redesign liquidity filter with multi-window, position-sizing, divergence check"
```

---

## Phase 2: Engine — Health Filters + Beneish (Sections B, C)

### Task 4: FilterResult Enhancement + INCONCLUSIVE Verdict

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Modify: `engine/tests/models/test_scoring.py` (or relevant test file)

**Step 1: Write failing tests**

```python
def test_filter_verdict_inconclusive():
    """INCONCLUSIVE verdict for insufficient data."""
    r = FilterResult(name="beneish", passed=True, insufficient_data=True)
    assert r.verdict == FilterVerdict.INCONCLUSIVE

def test_filter_result_warning():
    """Warning flag for trend deterioration."""
    r = FilterResult(
        name="interest_coverage", passed=True, value=2.8, threshold=2.5,
        warning=True, warning_reason="ICR declined 25% over 3 years",
    )
    assert r.warning is True
    assert r.warning_reason is not None

def test_filter_result_computed_metrics():
    """Computed metrics dict for auditability."""
    r = FilterResult(
        name="liquidity", passed=True,
        computed_metrics={"median_dollar_volume_90d": 15_000_000, "days_to_fill": 1.5},
    )
    assert r.computed_metrics["days_to_fill"] == 1.5
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/models/test_scoring.py -k "inconclusive or warning or computed_metrics" -v`

**Step 3: Implement changes**

In `scoring.py`:

```python
class FilterVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"

class FilterResult(BaseModel):
    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    insufficient_data: bool = False
    missing_fields: list[str] | None = None
    warning: bool = False
    warning_reason: str | None = None
    computed_metrics: dict[str, float] | None = None

    @property
    def verdict(self) -> FilterVerdict:
        if self.insufficient_data:
            return FilterVerdict.INCONCLUSIVE
        return FilterVerdict.PASS if self.passed else FilterVerdict.FAIL
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -20`
Expected: PASS. Check that existing tests referencing `FilterVerdict` still work.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/
git commit -m "feat(engine): add INCONCLUSIVE verdict, warning flag, and computed_metrics to FilterResult"
```

---

### Task 5: FCF Distress Multi-Year Upgrade

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/fcf_distress.py`
- Modify: `engine/tests/scoring/filters/test_fcf_distress.py`

**Step 1: Write failing tests for multi-year FCF logic**

```python
def test_fcf_distress_3_of_5_positive(self):
    """3 of 5 years positive FCF should PASS."""
    history = _make_history_with_fcf([100, -50, 200, 150, -30])  # 3 positive
    result = fcf_distress_check_v2(history)
    assert result.passed

def test_fcf_distress_1_of_5_positive(self):
    """Only 1 of 5 years positive should FAIL."""
    history = _make_history_with_fcf([-100, -50, 200, -150, -30])  # 1 positive
    result = fcf_distress_check_v2(history)
    assert not result.passed

def test_fcf_distress_positive_trend_rescue(self):
    """Negative but improving for 2+ years → WARNING, not FAIL."""
    history = _make_history_with_fcf([-200, -150, -80, -30, -10])
    result = fcf_distress_check_v2(history)
    assert result.passed
    assert result.warning is True
    assert "trend" in result.warning_reason.lower()

def test_fcf_distress_cyclical_relaxed(self):
    """Energy sector uses 2-of-5 instead of 3-of-5."""
    history = _make_history_with_fcf([100, -50, -20, -150, 30], sector="energy")
    result = fcf_distress_check_v2(history, sector=GICSSector.ENERGY)
    assert result.passed  # 2 of 5 positive, meets cyclical threshold

def test_fcf_margin_floor(self):
    """Median FCF margin below -5% should FAIL."""
    history = _make_history_with_fcf_margin([-0.08, -0.10, -0.06, -0.07, -0.09])
    result = fcf_distress_check_v2(history)
    assert not result.passed
    assert "margin" in result.detail.lower()
```

**Step 2: Run to verify failure, implement, run tests, commit**

Pattern: rewrite `fcf_distress_check()` to accept `FinancialHistory | FinancialPeriod`. When `FinancialHistory` provided, apply multi-year rules. When only `FinancialPeriod`, fall back to single-period check (backward compat).

**Step 3: Commit**

```bash
git commit -m "feat(engine): upgrade FCF distress filter to multi-year with trend rescue"
```

---

### Task 6: Interest Coverage Multi-Year Upgrade

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/interest_coverage.py`
- Modify: `engine/tests/scoring/filters/test_interest_coverage.py`

**Step 1: Write failing tests**

```python
def test_icr_3yr_median(self):
    """Uses 3-year median, not spot value."""
    history = _make_icr_history([5.0, 2.5, 3.0])  # median = 3.0
    result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
    assert result.passed  # median 3.0 > 2.5 threshold
    assert result.computed_metrics["median_icr"] == pytest.approx(3.0)

def test_icr_trend_guard(self):
    """Current ICR >20% below median triggers warning."""
    history = _make_icr_history([4.0, 3.5, 2.5])  # median=3.5, current=2.5, decline=28%
    result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
    assert result.passed  # 2.5 == threshold, passes
    assert result.warning is True
    assert "deteriorat" in result.warning_reason.lower()

def test_icr_negative_ebit_auto_fail(self):
    """Negative EBIT with interest expense = auto FAIL."""
    history = _make_negative_ebit_history()
    result = interest_coverage_check_v2(history)
    assert not result.passed
    assert "negative ebit" in result.detail.lower()

def test_icr_expanded_sector_thresholds(self):
    """Tech requires ICR > 5.0, not the old 3.0."""
    history = _make_icr_history([4.5, 4.0, 4.8])  # median = 4.5
    result = interest_coverage_check_v2(history, sector=GICSSector.INFORMATION_TECHNOLOGY)
    assert not result.passed  # 4.5 < 5.0 new tech threshold
```

**Step 2: Implement, test, commit**

Same pattern: accept `FinancialHistory`, compute 3-year median ICR, apply expanded sector thresholds from config, add trend guard logic.

```bash
git commit -m "feat(engine): upgrade interest coverage filter to 3-year median with trend guard"
```

---

### Task 7: Current Ratio Multi-Year Upgrade

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/current_ratio.py`
- Modify: `engine/tests/scoring/filters/test_current_ratio.py`

**Step 1: Write failing tests for median + quick ratio rescue + trend guard**

```python
def test_cr_3yr_median(self):
    history = _make_cr_history([1.2, 0.9, 1.0])  # median = 1.0
    result = current_ratio_check_v2(history)
    assert result.passed  # 1.0 > 0.8

def test_cr_quick_ratio_rescue(self):
    """CR < threshold but quick ratio > 0.5 → PASS with warning."""
    history = _make_cr_history_with_quick([0.6, 0.7, 0.65], quick_ratios=[0.55, 0.6, 0.58])
    result = current_ratio_check_v2(history)
    assert result.passed
    assert result.warning is True
    assert "quick ratio" in result.warning_reason.lower()

def test_cr_3yr_decline_guard(self):
    """>30% decline over 3 years triggers warning."""
    history = _make_cr_history([1.5, 1.2, 0.95])  # 37% decline
    result = current_ratio_check_v2(history)
    assert result.passed  # median 1.2 > 0.8
    assert result.warning is True
    assert "decline" in result.warning_reason.lower()
```

**Step 2: Implement, test, commit**

```bash
git commit -m "feat(engine): upgrade current ratio filter to 3-year median with quick ratio rescue"
```

---

### Task 8: Beneish Multi-Period + INCONCLUSIVE

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/beneish.py`
- Modify: `engine/tests/scoring/filters/test_beneish.py`

**Step 1: Write failing tests**

```python
def test_beneish_multi_period_computation(self):
    """Computes M-Score for each consecutive period pair."""
    history = _make_beneish_history(n_periods=4)  # 3 consecutive pairs
    result = beneish_m_score_v2(history)
    assert len(result.historical_m_scores) == 3
    assert result.current_m_score is not None

def test_beneish_inconclusive_no_prior(self):
    """Zero computable pairs → INCONCLUSIVE, not silent PASS."""
    history = _make_beneish_history(n_periods=1)  # only 1 period, no prior
    result = beneish_m_score_v2(history)
    assert result.verdict == FilterVerdict.INCONCLUSIVE
    assert result.insufficient_data is True

def test_beneish_trend_detection(self):
    """Detects worsening M-Score trend."""
    history = _make_beneish_history_with_scores([-3.0, -2.5, -2.0])  # getting closer to -1.78
    result = beneish_m_score_v2(history)
    assert result.trend == "deteriorating"

def test_beneish_backward_compat_single_period(self):
    """Still works with single FinancialPeriod input."""
    period = _make_period_with_prior()
    result = beneish_m_score(period)  # old signature
    assert result.passed or not result.passed  # just verify it runs
```

**Step 2: Implement**

Refactor `beneish.py`:
- New `beneish_m_score_v2(history: FinancialHistory)` function
- Iterates consecutive period pairs, computes M-Score for each
- Returns `FilterResult` with `computed_metrics` containing `historical_m_scores`
- Old `beneish_m_score(period)` wraps v2 for backward compat

**Step 3: Run tests, commit**

```bash
git commit -m "feat(engine): Beneish multi-period computation with INCONCLUSIVE verdict and trend detection"
```

---

### Task 9: Update Filter Pipeline to Use v2 Filters

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/pipeline.py`
- Modify: `engine/tests/scoring/filters/test_pipeline.py`

**Step 1: Write test for pipeline with FinancialHistory**

```python
def test_pipeline_accepts_financial_history(self):
    """Pipeline should use multi-year checks when history is provided."""
    history = _make_full_history()
    profile = _make_profile()
    bars = _make_bars()
    result = run_elimination_filters(
        history=history,
        profile=profile,
        price_bars=bars,
    )
    assert len(result.results) >= 6
    # Verify Beneish used multi-period
    beneish = next(r for r in result.results if r.name == "beneish_m_score")
    assert beneish.computed_metrics is not None
```

**Step 2: Update pipeline signature**

```python
def run_elimination_filters(
    profile: AssetProfile,
    period: FinancialPeriod | None = None,
    history: FinancialHistory | None = None,
    price_bars: list[PriceBar] | None = None,
    config: FilterConfig | None = None,
) -> PipelineResult:
```

When `history` is provided, use v2 filters. When only `period`, fall back to v1 single-period filters.

**Step 3: Run full engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All pass.

**Step 4: Commit**

```bash
git commit -m "feat(engine): wire v2 multi-year filters into pipeline with FinancialHistory support"
```

---

## Phase 3: Engine — Risk Metrics (Section D)

### Task 10: Risk Metrics Module (Sharpe, Max Drawdown, Volatility)

**Files:**
- Create: `engine/src/margin_engine/scoring/risk_metrics.py`
- Create: `engine/tests/scoring/test_risk_metrics.py`

**Step 1: Write failing tests**

```python
"""Tests for risk metric computation."""

import pytest
from decimal import Decimal
from margin_engine.scoring.risk_metrics import (
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_volatility,
    compute_risk_metrics,
    RiskMetrics,
)


class TestSharpeRatio:
    def test_sharpe_basic(self):
        """Known returns → known Sharpe."""
        # 252 days of 0.04% daily return = ~10% annualized
        bars = _make_constant_return_bars(n=252, daily_return=0.0004)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043)
        # (10% - 4.3%) / low_vol → high Sharpe
        assert sharpe is not None
        assert sharpe > 0

    def test_sharpe_insufficient_bars(self):
        bars = _make_bars(n=100)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, min_bars=252)
        assert sharpe is None

    def test_sharpe_3y(self):
        bars = _make_constant_return_bars(n=756, daily_return=0.0003)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, window=756)
        assert sharpe is not None


class TestMaxDrawdown:
    def test_drawdown_known_sequence(self):
        """Price goes 100 → 120 → 80 → 90. Max drawdown = (80-120)/120 = -33.3%."""
        bars = _make_bars_from_prices([100, 110, 120, 100, 80, 90])
        dd = compute_max_drawdown(bars)
        assert dd == pytest.approx(-0.333, abs=0.01)

    def test_drawdown_no_decline(self):
        """Monotonically increasing → max drawdown = 0."""
        bars = _make_bars_from_prices([100, 101, 102, 103, 104])
        dd = compute_max_drawdown(bars)
        assert dd == 0.0


class TestVolatility:
    def test_volatility_known(self):
        bars = _make_constant_return_bars(n=252, daily_return=0.001)
        vol = compute_volatility(bars, window=252)
        assert vol is not None
        assert vol > 0

    def test_volatility_zero_for_constant_price(self):
        bars = _make_bars_from_prices([100.0] * 30)
        vol = compute_volatility(bars, window=20)
        assert vol == pytest.approx(0.0, abs=0.001)


class TestRiskMetricsBundle:
    def test_full_bundle(self):
        bars = _make_constant_return_bars(n=756, daily_return=0.0004)
        metrics = compute_risk_metrics(bars, risk_free_rate=0.043)
        assert isinstance(metrics, RiskMetrics)
        assert metrics.sharpe_1y is not None
        assert metrics.sharpe_3y is not None
        assert metrics.max_drawdown_1y is not None
        assert metrics.volatility_1y is not None
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/scoring/test_risk_metrics.py -v`

**Step 3: Implement**

```python
"""Risk metrics: Sharpe, Max Drawdown, Volatility from daily price bars."""

from __future__ import annotations
from decimal import Decimal
from math import sqrt
from statistics import mean, stdev
from pydantic import BaseModel
from margin_engine.models.financial import PriceBar


class RiskMetrics(BaseModel):
    sharpe_1y: float | None = None
    sharpe_3y: float | None = None
    max_drawdown_1y: float | None = None
    max_drawdown_3y: float | None = None
    volatility_1y: float | None = None
    volatility_3y: float | None = None
    sharpe_unavailable_reason: str | None = None
    drawdown_unavailable_reason: str | None = None
    volatility_unavailable_reason: str | None = None


def _daily_returns(bars: list[PriceBar], window: int) -> list[float] | None:
    sorted_bars = sorted(bars, key=lambda b: b.date)
    if len(sorted_bars) < window + 1:
        return None
    recent = sorted_bars[-(window + 1):]
    returns = []
    for i in range(1, len(recent)):
        prev = float(recent[i - 1].close)
        curr = float(recent[i].close)
        if prev > 0:
            returns.append(curr / prev - 1)
    return returns if len(returns) >= window else None


def compute_sharpe_ratio(
    bars: list[PriceBar],
    risk_free_rate: float = 0.043,
    window: int = 252,
    min_bars: int | None = None,
) -> float | None:
    min_required = min_bars or window
    rets = _daily_returns(bars, min_required)
    if rets is None or len(rets) < 2:
        return None
    ann_return = mean(rets) * 252
    ann_vol = stdev(rets) * sqrt(252)
    if ann_vol == 0:
        return None
    return (ann_return - risk_free_rate) / ann_vol


def compute_max_drawdown(
    bars: list[PriceBar],
    window: int | None = None,
) -> float | None:
    sorted_bars = sorted(bars, key=lambda b: b.date)
    if window:
        sorted_bars = sorted_bars[-window:]
    if len(sorted_bars) < 2:
        return None
    prices = [float(b.close) for b in sorted_bars]
    running_max = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > running_max:
            running_max = p
        dd = (p - running_max) / running_max if running_max > 0 else 0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def compute_volatility(
    bars: list[PriceBar],
    window: int = 252,
) -> float | None:
    rets = _daily_returns(bars, window)
    if rets is None or len(rets) < 2:
        return None
    return stdev(rets) * sqrt(252)


def compute_risk_metrics(
    bars: list[PriceBar],
    risk_free_rate: float = 0.043,
) -> RiskMetrics:
    n = len(bars)
    return RiskMetrics(
        sharpe_1y=compute_sharpe_ratio(bars, risk_free_rate, window=252),
        sharpe_3y=compute_sharpe_ratio(bars, risk_free_rate, window=756),
        max_drawdown_1y=compute_max_drawdown(bars, window=252),
        max_drawdown_3y=compute_max_drawdown(bars, window=756),
        volatility_1y=compute_volatility(bars, window=252),
        volatility_3y=compute_volatility(bars, window=756),
        sharpe_unavailable_reason=f"Need 252 trading days, have {n}" if n < 253 else None,
        drawdown_unavailable_reason=f"Need 20+ trading days, have {n}" if n < 20 else None,
        volatility_unavailable_reason=f"Need 20+ trading days, have {n}" if n < 20 else None,
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_risk_metrics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/risk_metrics.py engine/tests/scoring/test_risk_metrics.py
git commit -m "feat(engine): add risk metrics module — Sharpe, Max Drawdown, Volatility (1Y + 3Y)"
```

---

## Phase 4: Engine — Valuation Audit (Section F)

### Task 11: ValuationAudit Model

**Files:**
- Create: `engine/src/margin_engine/models/valuation_audit.py`
- Create: `engine/tests/models/test_valuation_audit.py`

**Step 1: Write failing test**

```python
def test_valuation_audit_round_trip():
    """Audit captures all method details and serializes to JSON."""
    audit = ValuationAudit(
        margin_invest_value=190.25,
        margin_of_safety=0.223,
        buy_price=148.10,
        sell_price=232.60,
        actual_price=185.0,
        methods=[
            MethodAudit(
                method="dcf",
                result_per_share=185.0,
                weight=0.35,
                renormalized_weight=0.35,
                included=True,
                exclusion_reason=None,
                inputs={"fcf": 110e9, "growth_rate": 0.05},
                intermediates={"pv_stage1": 1.2e12, "terminal_value": 2.8e12},
            ),
        ],
        mos_base=0.25,
        mos_cv=0.045,
        mos_adjustment=-0.0273,
        was_clamped=False,
        clamp_reason=None,
    )
    d = audit.model_dump(mode="json")
    restored = ValuationAudit.model_validate(d)
    assert restored.margin_invest_value == 190.25
    assert len(restored.methods) == 1
    assert restored.methods[0].inputs["fcf"] == 110e9
```

**Step 2: Implement model**

Create `valuation_audit.py` with `MethodAudit` and `ValuationAudit` as Pydantic models per the design doc.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(engine): add ValuationAudit model for auditable valuation breakdown"
```

---

### Task 12: Wire ValuationAudit Into Price Targets

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- Modify: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing test**

```python
def test_price_targets_returns_audit(self):
    """compute_price_targets should return a ValuationAudit."""
    result = compute_price_targets(
        period=healthy_period,
        profile=healthy_profile,
        price_bars=price_bars,
        conviction_level=ConvictionLevel.HIGH,
    )
    assert result.valuation_audit is not None
    assert len(result.valuation_audit.methods) > 0
    # Verify DCF audit has expected inputs
    dcf = next((m for m in result.valuation_audit.methods if m.method == "dcf"), None)
    if dcf and dcf.included:
        assert "fcf" in dcf.inputs
        assert "growth_rate" in dcf.inputs
```

**Step 2: Modify `compute_price_targets` to build audit**

Each valuation method (`_dcf_intrinsic_per_share`, etc.) returns both the result AND an `inputs`/`intermediates` dict. The orchestrator builds `MethodAudit` objects and attaches a `ValuationAudit` to the `PriceTargets` result.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(engine): wire ValuationAudit into price target computation"
```

---

### Task 13: Complete intrinsic_value → margin_invest_value Rename in Engine

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Modify: `engine/src/margin_engine/scoring/composite.py`
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- Modify: All engine test files referencing `intrinsic_value`

**Step 1: Grep for all occurrences**

Run: `rg "intrinsic_value" engine/src/ engine/tests/ --type py`

**Step 2: Rename field in CompositeScore**

`CompositeScore.intrinsic_value` → `CompositeScore.margin_invest_value`

Add a deprecated property for backward compat if needed by API layer:
```python
@property
def intrinsic_value(self) -> float | None:
    """Deprecated: use margin_invest_value."""
    return self.margin_invest_value
```

**Step 3: Update all tests, run full suite**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`

**Step 4: Commit**

```bash
git commit -m "refactor(engine): rename intrinsic_value to margin_invest_value across engine"
```

---

### Task 14: Golden Valuation Test Cases

**Files:**
- Create: `engine/tests/scoring/quantitative/test_valuation_golden.py`

**Step 1: Write golden tests per design doc**

```python
"""Golden test cases for valuation correctness — regression safety net."""

class TestValuationGolden:
    def test_normal_all_methods_valid(self):
        """All 4 methods valid → known MIV, MoS, Buy/Sell."""
        # Fixed inputs → deterministic outputs
        result = compute_price_targets(period=GOLDEN_PERIOD, ...)
        assert result.margin_invest_value == pytest.approx(EXPECTED_MIV, rel=1e-3)
        assert result.buy_price == pytest.approx(EXPECTED_BUY, rel=1e-3)
        assert result.sell_price == pytest.approx(EXPECTED_SELL, rel=1e-3)
        assert result.margin_of_safety == pytest.approx(EXPECTED_MOS, rel=1e-3)

    def test_negative_fcf_two_methods_only(self):
        """Negative FCF → DCF + EV/FCF return None → 2 methods with renormalized weights."""

    def test_high_leverage_acquirers_excluded(self):
        """Acquirer's implied equity ≤ 0 → excluded from consensus."""

    def test_cyclical_higher_mos(self):
        """Cyclical growth stage → base MoS 0.35, wider buy/sell spread."""

    def test_outlier_method_removed(self):
        """One method producing 15× median → excluded."""

    def test_deterministic_same_inputs_same_outputs(self):
        """Run twice with identical inputs → bit-identical results."""
        r1 = compute_price_targets(period=GOLDEN_PERIOD, ...)
        r2 = compute_price_targets(period=GOLDEN_PERIOD, ...)
        assert r1.margin_invest_value == r2.margin_invest_value
        assert r1.buy_price == r2.buy_price
```

**Step 2: Run tests, commit**

```bash
git commit -m "test(engine): add golden valuation test cases for regression coverage"
```

---

## Phase 5: API Layer (Sections D, E, F)

### Task 15: Risk Metrics API Endpoint

**Files:**
- Modify: `api/src/margin_api/routes/metrics.py` (or wherever metrics endpoint lives)
- Modify: `api/src/margin_api/schemas/metrics.py`
- Modify: `api/tests/`

**Step 1: Update metrics endpoint**

Wire `compute_risk_metrics()` from engine into the metrics API response:
- Fetch price bars for the ticker
- Compute `RiskMetrics`
- Map to `MetricStatus` objects (value + unavailable_reason)
- Remove `allocation_weight` from response
- Wire `price_upside` as "delta" metric

**Step 2: Update `InstitutionalMetricsResponse` schema**

```python
class InstitutionalMetricsResponse(BaseModel):
    sharpe_ratio: MetricStatus
    sharpe_ratio_3y: MetricStatus
    max_drawdown: MetricStatus
    max_drawdown_3y: MetricStatus
    volatility: MetricStatus
    volatility_3y: MetricStatus
    avg_profit_margin: MetricStatus
    delta: MetricStatus  # price_upside renamed
    risk_classification: str
```

**Step 3: Run API tests, commit**

```bash
git commit -m "feat(api): wire risk metrics into metrics endpoint, remove allocation, add delta"
```

---

### Task 16: Valuation Audit API Endpoint

**Files:**
- Modify: `api/src/margin_api/routes/scores.py`
- Create: `api/src/margin_api/schemas/valuation_audit.py`
- Create: `api/tests/test_valuation_audit.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_valuation_audit_returns_methods(client_with_scored_asset):
    resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "methods" in data
    assert "margin_invest_value" in data
    assert "margin_of_safety" in data
```

**Step 2: Implement endpoint**

Extract `valuation_audit` from the `score_detail` JSONB column of the latest `Score` row for the ticker. Return as `ValuationAuditResponse`.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(api): add GET /scores/{ticker}/valuation-audit endpoint"
```

---

### Task 17: score-universe CLI Command

**Files:**
- Modify: `api/src/margin_api/cli.py`
- Create: `api/tests/test_cli_score_universe.py`

**Step 1: Write test**

```python
@pytest.mark.asyncio
async def test_score_universe_creates_new_rows(seeded_db):
    """score-universe should create Score rows for all eligible assets."""
    from margin_api.cli import score_universe
    count = await score_universe(db=seeded_db)
    assert count > 0
    # Verify new rows exist
    rows = await seeded_db.execute(select(Score))
    assert len(rows.scalars().all()) >= count
```

**Step 2: Implement**

```python
@cli.command()
@click.option("--limit", default=None, type=int, help="Max assets to score")
async def score_universe(limit: int | None = None):
    """Score all eligible assets in one batch."""
    async with get_session() as session:
        assets = await session.execute(select(Asset).limit(limit))
        tickers = [a.ticker for a in assets.scalars().all()]

    scored, filtered, failed = 0, 0, 0
    for ticker in tickers:
        try:
            # Reuse existing score_tickers logic
            await score_tickers(tickers=[ticker])
            scored += 1
        except FilteredOutError:
            filtered += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to score {ticker}: {e}")

    click.echo(f"Scored: {scored} | Filtered: {filtered} | Failed: {failed}")
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(api): add score-universe CLI command for batch scoring"
```

---

## Phase 6: Frontend (Sections D, F, G)

### Task 18: KPI Grid Redesign

**Files:**
- Modify: `web/src/components/dashboard/panel/kpi-grid.tsx`
- Modify: `web/src/components/dashboard/panel/kpi-cell.tsx`
- Modify: `web/src/lib/api/types.ts`

**Step 1: Update types to match new API schema**

Update `InstitutionalMetricsResponse` to use new `MetricStatus` shape, remove `allocation_weight`, add `delta`, add `_3y` variants.

**Step 2: Update KpiCell to show unavailable reasons**

Add `unavailableReason` prop. When value is null and reason exists, render below the em-dash.

**Step 3: Update KpiGrid layout**

Remove Allocation cell, add Delta as prominent full-width cell at bottom. Map 1Y values as primary, 3Y on hover or secondary label.

**Step 4: Build and verify**

Run: `cd web && npm run build`

**Step 5: Commit**

```bash
git commit -m "feat(web): redesign KPI grid — remove Allocation, add Delta, show unavailable reasons"
```

---

### Task 19: INCONCLUSIVE Filter Badge

**Files:**
- Modify: `web/src/components/dashboard/panel/panel-filter-list.tsx`
- Modify: `web/src/components/dashboard/filter-list.tsx`

**Step 1: Add INCONCLUSIVE visual treatment**

When filter verdict is INCONCLUSIVE:
- Amber/yellow badge instead of green/red
- Show missing fields list
- Show "Cannot assess" message

**Step 2: Commit**

```bash
git commit -m "feat(web): add INCONCLUSIVE filter badge with amber visual treatment"
```

---

### Task 20: Valuation Audit Expandable Detail

**Files:**
- Modify: `web/src/components/dashboard/panel/panel-valuation.tsx`
- Create: `web/src/components/dashboard/panel/method-audit-detail.tsx`
- Modify: `web/src/lib/api/scores.ts` (add `getValuationAudit`)

**Step 1: Add API client function**

```typescript
export async function getValuationAudit(ticker: string): Promise<ValuationAudit> {
  return apiFetch(`/api/v1/scores/${ticker}/valuation-audit`)
}
```

**Step 2: Create MethodAuditDetail component**

Expandable panel showing inputs, intermediates, result, and inclusion status for a single valuation method.

**Step 3: Wire into PanelValuation method bars**

Clicking a method bar fetches audit data and expands the detail panel below it.

**Step 4: Commit**

```bash
git commit -m "feat(web): add expandable valuation audit detail in PanelValuation"
```

---

### Task 21: Chart Empty States + Tooltip Enrichment

**Files:**
- Modify: `web/src/components/dashboard/panel/score-chart.tsx`
- Modify: `web/src/components/dashboard/panel/price-target-chart.tsx`

**Step 1: Add empty state messages**

ScoreChart with < 2 points: "Score tracking begins after the next scoring run. Scores are computed weekly."

PriceTargetChart with no score history: "Buy/Sell targets will appear after 2+ scoring runs."

**Step 2: Enrich tooltips**

ScoreChart tooltip: date, score, delta, conviction, Q/V/M.
PriceTargetChart tooltip: date, price, buy/MIV/sell, zone label.

**Step 3: Build and verify**

Run: `cd web && npm run build`

**Step 4: Commit**

```bash
git commit -m "feat(web): improve chart empty states and tooltip detail"
```

---

### Task 22: Final Rename Sweep + Buy Below Removal

**Files:**
- All frontend files with "Intrinsic Value" or "intrinsic_value"
- Any remaining "Buy Below" standalone sections

**Step 1: Grep and replace**

```bash
rg "Intrinsic Value" web/src/ --type ts --type tsx
rg "intrinsic_value" web/src/ --type ts --type tsx
rg "Buy Below" web/src/ --type ts --type tsx
```

Replace all user-facing "Intrinsic Value" → "Margin Invest Value".
Remove any standalone "Buy Below" section (should already be in Price Ladder).

**Step 2: Build**

Run: `cd web && npm run build`

**Step 3: Commit**

```bash
git commit -m "refactor(web): complete Intrinsic Value → Margin Invest Value rename, remove Buy Below remnants"
```

---

## Verification Checklist

After all tasks are complete:

- [ ] `uv run pytest engine/tests/ -v` — all pass
- [ ] `uv run pytest api/tests/ -v` — all pass
- [ ] `cd web && npm run build` — no type errors
- [ ] No "Intrinsic Value" in codebase: `rg "Intrinsic Value" --type-add 'code:*.{py,ts,tsx}' -t code`
- [ ] No `intrinsic_value` in frontend: `rg "intrinsic_value" web/src/`
- [ ] `buy_price < margin_invest_value < sell_price` invariant in golden tests
- [ ] Score history endpoint returns multiple points after 2+ CLI runs
- [ ] KPI grid: no "–" for Sharpe/Vol/Drawdown on assets with 252+ price bars
- [ ] Avg Profit Margin populates for assets with income data
- [ ] Delta shows price-to-value gap
- [ ] Allocation cell removed
- [ ] INCONCLUSIVE badge renders for Beneish with insufficient data
- [ ] Filter warnings render for trend deterioration
- [ ] Valuation audit expandable shows inputs/intermediates
- [ ] `score-universe` CLI runs without error

---

## Task Dependency Graph

```
Task 1 (LiquidityProfile) → Task 2 (Position Sizing) → Task 3 (Liquidity Filter)
Task 4 (FilterResult enhancement) → Task 5, 6, 7, 8 (all v2 filters)
Task 5-8 (v2 filters) → Task 9 (Pipeline wiring)
Task 10 (Risk Metrics) — independent
Task 11 (ValuationAudit model) → Task 12 (Wire into price targets)
Task 13 (Rename) — can run after Task 12
Task 14 (Golden tests) — after Task 12 + 13
Task 10 → Task 15 (Risk Metrics API)
Task 11-12 → Task 16 (Valuation Audit API)
Task 9 → Task 17 (score-universe CLI)
Task 15 → Task 18 (KPI Grid frontend)
Task 4 → Task 19 (INCONCLUSIVE badge)
Task 16 → Task 20 (Audit expandable)
Task 17 → Task 21 (Chart empty states)
Task 13 → Task 22 (Rename sweep)
```

Parallelizable groups:
- Tasks 1-3 (liquidity) || Tasks 4-8 (health filters) — after Task 4
- Task 10 (risk metrics) || Task 11-12 (valuation audit) || Task 13 (rename)
- Tasks 15-17 (API) — after their engine deps
- Tasks 18-22 (frontend) — after their API deps
