# v3 Conviction Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace additive percentile averaging with gates-first multiplicative scoring, adding moat detection, reverse DCF, ensemble valuation, and absolute conviction thresholds.

**Architecture:** The v1 composite scorer is deprecated. The dual-track architecture (Track A: Compounder, Track B: Mispricing) becomes the sole scoring path. Each track runs a sequential gate cascade with multiplicative final scoring. Conviction is determined by absolute thresholds, not universe-relative percentile rank.

**Tech Stack:** Python 3.13, Pydantic, pytest, existing margin_engine models

**Design Doc:** `docs/plans/2026-02-16-v3-conviction-engine-design.md`

---

## Task 1: Moat Durability Classifier

New factor that detects 4 moat signatures from financial statement patterns. This is the foundation of Track A's redesign.

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/moat_durability.py`
- Create: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Step 1: Write the failing tests**

```python
"""Tests for moat durability classifier — detects moat signatures from financial patterns."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score


def _make_period(
    *,
    revenue: Decimal = Decimal("1000"),
    ebit: Decimal = Decimal("200"),
    cost_of_revenue: Decimal = Decimal("600"),
    gross_profit: Decimal = Decimal("400"),
    depreciation: Decimal | None = Decimal("50"),
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = Decimal("200"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("0"),
    operating_cash_flow: Decimal = Decimal("250"),
    capital_expenditures: Decimal = Decimal("-80"),
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        ebit=ebit,
        depreciation=depreciation,
        net_income=ebit * Decimal("0.79"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1500"),
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestMoatDurability:
    def test_scale_economics_detected(self):
        """ROIC increases as revenue grows -> scale economics signature."""
        periods = [
            _make_period(revenue=Decimal("500"), ebit=Decimal("50"),
                         total_equity=Decimal("300"), period_end="2019-12-31"),
            _make_period(revenue=Decimal("700"), ebit=Decimal("100"),
                         total_equity=Decimal("400"), period_end="2020-12-31"),
            _make_period(revenue=Decimal("900"), ebit=Decimal("170"),
                         total_equity=Decimal("500"), period_end="2021-12-31"),
            _make_period(revenue=Decimal("1100"), ebit=Decimal("260"),
                         total_equity=Decimal("600"), period_end="2022-12-31"),
            _make_period(revenue=Decimal("1300"), ebit=Decimal("370"),
                         total_equity=Decimal("700"), period_end="2023-12-31"),
        ]
        history = FinancialHistory(ticker="SCALE", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value >= 1.0
        assert "scale_economics" in result.detail

    def test_capital_efficiency_detected(self):
        """Incremental ROIC >= trailing ROIC -> capital efficiency signature."""
        periods = [
            _make_period(ebit=Decimal("100"), total_equity=Decimal("400"),
                         period_end="2019-12-31"),
            _make_period(ebit=Decimal("200"), total_equity=Decimal("600"),
                         period_end="2023-12-31"),
        ]
        history = FinancialHistory(ticker="CAPEFF", periods=periods)
        result = moat_durability_score(history)
        assert "capital_efficiency" in result.detail

    def test_pricing_power_detected(self):
        """Gross margin expands while revenue grows -> pricing power signature."""
        periods = [
            _make_period(revenue=Decimal("1000"), gross_profit=Decimal("400"),
                         cost_of_revenue=Decimal("600"), period_end="2019-12-31"),
            _make_period(revenue=Decimal("1100"), gross_profit=Decimal("460"),
                         cost_of_revenue=Decimal("640"), period_end="2020-12-31"),
            _make_period(revenue=Decimal("1200"), gross_profit=Decimal("530"),
                         cost_of_revenue=Decimal("670"), period_end="2021-12-31"),
            _make_period(revenue=Decimal("1300"), gross_profit=Decimal("610"),
                         cost_of_revenue=Decimal("690"), period_end="2022-12-31"),
            _make_period(revenue=Decimal("1400"), gross_profit=Decimal("700"),
                         cost_of_revenue=Decimal("700"), period_end="2023-12-31"),
        ]
        history = FinancialHistory(ticker="PRICE", periods=periods)
        result = moat_durability_score(history)
        assert "pricing_power" in result.detail

    def test_no_moat_signatures(self):
        """Declining ROIC with flat margins -> 0 signatures."""
        periods = [
            _make_period(ebit=Decimal("200"), total_equity=Decimal("400"),
                         gross_profit=Decimal("400"), period_end="2019-12-31"),
            _make_period(ebit=Decimal("150"), total_equity=Decimal("500"),
                         gross_profit=Decimal("380"), period_end="2020-12-31"),
            _make_period(ebit=Decimal("100"), total_equity=Decimal("600"),
                         gross_profit=Decimal("360"), period_end="2021-12-31"),
        ]
        history = FinancialHistory(ticker="NOMOAT", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_single_period_returns_zero(self):
        """Need 2+ periods to detect moat patterns."""
        history = FinancialHistory(ticker="ONE", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_percentile_rank_placeholder(self):
        history = FinancialHistory(ticker="PH", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.percentile_rank == 0.0
        assert result.name == "moat_durability"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_moat_durability.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""Moat Durability classifier — detects moat signatures from financial patterns.

Four signatures detected from multi-year financial data:
1. Scale Economics: ROIC increases as revenue grows (positive slope)
2. Pricing Power: Gross margins expand over time
3. Switching Costs: Revenue growth exceeds proportional cost growth (approximation)
4. Capital Efficiency: Incremental ROIC >= trailing ROIC

raw_value = count of detected signatures (0-4).
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore


def _compute_roic(period) -> float | None:
    ci = period.current_income
    cb = period.current_balance
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    if ic <= 0:
        return None
    return nopat / ic


def _detect_scale_economics(history: FinancialHistory) -> bool:
    """ROIC increases as revenue grows over 3+ periods."""
    pairs: list[tuple[float, float]] = []
    for p in history.periods:
        roic = _compute_roic(p)
        if roic is not None:
            pairs.append((float(p.current_income.revenue), roic))
    if len(pairs) < 3:
        return False
    # Check if ROIC trend is positive as revenue grows
    # Simple: is last ROIC > first ROIC while revenue grew?
    rev_grew = pairs[-1][0] > pairs[0][0]
    roic_grew = pairs[-1][1] > pairs[0][1]
    if not (rev_grew and roic_grew):
        return False
    # Confirm monotonic-ish: at least 60% of consecutive periods show ROIC growth
    increases = sum(1 for i in range(1, len(pairs)) if pairs[i][1] > pairs[i - 1][1])
    return increases / (len(pairs) - 1) >= 0.6


def _detect_pricing_power(history: FinancialHistory) -> bool:
    """Gross margins expand over 3+ periods."""
    margins = [p.current_income.gross_margin for p in history.periods]
    if len(margins) < 3:
        return False
    # Margin trend: last > first AND at least 60% of consecutive periods show expansion
    if margins[-1] <= margins[0]:
        return False
    increases = sum(1 for i in range(1, len(margins)) if margins[i] > margins[i - 1])
    return increases / (len(margins) - 1) >= 0.6


def _detect_switching_costs(history: FinancialHistory) -> bool:
    """Revenue retention proxy: revenue growth rate exceeds cost growth rate."""
    if len(history.periods) < 3:
        return False
    revenues = [float(p.current_income.revenue) for p in history.periods]
    costs = [float(p.current_income.cost_of_revenue) for p in history.periods]
    if revenues[0] <= 0 or costs[0] <= 0:
        return False
    rev_growth = (revenues[-1] / revenues[0]) - 1.0
    cost_growth = (costs[-1] / costs[0]) - 1.0
    # Revenue growing faster than costs = expanding margins = sticky customers
    return rev_growth > cost_growth and rev_growth > 0


def _detect_capital_efficiency(history: FinancialHistory) -> bool:
    """Incremental ROIC >= trailing median ROIC."""
    roics = [r for p in history.periods if (r := _compute_roic(p)) is not None]
    if len(roics) < 2:
        return False
    median_roic = statistics.median(roics)
    # Compute incremental ROIC (same logic as incremental_roic.py)
    earliest = history.periods[0]
    latest = history.periods[-1]
    e_roic = _compute_roic(earliest)
    l_roic = _compute_roic(latest)
    if e_roic is None or l_roic is None:
        return False
    ci_e, cb_e = earliest.current_income, earliest.current_balance
    ci_l, cb_l = latest.current_income, latest.current_balance
    nopat_e = float(ci_e.ebit) * (1.0 - ci_e.effective_tax_rate)
    nopat_l = float(ci_l.ebit) * (1.0 - ci_l.effective_tax_rate)
    cash_e = float(cb_e.cash_and_equivalents or Decimal("0"))
    cash_l = float(cb_l.cash_and_equivalents or Decimal("0"))
    ic_e = float(cb_e.total_equity) + float(cb_e.total_debt) - cash_e
    ic_l = float(cb_l.total_equity) + float(cb_l.total_debt) - cash_l
    delta_ic = ic_l - ic_e
    if delta_ic <= 0:
        return False
    inc_roic = (nopat_l - nopat_e) / delta_ic
    return inc_roic >= median_roic and inc_roic > 0


def moat_durability_score(history: FinancialHistory) -> FactorScore:
    """Compute moat durability score (0-4 signatures detected).

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="moat_durability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need 2+ periods for moat detection",
        )

    signatures: list[str] = []
    if _detect_scale_economics(history):
        signatures.append("scale_economics")
    if _detect_pricing_power(history):
        signatures.append("pricing_power")
    if _detect_switching_costs(history):
        signatures.append("switching_costs")
    if _detect_capital_efficiency(history):
        signatures.append("capital_efficiency")

    return FactorScore(
        name="moat_durability",
        raw_value=float(len(signatures)),
        percentile_rank=0.0,
        detail=f"signatures={signatures}, count={len(signatures)}",
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_moat_durability.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/moat_durability.py engine/tests/scoring/quantitative/test_moat_durability.py
git commit -m "feat(engine): add moat durability classifier with 4 financial pattern signatures"
```

---

## Task 2: Reverse DCF (Implied Growth Gap)

Computes the growth rate the market is pricing in, compares to sustainable growth rate, returns the gap.

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/reverse_dcf.py`
- Create: `engine/tests/scoring/quantitative/test_reverse_dcf.py`

**Step 1: Write the failing tests**

```python
"""Tests for reverse DCF — implied growth rate vs sustainable growth gap."""

import pytest
from margin_engine.scoring.quantitative.reverse_dcf import (
    reverse_dcf_growth_gap,
    solve_implied_growth_rate,
)


class TestSolveImpliedGrowthRate:
    def test_known_values(self):
        """Price=100, FCF=5, WACC=10%, terminal=2.5% -> solve for implied growth."""
        implied = solve_implied_growth_rate(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        # Implied growth should be between 0% and WACC
        assert 0.0 < implied < 0.10

    def test_expensive_stock_high_implied(self):
        """High price relative to FCF -> high implied growth."""
        implied = solve_implied_growth_rate(
            current_price=500.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied > 0.10  # Market expects very high growth

    def test_cheap_stock_low_implied(self):
        """Low price relative to FCF -> low implied growth."""
        implied = solve_implied_growth_rate(
            current_price=30.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied < 0.03

    def test_negative_fcf_returns_none(self):
        implied = solve_implied_growth_rate(
            current_price=100.0,
            current_fcf=-5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied is None

    def test_zero_price_returns_none(self):
        implied = solve_implied_growth_rate(
            current_price=0.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied is None


class TestReverseDcfGrowthGap:
    def test_positive_gap_undervalued(self):
        """Sustainable growth > implied growth -> positive gap (opportunity)."""
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.name == "reverse_dcf_growth_gap"
        assert result.raw_value > 0.0

    def test_negative_gap_overvalued(self):
        """Sustainable growth < implied growth -> negative gap (no opportunity)."""
        result = reverse_dcf_growth_gap(
            current_price=500.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.05,
        )
        assert result.raw_value < 0.0

    def test_negative_fcf_returns_zero(self):
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=-5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.raw_value == 0.0

    def test_percentile_rank_placeholder(self):
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.percentile_rank == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reverse_dcf.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""Reverse DCF — solve for implied growth rate and compute growth gap.

Instead of "what is this business worth?", asks "what growth is the market pricing in?"

implied_growth = solve_for_g where: price = sum(FCF*(1+g)^t / (1+WACC)^t) + terminal
growth_gap = sustainable_growth_rate - implied_growth_rate

Positive gap = market underestimates growth (opportunity).
Negative gap = market overestimates growth (no edge).
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_PROJECTION_YEARS = 10
_MAX_GROWTH = 0.50  # Cap solver at 50%
_MIN_GROWTH = -0.10  # Floor solver at -10%
_SOLVER_TOLERANCE = 0.0001
_SOLVER_MAX_ITER = 100


def _dcf_value(
    fcf: float, growth: float, wacc: float, terminal_growth: float, years: int
) -> float:
    """Compute DCF intrinsic value for a given growth rate."""
    pv_sum = 0.0
    for t in range(1, years + 1):
        projected = fcf * (1 + growth) ** t
        pv_sum += projected / (1 + wacc) ** t
    final_fcf = fcf * (1 + growth) ** years
    if wacc <= terminal_growth:
        return pv_sum  # No valid terminal value
    terminal = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal / (1 + wacc) ** years
    return pv_sum + pv_terminal


def solve_implied_growth_rate(
    current_price: float,
    current_fcf: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    projection_years: int = _PROJECTION_YEARS,
) -> float | None:
    """Solve for the growth rate implied by the current market price.

    Uses bisection method to find g where DCF(g) / shares = current_price.

    Returns None if FCF <= 0 or price <= 0 (unsolvable).
    """
    if current_fcf <= 0 or current_price <= 0 or shares_outstanding <= 0:
        return None

    target = current_price * shares_outstanding  # Total market cap

    lo, hi = _MIN_GROWTH, _MAX_GROWTH

    for _ in range(_SOLVER_MAX_ITER):
        mid = (lo + hi) / 2.0
        val = _dcf_value(current_fcf, mid, wacc, terminal_growth, projection_years)
        if abs(val - target) / max(target, 1.0) < _SOLVER_TOLERANCE:
            return mid
        if val < target:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2.0  # Best approximation


def reverse_dcf_growth_gap(
    current_price: float,
    current_fcf: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    sustainable_growth_rate: float,
    projection_years: int = _PROJECTION_YEARS,
) -> FactorScore:
    """Compute growth gap between sustainable and implied growth rates.

    Returns a FactorScore with:
    - raw_value: growth_gap (positive = opportunity, negative = no edge)
    - percentile_rank: 0.0 (placeholder)
    """
    implied = solve_implied_growth_rate(
        current_price, current_fcf, wacc, terminal_growth,
        shares_outstanding, projection_years,
    )

    if implied is None:
        return FactorScore(
            name="reverse_dcf_growth_gap",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Cannot solve implied growth (negative FCF or invalid price)",
        )

    gap = sustainable_growth_rate - implied

    return FactorScore(
        name="reverse_dcf_growth_gap",
        raw_value=gap,
        percentile_rank=0.0,
        detail=(
            f"implied_growth={implied:.4f}, sustainable_growth={sustainable_growth_rate:.4f}, "
            f"gap={gap:.4f}"
        ),
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reverse_dcf.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/reverse_dcf.py engine/tests/scoring/quantitative/test_reverse_dcf.py
git commit -m "feat(engine): add reverse DCF solver for implied growth gap"
```

---

## Task 3: Ensemble Valuation with Convergence Test

Four independent valuation methods with a convergence gate for Track B.

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/ensemble_valuation.py`
- Create: `engine/tests/scoring/quantitative/test_ensemble_valuation.py`

**Step 1: Write the failing tests**

```python
"""Tests for ensemble valuation — 4-method convergence for reliable intrinsic value."""

import pytest
from margin_engine.scoring.quantitative.ensemble_valuation import (
    EnsembleResult,
    compute_ensemble_valuation,
)


class TestEnsembleValuation:
    def test_all_methods_converge(self):
        """4 values within 30% of median -> all converge."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=90.0,
            peer_comparison_iv=105.0,
        )
        assert result.converged is True
        assert result.converging_count == 4
        assert 90.0 <= result.ensemble_iv <= 110.0

    def test_three_converge_one_outlier(self):
        """3 values agree, 1 is an outlier -> still converges (3 >= 3)."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=95.0,
            peer_comparison_iv=300.0,  # outlier
        )
        assert result.converged is True
        assert result.converging_count == 3

    def test_two_converge_fails(self):
        """Only 2 values agree -> fails convergence gate."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=105.0,
            asset_floor_iv=300.0,
            peer_comparison_iv=500.0,
        )
        assert result.converged is False
        assert result.converging_count == 2

    def test_ensemble_iv_is_median_of_converging(self):
        """Ensemble IV uses median of converging methods, not mean."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=120.0,
            asset_floor_iv=110.0,
            peer_comparison_iv=500.0,  # outlier, excluded
        )
        # Converging: 100, 110, 120 -> median = 110
        assert result.ensemble_iv == pytest.approx(110.0)

    def test_all_zero_returns_not_converged(self):
        result = compute_ensemble_valuation(
            dcf_iv=0.0,
            owner_earnings_iv=0.0,
            asset_floor_iv=0.0,
            peer_comparison_iv=0.0,
        )
        assert result.converged is False

    def test_negative_values_excluded(self):
        result = compute_ensemble_valuation(
            dcf_iv=-50.0,
            owner_earnings_iv=100.0,
            asset_floor_iv=110.0,
            peer_comparison_iv=105.0,
        )
        assert result.converged is True
        assert result.converging_count == 3

    def test_methods_dict_populated(self):
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=90.0,
            peer_comparison_iv=105.0,
        )
        assert "dcf" in result.methods
        assert "owner_earnings" in result.methods
        assert "asset_floor" in result.methods
        assert "peer_comparison" in result.methods
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_ensemble_valuation.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""Ensemble Valuation — 4-method convergence test for reliable intrinsic value.

