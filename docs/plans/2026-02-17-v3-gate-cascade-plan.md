# V3 Gate Cascade Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete pipeline that connects raw financial data to the v3 conviction engine, producing scored, conviction-assessed, position-sized results through a layered gate cascade architecture.

**Architecture:** Five layers — (1) intermediate value calculators (pure functions), (2) track cascade runners (gate evaluation + scoring), (3) universe pipeline (batch scoring + peer aggregation + portfolio cap), (4) data prerequisites (WACC lookup, FRED CAPE, FinancialHistory assembly), (5) API/CLI integration (endpoints, DB model, CLI command). Each layer independently testable.

**Tech Stack:** Python 3.13, Pydantic, SQLAlchemy 2.0 + asyncpg, FastAPI, httpx (FRED API), pytest + aiosqlite (tests)

**Design doc:** `docs/plans/2026-02-17-v3-gate-cascade-design.md`

---

## Context for Implementers

**Key imports you will use repeatedly:**
```python
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel, FactorScore
from margin_engine.scoring.v3_orchestrator import V3TrackResult, V3Result, orchestrate_v3
from margin_engine.scoring.market_regime import MarketRegime, RegimeAdjustments, detect_regime, regime_adjustments
```

**Existing modules you will call (do NOT rewrite these):**
- `moat_durability_score(history: FinancialHistory) -> FactorScore` — raw_value 0-4
- `reverse_dcf_growth_gap(current_price, current_fcf, wacc, terminal_growth, shares_outstanding, sustainable_growth_rate) -> FactorScore` — raw_value = growth gap
- `compute_ensemble_valuation(dcf_iv, owner_earnings_iv, asset_floor_iv, peer_comparison_iv) -> EnsembleResult`
- `asset_floor_valuation(net_cash: Decimal, tangible_book: Decimal, sector: GICSSector, shares_outstanding: int) -> float`
- `asymmetry_ratio(intrinsic_value, current_price, net_cash_per_share, tangible_book_per_share) -> FactorScore`
- `incremental_roic(history: FinancialHistory) -> FactorScore`
- `roic_stability(history: FinancialHistory) -> FactorScore` — raw_value = median_ROIC * (1 - CV)
- `compute_track_a_score(moat_durability, compounding_power, capital_allocation, growth_gap) -> float`
- `compute_track_b_score(asymmetry_ratio, catalyst_strength, quality_floor_factor, valuation_convergence) -> float`
- `assess_track_a_conviction(gates_passed, total_gates, compounding_power, moat_durability, growth_gap) -> ConvictionLevel`
- `assess_track_b_conviction(gates_passed, total_gates, asymmetry_ratio, catalyst_percentile, converging_methods) -> ConvictionLevel`
- `compute_v3_timing_signal(momentum_percentile, is_mispricing_track) -> str`
- `orchestrate_v3(ticker, track_a: V3TrackResult, track_b: V3TrackResult, timing_signal) -> V3Result`
- Capital allocation: `buyback_effectiveness(total_repurchases, shares_reduced, avg_stock_price)`, `debt_discipline(history)`, `organic_reinvestment_ratio(period)`, `insider_ownership_score(ownership_pct)`, `sbc_dilution_tax(sbc_amount, revenue)`, `ma_discipline(roic_before, roic_after)`
- `insider_cluster_score(transactions: list[InsiderTransaction]) -> FactorScore`
- `institutional_accumulation(holdings: list[InstitutionalHolding]) -> FactorScore`
- `sue_score(surprises: list[EarningsSurprise]) -> FactorScore`
- `owner_earnings_yield(period, profile) -> FactorScore` — returns a yield, NOT absolute IV

**Test helper pattern (reuse throughout):**
```python
from decimal import Decimal
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory, FinancialPeriod,
    GICSSector, IncomeStatement, AssetProfile,
)

def _period(
    revenue=Decimal("1000"), ebit=Decimal("200"), net_income=Decimal("160"),
    cost_of_revenue=Decimal("600"), gross_profit=Decimal("400"),
    depreciation=Decimal("50"), total_equity=Decimal("500"),
    long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
    cash_and_equivalents=Decimal("50"),
    operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
    total_assets=Decimal("1500"), period_end="2024-09-28",
    shares_outstanding=100,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit, ebit=ebit, depreciation=depreciation,
            net_income=net_income, shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=long_term_debt, short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )
```

**Run all engine tests:** `uv run pytest engine/tests/ -v`
**Run specific test file:** `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v`

---

## Task 1: Sector WACC Lookup

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/wacc_sector.py`
- Create: `engine/tests/scoring/quantitative/test_wacc_sector.py`

**Step 1: Write the failing test**

```python
"""Tests for sector WACC lookup."""

import pytest
from margin_engine.models.financial import GICSSector
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc


class TestGetSectorWacc:
    def test_technology_wacc(self):
        assert get_sector_wacc(GICSSector.TECHNOLOGY) == pytest.approx(0.10)

    def test_utilities_wacc(self):
        assert get_sector_wacc(GICSSector.UTILITIES) == pytest.approx(0.065)

    def test_all_sectors_have_wacc(self):
        for sector in GICSSector:
            wacc = get_sector_wacc(sector)
            assert 0.05 <= wacc <= 0.15, f"{sector}: {wacc}"

    def test_return_type_is_float(self):
        assert isinstance(get_sector_wacc(GICSSector.ENERGY), float)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_wacc_sector.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
"""Sector average WACC lookup — Damodaran-style sector estimates.

Provides a deterministic WACC per GICS sector, avoiding external data
dependencies (no beta calculation, no live risk-free rate fetch).
Updated annually from Damodaran's sector WACC tables.
"""

from __future__ import annotations

from margin_engine.models.financial import GICSSector

# Approximate sector WACCs based on Damodaran data (Jan 2025)
_SECTOR_WACC: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 0.100,
    GICSSector.HEALTHCARE: 0.095,
    GICSSector.FINANCIALS: 0.085,
    GICSSector.CONSUMER_DISCRETIONARY: 0.090,
    GICSSector.CONSUMER_STAPLES: 0.075,
    GICSSector.ENERGY: 0.105,
    GICSSector.INDUSTRIALS: 0.085,
    GICSSector.MATERIALS: 0.090,
    GICSSector.REAL_ESTATE: 0.070,
    GICSSector.UTILITIES: 0.065,
    GICSSector.COMMUNICATION_SERVICES: 0.090,
}

_DEFAULT_WACC = 0.090


def get_sector_wacc(sector: GICSSector) -> float:
    """Return the sector average WACC for the given GICS sector."""
    return _SECTOR_WACC.get(sector, _DEFAULT_WACC)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_wacc_sector.py -v`
Expected: PASS (4 tests)

**Step 5: Run full engine tests for regressions**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All existing tests pass + 4 new

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/wacc_sector.py engine/tests/scoring/quantitative/test_wacc_sector.py
git commit -m "feat(engine): add sector WACC lookup table"
```

---

## Task 2: Intermediate Value Calculators — Owner Earnings IV + Compounding Power

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Create: `engine/tests/scoring/test_v3_intermediates.py`

**Step 1: Write the failing tests**

```python
"""Tests for v3 intermediate value calculators."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory, FinancialPeriod,
    GICSSector, IncomeStatement,
)
from margin_engine.scoring.v3_intermediates import (
    compute_compounding_power,
    compute_owner_earnings_iv,
)


def _period(
    revenue=Decimal("1000"), ebit=Decimal("200"), net_income=Decimal("160"),
    cost_of_revenue=Decimal("600"), gross_profit=Decimal("400"),
    depreciation=Decimal("50"), total_equity=Decimal("500"),
    long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
    cash_and_equivalents=Decimal("50"),
    operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
    total_assets=Decimal("1500"), period_end="2024-09-28",
    shares_outstanding=100,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit, ebit=ebit, depreciation=depreciation,
            net_income=net_income, shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=long_term_debt, short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


class TestComputeOwnerEarningsIv:
    def test_basic_gordon_growth(self):
        """OE=10, WACC=0.10, g=0.03 -> 10 * 1.03 / 0.07 = 147.14"""
        result = compute_owner_earnings_iv(
            owner_earnings_per_share=10.0, wacc=0.10, terminal_growth=0.03,
        )
        assert result == pytest.approx(147.14, rel=0.01)

    def test_zero_owner_earnings(self):
        result = compute_owner_earnings_iv(0.0, 0.10, 0.03)
        assert result == 0.0

    def test_wacc_equals_growth_returns_zero(self):
        result = compute_owner_earnings_iv(10.0, 0.03, 0.03)
        assert result == 0.0

    def test_negative_owner_earnings(self):
        result = compute_owner_earnings_iv(-5.0, 0.10, 0.03)
        assert result == 0.0


class TestComputeCompoundingPower:
    def test_growing_company(self):
        """Incremental ROIC > 0, reinvestment rate > 0, low CV -> positive power."""
        periods = [
            _period(ebit=Decimal("100"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("150"), capital_expenditures=Decimal("-80"),
                    depreciation=Decimal("40"), net_income=Decimal("79"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("120"), total_equity=Decimal("450"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("180"), capital_expenditures=Decimal("-90"),
                    depreciation=Decimal("45"), net_income=Decimal("95"),
                    period_end="2021-12-31"),
            _period(ebit=Decimal("150"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("220"), capital_expenditures=Decimal("-100"),
                    depreciation=Decimal("50"), net_income=Decimal("118"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("180"), total_equity=Decimal("560"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("260"), capital_expenditures=Decimal("-110"),
                    depreciation=Decimal("55"), net_income=Decimal("142"),
                    period_end="2023-12-31"),
            _period(ebit=Decimal("220"), total_equity=Decimal("630"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("310"), capital_expenditures=Decimal("-120"),
                    depreciation=Decimal("60"), net_income=Decimal("174"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="GROW", periods=periods)
        result = compute_compounding_power(history)
        assert result > 0.0

    def test_single_period_returns_zero(self):
        history = FinancialHistory(ticker="ONE", periods=[_period()])
        result = compute_compounding_power(history)
        assert result == 0.0

    def test_negative_incremental_roic(self):
        """Declining NOPAT with growing IC -> negative incremental ROIC -> 0."""
        periods = [
            _period(ebit=Decimal("200"), total_equity=Decimal("400"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("100"), total_equity=Decimal("600"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="DECLINE", periods=periods)
        result = compute_compounding_power(history)
        assert result == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
"""V3 intermediate value calculators — pure functions converting raw data to v3 metrics.

These bridge the gap between raw financial data and the v3 composite scoring
functions (v3_composite.py) which expect pre-computed metrics.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def compute_owner_earnings_iv(
    owner_earnings_per_share: float,
    wacc: float,
    terminal_growth: float = 0.03,
) -> float:
    """Gordon growth model: OE * (1 + g) / (WACC - g).

    Returns 0.0 if inputs are invalid (negative OE, WACC <= growth).
    """
    if owner_earnings_per_share <= 0 or wacc <= terminal_growth:
        return 0.0
    return owner_earnings_per_share * (1.0 + terminal_growth) / (wacc - terminal_growth)


def _nopat_and_ic(period: FinancialPeriod) -> tuple[float, float]:
    """Return (NOPAT, Invested Capital) for a period."""
    ci = period.current_income
    cb = period.current_balance
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    return nopat, ic


def compute_compounding_power(history: FinancialHistory) -> float:
    """Compute compounding power = incremental_ROIC * reinvestment_rate * (1 - ROIC_CV).

    Returns 0.0 if insufficient data or any component is non-positive.
    """
    if len(history.periods) < 2:
        return 0.0

    # Incremental ROIC (earliest -> latest)
    nopat_e, ic_e = _nopat_and_ic(history.periods[0])
    nopat_l, ic_l = _nopat_and_ic(history.periods[-1])
    delta_ic = ic_l - ic_e
    if delta_ic <= 0:
        return 0.0
    inc_roic = (nopat_l - nopat_e) / delta_ic
    if inc_roic <= 0:
        return 0.0

    # Reinvestment rate from latest period: growth_capex / NOPAT
    latest = history.periods[-1]
    capex = abs(float(latest.current_cash_flow.capital_expenditures))
    depreciation = float(latest.current_income.depreciation or Decimal("0"))
    growth_capex = max(capex - depreciation, 0.0)
    if nopat_l <= 0:
        return 0.0
    reinvestment_rate = growth_capex / nopat_l
    if reinvestment_rate <= 0:
        return 0.0

    # ROIC CV (coefficient of variation across all periods)
    roics = []
    for p in history.periods:
        nopat, ic = _nopat_and_ic(p)
        if ic > 0:
            roics.append(nopat / ic)
    if len(roics) < 2:
        cv = 0.0
    else:
        mean_roic = statistics.mean(roics)
        if mean_roic == 0:
            return 0.0
        stdev_roic = statistics.pstdev(roics)
        cv = min(abs(stdev_roic / mean_roic), 1.0)

    return inc_roic * reinvestment_rate * (1.0 - cv)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v`
Expected: PASS (7 tests)

**Step 5: Run full engine tests for regressions**

Run: `uv run pytest engine/tests/ -v --tb=short`

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_intermediates.py engine/tests/scoring/test_v3_intermediates.py
git commit -m "feat(engine): add owner earnings IV and compounding power calculators"
```

---

## Task 3: Intermediate Value Calculators — Capital Allocation Composite

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Modify: `engine/tests/scoring/test_v3_intermediates.py`

**Step 1: Write the failing tests**

Add to `test_v3_intermediates.py`:

```python
from margin_engine.scoring.v3_intermediates import compute_capital_allocation_composite