Methods:
1. DCF (passed in from existing dcf_mos.py)
2. Owner Earnings Capitalization (Owner Earnings / WACC)
3. Asset-Based Floor (Net Cash + Tangible Book * sector liquidation multiple)
4. EV/EBIT Peer Comparison (sector median EV/EBIT * company EBIT)

Convergence: >= 3 of 4 methods must agree within 30% of their median.
Ensemble IV = median of converging methods.
"""

from __future__ import annotations

import statistics

from pydantic import BaseModel


class EnsembleResult(BaseModel):
    """Result of ensemble valuation convergence test."""

    converged: bool
    converging_count: int
    ensemble_iv: float
    methods: dict[str, float]
    convergence_threshold: float = 0.30


def compute_ensemble_valuation(
    dcf_iv: float,
    owner_earnings_iv: float,
    asset_floor_iv: float,
    peer_comparison_iv: float,
    convergence_pct: float = 0.30,
    min_converging: int = 3,
) -> EnsembleResult:
    """Compute ensemble intrinsic value from 4 independent methods.

    Args:
        dcf_iv: Intrinsic value from DCF model.
        owner_earnings_iv: Owner Earnings / WACC.
        asset_floor_iv: Net Cash + Tangible Book * liquidation multiple.
        peer_comparison_iv: Sector median EV/EBIT * company EBIT.
        convergence_pct: Max deviation from median to count as converging.
        min_converging: Minimum methods that must converge.

    Returns:
        EnsembleResult with convergence status and ensemble IV.
    """
    methods = {
        "dcf": dcf_iv,
        "owner_earnings": owner_earnings_iv,
        "asset_floor": asset_floor_iv,
        "peer_comparison": peer_comparison_iv,
    }

    # Filter out non-positive values
    valid = {k: v for k, v in methods.items() if v > 0}

    if len(valid) < min_converging:
        return EnsembleResult(
            converged=False,
            converging_count=len(valid),
            ensemble_iv=0.0,
            methods=methods,
        )

    values = list(valid.values())
    median_iv = statistics.median(values)

    if median_iv <= 0:
        return EnsembleResult(
            converged=False,
            converging_count=0,
            ensemble_iv=0.0,
            methods=methods,
        )

    # Check convergence: which methods are within convergence_pct of median
    converging = [v for v in values if abs(v - median_iv) / median_iv <= convergence_pct]
    converging_count = len(converging)

    if converging_count >= min_converging:
        ensemble_iv = statistics.median(converging)
        return EnsembleResult(
            converged=True,
            converging_count=converging_count,
            ensemble_iv=ensemble_iv,
            methods=methods,
        )

    return EnsembleResult(
        converged=False,
        converging_count=converging_count,
        ensemble_iv=0.0,
        methods=methods,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_ensemble_valuation.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/ensemble_valuation.py engine/tests/scoring/quantitative/test_ensemble_valuation.py
git commit -m "feat(engine): add ensemble valuation with 4-method convergence test"
```

---

## Task 4: Asset-Based Floor Valuation

New valuation method for the ensemble: liquidation/breakup value with sector-specific multiples.

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/asset_floor.py`
- Create: `engine/tests/scoring/quantitative/test_asset_floor.py`

**Step 1: Write the failing tests**

```python
"""Tests for asset-based floor valuation — liquidation/breakup value."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import GICSSector
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation


class TestAssetFloorValuation:
    def test_technology_low_multiple(self):
        """Tech gets 0.3x tangible book (IP-heavy)."""
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
        )
        # 500 + 1000*0.3 = 800, per share = 8.0
        assert result == pytest.approx(8.0)

    def test_utilities_high_multiple(self):
        """Utilities get 0.8x tangible book (regulated assets)."""
        result = asset_floor_valuation(
            net_cash=Decimal("200"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.UTILITIES,
            shares_outstanding=100,
        )
        # 200 + 1000*0.8 = 1000, per share = 10.0
        assert result == pytest.approx(10.0)

    def test_negative_net_cash(self):
        """Negative net cash (net debt) reduces floor."""
        result = asset_floor_valuation(
            net_cash=Decimal("-300"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.INDUSTRIALS,
            shares_outstanding=100,
        )
        # -300 + 1000*0.6 = 300, per share = 3.0
        assert result == pytest.approx(3.0)

    def test_floor_cannot_go_negative(self):
        """Floor bottoms at 0.0 even with massive debt."""
        result = asset_floor_valuation(
            net_cash=Decimal("-5000"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
        )
        assert result == 0.0

    def test_zero_shares_returns_zero(self):
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=0,
        )
        assert result == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_asset_floor.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""Asset-Based Floor valuation — liquidation/breakup value per share.

Floor = max(Net Cash + Tangible Book * sector_liquidation_multiple, 0) / shares

Sector liquidation multiples reflect realistic recovery in distressed sale.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import GICSSector

_SECTOR_LIQUIDATION_MULTIPLES: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 0.3,
    GICSSector.HEALTHCARE: 0.4,
    GICSSector.CONSUMER_STAPLES: 0.7,
    GICSSector.CONSUMER_DISCRETIONARY: 0.5,
    GICSSector.INDUSTRIALS: 0.6,
    GICSSector.ENERGY: 0.5,
    GICSSector.MATERIALS: 0.6,
    GICSSector.UTILITIES: 0.8,
    GICSSector.COMMUNICATION_SERVICES: 0.3,
    GICSSector.FINANCIALS: 0.5,
    GICSSector.REAL_ESTATE: 0.7,
}

_DEFAULT_MULTIPLE = 0.5


def asset_floor_valuation(
    net_cash: Decimal,
    tangible_book: Decimal,
    sector: GICSSector,
    shares_outstanding: int,
) -> float:
    """Compute asset-based floor valuation per share.

    Args:
        net_cash: Cash - Total Debt (can be negative for net debt).
        tangible_book: Total Equity - Intangible Assets - Goodwill.
        sector: GICS sector for liquidation multiple lookup.
        shares_outstanding: Total shares outstanding.

    Returns:
        Floor value per share (>= 0.0).
    """
    if shares_outstanding <= 0:
        return 0.0

    multiple = _SECTOR_LIQUIDATION_MULTIPLES.get(sector, _DEFAULT_MULTIPLE)
    total_floor = float(net_cash) + float(tangible_book) * multiple
    per_share = max(total_floor, 0.0) / shares_outstanding

    return per_share
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_asset_floor.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/asset_floor.py engine/tests/scoring/quantitative/test_asset_floor.py
git commit -m "feat(engine): add asset-based floor valuation with sector liquidation multiples"
```

---

## Task 5: Market Regime Modifier

Detects market regime from Shiller CAPE and adjusts conviction thresholds.

**Files:**
- Create: `engine/src/margin_engine/scoring/market_regime.py`
- Create: `engine/tests/scoring/test_market_regime.py`

**Step 1: Write the failing tests**

```python
"""Tests for market regime modifier — CAPE-based threshold adjustment."""

import pytest
from margin_engine.scoring.market_regime import (
    MarketRegime,
    detect_regime,
    regime_adjustments,
)


class TestDetectRegime:
    def test_cheap(self):
        assert detect_regime(12.0) == MarketRegime.CHEAP

    def test_normal(self):
        assert detect_regime(20.0) == MarketRegime.NORMAL

    def test_expensive(self):
        assert detect_regime(30.0) == MarketRegime.EXPENSIVE

    def test_euphoria(self):
        assert detect_regime(40.0) == MarketRegime.EUPHORIA

    def test_boundary_15_is_normal(self):
        assert detect_regime(15.0) == MarketRegime.NORMAL

    def test_boundary_25_is_normal(self):
        assert detect_regime(25.0) == MarketRegime.NORMAL

    def test_boundary_25_01_is_expensive(self):
        assert detect_regime(25.01) == MarketRegime.EXPENSIVE

    def test_boundary_35_01_is_euphoria(self):
        assert detect_regime(35.01) == MarketRegime.EUPHORIA


class TestRegimeAdjustments:
    def test_cheap_relaxes_growth_gap(self):
        adj = regime_adjustments(MarketRegime.CHEAP)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(-0.02)
        assert adj.track_b_asymmetry_adjustment == pytest.approx(-1.0)

    def test_normal_no_adjustment(self):
        adj = regime_adjustments(MarketRegime.NORMAL)
        assert adj.track_a_growth_gap_adjustment == 0.0
        assert adj.track_b_asymmetry_adjustment == 0.0
        assert adj.track_b_catalyst_percentile_override is None

    def test_expensive_tightens_growth_gap(self):
        adj = regime_adjustments(MarketRegime.EXPENSIVE)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(0.02)

    def test_euphoria_tightens_both(self):
        adj = regime_adjustments(MarketRegime.EUPHORIA)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(0.05)
        assert adj.track_b_catalyst_percentile_override == pytest.approx(90.0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_market_regime.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""Market Regime modifier — CAPE-based threshold adjustment.

Detects current market regime and returns adjustment values for conviction thresholds.
Not prediction — detection of current conditions.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class MarketRegime(StrEnum):
    CHEAP = "cheap"
    NORMAL = "normal"
    EXPENSIVE = "expensive"
    EUPHORIA = "euphoria"


class RegimeAdjustments(BaseModel):
    """Adjustments to apply to conviction thresholds based on market regime."""

    regime: MarketRegime
    track_a_growth_gap_adjustment: float  # Added to growth_gap threshold (positive = tighter)
    track_b_asymmetry_adjustment: float  # Added to asymmetry threshold (negative = relaxed)
    track_b_catalyst_percentile_override: float | None  # Override catalyst gate if set


def detect_regime(shiller_cape: float) -> MarketRegime:
    """Detect market regime from Shiller CAPE ratio."""
    if shiller_cape < 15.0:
        return MarketRegime.CHEAP
    if shiller_cape <= 25.0:
        return MarketRegime.NORMAL
    if shiller_cape <= 35.0:
        return MarketRegime.EXPENSIVE
    return MarketRegime.EUPHORIA


def regime_adjustments(regime: MarketRegime) -> RegimeAdjustments:
    """Return threshold adjustments for a given market regime."""
    if regime == MarketRegime.CHEAP:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=-0.02,
            track_b_asymmetry_adjustment=-1.0,
            track_b_catalyst_percentile_override=None,
        )
    if regime == MarketRegime.NORMAL:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=0.0,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
    if regime == MarketRegime.EXPENSIVE:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=0.02,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
    # EUPHORIA
    return RegimeAdjustments(
        regime=regime,
        track_a_growth_gap_adjustment=0.05,
        track_b_asymmetry_adjustment=0.0,
        track_b_catalyst_percentile_override=90.0,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_market_regime.py -v`
Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/market_regime.py engine/tests/scoring/test_market_regime.py
git commit -m "feat(engine): add market regime detector with CAPE-based threshold adjustments"
```

---

## Task 6: SBC Dilution Tax and M&A Discipline (Capital Allocation Extensions)

Extend `capital_allocation.py` with two new sub-factors.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/capital_allocation.py`
- Modify: `engine/tests/scoring/quantitative/test_capital_allocation.py`

**Step 1: Write the failing tests**

Add to the existing test file:

```python
class TestSbcDilutionTax:
    def test_low_sbc_good_score(self):
        """SBC < 3% of revenue -> low dilution."""
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax
        result = sbc_dilution_tax(
            sbc_amount=Decimal("30"),
            revenue=Decimal("1000"),
        )
        assert result.name == "sbc_dilution_tax"
        assert result.raw_value == pytest.approx(0.03)

    def test_high_sbc_bad_score(self):
        """SBC > 10% of revenue -> heavy dilution."""
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax
        result = sbc_dilution_tax(
            sbc_amount=Decimal("120"),
            revenue=Decimal("1000"),
        )
        assert result.raw_value == pytest.approx(0.12)

    def test_zero_revenue(self):
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax
        result = sbc_dilution_tax(
            sbc_amount=Decimal("30"),
            revenue=Decimal("0"),
        )
        assert result.raw_value == 1.0  # Worst case


class TestMaDiscipline:
    def test_roic_stable_after_acquisition(self):
        """ROIC doesn't decline after acquisition -> good discipline."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline
        result = ma_discipline(
            roic_before_acquisition=0.20,
            roic_after_acquisition=0.22,
        )
        assert result.name == "ma_discipline"
        assert result.raw_value > 0.0

    def test_roic_declines_after_acquisition(self):
        """ROIC declines after acquisition -> bad discipline."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline
        result = ma_discipline(
            roic_before_acquisition=0.20,
            roic_after_acquisition=0.12,
        )
        assert result.raw_value < 0.0

    def test_no_acquisition(self):
        """No acquisition data -> neutral."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline
        result = ma_discipline(
            roic_before_acquisition=None,
            roic_after_acquisition=None,
        )
        assert result.raw_value == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_capital_allocation.py -v -k "Sbc or Ma"`
Expected: FAIL (function not found)

**Step 3: Add implementations to `capital_allocation.py`**

Append to existing file:

```python
def sbc_dilution_tax(
    sbc_amount: Decimal,
    revenue: Decimal,
) -> FactorScore:
    """SBC as % of revenue. Lower = better. Inverted at ranking time."""
    if revenue <= 0:
        return FactorScore(
            name="sbc_dilution_tax",
            raw_value=1.0,
            percentile_rank=0.0,
            detail="zero revenue, worst case",
        )

    ratio = float(abs(sbc_amount) / revenue)
    return FactorScore(
        name="sbc_dilution_tax",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=f"SBC={float(sbc_amount):,.2f}, revenue={float(revenue):,.2f}, ratio={ratio:.4f}",
    )


def ma_discipline(
    roic_before_acquisition: float | None,
    roic_after_acquisition: float | None,
) -> FactorScore:
    """ROIC change after large acquisitions. Positive = value-creating."""
    if roic_before_acquisition is None or roic_after_acquisition is None:
        return FactorScore(
            name="ma_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No acquisition data, neutral",
        )

    delta = roic_after_acquisition - roic_before_acquisition
    return FactorScore(
        name="ma_discipline",
        raw_value=delta,
        percentile_rank=0.0,
        detail=f"ROIC_before={roic_before_acquisition:.4f}, after={roic_after_acquisition:.4f}, delta={delta:.4f}",
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_capital_allocation.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/capital_allocation.py engine/tests/scoring/quantitative/test_capital_allocation.py
git commit -m "feat(engine): add SBC dilution tax and M&A discipline to capital allocation"
```

---

## Task 7: v3 Conviction Thresholds Model

New model for absolute conviction thresholds replacing universe-relative percentile thresholds.

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_thresholds.py`
- Create: `engine/tests/scoring/test_v3_thresholds.py`

**Step 1: Write the failing tests**

```python
"""Tests for v3 absolute conviction thresholds."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_thresholds import (
    assess_track_a_conviction,
    assess_track_b_conviction,
)


class TestTrackAConviction:
    def test_exceptional(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=3,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.EXCEPTIONAL

    def test_high(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=2,
            growth_gap=0.05,
        )
        assert level == ConvictionLevel.HIGH

    def test_watchlist(self):
        level = assess_track_a_conviction(
            gates_passed=3,
            total_gates=4,
            compounding_power=0.06,
            moat_durability=2,
            growth_gap=0.01,
        )
        assert level == ConvictionLevel.WATCHLIST

    def test_none_insufficient_gates(self):
        level = assess_track_a_conviction(
            gates_passed=2,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=3,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.NONE

    def test_none_low_moat(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=1,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.NONE


class TestTrackBConviction:
    def test_exceptional(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=6.0,
            catalyst_percentile=85.0,
            converging_methods=4,
        )
        assert level == ConvictionLevel.EXCEPTIONAL

    def test_high(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=4.0,
            catalyst_percentile=65.0,
            converging_methods=3,
        )
        assert level == ConvictionLevel.HIGH

    def test_watchlist(self):
        level = assess_track_b_conviction(
            gates_passed=3,
            total_gates=4,
            asymmetry_ratio=2.0,
            catalyst_percentile=50.0,
            converging_methods=2,
        )
        assert level == ConvictionLevel.WATCHLIST

    def test_none_low_asymmetry(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=1.0,
            catalyst_percentile=85.0,
            converging_methods=4,
        )
        assert level == ConvictionLevel.NONE
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_thresholds.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""v3 Conviction Thresholds — absolute conviction levels per track.

Replaces universe-relative percentile thresholds (99.95, 99.3, 98.0).
Conviction determined by absolute quality of the opportunity, not rank vs peers.
"""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

# Track A thresholds
_A_EXCEPTIONAL_POWER = 0.15
_A_EXCEPTIONAL_MOAT = 3
_A_EXCEPTIONAL_GAP = 0.08
_A_HIGH_POWER = 0.08
_A_HIGH_MOAT = 2
_A_HIGH_GAP = 0.03
_A_WATCHLIST_POWER = 0.04
_A_WATCHLIST_MOAT = 2
_A_MIN_GATES_FULL = 4
_A_MIN_GATES_WATCHLIST = 3

# Track B thresholds
_B_EXCEPTIONAL_ASYMMETRY = 5.0
_B_EXCEPTIONAL_CATALYST = 80.0
_B_EXCEPTIONAL_CONVERGING = 4
_B_HIGH_ASYMMETRY = 3.0
_B_HIGH_CATALYST = 60.0
_B_HIGH_CONVERGING = 3
_B_WATCHLIST_ASYMMETRY = 1.5
_B_MIN_GATES_FULL = 4
_B_MIN_GATES_WATCHLIST = 3


def assess_track_a_conviction(
    gates_passed: int,
    total_gates: int,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
) -> ConvictionLevel:
    """Determine Track A conviction level from absolute thresholds."""
    if gates_passed < _A_MIN_GATES_WATCHLIST or moat_durability < _A_WATCHLIST_MOAT:
        return ConvictionLevel.NONE

    if (
        gates_passed >= _A_MIN_GATES_FULL
        and compounding_power > _A_EXCEPTIONAL_POWER
        and moat_durability >= _A_EXCEPTIONAL_MOAT
        and growth_gap > _A_EXCEPTIONAL_GAP
    ):
        return ConvictionLevel.EXCEPTIONAL

    if (
        gates_passed >= _A_MIN_GATES_FULL
        and compounding_power > _A_HIGH_POWER
        and moat_durability >= _A_HIGH_MOAT
        and growth_gap > _A_HIGH_GAP
    ):
        return ConvictionLevel.HIGH

    if compounding_power > _A_WATCHLIST_POWER:
        return ConvictionLevel.WATCHLIST

    return ConvictionLevel.NONE


def assess_track_b_conviction(
    gates_passed: int,
    total_gates: int,
    asymmetry_ratio: float,
    catalyst_percentile: float,
    converging_methods: int,
) -> ConvictionLevel:
    """Determine Track B conviction level from absolute thresholds."""
    if gates_passed < _B_MIN_GATES_WATCHLIST or asymmetry_ratio < _B_WATCHLIST_ASYMMETRY:
        return ConvictionLevel.NONE

    if (
        gates_passed >= _B_MIN_GATES_FULL
        and asymmetry_ratio > _B_EXCEPTIONAL_ASYMMETRY
        and catalyst_percentile > _B_EXCEPTIONAL_CATALYST
        and converging_methods >= _B_EXCEPTIONAL_CONVERGING
    ):
        return ConvictionLevel.EXCEPTIONAL

    if (
        gates_passed >= _B_MIN_GATES_FULL
        and asymmetry_ratio > _B_HIGH_ASYMMETRY
        and catalyst_percentile > _B_HIGH_CATALYST
        and converging_methods >= _B_HIGH_CONVERGING
    ):
        return ConvictionLevel.HIGH

    return ConvictionLevel.WATCHLIST
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_thresholds.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_thresholds.py engine/tests/scoring/test_v3_thresholds.py
git commit -m "feat(engine): add v3 absolute conviction thresholds for Track A and Track B"
```

---

## Task 8: v3 Multiplicative Composite Scorers

Replace additive averaging with multiplicative scoring for both tracks.

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_composite.py`
- Create: `engine/tests/scoring/test_v3_composite.py`

**Step 1: Write the failing tests**

```python
"""Tests for v3 multiplicative composite scoring."""

import pytest
from margin_engine.scoring.v3_composite import (
    compute_track_a_score,
    compute_track_b_score,
)


class TestTrackAScore:
    def test_multiplicative_product(self):
        """Score = moat * compounding * cap_alloc * growth_gap."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        expected = 3.0 * 0.20 * 0.80 * 0.10
        assert score == pytest.approx(expected)

    def test_zero_in_any_factor_kills_score(self):
        """A zero moat -> zero score, regardless of other factors."""
        score = compute_track_a_score(
            moat_durability=0.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        assert score == 0.0

    def test_magnitude_preserved(self):
        """5x better inputs produce ~5x better score (not 1.3x like averaging)."""
        weak = compute_track_a_score(
            moat_durability=2.0, compounding_power=0.05,
            capital_allocation=0.50, growth_gap=0.03,
        )
        strong = compute_track_a_score(
            moat_durability=4.0, compounding_power=0.25,
            capital_allocation=0.90, growth_gap=0.12,
        )
        ratio = strong / weak if weak > 0 else float("inf")
        assert ratio > 10.0  # Massive gap preserved

    def test_negative_growth_gap(self):
        """Negative growth gap -> negative score (overvalued)."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=-0.05,
        )
        assert score < 0.0


class TestTrackBScore:
    def test_multiplicative_product(self):
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        expected = 5.0 * 0.80 * 1.0 * 0.75
        assert score == pytest.approx(expected)

    def test_zero_catalyst_kills_score(self):
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.0,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        assert score == 0.0

    def test_asymmetry_capped_at_20(self):
        """Asymmetry ratio capped at 20 to prevent distortion."""
        score = compute_track_b_score(
            asymmetry_ratio=100.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        expected = 20.0 * 0.80 * 1.0 * 0.75
        assert score == pytest.approx(expected)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_composite.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""v3 Multiplicative Composite Scoring.

Replaces additive percentile averaging with multiplicative products.
A zero in any critical factor produces a zero score.
Magnitude differences are preserved (5x better = 5x higher score).
"""

from __future__ import annotations

_ASYMMETRY_CAP = 20.0


def compute_track_a_score(
    moat_durability: float,
    compounding_power: float,
    capital_allocation: float,
    growth_gap: float,
) -> float:
    """Compute Track A (Compounder) multiplicative score.

    score = moat_durability * compounding_power * capital_allocation * growth_gap
    """
    return moat_durability * compounding_power * capital_allocation * growth_gap


def compute_track_b_score(
    asymmetry_ratio: float,
    catalyst_strength: float,
    quality_floor_factor: float,
    valuation_convergence: float,
) -> float:
    """Compute Track B (Mispricing) multiplicative score.

    score = min(asymmetry, 20) * catalyst * quality_floor * convergence
    """
    capped_asymmetry = min(asymmetry_ratio, _ASYMMETRY_CAP)
    return capped_asymmetry * catalyst_strength * quality_floor_factor * valuation_convergence
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_composite.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_composite.py engine/tests/scoring/test_v3_composite.py
git commit -m "feat(engine): add v3 multiplicative composite scoring for both tracks"
```

---

## Task 9: v3 Position Sizing (Track-Specific)

Replace current asymmetry-tier sizing with track-specific limits and portfolio cap.

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_position_sizing.py`
- Create: `engine/tests/scoring/test_v3_position_sizing.py`

**Step 1: Write the failing tests**

```python
"""Tests for v3 position sizing — track-specific with portfolio cap."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_position_sizing import (
    compute_v3_position_size,
    MAX_POSITIONS,
)


class TestV3PositionSizing:
    def test_track_a_exceptional(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.EXCEPTIONAL) == 15.0

    def test_track_a_high(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.HIGH) == 8.0

    def test_track_a_watchlist_zero(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.WATCHLIST) == 0.0

    def test_track_b_exceptional(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.EXCEPTIONAL) == 12.0

    def test_track_b_high(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.HIGH) == 6.0

    def test_both_exceptional(self):
        assert compute_v3_position_size("both", ConvictionLevel.EXCEPTIONAL) == 20.0

    def test_none_always_zero(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.NONE) == 0.0

    def test_portfolio_cap_is_10(self):
        assert MAX_POSITIONS == 10
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_position_sizing.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""v3 Position Sizing — track-specific with portfolio concentration cap.

Watchlist = 0% (not actionable). Compounders slightly larger than mispricings.
"Both" classification gets maximum 20%.
"""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

MAX_POSITIONS = 10

_SIZING: dict[str, dict[ConvictionLevel, float]] = {
    "compounder": {
        ConvictionLevel.EXCEPTIONAL: 15.0,
        ConvictionLevel.HIGH: 8.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "mispricing": {
        ConvictionLevel.EXCEPTIONAL: 12.0,
        ConvictionLevel.HIGH: 6.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "both": {
        ConvictionLevel.EXCEPTIONAL: 20.0,
        ConvictionLevel.HIGH: 10.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
}


def compute_v3_position_size(track: str, conviction: ConvictionLevel) -> float:
    """Compute max position size (%) for a track and conviction level."""
    track_key = track if track in _SIZING else "compounder"
    return _SIZING[track_key].get(conviction, 0.0)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_position_sizing.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_position_sizing.py engine/tests/scoring/test_v3_position_sizing.py
git commit -m "feat(engine): add v3 track-specific position sizing with 10-position cap"
```

---

## Task 10: Update Timing Overlay

Add `accumulate_slowly` signal for Track A compounders in sharp decline.

**Files:**
- Modify: `engine/src/margin_engine/scoring/timing_overlay.py`
- Modify: `engine/tests/scoring/test_timing_overlay.py`

**Step 1: Write failing tests**

Add to existing test file:

```python
class TestV3TimingSignals:
    def test_track_a_buy_now(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
        assert compute_v3_timing_signal(60.0, is_mispricing_track=False) == "buy_now"

    def test_track_a_add_on_pullback(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
        assert compute_v3_timing_signal(40.0, is_mispricing_track=False) == "add_on_pullback"

    def test_track_a_accumulate_slowly(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
        assert compute_v3_timing_signal(20.0, is_mispricing_track=False) == "accumulate_slowly"

    def test_track_b_buy_now(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
        assert compute_v3_timing_signal(30.0, is_mispricing_track=True) == "buy_now"

    def test_track_b_wait(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
        assert compute_v3_timing_signal(60.0, is_mispricing_track=True) == "wait_for_catalyst"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_timing_overlay.py -v -k "V3"`
Expected: FAIL (function not found)

**Step 3: Add `compute_v3_timing_signal` to `timing_overlay.py`**

Append to existing file:

```python
def compute_v3_timing_signal(
    momentum_percentile: float,
    is_mispricing_track: bool,
) -> str:
    """Compute v3 timing signal with 3-tier Track A signals.

    Track A (Compounder):
        >= 50  -> buy_now
        30-49  -> add_on_pullback
        < 30   -> accumulate_slowly (DCA into compounders in pain)

    Track B (Mispricing):
        < 50   -> buy_now (contrarian confirmation)
        >= 50  -> wait_for_catalyst
    """
    if is_mispricing_track:
        return "buy_now" if momentum_percentile < 50.0 else "wait_for_catalyst"
    # Track A: 3-tier
    if momentum_percentile >= 50.0:
        return "buy_now"
    if momentum_percentile >= 30.0:
        return "add_on_pullback"
    return "accumulate_slowly"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_timing_overlay.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/timing_overlay.py engine/tests/scoring/test_timing_overlay.py
git commit -m "feat(engine): add v3 timing overlay with accumulate_slowly signal"
```

---

## Task 11: v3 Dual-Track Orchestrator

The top-level v3 entry point. Runs both tracks independently, determines conviction per track, handles "both" promotion.

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_orchestrator.py`
- Create: `engine/tests/scoring/test_v3_orchestrator.py`

**Step 1: Write the failing tests**

```python
"""Tests for v3 orchestrator — runs both tracks, assigns conviction, handles 'both'."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import (
    V3Result,
    V3TrackResult,
    orchestrate_v3,
)


def _track_a_exceptional() -> V3TrackResult:
    return V3TrackResult(
        track="compounder", qualifies=True,
        conviction=ConvictionLevel.EXCEPTIONAL,
        score=0.048, gates_passed=4, total_gates=4,
    )

def _track_b_exceptional() -> V3TrackResult:
    return V3TrackResult(
        track="mispricing", qualifies=True,
        conviction=ConvictionLevel.EXCEPTIONAL,
        score=9.0, gates_passed=4, total_gates=4,
    )

def _track_a_high() -> V3TrackResult:
    return V3TrackResult(
        track="compounder", qualifies=True,
        conviction=ConvictionLevel.HIGH,
        score=0.012, gates_passed=4, total_gates=4,
    )

def _track_not_qualified() -> V3TrackResult:
    return V3TrackResult(
        track="compounder", qualifies=False,
        conviction=ConvictionLevel.NONE,
        score=0.0, gates_passed=1, total_gates=4,
    )


class TestOrchestrate:
    def test_both_exceptional_promotes_to_both(self):
        result = orchestrate_v3(
            ticker="RARE", track_a=_track_a_exceptional(), track_b=_track_b_exceptional(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_only_track_a_qualifies(self):
        result = orchestrate_v3(
            ticker="COMP", track_a=_track_a_high(), track_b=_track_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder"
        assert result.conviction == ConvictionLevel.HIGH
        assert result.max_position_pct == 8.0

    def test_neither_qualifies(self):
        result = orchestrate_v3(
            ticker="MEDI",
            track_a=_track_not_qualified(),
            track_b=_track_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "neither"
        assert result.conviction == ConvictionLevel.NONE
        assert result.max_position_pct == 0.0

    def test_zero_output_valid(self):
        """System can output zero actionable results."""
        result = orchestrate_v3(
            ticker="NONE",
            track_a=_track_not_qualified(),
            track_b=_track_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_orchestrator.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

```python
"""v3 Orchestrator — runs both tracks independently, assigns conviction, handles 'both'.

This is the top-level v3 scoring entry point. It does NOT pick a winner —
each track produces an independent result. A stock can qualify on either, both, or neither.
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size


class V3TrackResult(BaseModel):
    """Result from a single track's gate cascade + scoring."""

    track: str  # "compounder" or "mispricing"
    qualifies: bool
    conviction: ConvictionLevel
    score: float
    gates_passed: int
    total_gates: int


class V3Result(BaseModel):
    """Final v3 scoring result for a single ticker."""

    ticker: str
    opportunity_type: str  # "compounder", "mispricing", "both", "neither"
    conviction: ConvictionLevel
    track_a: V3TrackResult
    track_b: V3TrackResult
    timing_signal: str
    max_position_pct: float


def orchestrate_v3(
    ticker: str,
    track_a: V3TrackResult,
    track_b: V3TrackResult,
    timing_signal: str,
) -> V3Result:
    """Orchestrate v3 scoring — combine independent track results.

    Rules:
    - Both tracks qualify at High+ -> "both", promoted to Exceptional, 20% position
    - Only Track A qualifies -> "compounder"
    - Only Track B qualifies -> "mispricing"
    - Neither qualifies -> "neither", 0% position
    """
    a_qualifies = track_a.qualifies and track_a.conviction in (
        ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST,
    )
    b_qualifies = track_b.qualifies and track_b.conviction in (
        ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST,
    )

    # "Both" promotion: both at High or Exceptional
    a_strong = track_a.conviction in (ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH)
    b_strong = track_b.conviction in (ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH)

    if a_qualifies and b_qualifies and a_strong and b_strong:
        conviction = ConvictionLevel.EXCEPTIONAL
        position = compute_v3_position_size("both", conviction)
        return V3Result(
            ticker=ticker,
            opportunity_type="both",
            conviction=conviction,
            track_a=track_a,
            track_b=track_b,
            timing_signal=timing_signal,
            max_position_pct=position,
        )

    if a_qualifies and (not b_qualifies or track_a.conviction.value <= track_b.conviction.value):
        conviction = track_a.conviction
        position = compute_v3_position_size("compounder", conviction)
        opp_type = "compounder"
    elif b_qualifies:
        conviction = track_b.conviction
        position = compute_v3_position_size("mispricing", conviction)
        opp_type = "mispricing"
    else:
        conviction = ConvictionLevel.NONE
        position = 0.0
        opp_type = "neither"

    return V3Result(
        ticker=ticker,
        opportunity_type=opp_type,
        conviction=conviction,
        track_a=track_a,
        track_b=track_b,
        timing_signal=timing_signal,
        max_position_pct=position,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_orchestrator.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_orchestrator.py engine/tests/scoring/test_v3_orchestrator.py
git commit -m "feat(engine): add v3 orchestrator with independent track results and 'both' promotion"
```

---

## Task 12: Update Scoring Package Exports

Update `__init__.py` to export v3 components alongside v1/v2 (backward compatible).

**Files:**
- Modify: `engine/src/margin_engine/scoring/__init__.py`

**Step 1: Update exports**

Add v3 exports to the existing `__init__.py`:

```python
# v3 exports (add after existing v2 exports)
from margin_engine.scoring.v3_composite import compute_track_a_score, compute_track_b_score
from margin_engine.scoring.v3_orchestrator import V3Result, V3TrackResult, orchestrate_v3
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size, MAX_POSITIONS
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction, assess_track_b_conviction
from margin_engine.scoring.market_regime import detect_regime, regime_adjustments, MarketRegime
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import reverse_dcf_growth_gap
from margin_engine.scoring.quantitative.ensemble_valuation import compute_ensemble_valuation
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
```

And add to `__all__`:

```python
    # v3 exports
    "compute_track_a_score",
    "compute_track_b_score",
    "orchestrate_v3",
    "V3Result",
    "V3TrackResult",
    "compute_v3_position_size",
    "MAX_POSITIONS",
    "assess_track_a_conviction",
    "assess_track_b_conviction",
    "detect_regime",
    "regime_adjustments",
    "MarketRegime",
    "moat_durability_score",
    "reverse_dcf_growth_gap",
    "compute_ensemble_valuation",
    "asset_floor_valuation",
```

**Step 2: Run full test suite to verify nothing breaks**

Run: `uv run pytest engine/tests/ -v`
Expected: All tests PASS (existing + new)

**Step 3: Commit**

```bash
git add engine/src/margin_engine/scoring/__init__.py
git commit -m "feat(engine): export v3 scoring components from scoring package"
```

---

## Task 13: Integration Test — Full v3 Pipeline

End-to-end test verifying the complete v3 scoring flow from raw financial data through to final conviction output.

**Files:**
- Create: `engine/tests/scoring/test_v3_integration.py`

**Step 1: Write the integration test**

```python
"""Integration test — full v3 pipeline from financial data to conviction output."""

import pytest
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import reverse_dcf_growth_gap
from margin_engine.scoring.quantitative.ensemble_valuation import compute_ensemble_valuation
from margin_engine.scoring.v3_composite import compute_track_a_score, compute_track_b_score
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction, assess_track_b_conviction
from margin_engine.scoring.v3_orchestrator import V3TrackResult, orchestrate_v3
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal


def _make_compounder_history() -> FinancialHistory:
    """5 years of data resembling a strong compounder (rising ROIC, margins)."""
    periods = []
    for i, year in enumerate(range(2019, 2024)):
        revenue = Decimal(str(500 + i * 200))
        ebit = Decimal(str(80 + i * 50))
        equity = Decimal(str(300 + i * 100))
        gross_profit = revenue * Decimal("0.45") + Decimal(str(i * 20))
        periods.append(FinancialPeriod(
            period_end=f"{year}-12-31",
            filing_date=f"{year + 1}-02-15",
            current_income=IncomeStatement(
                revenue=revenue, ebit=ebit,
                cost_of_revenue=revenue - gross_profit,
                gross_profit=gross_profit,
                depreciation=Decimal("30"),
                net_income=ebit * Decimal("0.79"),
                shares_outstanding=100,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("1500"),
                total_equity=equity,
                long_term_debt=Decimal("200"),
                short_term_debt=Decimal("50"),
                cash_and_equivalents=Decimal("50"),
                shares_outstanding=100,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=ebit * Decimal("1.1"),
                capital_expenditures=Decimal("-80"),
            ),
        ))
    return FinancialHistory(ticker="COMP", periods=periods)


class TestV3FullPipeline:
    def test_compounder_pipeline(self):
        """Strong compounder data flows through entire v3 pipeline."""
        history = _make_compounder_history()

        # Step 1: Moat durability
        moat = moat_durability_score(history)
        assert moat.raw_value >= 2.0, f"Expected 2+ moat signatures, got {moat.raw_value}"

        # Step 2: Reverse DCF growth gap
        gap = reverse_dcf_growth_gap(
            current_price=50.0, current_fcf=8.0, wacc=0.10,
            terminal_growth=0.025, shares_outstanding=100,
            sustainable_growth_rate=0.18,
        )
        assert gap.raw_value > 0, "Expected positive growth gap"

        # Step 3: Multiplicative score
        track_a_score = compute_track_a_score(
            moat_durability=moat.raw_value,
            compounding_power=0.15,
            capital_allocation=0.75,
            growth_gap=gap.raw_value,
        )
        assert track_a_score > 0

        # Step 4: Conviction assessment
        conviction = assess_track_a_conviction(
            gates_passed=4, total_gates=4,
            compounding_power=0.15,
            moat_durability=int(moat.raw_value),
            growth_gap=gap.raw_value,
        )
        assert conviction in (ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL)

        # Step 5: Timing
        timing = compute_v3_timing_signal(55.0, is_mispricing_track=False)
        assert timing == "buy_now"

        # Step 6: Orchestrate
        track_a = V3TrackResult(
            track="compounder", qualifies=True,
            conviction=conviction, score=track_a_score,
            gates_passed=4, total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing", qualifies=False,
            conviction=ConvictionLevel.NONE, score=0.0,
            gates_passed=1, total_gates=4,
        )
        result = orchestrate_v3("COMP", track_a, track_b, timing)
        assert result.opportunity_type == "compounder"
        assert result.max_position_pct > 0

    def test_neither_track_qualifies(self):
        """Mediocre company fails both tracks -> zero output."""
        track_a = V3TrackResult(
            track="compounder", qualifies=False,
            conviction=ConvictionLevel.NONE, score=0.0,
            gates_passed=1, total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing", qualifies=False,
            conviction=ConvictionLevel.NONE, score=0.0,
            gates_passed=1, total_gates=4,
        )
        result = orchestrate_v3("MEDI", track_a, track_b, "buy_now")
        assert result.opportunity_type == "neither"
        assert result.max_position_pct == 0.0
        assert result.conviction == ConvictionLevel.NONE
```

**Step 2: Run integration tests**

Run: `uv run pytest engine/tests/scoring/test_v3_integration.py -v`
Expected: All tests PASS

**Step 3: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All tests PASS (existing 784 + ~60 new)

**Step 4: Commit**

```bash
git add engine/tests/scoring/test_v3_integration.py
git commit -m "test(engine): add v3 full pipeline integration tests"
```

---

## Task Summary

| Task | Component | New Files | Tests |
|------|-----------|-----------|-------|
| 1 | Moat Durability Classifier | 2 | 6 |
| 2 | Reverse DCF | 2 | 9 |
| 3 | Ensemble Valuation | 2 | 7 |
| 4 | Asset-Based Floor | 2 | 5 |
| 5 | Market Regime Modifier | 2 | 12 |
| 6 | SBC + M&A (extend cap alloc) | 0 (modify) | 5 |
| 7 | v3 Conviction Thresholds | 2 | 9 |
| 8 | v3 Multiplicative Composite | 2 | 7 |
| 9 | v3 Position Sizing | 2 | 8 |
| 10 | v3 Timing Overlay | 0 (modify) | 5 |
| 11 | v3 Orchestrator | 2 | 4 |
| 12 | Package Exports | 0 (modify) | 0 (run existing) |
| 13 | Integration Test | 1 | 2 |

**Total: ~17 new files, ~79 new tests, 13 commits**

Tasks 1-6 are independent and can be parallelized. Tasks 7-11 depend on earlier tasks. Tasks 12-13 are final integration.