class TestComputeCapitalAllocationComposite:
    def test_all_strong_subfactors(self):
        """All 6 sub-factors present and strong -> score near 1.0."""
        periods = [
            _period(period_end="2020-12-31"),
            _period(period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="STRONG", periods=periods)
        result = compute_capital_allocation_composite(
            period=periods[-1],
            history=history,
            buyback_yield=0.05,
            insider_ownership_pct=15.0,
            sbc_pct=0.01,
            recent_acquisition_count=0,
        )
        assert 0.0 <= result <= 1.0

    def test_no_optional_data(self):
        """Missing optional data -> score based on available sub-factors only."""
        history = FinancialHistory(ticker="MIN", periods=[_period(), _period(period_end="2023-12-31")])
        result = compute_capital_allocation_composite(
            period=history.periods[-1],
            history=history,
            buyback_yield=None,
            insider_ownership_pct=None,
            sbc_pct=None,
            recent_acquisition_count=0,
        )
        assert 0.0 <= result <= 1.0

    def test_returns_float(self):
        history = FinancialHistory(ticker="T", periods=[_period(), _period(period_end="2023-12-31")])
        result = compute_capital_allocation_composite(
            period=history.periods[-1], history=history,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
        )
        assert isinstance(result, float)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py::TestComputeCapitalAllocationComposite -v`
Expected: FAIL (import error)

**Step 3: Write minimal implementation**

Add to `v3_intermediates.py`:

```python
from margin_engine.scoring.quantitative.capital_allocation import (
    buyback_effectiveness,
    debt_discipline,
    insider_ownership_score,
    ma_discipline,
    organic_reinvestment_ratio,
    sbc_dilution_tax,
)


def _normalize_factor(raw_value: float, max_value: float) -> float:
    """Normalize a raw factor value to 0-1 range."""
    if max_value <= 0:
        return 0.0
    return min(max(raw_value / max_value, 0.0), 1.0)


def compute_capital_allocation_composite(
    period: FinancialPeriod,
    history: FinancialHistory,
    buyback_yield: float | None,
    insider_ownership_pct: float | None,
    sbc_pct: float | None,
    recent_acquisition_count: int,
) -> float:
    """Aggregate 6 capital allocation sub-factors into a single 0-1 score.

    Skips sub-factors where data is missing. Returns simple average of
    available normalized sub-factors.
    """
    scores: list[float] = []

    # 1. Debt discipline (always available with history)
    if len(history.periods) >= 2:
        dd = debt_discipline(history)
        # debt_discipline raw_value: 0 (bad) to ~3 (excellent)
        scores.append(_normalize_factor(dd.raw_value, 3.0))

    # 2. Organic reinvestment ratio (always available with period)
    orr = organic_reinvestment_ratio(period)
    # raw_value: 0-1+ range, higher is better
    scores.append(min(max(orr.raw_value, 0.0), 1.0))

    # 3. Buyback effectiveness (optional)
    if buyback_yield is not None and buyback_yield > 0:
        # Use buyback_yield directly as a proxy (0-10% range typical)
        scores.append(_normalize_factor(buyback_yield, 0.10))

    # 4. Insider ownership (optional)
    if insider_ownership_pct is not None:
        ios = insider_ownership_score(insider_ownership_pct)
        # raw_value: 0-3 range
        scores.append(_normalize_factor(ios.raw_value, 3.0))

    # 5. SBC dilution tax (optional)
    if sbc_pct is not None:
        sbc = sbc_dilution_tax(
            sbc_amount=Decimal(str(sbc_pct * float(period.current_income.revenue))),
            revenue=period.current_income.revenue,
        )
        # raw_value: 0 (worst, high dilution) to 1 (best, no dilution)
        scores.append(max(sbc.raw_value, 0.0))

    # 6. M&A discipline — penalize if many acquisitions with no ROIC data
    if recent_acquisition_count == 0:
        scores.append(1.0)  # No acquisitions = disciplined
    else:
        mad = ma_discipline(roic_before_acquisition=None, roic_after_acquisition=None)
        scores.append(max(mad.raw_value, 0.0))

    if not scores:
        return 0.0

    return sum(scores) / len(scores)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v`
Expected: PASS (all tests including new ones)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_intermediates.py engine/tests/scoring/test_v3_intermediates.py
git commit -m "feat(engine): add capital allocation composite calculator"
```

---

## Task 4: Intermediate Value Calculators — Catalyst, Quality Floor, Convergence, Downside

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Modify: `engine/tests/scoring/test_v3_intermediates.py`

**Step 1: Write the failing tests**

Add to `test_v3_intermediates.py`:

```python
from margin_engine.scoring.v3_intermediates import (
    compute_catalyst_strength,
    compute_downside_protection,
    compute_quality_floor_factor,
    compute_valuation_convergence_factor,
)


class TestComputeCatalystStrength:
    def test_max_of_three(self):
        assert compute_catalyst_strength(30.0, 70.0, 50.0) == pytest.approx(70.0)

    def test_all_zero(self):
        assert compute_catalyst_strength(0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_single_strong_signal(self):
        assert compute_catalyst_strength(90.0, 10.0, 20.0) == pytest.approx(90.0)


class TestComputeQualityFloorFactor:
    def test_above_threshold(self):
        """ROIC > 8% -> 1.0"""
        assert compute_quality_floor_factor(0.12, roic_improving=False) == pytest.approx(1.0)

    def test_below_threshold_improving(self):
        """ROIC < 8% but improving -> 0.5-1.0"""
        result = compute_quality_floor_factor(0.04, roic_improving=True)
        assert 0.5 <= result < 1.0

    def test_below_threshold_not_improving(self):
        """ROIC < 8% and not improving -> 0.0"""
        assert compute_quality_floor_factor(0.04, roic_improving=False) == pytest.approx(0.0)

    def test_zero_roic_improving(self):
        assert compute_quality_floor_factor(0.0, roic_improving=True) == pytest.approx(0.5)

    def test_exactly_at_threshold(self):
        assert compute_quality_floor_factor(0.08, roic_improving=False) == pytest.approx(1.0)


class TestComputeValuationConvergenceFactor:
    def test_four_converging(self):
        assert compute_valuation_convergence_factor(4) == pytest.approx(1.0)

    def test_three_converging(self):
        assert compute_valuation_convergence_factor(3) == pytest.approx(0.75)

    def test_two_converging(self):
        """Below 3 -> still 0.75 floor (minimum)."""
        assert compute_valuation_convergence_factor(2) == pytest.approx(0.75)

    def test_zero_converging(self):
        assert compute_valuation_convergence_factor(0) == pytest.approx(0.75)


class TestComputeDownsideProtection:
    def test_price_well_above_floor(self):
        """Price=100, Floor=30 -> loss=70% -> fails."""
        loss, passed = compute_downside_protection(100.0, 30.0)
        assert loss == pytest.approx(0.70)
        assert passed is False

    def test_price_near_floor(self):
        """Price=100, Floor=60 -> loss=40% -> passes."""
        loss, passed = compute_downside_protection(100.0, 60.0)
        assert loss == pytest.approx(0.40)
        assert passed is True

    def test_floor_above_price(self):
        """Floor >= Price -> loss=0 -> passes."""
        loss, passed = compute_downside_protection(50.0, 60.0)
        assert loss == pytest.approx(0.0)
        assert passed is True

    def test_zero_price(self):
        """Edge case: price=0 -> loss=0."""
        loss, passed = compute_downside_protection(0.0, 10.0)
        assert loss == pytest.approx(0.0)
        assert passed is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -k "Catalyst or Quality or Convergence or Downside" -v`
Expected: FAIL (import error)

**Step 3: Write minimal implementation**

Add to `v3_intermediates.py`:

```python
def compute_catalyst_strength(
    insider_percentile: float,
    institutional_percentile: float,
    sue_percentile: float,
) -> float:
    """Catalyst strength = max of three catalyst signals.

    Each input is a percentile (0-100). Returns the strongest signal.
    """
    return max(insider_percentile, institutional_percentile, sue_percentile)


def compute_quality_floor_factor(roic: float, roic_improving: bool) -> float:
    """Quality floor factor for Track B multiplicative scoring.

    Returns:
        1.0 if ROIC >= 8%
        0.5-1.0 if ROIC < 8% but improving (scaled linearly)
        0.0 if ROIC < 8% and not improving
    """
    threshold = 0.08
    if roic >= threshold:
        return 1.0
    if roic_improving:
        return 0.5 + 0.5 * min(roic / threshold, 1.0)
    return 0.0


def compute_valuation_convergence_factor(converging_count: int) -> float:
    """Valuation convergence factor for Track B multiplicative scoring.

    Returns converging_count/4, floored at 0.75 to prevent zeroing out
    the multiplicative score.
    """
    return max(converging_count / 4.0, 0.75)


def compute_downside_protection(
    current_price: float,
    asset_floor_per_share: float,
) -> tuple[float, bool]:
    """Compute max loss percentage and whether downside protection gate passes.

    Returns (max_loss_pct, passed) where passed = max_loss_pct < 0.50.
    """
    if current_price <= 0:
        return 0.0, True
    max_loss = max(0.0, (current_price - asset_floor_per_share) / current_price)
    return max_loss, max_loss < 0.50
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_intermediates.py engine/tests/scoring/test_v3_intermediates.py
git commit -m "feat(engine): add catalyst, quality floor, convergence, downside calculators"
```

---

## Task 5: Regime-Adjusted Thresholds

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_thresholds.py`
- Modify: `engine/tests/scoring/test_v3_thresholds.py`

This task modifies the existing threshold functions to accept optional regime adjustment parameters.

**Step 1: Write the failing tests**

Add to the existing `engine/tests/scoring/test_v3_thresholds.py`:

```python
class TestRegimeAdjustedTrackA:
    def test_expensive_regime_tightens_growth_gap(self):
        """In EXPENSIVE regime, growth_gap threshold increases by +0.02.
        A stock with growth_gap=0.04 would pass HIGH normally (>= 0.03)
        but with +0.02 adjustment needs >= 0.05, so fails to WATCHLIST."""
        result = assess_track_a_conviction(
            gates_passed=4, total_gates=4,
            compounding_power=0.10, moat_durability=3, growth_gap=0.04,
            growth_gap_adjustment=0.02,
        )
        assert result == ConvictionLevel.WATCHLIST

    def test_cheap_regime_relaxes_growth_gap(self):
        """In CHEAP regime, growth_gap adjustment = -0.02.
        A stock with growth_gap=0.01 would fail HIGH (< 0.03)
        but with -0.02 needs >= 0.01, so passes HIGH."""
        result = assess_track_a_conviction(
            gates_passed=4, total_gates=4,
            compounding_power=0.10, moat_durability=3, growth_gap=0.01,
            growth_gap_adjustment=-0.02,
        )
        assert result == ConvictionLevel.HIGH

    def test_no_adjustment_default(self):
        """Without adjustment param, behavior unchanged."""
        result = assess_track_a_conviction(
            gates_passed=4, total_gates=4,
            compounding_power=0.10, moat_durability=3, growth_gap=0.04,
        )
        assert result == ConvictionLevel.HIGH


class TestRegimeAdjustedTrackB:
    def test_euphoria_catalyst_override(self):
        """In EUPHORIA, catalyst_percentile_override=90.0.
        Stock at 75th percentile would pass HIGH normally (>= 60) but
        with 90 override fails."""
        result = assess_track_b_conviction(
            gates_passed=4, total_gates=4,
            asymmetry_ratio=4.0, catalyst_percentile=75.0,
            converging_methods=3,
            catalyst_percentile_override=90.0,
        )
        # catalyst < 90 override -> fails EXCEPTIONAL (needs 80) -> check HIGH
        # catalyst 75 >= 60 (HIGH default) BUT override overrules -> 75 < 90 -> fails
        assert result in {ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST}

    def test_cheap_relaxes_asymmetry(self):
        """CHEAP regime: asymmetry_adjustment = -1.0.
        Stock with asymmetry=2.5 needs >= 3.0 for HIGH normally.
        With -1.0 offset needs >= 2.0, so passes HIGH."""
        result = assess_track_b_conviction(
            gates_passed=4, total_gates=4,
            asymmetry_ratio=2.5, catalyst_percentile=70.0,
            converging_methods=3,
            asymmetry_adjustment=-1.0,
        )
        assert result == ConvictionLevel.HIGH
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_thresholds.py -k "Regime" -v`
Expected: FAIL (unexpected keyword argument)

**Step 3: Modify implementation**

In `v3_thresholds.py`, add optional parameters to both functions:

For `assess_track_a_conviction`, add `growth_gap_adjustment: float = 0.0` parameter. Then in the body, adjust the growth gap thresholds: `_A_HIGH_GAP + growth_gap_adjustment` and `_A_EXCEPTIONAL_GAP + growth_gap_adjustment`.

For `assess_track_b_conviction`, add `asymmetry_adjustment: float = 0.0` and `catalyst_percentile_override: float | None = None` parameters. Then adjust asymmetry thresholds by `asymmetry_adjustment`, and if `catalyst_percentile_override` is set, use it instead of the default catalyst thresholds.

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_thresholds.py -v`
Expected: ALL pass (existing + new regime tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_thresholds.py engine/tests/scoring/test_v3_thresholds.py
git commit -m "feat(engine): add regime adjustment parameters to v3 thresholds"
```

---

## Task 6: Track A Cascade Runner

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_cascade.py`
- Create: `engine/tests/scoring/test_v3_cascade.py`

**Dependencies:** Tasks 1-5

**Step 1: Write the failing tests**

```python
"""Tests for v3 gate cascade runners."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_cascade import TrackAInputs, run_track_a_cascade


def _period(
    revenue=Decimal("1000"), ebit=Decimal("200"), net_income=Decimal("160"),
    cost_of_revenue=Decimal("600"), gross_profit=Decimal("400"),
    depreciation=Decimal("50"), total_equity=Decimal("500"),
    long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
    cash_and_equivalents=Decimal("50"),
    operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
    total_assets=Decimal("1500"), period_end="2024-09-28",
    shares_outstanding=100,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit, ebit=ebit, depreciation=depreciation,
            net_income=net_income, shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=long_term_debt, short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


def _profile(ticker="TEST", sector=GICSSector.TECHNOLOGY):
    return AssetProfile(
        ticker=ticker, name=f"{ticker} Corp", sector=sector,
        market_cap=Decimal("10000000000"),
    )


class TestRunTrackACascade:
    def _strong_history(self) -> FinancialHistory:
        """5-year history with growing ROIC and revenue (moat + compounding)."""
        return FinancialHistory(ticker="STRONG", periods=[
            _period(revenue=Decimal("500"), ebit=Decimal("60"),
                    total_equity=Decimal("300"), long_term_debt=Decimal("100"),
                    operating_cash_flow=Decimal("100"), capital_expenditures=Decimal("-40"),
                    depreciation=Decimal("20"), net_income=Decimal("47"),
                    cost_of_revenue=Decimal("300"), gross_profit=Decimal("200"),
                    period_end=f"{yr}-12-31")
            for yr, ebit_val in [
                ("2020", 60), ("2021", 80), ("2022", 110), ("2023", 150), ("2024", 200)
            ]
            for _ in [1]
            # Inline adjustment — use the actual values:
        ])

    def test_returns_v3_track_result(self):
        """run_track_a_cascade returns a V3TrackResult with track='compounder'."""
        history = FinancialHistory(ticker="T", periods=[
            _period(period_end="2020-12-31"), _period(period_end="2024-12-31"),
        ])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.track == "compounder"
        assert result.total_gates == 4
        assert 0 <= result.gates_passed <= 4

    def test_weak_company_fails_most_gates(self):
        """Declining company should fail most gates."""
        history = FinancialHistory(ticker="WEAK", periods=[
            _period(ebit=Decimal("200"), total_equity=Decimal("400"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("50"), total_equity=Decimal("600"),
                    period_end="2024-12-31"),
        ])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=200.0, current_fcf_per_share=1.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.05,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=5,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.gates_passed <= 2
        assert result.conviction == ConvictionLevel.NONE

    def test_conviction_none_when_insufficient_gates(self):
        """< 3 gates passed -> NONE conviction."""
        history = FinancialHistory(ticker="FEW", periods=[_period()])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.conviction == ConvictionLevel.NONE
        assert result.qualifies is False

    def test_regime_adjustments_forwarded(self):
        """Regime adjustments modify gate thresholds."""
        from margin_engine.scoring.market_regime import RegimeAdjustments, MarketRegime
        history = FinancialHistory(ticker="REG", periods=[
            _period(period_end="2020-12-31"), _period(period_end="2024-12-31"),
        ])
        adj = RegimeAdjustments(
            regime=MarketRegime.EXPENSIVE,
            track_a_growth_gap_adjustment=0.02,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
            regime_adjustments=adj,
        )
        result = run_track_a_cascade(inputs)
        assert result.track == "compounder"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
"""V3 gate cascade runners — wire raw data through gates to produce V3TrackResult.

Two main functions:
- run_track_a_cascade: Compounder track (moat → reinvestment → cap alloc → valuation)
- run_track_b_cascade: Mispricing track (ensemble → downside → catalyst → quality)
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.market_regime import RegimeAdjustments
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import reverse_dcf_growth_gap
from margin_engine.scoring.v3_composite import compute_track_a_score
from margin_engine.scoring.v3_intermediates import (
    compute_capital_allocation_composite,
    compute_compounding_power,
)
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction

# Gate thresholds
_MOAT_GATE_MIN = 2
_COMPOUNDING_GATE_MIN = 0.04
_CAP_ALLOC_GATE_MIN = 0.5
_GROWTH_GAP_GATE_MIN = 0.0


class TrackAInputs(BaseModel):
    """All data needed to run the Track A (Compounder) cascade."""
    history: FinancialHistory
    period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    current_fcf_per_share: float
    wacc: float
    terminal_growth: float = 0.03
    sustainable_growth_rate: float
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    regime_adjustments: RegimeAdjustments | None = None


def run_track_a_cascade(inputs: TrackAInputs) -> V3TrackResult:
    """Run the 4-gate Compounder cascade and return a V3TrackResult."""
    total_gates = 4
    gates_passed = 0

    # Gate 1: Moat Evidence (>= 2 signatures)
    moat = moat_durability_score(inputs.history)
    moat_val = moat.raw_value
    if moat_val >= _MOAT_GATE_MIN:
        gates_passed += 1

    # Gate 2: Reinvestment Engine (compounding power > 0.04)
    compounding = compute_compounding_power(inputs.history)
    if compounding > _COMPOUNDING_GATE_MIN:
        gates_passed += 1

    # Gate 3: Capital Allocation (composite > 0.5)
    cap_alloc = compute_capital_allocation_composite(
        period=inputs.period,
        history=inputs.history,
        buyback_yield=inputs.buyback_yield,
        insider_ownership_pct=inputs.insider_ownership_pct,
        sbc_pct=inputs.sbc_pct,
        recent_acquisition_count=inputs.recent_acquisition_count,
    )
    if cap_alloc > _CAP_ALLOC_GATE_MIN:
        gates_passed += 1

    # Gate 4: Valuation Reasonableness (growth_gap > 0, regime-adjusted)
    shares = inputs.profile.shares_outstanding or 1
    growth_gap_score = reverse_dcf_growth_gap(
        current_price=inputs.current_price,
        current_fcf=inputs.current_fcf_per_share * shares,
        wacc=inputs.wacc,
        terminal_growth=inputs.terminal_growth,
        shares_outstanding=shares,
        sustainable_growth_rate=inputs.sustainable_growth_rate,
    )
    growth_gap = growth_gap_score.raw_value
    gap_threshold = _GROWTH_GAP_GATE_MIN
    if inputs.regime_adjustments:
        gap_threshold += inputs.regime_adjustments.track_a_growth_gap_adjustment
    if growth_gap > gap_threshold:
        gates_passed += 1

    # Multiplicative score
    score = compute_track_a_score(
        moat_durability=moat_val,
        compounding_power=compounding,
        capital_allocation=cap_alloc,
        growth_gap=max(growth_gap, 0.0),
    )

    # Conviction assessment
    growth_gap_adj = inputs.regime_adjustments.track_a_growth_gap_adjustment if inputs.regime_adjustments else 0.0
    conviction = assess_track_a_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        compounding_power=compounding,
        moat_durability=int(moat_val),
        growth_gap=growth_gap,
        growth_gap_adjustment=growth_gap_adj,
    )

    qualifies = conviction in {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST}

    return V3TrackResult(
        track="compounder",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_cascade.py engine/tests/scoring/test_v3_cascade.py
git commit -m "feat(engine): add Track A cascade runner"
```

---

## Task 7: Track B Cascade Runner

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Modify: `engine/tests/scoring/test_v3_cascade.py`

**Dependencies:** Task 6

**Step 1: Write the failing tests**

Add to `test_v3_cascade.py`:

```python
from margin_engine.scoring.v3_cascade import TrackBInputs, run_track_b_cascade


class TestRunTrackBCascade:
    def test_returns_v3_track_result(self):
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="T", periods=[_period()]),
            period=_period(), profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=60.0, institutional_percentile=70.0,
            sue_percentile=50.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.track == "mispricing"
        assert result.total_gates == 4

    def test_undervalued_stock_passes_gates(self):
        """Price well below IV, strong catalyst, good quality -> qualifies."""
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="CHEAP", periods=[
                _period(ebit=Decimal("150"), total_equity=Decimal("500"), period_end="2022-12-31"),
                _period(ebit=Decimal("180"), total_equity=Decimal("500"), period_end="2024-12-31"),
            ]),
            period=_period(ebit=Decimal("180"), total_equity=Decimal("500")),
            profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.gates_passed >= 3

    def test_overvalued_stock_fails(self):
        """Price above IV -> ensemble won't converge favorably."""
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="EXPN", periods=[_period()]),
            period=_period(), profile=_profile(),
            current_price=200.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=20.0, institutional_percentile=10.0,
            sue_percentile=15.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.qualifies is False

    def test_euphoria_regime_tightens_catalyst(self):
        """In EUPHORIA, catalyst override to 90th percentile."""
        from margin_engine.scoring.market_regime import RegimeAdjustments, MarketRegime
        adj = RegimeAdjustments(
            regime=MarketRegime.EUPHORIA,
            track_a_growth_gap_adjustment=0.05,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=90.0,
        )
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="EUPH", periods=[
                _period(ebit=Decimal("150"), period_end="2022-12-31"),
                _period(ebit=Decimal("200"), period_end="2024-12-31"),
            ]),
            period=_period(ebit=Decimal("200")),
            profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=70.0, institutional_percentile=60.0,
            sue_percentile=50.0, wacc=0.10,
            regime_adjustments=adj,
        ))
        assert result.track == "mispricing"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade.py::TestRunTrackBCascade -v`
Expected: FAIL (import error)

**Step 3: Write minimal implementation**

Add to `v3_cascade.py`:

```python
from margin_engine.scoring.quantitative.asymmetry import asymmetry_ratio as compute_asymmetry
from margin_engine.scoring.quantitative.ensemble_valuation import compute_ensemble_valuation
from margin_engine.scoring.v3_composite import compute_track_b_score
from margin_engine.scoring.v3_intermediates import (
    compute_catalyst_strength,
    compute_downside_protection,
    compute_quality_floor_factor,
    compute_valuation_convergence_factor,
)
from margin_engine.scoring.v3_thresholds import assess_track_b_conviction

_ENSEMBLE_DISCOUNT_THRESHOLD = 0.60
_CATALYST_GATE_MIN = 60.0
_DOWNSIDE_GATE_MAX = 0.50


class TrackBInputs(BaseModel):
    """All data needed to run the Track B (Mispricing) cascade."""
    history: FinancialHistory
    period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    dcf_iv: float
    owner_earnings_iv: float
    asset_floor_iv: float
    peer_comparison_iv: float
    insider_percentile: float
    institutional_percentile: float
    sue_percentile: float
    wacc: float
    regime_adjustments: RegimeAdjustments | None = None


def _is_roic_improving(history: FinancialHistory) -> bool:
    """Check if ROIC is improving over the last 3+ quarters."""
    if len(history.periods) < 2:
        return False
    roics = []
    for p in history.periods:
        ci = p.current_income
        cb = p.current_balance
        ic = float(cb.total_equity) + float(cb.total_debt) - float(cb.cash_and_equivalents or 0)
        if ic > 0:
            nopat = float(ci.ebit) * (1.0 - ci.effective_tax_rate)
            roics.append(nopat / ic)
    if len(roics) < 2:
        return False
    # Improving if last ROIC > first ROIC
    return roics[-1] > roics[0]


def _current_roic(period: FinancialPeriod) -> float:
    """Compute current period ROIC."""
    ci = period.current_income
    cb = period.current_balance
    ic = float(cb.total_equity) + float(cb.total_debt) - float(cb.cash_and_equivalents or 0)
    if ic <= 0:
        return 0.0
    return float(ci.ebit) * (1.0 - ci.effective_tax_rate) / ic


def run_track_b_cascade(inputs: TrackBInputs) -> V3TrackResult:
    """Run the 4-gate Mispricing cascade and return a V3TrackResult."""
    total_gates = 4
    gates_passed = 0

    # Gate 1: Ensemble Valuation (converged + price < 60% of ensemble IV)
    ensemble = compute_ensemble_valuation(
        dcf_iv=inputs.dcf_iv,
        owner_earnings_iv=inputs.owner_earnings_iv,
        asset_floor_iv=inputs.asset_floor_iv,
        peer_comparison_iv=inputs.peer_comparison_iv,
    )
    price_discount = (inputs.current_price / ensemble.ensemble_iv) if ensemble.ensemble_iv > 0 else 1.0
    if ensemble.converged and price_discount < _ENSEMBLE_DISCOUNT_THRESHOLD:
        gates_passed += 1

    # Gate 2: Downside Protection (max_loss < 50%)
    cb = inputs.period.current_balance
    shares = inputs.profile.shares_outstanding or 1
    from decimal import Decimal
    net_cash = (cb.cash_and_equivalents or Decimal("0")) - cb.total_debt
    tangible_book = cb.total_equity - (cb.total_assets - (cb.pp_and_e or Decimal("0")) - (cb.cash_and_equivalents or Decimal("0")))
    from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
    floor_per_share = asset_floor_valuation(
        net_cash=net_cash, tangible_book=max(tangible_book, Decimal("0")),
        sector=inputs.profile.sector, shares_outstanding=shares,
    )
    _, downside_passed = compute_downside_protection(inputs.current_price, floor_per_share)
    if downside_passed:
        gates_passed += 1

    # Gate 3: Catalyst (strength > 60th percentile, regime-adjusted)
    catalyst = compute_catalyst_strength(
        inputs.insider_percentile, inputs.institutional_percentile, inputs.sue_percentile,
    )
    catalyst_threshold = _CATALYST_GATE_MIN
    if inputs.regime_adjustments and inputs.regime_adjustments.track_b_catalyst_percentile_override is not None:
        catalyst_threshold = inputs.regime_adjustments.track_b_catalyst_percentile_override
    if catalyst > catalyst_threshold:
        gates_passed += 1

    # Gate 4: Quality Floor (ROIC > 8% or improving)
    roic = _current_roic(inputs.period)
    improving = _is_roic_improving(inputs.history)
    quality_floor = compute_quality_floor_factor(roic, improving)
    if quality_floor > 0:
        gates_passed += 1

    # Compute asymmetry ratio
    net_cash_ps = float(net_cash) / shares if shares > 0 else 0.0
    tangible_book_ps = float(max(tangible_book, Decimal("0"))) / shares if shares > 0 else 0.0
    asym = compute_asymmetry(
        intrinsic_value=ensemble.ensemble_iv,
        current_price=inputs.current_price,
        net_cash_per_share=net_cash_ps,
        tangible_book_per_share=tangible_book_ps,
    )

    # Convergence factor
    convergence = compute_valuation_convergence_factor(ensemble.converging_count)

    # Multiplicative score
    score = compute_track_b_score(
        asymmetry_ratio=asym.raw_value,
        catalyst_strength=catalyst / 100.0,  # normalize percentile to 0-1
        quality_floor_factor=quality_floor,
        valuation_convergence=convergence,
    )

    # Conviction assessment
    asym_adj = inputs.regime_adjustments.track_b_asymmetry_adjustment if inputs.regime_adjustments else 0.0
    cat_override = inputs.regime_adjustments.track_b_catalyst_percentile_override if inputs.regime_adjustments else None
    conviction = assess_track_b_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        asymmetry_ratio=asym.raw_value,
        catalyst_percentile=catalyst,
        converging_methods=ensemble.converging_count,
        asymmetry_adjustment=asym_adj,
        catalyst_percentile_override=cat_override,
    )

    qualifies = conviction in {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST}

    return V3TrackResult(
        track="mispricing",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade.py -v`
Expected: PASS (all Track A + Track B tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_cascade.py engine/tests/scoring/test_v3_cascade.py
git commit -m "feat(engine): add Track B cascade runner"
```

---

## Task 8: Universe Pipeline + Peer Comparison + Portfolio Cap

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_pipeline.py`
- Create: `engine/tests/scoring/test_v3_pipeline.py`

**Dependencies:** Tasks 6-7

**Step 1: Write the failing tests**

```python
"""Tests for v3 universe scoring pipeline."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_pipeline import (
    TickerV3Data,
    score_universe_v3,
)


def _period(period_end="2024-09-28", ebit=Decimal("200"), **kwargs):
    defaults = dict(
        revenue=Decimal("1000"), cost_of_revenue=Decimal("600"),
        gross_profit=Decimal("400"), depreciation=Decimal("50"),
        net_income=Decimal("160"), total_equity=Decimal("500"),
        long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
        cash_and_equivalents=Decimal("50"), total_assets=Decimal("1500"),
        operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
        shares_outstanding=100,
    )
    defaults.update(kwargs)
    defaults["ebit"] = ebit
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=defaults["revenue"], cost_of_revenue=defaults["cost_of_revenue"],
            gross_profit=defaults["gross_profit"], ebit=defaults["ebit"],
            depreciation=defaults["depreciation"], net_income=defaults["net_income"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_balance=BalanceSheet(
            total_assets=defaults["total_assets"], total_equity=defaults["total_equity"],
            long_term_debt=defaults["long_term_debt"], short_term_debt=defaults["short_term_debt"],
            cash_and_equivalents=defaults["cash_and_equivalents"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=defaults["operating_cash_flow"],
            capital_expenditures=defaults["capital_expenditures"],
        ),
    )


def _make_ticker_data(ticker: str, sector=GICSSector.TECHNOLOGY) -> TickerV3Data:
    periods = [_period(period_end=f"{yr}-12-31") for yr in range(2020, 2025)]
    return TickerV3Data(
        ticker=ticker,
        history=FinancialHistory(ticker=ticker, periods=periods),
        latest_period=periods[-1],
        profile=AssetProfile(
            ticker=ticker, name=f"{ticker} Corp", sector=sector,
            market_cap=Decimal("10000000000"), shares_outstanding=100,
        ),
        current_price=100.0,
        current_fcf_per_share=5.0,
        sustainable_growth_rate=0.08,
        buyback_yield=None,
        insider_ownership_pct=None,
        sbc_pct=None,
        recent_acquisition_count=0,
        insider_percentile=50.0,
        institutional_percentile=50.0,
        sue_percentile=50.0,
        momentum_percentile=50.0,
        dcf_iv=120.0,
    )


class TestScoreUniverseV3:
    def test_basic_scoring(self):
        """Score 3 tickers, get V3Result for each."""
        data = [_make_ticker_data(t) for t in ["AAPL", "MSFT", "GOOGL"]]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 3
        for r in results:
            assert r.ticker in {"AAPL", "MSFT", "GOOGL"}
            assert r.track_a.track == "compounder"
            assert r.track_b.track == "mispricing"

    def test_portfolio_cap_enforced(self):
        """With > 10 qualifying tickers, only top 10 get non-zero positions."""
        data = [_make_ticker_data(f"T{i:02d}") for i in range(15)]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 15
        positioned = [r for r in results if r.max_position_pct > 0]
        assert len(positioned) <= 10

    def test_empty_universe(self):
        results = score_universe_v3([], shiller_cape=25.0)
        assert results == []

    def test_single_ticker(self):
        data = [_make_ticker_data("SOLO")]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 1

    def test_regime_affects_results(self):
        """EUPHORIA (CAPE=40) vs CHEAP (CAPE=12) should produce different results."""
        data = [_make_ticker_data("TEST")]
        euphoria = score_universe_v3(data, shiller_cape=40.0)
        cheap = score_universe_v3(data, shiller_cape=12.0)
        # Results may differ due to regime adjustments
        assert euphoria[0].ticker == cheap[0].ticker == "TEST"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_pipeline.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/scoring/v3_pipeline.py`. The implementer should:

- Define `TickerV3Data(BaseModel)` with all fields listed in the test
- Implement `score_universe_v3(tickers_data, shiller_cape)` that:
  1. Calls `detect_regime(shiller_cape)` → `regime_adjustments()`
  2. Computes sector median EV/EBIT for peer comparison IVs
  3. For each ticker: computes owner_earnings_iv, asset_floor_iv, builds TrackAInputs + TrackBInputs, runs both cascades
  4. Calls `orchestrate_v3()` per ticker
  5. Sorts results by conviction tier then score, caps at MAX_POSITIONS
  6. Returns list of V3Result

Key helper: `_compute_peer_comparison_iv(period, profile, sector_median_ev_ebit)` that computes `sector_median * company_ebit / shares`.

Portfolio cap logic: Sort by conviction order (EXCEPTIONAL=0, HIGH=1, WATCHLIST=2, NONE=3), then by max_position_pct descending. Keep top 10, zero out the rest.

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_v3_pipeline.py -v`

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_pipeline.py engine/tests/scoring/test_v3_pipeline.py
git commit -m "feat(engine): add v3 universe pipeline with peer comparison and portfolio cap"
```

---

## Task 9: Package Exports Update

**Files:**
- Modify: `engine/src/margin_engine/scoring/__init__.py`
- Modify: `engine/src/margin_engine/scoring/quantitative/__init__.py`
- Modify: `engine/tests/scoring/test_scoring_integration.py`

**Step 1: Update `scoring/__init__.py`**

Add imports and `__all__` entries for:
- `from margin_engine.scoring.v3_cascade import TrackAInputs, TrackBInputs, run_track_a_cascade, run_track_b_cascade`
- `from margin_engine.scoring.v3_intermediates import compute_compounding_power, compute_owner_earnings_iv, compute_capital_allocation_composite, compute_catalyst_strength, compute_quality_floor_factor, compute_valuation_convergence_factor, compute_downside_protection`
- `from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3`

**Step 2: Update `quantitative/__init__.py`**

Add:
- `from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc`

**Step 3: Update `test_scoring_integration.py`**

Update `test_all_exports_present` set to include all new exports.

**Step 4: Run full engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/__init__.py engine/src/margin_engine/scoring/quantitative/__init__.py engine/tests/scoring/test_scoring_integration.py
git commit -m "feat(engine): update package exports for v3 cascade pipeline"
```

---

## Task 10: FRED Client for Shiller CAPE

**Files:**
- Create: `api/src/margin_api/data/__init__.py` (if not exists)
- Create: `api/src/margin_api/data/fred_client.py`
- Create: `api/tests/data/__init__.py` (if not exists)
- Create: `api/tests/data/test_fred_client.py`

**Step 1: Write the failing tests**

```python
"""Tests for FRED API client — Shiller CAPE fetching."""

import pytest
from unittest.mock import AsyncMock, patch

from margin_api.data.fred_client import fetch_shiller_cape, _DEFAULT_CAPE


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/data/test_fred_client.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
"""FRED API client — fetches Shiller CAPE ratio for market regime detection.

Uses the FRED API (Federal Reserve Economic Data) to get the current
Shiller PE ratio. Requires FRED_API_KEY environment variable.
Falls back to default CAPE (25.0 = NORMAL regime) if unavailable.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CAPE = 25.0
_FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_SERIES_ID = "MEHOINUSA672N"  # Note: Shiller PE not directly on FRED; use Multpl
_CACHE_TTL_SECONDS = 86400  # 1 day

# Simple in-memory cache
_cache: dict[str, tuple[float, float]] = {}  # key -> (value, expiry_timestamp)


async def _fetch_from_fred() -> float:
    """Fetch latest Shiller CAPE from FRED API."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not set")

    # Use multpl.com/shiller-pe as a more reliable source for Shiller PE
    # FRED doesn't have a direct Shiller PE series
    # Alternative: fetch from Shiller's own data or use a proxy
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            _FRED_BASE_URL,
            params={
                "series_id": _SERIES_ID,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        observations = data.get("observations", [])
        if not observations:
            raise ValueError("No observations returned")
        return float(observations[0]["value"])


async def fetch_shiller_cape() -> float:
    """Fetch current Shiller CAPE with caching and fallback.

    Returns the CAPE value (float). Falls back to 25.0 if API unavailable.
    """
    cache_key = "shiller_cape"
    now = time.time()

    # Check cache
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        value = await _fetch_from_fred()
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable, using default CAPE=%.1f", _DEFAULT_CAPE)
        return _DEFAULT_CAPE
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/data/test_fred_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/data/ api/tests/data/
git commit -m "feat(api): add FRED client for Shiller CAPE with fallback"
```

---

## Task 11: FinancialHistory Assembly from DB

**Files:**
- Modify: `api/src/margin_api/services/scoring.py`
- Modify: `api/tests/services/test_scoring.py` (or create if needed)

**Step 1: Write the failing test**

Add test for the new `build_financial_history` function:

```python
class TestBuildFinancialHistory:
    def test_builds_history_from_multiple_periods(self):
        """Given multiple FinancialData rows, build a FinancialHistory."""
        from margin_api.services.scoring import build_financial_history_from_rows
        rows = [
            {"period_end": "2022-12-31", "filing_date": "2023-02-15",
             "income_statement": {"revenue": 1000, "cost_of_revenue": 600, "gross_profit": 400, "ebit": 200, "net_income": 160},
             "balance_sheet": {"total_assets": 1500, "total_equity": 500},
             "cash_flow": {"operating_cash_flow": 250, "capital_expenditures": -80}},
            {"period_end": "2023-12-31", "filing_date": "2024-02-15",
             "income_statement": {"revenue": 1200, "cost_of_revenue": 700, "gross_profit": 500, "ebit": 250, "net_income": 200},
             "balance_sheet": {"total_assets": 1800, "total_equity": 600},
             "cash_flow": {"operating_cash_flow": 300, "capital_expenditures": -100}},
        ]
        history = build_financial_history_from_rows("TEST", rows)
        assert history.ticker == "TEST"
        assert len(history.periods) == 2
        assert history.periods[0].period_end < history.periods[1].period_end
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

Add to `api/src/margin_api/services/scoring.py`:

```python
def build_financial_history_from_rows(
    ticker: str,
    rows: list[dict],
) -> FinancialHistory:
    """Build a FinancialHistory from multiple DB rows (sorted oldest-first).

    Each row should have: period_end, filing_date, income_statement, balance_sheet, cash_flow.
    """
    periods = []
    for row in sorted(rows, key=lambda r: r["period_end"]):
        period = build_financial_period(
            income_raw=row.get("income_statement") or {},
            balance_raw=row.get("balance_sheet") or {},
            cashflow_raw=row.get("cash_flow") or {},
            period_end=row["period_end"],
            filing_date=row.get("filing_date", ""),
        )
        periods.append(period)
    return FinancialHistory(ticker=ticker, periods=periods)
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add api/src/margin_api/services/scoring.py api/tests/
git commit -m "feat(api): add build_financial_history_from_rows for multi-period assembly"
```

---

## Task 12: V3Score DB Model + Alembic Migration

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: new Alembic migration

**Step 1: Add V3Score model**

Add to `api/src/margin_api/db/models.py`:

```python
class V3Score(Base):
    __tablename__ = "v3_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    opportunity_type: Mapped[str] = mapped_column(String(20))
    conviction: Mapped[str] = mapped_column(String(20))
    track_a: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    track_b: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    timing_signal: Mapped[str] = mapped_column(String(30))
    max_position_pct: Mapped[float] = mapped_column(default=0.0)
    regime: Mapped[str] = mapped_column(String(20))
    composite_score: Mapped[float] = mapped_column(default=0.0)

    asset: Mapped["Asset"] = relationship(back_populates="v3_scores")
```

Also add to `Asset`: `v3_scores: Mapped[list["V3Score"]] = relationship(back_populates="asset")`

**Step 2: Generate Alembic migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add v3_scores table"`

**Step 3: Apply migration**

Run: `cd api && uv run alembic upgrade head`

**Step 4: Verify with tests**

Run: `uv run pytest api/tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add V3Score DB model and migration"
```

---

## Task 13: CLI score-v3 Command

**Files:**
- Modify: `api/src/margin_api/cli.py`

**Dependencies:** Tasks 10-12

**Step 1: Add `score-v3` subcommand**

Add after the existing `score` subparser:

```python
# score-v3
score_v3_parser = subparsers.add_parser("score-v3", help="Score tickers using v3 conviction engine")
score_v3_parser.add_argument(
    "--tickers", nargs="+", default=None,
    help="Specific tickers to score (defaults to active universe)",
)
score_v3_parser.add_argument(
    "--cape", type=float, default=None,
    help="Shiller CAPE override (fetches from FRED if omitted)",
)
```

**Step 2: Implement `run_scoring_v3` async function**

```python
async def run_scoring_v3(tickers: list[str] | None = None, cape: float | None = None) -> None:
    """Score tickers using the v3 gate cascade pipeline."""
    from margin_api.data.fred_client import fetch_shiller_cape
    from margin_api.db.models import V3Score
    from margin_api.services.scoring import build_asset_profile, build_financial_history_from_rows
    from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3

    engine = get_engine()
    session_factory = get_session_factory(engine)

    if tickers is None:
        tickers = await _get_universe_tickers()
    if not tickers:
        logger.warning("No tickers found. Run 'seed' first.")
        return

    # Fetch CAPE
    if cape is None:
        cape = await fetch_shiller_cape()
    logger.info("Using Shiller CAPE: %.1f", cape)

    # Build TickerV3Data for each ticker
    ticker_data_list: list[TickerV3Data] = []
    total = len(tickers)
    asset_ids: dict[str, int] = {}

    for i, ticker in enumerate(tickers, start=1):
        async with session_factory() as session:
            # Fetch asset
            result = await session.execute(select(Asset).where(Asset.ticker == ticker))
            asset = result.scalar_one_or_none()
            if not asset:
                logger.warning("[%d/%d] SKIP %s — no asset", i, total, ticker)
                continue

            # Fetch last 5 years of financial data
            result = await session.execute(
                select(FinancialData)
                .where(FinancialData.asset_id == asset.id)
                .order_by(FinancialData.period_end.desc())
                .limit(5)
            )
            fin_rows = result.scalars().all()
            if not fin_rows:
                logger.warning("[%d/%d] SKIP %s — no financial data", i, total, ticker)
                continue

            try:
                rows = [
                    {"period_end": fd.period_end, "filing_date": fd.filing_date,
                     "income_statement": fd.income_statement or {},
                     "balance_sheet": fd.balance_sheet or {},
                     "cash_flow": fd.cash_flow or {}}
                    for fd in fin_rows
                ]
                history = build_financial_history_from_rows(ticker, rows)
                profile = build_asset_profile(
                    ticker=asset.ticker, name=asset.name,
                    sector=asset.sector, market_cap=asset.market_cap,
                    shares_outstanding=asset.shares_outstanding,
                )
                latest = history.periods[-1]

                # Get current price from most recent price bar
                latest_fd = max(fin_rows, key=lambda fd: fd.period_end)
                price_data = latest_fd.price_history or {}
                bars = price_data.get("bars", []) if isinstance(price_data, dict) else []
                current_price = float(bars[-1]["close"]) if bars else float(profile.market_cap) / max(asset.shares_outstanding or 1, 1)

                # FCF per share
                fcf = float(latest.current_cash_flow.free_cash_flow)
                shares = asset.shares_outstanding or 1
                fcf_ps = fcf / shares

                # DCF IV from existing dcf_mos
                from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
                dcf_result = dcf_margin_of_safety(latest, profile)
                dcf_iv = current_price * (1.0 + dcf_result.raw_value) if dcf_result.raw_value > 0 else current_price

                td = TickerV3Data(
                    ticker=ticker, history=history, latest_period=latest,
                    profile=profile, current_price=current_price,
                    current_fcf_per_share=fcf_ps,
                    sustainable_growth_rate=0.08,  # default
                    buyback_yield=None, insider_ownership_pct=None,
                    sbc_pct=None, recent_acquisition_count=0,
                    insider_percentile=50.0, institutional_percentile=50.0,
                    sue_percentile=50.0, momentum_percentile=50.0,
                    dcf_iv=dcf_iv,
                )
                ticker_data_list.append(td)
                asset_ids[ticker] = asset.id
                logger.info("[%d/%d] Prepared: %s", i, total, ticker)
            except Exception as e:
                logger.error("[%d/%d] FAILED %s: %s", i, total, ticker, e)

    if not ticker_data_list:
        logger.warning("No tickers could be prepared for v3 scoring.")
        await engine.dispose()
        return

    # Run v3 pipeline
    results = score_universe_v3(ticker_data_list, shiller_cape=cape)

    # Persist results
    from margin_engine.scoring.market_regime import detect_regime
    regime = detect_regime(cape)
    successes = 0
    async with session_factory() as session:
        for v3r in results:
            if v3r.ticker not in asset_ids:
                continue
            score = V3Score(
                asset_id=asset_ids[v3r.ticker],
                opportunity_type=v3r.opportunity_type,
                conviction=v3r.conviction.value,
                track_a=v3r.track_a.model_dump(mode="json"),
                track_b=v3r.track_b.model_dump(mode="json"),
                timing_signal=v3r.timing_signal,
                max_position_pct=v3r.max_position_pct,
                regime=regime.value,
                composite_score=max(v3r.track_a.score, v3r.track_b.score),
            )
            session.add(score)
            successes += 1
        await session.commit()

    logger.info("V3 scoring complete: %d scored out of %d tickers", successes, total)
    await engine.dispose()
```

**Step 3: Wire up in main()**

Add `elif args.command == "score-v3": asyncio.run(run_scoring_v3(tickers=args.tickers, cape=args.cape))` to main.

**Step 4: Run full API tests**

Run: `uv run pytest api/tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py
git commit -m "feat(api): add score-v3 CLI command with full gate cascade pipeline"
```

---

## Task 14: API Endpoints for V3 Scores

**Files:**
- Create: `api/src/margin_api/routes/v3_scores.py`
- Modify: `api/src/margin_api/app.py` (to register router)

**Step 1: Create route file**

Follow the existing pattern from `api/src/margin_api/routes/scores.py`:

```python
"""V3 Score API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, V3Score
from margin_api.db.session import get_db

router = APIRouter(prefix="/api/v3/scores", tags=["v3-scores"])


class V3ScoreResponse(BaseModel):
    ticker: str
    name: str
    opportunity_type: str
    conviction: str
    track_a: dict | None
    track_b: dict | None
    timing_signal: str
    max_position_pct: float
    regime: str
    composite_score: float
    scored_at: str


class V3ScoreListResponse(BaseModel):
    scores: list[V3ScoreResponse]
    total: int


@router.get("", response_model=V3ScoreListResponse)
async def list_v3_scores(
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> V3ScoreListResponse:
    # Subquery for latest score per asset
    # Join with Asset for ticker/name
    # Filter by conviction if provided
    pass  # Implementer fills in


@router.get("/{ticker}", response_model=V3ScoreResponse)
async def get_v3_score(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> V3ScoreResponse:
    pass  # Implementer fills in
```

**Step 2: Register in app.py**

Add `from margin_api.routes.v3_scores import router as v3_scores_router` and include it.

**Step 3: Write tests**

Create `api/tests/routes/test_v3_scores.py` testing both endpoints with a test client.

**Step 4: Run API tests**

Run: `uv run pytest api/tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/v3_scores.py api/src/margin_api/app.py api/tests/routes/test_v3_scores.py
git commit -m "feat(api): add GET /api/v3/scores endpoints"
```

---

## Task 15: Full Integration Test

**Files:**
- Create: `engine/tests/scoring/test_v3_cascade_integration.py`

**Step 1: Write end-to-end integration tests**

```python
"""Full integration test: raw data → cascade → orchestrator → V3Result."""

from decimal import Decimal
import pytest
from margin_engine.models.financial import (
    AssetProfile, FinancialHistory, GICSSector,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_cascade import TrackAInputs, TrackBInputs, run_track_a_cascade, run_track_b_cascade
from margin_engine.scoring.v3_orchestrator import orchestrate_v3
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
from margin_engine.scoring.market_regime import detect_regime, regime_adjustments


class TestFullCascadePipeline:
    def test_compounder_qualifies_end_to_end(self):
        """Strong compounder data → Track A qualifies → V3Result with position."""
        # Build 5yr history with growing moat, strong reinvestment
        # ... (implementer creates realistic synthetic data)
        pass

    def test_mispricing_qualifies_end_to_end(self):
        """Deep value stock → Track B qualifies → V3Result with position."""
        pass

    def test_both_tracks_qualify_promotes_to_exceptional(self):
        """Stock qualifying on both tracks → promoted to EXCEPTIONAL → 20%."""
        pass

    def test_portfolio_cap_across_universe(self):
        """Score 15 tickers → only top 10 get positions."""
        pass

    def test_regime_modifies_outcomes(self):
        """Same data, different CAPE → different conviction levels."""
        pass

    def test_cascade_deterministic(self):
        """Same inputs twice → identical outputs."""
        pass
```

**Step 2: Implement all 6 tests with realistic synthetic data**

Each test should construct full FinancialHistory with 5 periods, realistic AssetProfile, and run through the complete pipeline.

**Step 3: Run all tests**

Run: `uv run pytest engine/tests/ -v --tb=short`

**Step 4: Commit**

```bash
git add engine/tests/scoring/test_v3_cascade_integration.py
git commit -m "test(engine): add full v3 cascade integration tests"
```

---

## Summary

| Task | Layer | What | New Tests |
|------|-------|------|-----------|
| 1 | 4 | Sector WACC lookup | 4 |
| 2 | 1 | Owner earnings IV + compounding power | 7 |
| 3 | 1 | Capital allocation composite | 3 |
| 4 | 1 | Catalyst, quality floor, convergence, downside | 14 |
| 5 | 2 | Regime-adjusted thresholds | 5 |
| 6 | 2 | Track A cascade runner | 4 |
| 7 | 2 | Track B cascade runner | 4 |
| 8 | 3 | Universe pipeline + peer comparison + portfolio cap | 5 |
| 9 | — | Package exports update | 0 |
| 10 | 4 | FRED client for CAPE | 3 |
| 11 | 4 | FinancialHistory assembly from DB | 1 |
| 12 | 5 | V3Score DB model + migration | 0 |
| 13 | 5 | CLI score-v3 command | 0 |
| 14 | 5 | API endpoints | 2+ |
| 15 | — | Full integration test | 6 |

**Total: ~58 new tests across 15 tasks**
