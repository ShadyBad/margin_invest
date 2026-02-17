# Conviction Engine v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the scoring engine from a single-pipeline percentile screener into a two-track conviction system (Compounder + Mispricing) with moat durability, capital allocation, asymmetry detection, and position sizing.

**Architecture:** New factors and composites layer on top of the existing engine. Existing factors (gross profitability, accrual ratio, EV/FCF, acquirer's multiple, insider cluster, institutional accumulation, DCF) are retained and reused. New temporal factors (ROIC stability, incremental ROIC, reinvestment engine) require multi-year `FinancialPeriod` lists. Two separate composite scorers replace the single composite. Momentum moves to a post-conviction timing overlay.

**Tech Stack:** Python 3.13, Pydantic v2, pytest. All code in `engine/src/margin_engine/`. Tests in `engine/tests/`.

**Design Doc:** `docs/plans/2026-02-16-conviction-engine-redesign.md`

**Test Command:** `uv run pytest engine/tests/ -v`

---

## Phase 1: Data Models & Multi-Year Infrastructure

Foundation for everything else. No scoring logic yet — just models and data structures.

---

### Task 1: Add OpportunityType enum and new fields to scoring models

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Test: `engine/tests/models/test_scoring.py`

**Step 1: Write failing tests for new enums and model fields**

Add to `engine/tests/models/test_scoring.py`:

```python
from margin_engine.models.scoring import OpportunityType


class TestOpportunityType:
    def test_compounder_value(self):
        assert OpportunityType.COMPOUNDER == "compounder"

    def test_mispricing_value(self):
        assert OpportunityType.MISPRICING == "mispricing"

    def test_both_value(self):
        assert OpportunityType.BOTH == "both"

    def test_neither_value(self):
        assert OpportunityType.NEITHER == "neither"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/models/test_scoring.py::TestOpportunityType -v`
Expected: FAIL with `ImportError: cannot import name 'OpportunityType'`

**Step 3: Add OpportunityType enum to scoring models**

In `engine/src/margin_engine/models/scoring.py`, add after `GrowthStage`:

```python
class OpportunityType(StrEnum):
    COMPOUNDER = "compounder"
    MISPRICING = "mispricing"
    BOTH = "both"
    NEITHER = "neither"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/models/test_scoring.py::TestOpportunityType -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/models/test_scoring.py
git commit -m "feat: add OpportunityType enum to scoring models"
```

---

### Task 2: Add FactorBreakdown weighted percentile support

Currently `FactorBreakdown.average_percentile` is a simple mean. Add weighted average support.

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Test: `engine/tests/models/test_scoring.py`

**Step 1: Write failing tests for weighted percentile**

```python
class TestFactorBreakdownWeighted:
    def test_weighted_average_with_weights(self):
        """Sub-scores with explicit weights should use weighted average."""
        scores = [
            FactorScore(name="a", raw_value=1.0, percentile_rank=90.0, weight=0.6),
            FactorScore(name="b", raw_value=2.0, percentile_rank=70.0, weight=0.4),
        ]
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=scores)
        # 90*0.6 + 70*0.4 = 54 + 28 = 82.0
        assert bd.average_percentile == pytest.approx(82.0)

    def test_weighted_average_falls_back_to_simple_when_no_weights(self):
        """Sub-scores without weights should use simple average (backward compat)."""
        scores = [
            FactorScore(name="a", raw_value=1.0, percentile_rank=90.0),
            FactorScore(name="b", raw_value=2.0, percentile_rank=70.0),
        ]
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=scores)
        assert bd.average_percentile == pytest.approx(80.0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/models/test_scoring.py::TestFactorBreakdownWeighted -v`
Expected: FAIL — `FactorScore` doesn't have a `weight` field yet, and weighted logic isn't implemented.

**Step 3: Add optional weight field to FactorScore and weighted average to FactorBreakdown**

In `engine/src/margin_engine/models/scoring.py`:

Add to `FactorScore`:
```python
class FactorScore(BaseModel):
    name: str
    raw_value: float
    percentile_rank: float = Field(ge=0.0, le=100.0)
    detail: str = ""
    weight: float | None = None  # NEW: optional sub-factor weight within pillar
```

Update `FactorBreakdown.average_percentile`:
```python
@property
def average_percentile(self) -> float:
    if not self.sub_scores:
        return 0.0
    # Use weighted average if any sub-score has an explicit weight
    weights = [s.weight for s in self.sub_scores if s.weight is not None]
    if weights and len(weights) == len(self.sub_scores):
        total_weight = sum(weights)
        if total_weight > 0:
            return sum(
                s.percentile_rank * s.weight for s in self.sub_scores
            ) / total_weight
    # Fallback: simple average (backward compatibility)
    return sum(s.percentile_rank for s in self.sub_scores) / len(self.sub_scores)
```

**Step 4: Run full test suite to verify nothing breaks**

Run: `uv run pytest engine/tests/ -v`
Expected: All existing tests PASS + 2 new tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/models/test_scoring.py
git commit -m "feat: add weighted percentile support to FactorBreakdown"
```

---

### Task 3: Add CompositeScore v2 fields (opportunity_type, winning_track, asymmetry_ratio, position_sizing)

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Test: `engine/tests/models/test_scoring.py`

**Step 1: Write failing tests**

```python
class TestCompositeScoreV2Fields:
    def test_opportunity_type_defaults_to_none(self):
        score = _make_composite()  # existing helper
        assert score.opportunity_type is None

    def test_winning_track_defaults_to_none(self):
        score = _make_composite()
        assert score.winning_track is None

    def test_asymmetry_ratio_defaults_to_none(self):
        score = _make_composite()
        assert score.asymmetry_ratio is None

    def test_max_position_pct_defaults_to_none(self):
        score = _make_composite()
        assert score.max_position_pct is None

    def test_timing_signal_defaults_to_none(self):
        score = _make_composite()
        assert score.timing_signal is None
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/models/test_scoring.py::TestCompositeScoreV2Fields -v`
Expected: FAIL — fields don't exist yet.

**Step 3: Add fields to CompositeScore**

In `CompositeScore` class, add after `price_target_invalid_reason`:

```python
    # v2 conviction engine fields
    opportunity_type: OpportunityType | None = None
    winning_track: str | None = None  # "compounder" or "mispricing"
    asymmetry_ratio: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None  # "buy_now", "add_on_pullback", "wait_for_catalyst"

    # Capital allocation pillar (Track A)
    capital_allocation: FactorBreakdown | None = None
    # Catalyst pillar (Track B)
    catalyst: FactorBreakdown | None = None
```

**Step 4: Run full suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/models/test_scoring.py
git commit -m "feat: add v2 fields to CompositeScore (opportunity type, asymmetry, position sizing)"
```

---

### Task 4: Create FinancialHistory model for multi-year data

The new temporal factors need a list of annual financial data. Create a model to hold it.

**Files:**
- Create: (add to `engine/src/margin_engine/models/financial.py`)
- Test: `engine/tests/models/test_financial.py`

**Step 1: Write failing tests**

Create or add to `engine/tests/models/test_financial.py`:

```python
from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(year: int, revenue: Decimal, ebit: Decimal, net_income: Decimal,
                 cfo: Decimal, capex: Decimal, total_equity: Decimal,
                 total_debt: Decimal, cash: Decimal, total_assets: Decimal) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue, ebit=ebit, net_income=net_income,
            cost_of_revenue=revenue * Decimal("0.6"),
            gross_profit=revenue * Decimal("0.4"),
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=total_debt, cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo, capital_expenditures=capex,
        ),
    )


class TestFinancialHistory:
    def test_requires_at_least_one_period(self):
        with pytest.raises(ValueError, match="at least 1"):
            FinancialHistory(ticker="TEST", periods=[])

    def test_periods_sorted_by_period_end(self):
        p2020 = _make_period(2020, Decimal("100"), Decimal("20"), Decimal("15"),
                             Decimal("25"), Decimal("-5"), Decimal("50"),
                             Decimal("20"), Decimal("10"), Decimal("100"))
        p2021 = _make_period(2021, Decimal("120"), Decimal("25"), Decimal("18"),
                             Decimal("30"), Decimal("-6"), Decimal("60"),
                             Decimal("25"), Decimal("12"), Decimal("120"))
        h = FinancialHistory(ticker="TEST", periods=[p2021, p2020])
        assert h.periods[0].period_end == "2020-12-31"
        assert h.periods[1].period_end == "2021-12-31"

    def test_years_of_data(self):
        periods = [
            _make_period(y, Decimal("100"), Decimal("20"), Decimal("15"),
                         Decimal("25"), Decimal("-5"), Decimal("50"),
                         Decimal("20"), Decimal("10"), Decimal("100"))
            for y in range(2019, 2024)
        ]
        h = FinancialHistory(ticker="TEST", periods=periods)
        assert h.years_of_data == 5
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/models/test_financial.py::TestFinancialHistory -v`
Expected: FAIL — `FinancialHistory` doesn't exist.

**Step 3: Implement FinancialHistory**

Add to end of `engine/src/margin_engine/models/financial.py`:

```python
class FinancialHistory(BaseModel):
    """Multi-year financial data for temporal analysis.

    Periods are sorted by period_end ascending on construction.
    """

    ticker: str
    periods: list[FinancialPeriod]

    @field_validator("periods")
    @classmethod
    def validate_periods(cls, v: list[FinancialPeriod]) -> list[FinancialPeriod]:
        if len(v) < 1:
            raise ValueError("FinancialHistory requires at least 1 period")
        return sorted(v, key=lambda p: p.period_end)

    @property
    def years_of_data(self) -> int:
        return len(self.periods)
```

Add `field_validator` to the imports at the top of the file:
```python
from pydantic import BaseModel, field_validator
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/models/test_financial.py::TestFinancialHistory -v`
Expected: PASS (3 tests)

**Step 5: Run full suite to verify nothing breaks**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/models/financial.py engine/tests/models/test_financial.py
git commit -m "feat: add FinancialHistory model for multi-year temporal analysis"
```

---

## Phase 2: New Quality Factors (Temporal)

These replace the single-period quality factors with durability and compounding metrics.

---

### Task 5: ROIC Stability factor (5yr median + coefficient of variation)

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/roic_stability.py`
- Test: `engine/tests/scoring/quantitative/test_roic_stability.py`

**Step 1: Write failing tests**

```python
"""Tests for ROIC Stability quality factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.roic_stability import roic_stability


def _make_period(year: int, ebit: Decimal, tax_provision: Decimal,
                 total_equity: Decimal, total_debt: Decimal,
                 cash: Decimal) -> FinancialPeriod:
    """Build a minimal FinancialPeriod with ROIC-relevant fields."""
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), ebit=ebit,
            tax_provision=tax_provision,
            interest_expense=Decimal("10"),
            net_income=ebit - tax_provision,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=total_equity,
            long_term_debt=total_debt,
            cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200"),
            capital_expenditures=Decimal("-50"),
        ),
    )


def _make_history_stable() -> FinancialHistory:
    """5 years of stable, high ROIC (~15.8% each year).
    NOPAT = 200 * (1-0.21) = 158. IC = 500 + 300 - 100 = 700. ROIC = 158/700 = 0.2257
    """
    periods = [
        _make_period(y, Decimal("200"), Decimal("42"), Decimal("500"),
                     Decimal("300"), Decimal("100"))
        for y in range(2019, 2024)
    ]
    return FinancialHistory(ticker="STABLE", periods=periods)


def _make_history_volatile() -> FinancialHistory:
    """5 years of volatile ROIC."""
    ebits = [Decimal("200"), Decimal("50"), Decimal("300"), Decimal("80"), Decimal("250")]
    periods = [
        _make_period(2019 + i, ebit, ebit * Decimal("0.21"), Decimal("500"),
                     Decimal("300"), Decimal("100"))
        for i, ebit in enumerate(ebits)
    ]
    return FinancialHistory(ticker="VOLATILE", periods=periods)


class TestRoicStability:
    def test_stable_high_roic(self):
        """Stable business should have high score (high median, low CV)."""
        result = roic_stability(_make_history_stable())
        assert result.name == "roic_stability"
        # Median ROIC ~0.2257, CV ~0 → score ≈ 0.2257 * 1.0 = 0.2257
        assert result.raw_value == pytest.approx(0.2257, abs=0.01)

    def test_volatile_roic_penalized(self):
        """Volatile business should have lower score than stable one."""
        stable = roic_stability(_make_history_stable())
        volatile = roic_stability(_make_history_volatile())
        assert volatile.raw_value < stable.raw_value

    def test_single_period_returns_score(self):
        """With only 1 period, CV is 0, score = ROIC."""
        h = FinancialHistory(ticker="ONE", periods=[
            _make_period(2023, Decimal("200"), Decimal("42"), Decimal("500"),
                         Decimal("300"), Decimal("100"))
        ])
        result = roic_stability(h)
        assert result.raw_value == pytest.approx(0.2257, abs=0.01)

    def test_percentile_rank_is_placeholder(self):
        result = roic_stability(_make_history_stable())
        assert result.percentile_rank == 0.0

    def test_zero_invested_capital_returns_zero(self):
        """IC = equity + debt - cash. If zero or negative, ROIC undefined."""
        periods = [
            _make_period(y, Decimal("200"), Decimal("42"), Decimal("100"),
                         Decimal("0"), Decimal("200"))  # IC = 100+0-200 = -100
            for y in range(2019, 2024)
        ]
        h = FinancialHistory(ticker="NEGIC", periods=periods)
        result = roic_stability(h)
        assert result.raw_value == 0.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_roic_stability.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement roic_stability**

Create `engine/src/margin_engine/scoring/quantitative/roic_stability.py`:

```python
"""ROIC Stability quality factor — moat durability over time.

Measures median ROIC over a multi-year window, penalized by
coefficient of variation. Stable high ROIC = durable moat.

Score = median_ROIC * (1 - CV)

Where:
    ROIC = NOPAT / Invested Capital (per year)
    NOPAT = EBIT * (1 - effective_tax_rate)
    Invested Capital = Total Equity + Total Debt - Cash
    CV = StdDev(ROIC series) / Mean(ROIC series)
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _compute_period_roic(period: FinancialPeriod) -> float | None:
    """Compute ROIC for a single period. Returns None if IC <= 0."""
    ci = period.current_income
    cb = period.current_balance

    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    cash = float(cb.cash_and_equivalents or Decimal("0"))
    total_equity = float(cb.total_equity)
    total_debt = float(cb.total_debt)
    invested_capital = total_equity + total_debt - cash

    if invested_capital <= 0:
        return None

    return nopat / invested_capital


def roic_stability(history: FinancialHistory) -> FactorScore:
    """Compute ROIC stability score from multi-year financial history.

    Score = median_ROIC * (1 - CV), where CV is clamped to [0, 1].
    Returns FactorScore with percentile_rank=0.0 (placeholder).
    """
    roics = []
    for period in history.periods:
        r = _compute_period_roic(period)
        if r is not None:
            roics.append(r)

    if not roics:
        return FactorScore(
            name="roic_stability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No valid ROIC periods (invested capital <= 0)",
        )

    median_roic = statistics.median(roics)

    if len(roics) < 2:
        cv = 0.0
    else:
        mean_roic = statistics.mean(roics)
        if mean_roic == 0:
            cv = 1.0
        else:
            stdev = statistics.stdev(roics)
            cv = min(1.0, abs(stdev / mean_roic))

    score = median_roic * (1.0 - cv)

    return FactorScore(
        name="roic_stability",
        raw_value=score,
        percentile_rank=0.0,
        detail=(
            f"median_ROIC={median_roic:.4f}, CV={cv:.4f}, "
            f"score={score:.4f}, periods={len(roics)}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_roic_stability.py -v`
Expected: PASS (5 tests)

**Step 5: Run full suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/roic_stability.py \
       engine/tests/scoring/quantitative/test_roic_stability.py
git commit -m "feat: add ROIC stability factor (5yr median * (1-CV))"
```

---

### Task 6: Incremental ROIC factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/incremental_roic.py`
- Test: `engine/tests/scoring/quantitative/test_incremental_roic.py`

**Step 1: Write failing tests**

```python
"""Tests for Incremental ROIC factor — return on NEW capital deployed."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, IncomeStatement,
)
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic


def _make_period(year: int, nopat_proxy_ebit: Decimal,
                 total_equity: Decimal, total_debt: Decimal,
                 cash: Decimal) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), ebit=nopat_proxy_ebit,
            net_income=nopat_proxy_ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=total_equity,
            long_term_debt=total_debt,
            cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200"),
            capital_expenditures=Decimal("-50"),
        ),
    )


class TestIncrementalRoic:
    def test_positive_incremental_roic(self):
        """Growing NOPAT on growing IC = positive incremental ROIC."""
        # Year 1: NOPAT = 200*0.79 = 158, IC = 500+200-100 = 600
        # Year 3: NOPAT = 300*0.79 = 237, IC = 700+300-100 = 900
        # Incremental ROIC = (237-158)/(900-600) = 79/300 = 0.2633
        periods = [
            _make_period(2021, Decimal("200"), Decimal("500"), Decimal("200"), Decimal("100")),
            _make_period(2022, Decimal("250"), Decimal("600"), Decimal("250"), Decimal("100")),
            _make_period(2023, Decimal("300"), Decimal("700"), Decimal("300"), Decimal("100")),
        ]
        h = FinancialHistory(ticker="GROW", periods=periods)
        result = incremental_roic(h)
        assert result.name == "incremental_roic"
        assert result.raw_value == pytest.approx(0.2633, abs=0.01)

    def test_zero_change_in_ic_returns_zero(self):
        """No change in invested capital means incremental ROIC is undefined."""
        periods = [
            _make_period(2021, Decimal("200"), Decimal("500"), Decimal("200"), Decimal("100")),
            _make_period(2023, Decimal("300"), Decimal("500"), Decimal("200"), Decimal("100")),
        ]
        h = FinancialHistory(ticker="FLAT", periods=periods)
        result = incremental_roic(h)
        assert result.raw_value == 0.0

    def test_single_period_returns_zero(self):
        """Need at least 2 periods to compute change."""
        h = FinancialHistory(ticker="ONE", periods=[
            _make_period(2023, Decimal("200"), Decimal("500"), Decimal("200"), Decimal("100")),
        ])
        result = incremental_roic(h)
        assert result.raw_value == 0.0

    def test_percentile_rank_is_placeholder(self):
        h = FinancialHistory(ticker="ONE", periods=[
            _make_period(2023, Decimal("200"), Decimal("500"), Decimal("200"), Decimal("100")),
        ])
        result = incremental_roic(h)
        assert result.percentile_rank == 0.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_incremental_roic.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/incremental_roic.py`:

```python
"""Incremental ROIC factor — return on NEW capital deployed.

Measures whether new capital is earning above cost of capital.
Widening moats show rising incremental ROIC; narrowing moats show falling.

Formula:
    Incremental ROIC = (NOPAT_latest - NOPAT_earliest) / (IC_latest - IC_earliest)

Uses the first and last period in the history (typically 3yr span).
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _nopat(period: FinancialPeriod) -> float:
    ebit = float(period.current_income.ebit)
    tax_rate = period.current_income.effective_tax_rate
    return ebit * (1.0 - tax_rate)


def _invested_capital(period: FinancialPeriod) -> float:
    cb = period.current_balance
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    return float(cb.total_equity) + float(cb.total_debt) - cash


def incremental_roic(history: FinancialHistory) -> FactorScore:
    """Compute incremental ROIC from earliest to latest period.

    Returns FactorScore with percentile_rank=0.0 (placeholder).
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="incremental_roic",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need at least 2 periods for incremental ROIC",
        )

    earliest = history.periods[0]
    latest = history.periods[-1]

    nopat_earliest = _nopat(earliest)
    nopat_latest = _nopat(latest)
    ic_earliest = _invested_capital(earliest)
    ic_latest = _invested_capital(latest)

    delta_ic = ic_latest - ic_earliest
    delta_nopat = nopat_latest - nopat_earliest

    if abs(delta_ic) < 1.0:  # No meaningful change in invested capital
        return FactorScore(
            name="incremental_roic",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"delta_IC={delta_ic:.2f} (< $1, no meaningful change), "
                f"delta_NOPAT={delta_nopat:.2f}"
            ),
        )

    inc_roic = delta_nopat / delta_ic

    return FactorScore(
        name="incremental_roic",
        raw_value=inc_roic,
        percentile_rank=0.0,
        detail=(
            f"NOPAT: {nopat_earliest:.2f} → {nopat_latest:.2f} "
            f"(Δ={delta_nopat:.2f}), "
            f"IC: {ic_earliest:.2f} → {ic_latest:.2f} "
            f"(Δ={delta_ic:.2f}), "
            f"Incremental ROIC={inc_roic:.4f}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_incremental_roic.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/incremental_roic.py \
       engine/tests/scoring/quantitative/test_incremental_roic.py
git commit -m "feat: add incremental ROIC factor (return on new capital deployed)"
```

---

### Task 7: Reinvestment Engine factor (ROIC * Reinvestment Rate)

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/reinvestment_engine.py`
- Test: `engine/tests/scoring/quantitative/test_reinvestment_engine.py`

**Step 1: Write failing tests**

```python
"""Tests for Reinvestment Engine factor — organic compounding power."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialPeriod, IncomeStatement,
)
from margin_engine.scoring.quantitative.reinvestment_engine import reinvestment_engine


def _make_period(
    ebit: Decimal = Decimal("200"),
    depreciation: Decimal = Decimal("30"),
    capex: Decimal = Decimal("-80"),
    total_equity: Decimal = Decimal("500"),
    total_debt: Decimal = Decimal("200"),
    cash: Decimal = Decimal("100"),
    cfo: Decimal = Decimal("250"),
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2023-12-31",
        filing_date="2024-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), ebit=ebit,
            depreciation=depreciation,
            net_income=ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=total_equity,
            long_term_debt=total_debt,
            cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo,
            capital_expenditures=capex,
        ),
    )


class TestReinvestmentEngine:
    def test_high_reinvestment_high_roic(self):
        """Business reinvesting heavily at high ROIC should score high."""
        # NOPAT = 200*0.79 = 158, IC = 500+200-100 = 600, ROIC = 158/600 = 0.2633
        # Growth CapEx = |capex| - depreciation = 80 - 30 = 50
        # Reinvestment Rate = 50 / 158 = 0.3165
        # Score = 0.2633 * 0.3165 = 0.0833
        result = reinvestment_engine(_make_period())
        assert result.name == "reinvestment_engine"
        assert result.raw_value == pytest.approx(0.0833, abs=0.005)

    def test_no_growth_capex_returns_zero(self):
        """If capex < depreciation, no growth investment, score = 0."""
        result = reinvestment_engine(_make_period(
            capex=Decimal("-20"), depreciation=Decimal("30"),
        ))
        assert result.raw_value == 0.0

    def test_zero_invested_capital(self):
        result = reinvestment_engine(_make_period(
            total_equity=Decimal("50"), total_debt=Decimal("0"), cash=Decimal("100"),
        ))
        assert result.raw_value == 0.0

    def test_percentile_placeholder(self):
        result = reinvestment_engine(_make_period())
        assert result.percentile_rank == 0.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reinvestment_engine.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/reinvestment_engine.py`:

```python
"""Reinvestment Engine factor — organic compounding power.

Measures how much of earnings are being reinvested at high returns.
Score = ROIC * Reinvestment Rate

Where:
    ROIC = NOPAT / Invested Capital
    Reinvestment Rate = Growth CapEx / NOPAT
    Growth CapEx = |CapEx| - Depreciation (net new investment)
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def reinvestment_engine(period: FinancialPeriod) -> FactorScore:
    """Compute reinvestment engine score (ROIC * Reinvestment Rate).

    Returns FactorScore with percentile_rank=0.0 (placeholder).
    """
    ci = period.current_income
    cb = period.current_balance
    cf = period.current_cash_flow

    # ROIC
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    cash = float(cb.cash_and_equivalents or Decimal("0"))
    invested_capital = float(cb.total_equity) + float(cb.total_debt) - cash

    if invested_capital <= 0 or nopat <= 0:
        return FactorScore(
            name="reinvestment_engine",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"IC={invested_capital:.2f}, NOPAT={nopat:.2f} — non-positive",
        )

    roic = nopat / invested_capital

    # Growth CapEx = |CapEx| - Depreciation
    capex_abs = abs(float(cf.capital_expenditures))
    depreciation = float(ci.depreciation or Decimal("0"))
    growth_capex = capex_abs - depreciation

    if growth_capex <= 0:
        return FactorScore(
            name="reinvestment_engine",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"ROIC={roic:.4f}, growth_capex={growth_capex:.2f} "
                f"(capex={capex_abs:.2f}, depr={depreciation:.2f}) — no growth investment"
            ),
        )

    reinvestment_rate = growth_capex / nopat
    score = roic * reinvestment_rate

    return FactorScore(
        name="reinvestment_engine",
        raw_value=score,
        percentile_rank=0.0,
        detail=(
            f"ROIC={roic:.4f}, RR={reinvestment_rate:.4f}, "
            f"score={score:.4f} "
            f"(NOPAT={nopat:.2f}, IC={invested_capital:.2f}, "
            f"growth_capex={growth_capex:.2f})"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reinvestment_engine.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/reinvestment_engine.py \
       engine/tests/scoring/quantitative/test_reinvestment_engine.py
git commit -m "feat: add reinvestment engine factor (ROIC * reinvestment rate)"
```

---

### Task 8: Owner Earnings Yield factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/owner_earnings.py`
- Test: `engine/tests/scoring/quantitative/test_owner_earnings.py`

**Step 1: Write failing tests**

```python
"""Tests for Owner Earnings Yield (Buffett-adjusted FCF / EV)."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.scoring.quantitative.owner_earnings import owner_earnings_yield


def _make_data(
    cfo: Decimal = Decimal("200"),
    capex: Decimal = Decimal("-80"),
    depreciation: Decimal = Decimal("50"),
    market_cap: Decimal = Decimal("2000"),
    total_debt: Decimal = Decimal("300"),
    cash: Decimal = Decimal("100"),
) -> tuple[FinancialPeriod, AssetProfile]:
    period = FinancialPeriod(
        period_end="2023-12-31", filing_date="2024-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), ebit=Decimal("200"),
            depreciation=depreciation, net_income=Decimal("150"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"), total_equity=Decimal("500"),
            long_term_debt=total_debt, cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo, capital_expenditures=capex,
        ),
    )
    profile = AssetProfile(
        ticker="TEST", name="Test Co", sector=GICSSector.TECHNOLOGY,
        market_cap=market_cap,
    )
    return period, profile


class TestOwnerEarningsYield:
    def test_basic_computation(self):
        """Owner Earnings = CFO - Maintenance CapEx. Yield = OE / EV."""
        period, profile = _make_data()
        # Maintenance CapEx = depreciation * 1.1 = 50 * 1.1 = 55
        # Owner Earnings = 200 - 55 = 145
        # EV = 2000 + 300 - 100 = 2200
        # Yield = 145 / 2200 = 0.0659
        result = owner_earnings_yield(period, profile)
        assert result.name == "owner_earnings_yield"
        assert result.raw_value == pytest.approx(0.0659, abs=0.001)

    def test_zero_ev_returns_zero(self):
        period, profile = _make_data(
            market_cap=Decimal("0"), total_debt=Decimal("0"), cash=Decimal("100"),
        )
        result = owner_earnings_yield(period, profile)
        assert result.raw_value == 0.0

    def test_negative_owner_earnings_returns_zero(self):
        """If maintenance capex exceeds CFO, owner earnings are negative."""
        period, profile = _make_data(cfo=Decimal("40"), depreciation=Decimal("50"))
        result = owner_earnings_yield(period, profile)
        assert result.raw_value == 0.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_owner_earnings.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/owner_earnings.py`:

```python
"""Owner Earnings Yield — Buffett-adjusted FCF / Enterprise Value.

Owner Earnings = CFO - Maintenance CapEx
Maintenance CapEx estimated as Depreciation * 1.1 (conservative buffer).
Yield = Owner Earnings / Enterprise Value.

Higher yield = business generating more real cash relative to its cost.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, FinancialPeriod
from margin_engine.models.scoring import FactorScore

_MAINTENANCE_MULTIPLIER = 1.1


def owner_earnings_yield(period: FinancialPeriod, profile: AssetProfile) -> FactorScore:
    """Compute owner earnings yield.

    Returns FactorScore with percentile_rank=0.0 (placeholder).
    """
    cfo = float(period.current_cash_flow.operating_cash_flow)
    depreciation = float(period.current_income.depreciation or Decimal("0"))
    maintenance_capex = depreciation * _MAINTENANCE_MULTIPLIER

    owner_earnings = cfo - maintenance_capex
    if owner_earnings <= 0:
        return FactorScore(
            name="owner_earnings_yield",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"CFO={cfo:.2f}, maintenance_capex={maintenance_capex:.2f}, "
                f"owner_earnings={owner_earnings:.2f} (non-positive)"
            ),
        )

    cash = float(
        period.current_balance.cash_and_equivalents or Decimal("0")
    )
    ev = float(profile.market_cap) + float(period.current_balance.total_debt) - cash

    if ev <= 0:
        return FactorScore(
            name="owner_earnings_yield",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"EV={ev:.2f} (non-positive)",
        )

    yield_val = owner_earnings / ev

    return FactorScore(
        name="owner_earnings_yield",
        raw_value=yield_val,
        percentile_rank=0.0,
        detail=(
            f"OE={owner_earnings:.2f} (CFO={cfo:.2f} - maint={maintenance_capex:.2f}), "
            f"EV={ev:.2f}, yield={yield_val:.4f}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_owner_earnings.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/owner_earnings.py \
       engine/tests/scoring/quantitative/test_owner_earnings.py
git commit -m "feat: add owner earnings yield factor (Buffett-adjusted FCF / EV)"
```

---

### Task 9: Runway Score factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/runway_score.py`
- Test: `engine/tests/scoring/quantitative/test_runway_score.py`

**Step 1: Write failing tests**

```python
"""Tests for Runway Score — revenue as % of sub-industry total."""

from decimal import Decimal

import pytest
from margin_engine.scoring.quantitative.runway_score import runway_score


class TestRunwayScore:
    def test_small_fish_big_pond(self):
        """$1B company in $100B industry = 1% penetration = massive runway."""
        result = runway_score(
            company_revenue=Decimal("1000000000"),
            sub_industry_revenue=Decimal("100000000000"),
        )
        assert result.name == "runway_score"
        # Penetration = 1%, raw_value = 0.01 (lower = more runway, invert at ranking)
        assert result.raw_value == pytest.approx(0.01)

    def test_big_fish_small_pond(self):
        """$50B company in $60B industry = 83% penetration = limited runway."""
        result = runway_score(
            company_revenue=Decimal("50000000000"),
            sub_industry_revenue=Decimal("60000000000"),
        )
        assert result.raw_value == pytest.approx(0.8333, abs=0.01)

    def test_zero_industry_revenue_returns_one(self):
        result = runway_score(
            company_revenue=Decimal("1000"),
            sub_industry_revenue=Decimal("0"),
        )
        assert result.raw_value == 1.0

    def test_missing_industry_data(self):
        result = runway_score(
            company_revenue=Decimal("1000"),
            sub_industry_revenue=None,
        )
        assert result.raw_value == 0.5  # neutral default
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_runway_score.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/runway_score.py`:

```python
"""Runway Score — company revenue as percentage of sub-industry total.

Lower penetration = more runway for growth. Inverted at ranking time.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.scoring import FactorScore

_NEUTRAL_DEFAULT = 0.5


def runway_score(
    company_revenue: Decimal,
    sub_industry_revenue: Decimal | None,
) -> FactorScore:
    """Compute runway score as revenue penetration ratio.

    raw_value = company_revenue / sub_industry_revenue (0 to 1+).
    Lower = more runway. Invert at percentile ranking.
    """
    if sub_industry_revenue is None:
        return FactorScore(
            name="runway_score",
            raw_value=_NEUTRAL_DEFAULT,
            percentile_rank=0.0,
            detail="sub_industry_revenue unavailable, using neutral default",
        )

    if sub_industry_revenue <= 0:
        return FactorScore(
            name="runway_score",
            raw_value=1.0,
            percentile_rank=0.0,
            detail="sub_industry_revenue <= 0, assuming saturated",
        )

    penetration = float(company_revenue / sub_industry_revenue)

    return FactorScore(
        name="runway_score",
        raw_value=penetration,
        percentile_rank=0.0,
        detail=(
            f"revenue={company_revenue}, industry={sub_industry_revenue}, "
            f"penetration={penetration:.4f}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_runway_score.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/runway_score.py \
       engine/tests/scoring/quantitative/test_runway_score.py
git commit -m "feat: add runway score factor (revenue penetration of sub-industry)"
```

---

### Task 10: Asymmetry Ratio factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/asymmetry.py`
- Test: `engine/tests/scoring/quantitative/test_asymmetry.py`

**Step 1: Write failing tests**

```python
"""Tests for Asymmetry Ratio — upside/downside structure."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import BalanceSheet
from margin_engine.scoring.quantitative.asymmetry import asymmetry_ratio


class TestAsymmetryRatio:
    def test_strong_asymmetry(self):
        """Large upside, small downside = high ratio."""
        # Intrinsic = 180, Price = 100, Floor = 80
        # Upside = 80, Downside = 20, Ratio = 4.0
        result = asymmetry_ratio(
            intrinsic_value=180.0,
            current_price=100.0,
            net_cash_per_share=80.0,
            tangible_book_per_share=60.0,
        )
        assert result.name == "asymmetry_ratio"
        assert result.raw_value == pytest.approx(4.0)

    def test_weak_asymmetry(self):
        """Small upside, large downside = low ratio."""
        # Intrinsic = 120, Price = 100, Floor = 30
        # Upside = 20, Downside = 70, Ratio = 0.286
        result = asymmetry_ratio(
            intrinsic_value=120.0,
            current_price=100.0,
            net_cash_per_share=30.0,
            tangible_book_per_share=20.0,
        )
        assert result.raw_value == pytest.approx(0.286, abs=0.01)

    def test_overvalued_returns_zero(self):
        """If intrinsic < price, no upside, ratio = 0."""
        result = asymmetry_ratio(
            intrinsic_value=80.0,
            current_price=100.0,
            net_cash_per_share=50.0,
            tangible_book_per_share=40.0,
        )
        assert result.raw_value == 0.0

    def test_negative_floor_uses_zero(self):
        """If both net cash and tangible book are negative, floor = 0."""
        # Intrinsic = 150, Price = 100, Floor = 0
        # Upside = 50, Downside = 100, Ratio = 0.5
        result = asymmetry_ratio(
            intrinsic_value=150.0,
            current_price=100.0,
            net_cash_per_share=-20.0,
            tangible_book_per_share=-10.0,
        )
        assert result.raw_value == pytest.approx(0.5)

    def test_floor_equals_price_returns_inf_capped(self):
        """If floor >= price, downside = 0, cap ratio at 100."""
        result = asymmetry_ratio(
            intrinsic_value=200.0,
            current_price=100.0,
            net_cash_per_share=100.0,
            tangible_book_per_share=50.0,
        )
        assert result.raw_value == 100.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_asymmetry.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/asymmetry.py`:

```python
"""Asymmetry Ratio — upside potential relative to downside risk.

Ratio = (Intrinsic Value - Price) / (Price - Downside Floor)

Where Floor = max(Net Cash per Share, Tangible Book per Share, 0)

Higher ratio = more asymmetric (limited downside, large upside).
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_MAX_RATIO = 100.0  # Cap to avoid infinity


def asymmetry_ratio(
    intrinsic_value: float,
    current_price: float,
    net_cash_per_share: float,
    tangible_book_per_share: float,
) -> FactorScore:
    """Compute asymmetry ratio.

    Returns FactorScore with percentile_rank=0.0 (placeholder).
    """
    upside = intrinsic_value - current_price
    if upside <= 0:
        return FactorScore(
            name="asymmetry_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"intrinsic={intrinsic_value:.2f}, price={current_price:.2f}, "
                f"upside={upside:.2f} (overvalued)"
            ),
        )

    floor = max(net_cash_per_share, tangible_book_per_share, 0.0)
    downside = current_price - floor

    if downside <= 0:
        ratio = _MAX_RATIO
    else:
        ratio = min(upside / downside, _MAX_RATIO)

    return FactorScore(
        name="asymmetry_ratio",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"intrinsic={intrinsic_value:.2f}, price={current_price:.2f}, "
            f"floor={floor:.2f}, upside={upside:.2f}, downside={downside:.2f}, "
            f"ratio={ratio:.2f}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_asymmetry.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/asymmetry.py \
       engine/tests/scoring/quantitative/test_asymmetry.py
git commit -m "feat: add asymmetry ratio factor (upside/downside structure)"
```

---

## Phase 3: Capital Allocation & Opportunity Classification

---

### Task 11: Capital Allocation Score (buyback effectiveness, debt discipline, organic reinvestment, insider ownership)

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/capital_allocation.py`
- Test: `engine/tests/scoring/quantitative/test_capital_allocation.py`

This is a compound factor that computes 4 sub-scores and returns them as a list.

**Step 1: Write failing tests**

```python
"""Tests for Capital Allocation sub-factors."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, IncomeStatement,
)
from margin_engine.scoring.quantitative.capital_allocation import (
    buyback_effectiveness,
    debt_discipline,
    organic_reinvestment_ratio,
    insider_ownership_score,
)


def _make_period(
    year: int,
    share_repurchases: Decimal = Decimal("-100"),
    shares_outstanding: int = 1000,
    long_term_debt: Decimal = Decimal("500"),
    ebit: Decimal = Decimal("200"),
    depreciation: Decimal = Decimal("30"),
    capex: Decimal = Decimal("-80"),
    dividends: Decimal = Decimal("-30"),
    cfo: Decimal = Decimal("250"),
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), ebit=ebit,
            depreciation=depreciation,
            net_income=ebit * Decimal("0.79"),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"), total_equity=Decimal("800"),
            long_term_debt=long_term_debt,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo, capital_expenditures=capex,
            dividends_paid=dividends, share_repurchases=share_repurchases,
        ),
    )


class TestBuybackEffectiveness:
    def test_buying_below_average(self):
        """If avg repurchase price < avg stock price, ratio < 1 = effective."""
        result = buyback_effectiveness(
            total_repurchases=Decimal("1000000"),
            shares_reduced=100,
            avg_stock_price=12000.0,
        )
        # Avg buyback price = 1000000 / 100 = 10000
        # Ratio = 10000 / 12000 = 0.833
        assert result.name == "buyback_effectiveness"
        assert result.raw_value == pytest.approx(0.833, abs=0.01)

    def test_no_buybacks_returns_neutral(self):
        result = buyback_effectiveness(
            total_repurchases=Decimal("0"),
            shares_reduced=0,
            avg_stock_price=100.0,
        )
        assert result.raw_value == 0.5  # neutral


class TestDebtDiscipline:
    def test_declining_leverage(self):
        """Net Debt / EBITDA declining over time = disciplined."""
        periods = [
            _make_period(2021, long_term_debt=Decimal("800")),
            _make_period(2022, long_term_debt=Decimal("600")),
            _make_period(2023, long_term_debt=Decimal("400")),
        ]
        h = FinancialHistory(ticker="DISC", periods=periods)
        result = debt_discipline(h)
        assert result.name == "debt_discipline"
        assert result.raw_value < 0  # Negative slope = improving


class TestOrganicReinvestmentRatio:
    def test_high_reinvestment(self):
        """Most capital deployed to growth capex = high ratio."""
        # Growth capex = |capex| - depr = 80 - 30 = 50
        # Total deployed = growth_capex + |buybacks| + |dividends| = 50 + 100 + 30 = 180
        # Ratio = 50 / 180 = 0.2778
        period = _make_period(2023)
        result = organic_reinvestment_ratio(period)
        assert result.name == "organic_reinvestment_ratio"
        assert result.raw_value == pytest.approx(0.2778, abs=0.01)


class TestInsiderOwnership:
    def test_basic(self):
        result = insider_ownership_score(ownership_pct=0.15)
        assert result.name == "insider_ownership"
        assert result.raw_value == pytest.approx(0.15)

    def test_zero(self):
        result = insider_ownership_score(ownership_pct=0.0)
        assert result.raw_value == 0.0
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_capital_allocation.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/capital_allocation.py`:

```python
"""Capital Allocation sub-factors.

Four metrics measuring management's skill at deploying capital:
1. Buyback Effectiveness — buying below average price
2. Debt Discipline — Net Debt / EBITDA trend
3. Organic Reinvestment Ratio — growth capex vs total deployment
4. Insider Ownership — skin in the game
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def buyback_effectiveness(
    total_repurchases: Decimal,
    shares_reduced: int,
    avg_stock_price: float,
) -> FactorScore:
    """Ratio of avg buyback price to avg stock price. < 1.0 = buying cheap."""
    if shares_reduced <= 0 or total_repurchases <= 0:
        return FactorScore(
            name="buyback_effectiveness",
            raw_value=0.5,
            percentile_rank=0.0,
            detail="No buybacks, neutral score",
        )

    avg_buyback_price = float(abs(total_repurchases)) / shares_reduced
    if avg_stock_price <= 0:
        return FactorScore(
            name="buyback_effectiveness",
            raw_value=0.5,
            percentile_rank=0.0,
            detail="avg_stock_price <= 0",
        )

    ratio = avg_buyback_price / avg_stock_price

    return FactorScore(
        name="buyback_effectiveness",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=f"avg_buyback={avg_buyback_price:.2f}, avg_price={avg_stock_price:.2f}, ratio={ratio:.4f}",
    )


def debt_discipline(history: FinancialHistory) -> FactorScore:
    """5yr slope of Net Debt / EBITDA. Negative slope = improving discipline."""
    if len(history.periods) < 2:
        return FactorScore(
            name="debt_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need 2+ periods for trend",
        )

    ratios = []
    for p in history.periods:
        ebitda = float(p.current_income.ebit) + float(p.current_income.depreciation or Decimal("0"))
        if ebitda <= 0:
            continue
        net_debt = float(p.current_balance.total_debt) - float(
            p.current_balance.cash_and_equivalents or Decimal("0")
        )
        ratios.append(net_debt / ebitda)

    if len(ratios) < 2:
        return FactorScore(
            name="debt_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Insufficient EBITDA-positive periods",
        )

    # Simple slope: (last - first) / (n - 1)
    slope = (ratios[-1] - ratios[0]) / (len(ratios) - 1)

    return FactorScore(
        name="debt_discipline",
        raw_value=slope,
        percentile_rank=0.0,
        detail=f"ND/EBITDA series={[f'{r:.2f}' for r in ratios]}, slope={slope:.4f}",
    )


def organic_reinvestment_ratio(period: FinancialPeriod) -> FactorScore:
    """Growth CapEx / Total Capital Deployed. Higher = investing in business."""
    ci = period.current_income
    cf = period.current_cash_flow

    capex_abs = abs(float(cf.capital_expenditures))
    depreciation = float(ci.depreciation or Decimal("0"))
    growth_capex = max(0.0, capex_abs - depreciation)

    buybacks = abs(float(cf.share_repurchases or Decimal("0")))
    dividends = abs(float(cf.dividends_paid or Decimal("0")))

    total_deployed = growth_capex + buybacks + dividends
    if total_deployed <= 0:
        return FactorScore(
            name="organic_reinvestment_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No capital deployed",
        )

    ratio = growth_capex / total_deployed

    return FactorScore(
        name="organic_reinvestment_ratio",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"growth_capex={growth_capex:.2f}, buybacks={buybacks:.2f}, "
            f"dividends={dividends:.2f}, total={total_deployed:.2f}, ratio={ratio:.4f}"
        ),
    )


def insider_ownership_score(ownership_pct: float) -> FactorScore:
    """Insider ownership as a raw percentage."""
    return FactorScore(
        name="insider_ownership",
        raw_value=ownership_pct,
        percentile_rank=0.0,
        detail=f"insider_ownership={ownership_pct:.4f}",
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_capital_allocation.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/capital_allocation.py \
       engine/tests/scoring/quantitative/test_capital_allocation.py
git commit -m "feat: add capital allocation sub-factors (buyback, debt, reinvestment, ownership)"
```

---

### Task 12: Contrarian Signal factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/contrarian_signal.py`
- Test: `engine/tests/scoring/quantitative/test_contrarian_signal.py`

**Step 1: Write failing tests**

```python
"""Tests for Contrarian Signal — negative momentum + strong quality."""

import pytest
from margin_engine.scoring.quantitative.contrarian_signal import contrarian_signal


class TestContrarianSignal:
    def test_negative_momentum_high_quality(self):
        """Negative momentum + high quality = strong contrarian signal."""
        # momentum_percentile = 15 (bad), quality_percentile = 90 (great)
        # signal = (100 - 15) * 90 / 100 = 85 * 0.9 = 76.5
        result = contrarian_signal(momentum_percentile=15.0, quality_percentile=90.0)
        assert result.name == "contrarian_signal"
        assert result.raw_value == pytest.approx(76.5)

    def test_positive_momentum_returns_zero(self):
        """Positive momentum (> 50th percentile) = no contrarian signal."""
        result = contrarian_signal(momentum_percentile=70.0, quality_percentile=90.0)
        assert result.raw_value == 0.0

    def test_low_quality_returns_low_signal(self):
        """Negative momentum but low quality = not contrarian, just bad."""
        result = contrarian_signal(momentum_percentile=10.0, quality_percentile=20.0)
        # (100 - 10) * 20 / 100 = 90 * 0.2 = 18.0
        assert result.raw_value == pytest.approx(18.0)
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_contrarian_signal.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/quantitative/contrarian_signal.py`:

```python
"""Contrarian Signal — negative price momentum combined with strong fundamentals.

Signal = (100 - momentum_percentile) * (quality_percentile / 100)

Only fires when momentum_percentile < 50 (market is negative on the stock).
The worse the momentum + the better the quality = the stronger the contrarian signal.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_MOMENTUM_THRESHOLD = 50.0  # Below this = negative momentum


def contrarian_signal(
    momentum_percentile: float,
    quality_percentile: float,
) -> FactorScore:
    """Compute contrarian signal strength."""
    if momentum_percentile >= _MOMENTUM_THRESHOLD:
        return FactorScore(
            name="contrarian_signal",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"momentum={momentum_percentile:.1f} (>= {_MOMENTUM_THRESHOLD}, not contrarian)",
        )

    momentum_pain = 100.0 - momentum_percentile
    quality_factor = quality_percentile / 100.0
    signal = momentum_pain * quality_factor

    return FactorScore(
        name="contrarian_signal",
        raw_value=signal,
        percentile_rank=0.0,
        detail=(
            f"momentum={momentum_percentile:.1f}, quality={quality_percentile:.1f}, "
            f"pain={momentum_pain:.1f}, signal={signal:.1f}"
        ),
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_contrarian_signal.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/contrarian_signal.py \
       engine/tests/scoring/quantitative/test_contrarian_signal.py
git commit -m "feat: add contrarian signal factor (negative momentum * quality)"
```

---

### Task 13: Opportunity Type Classifier

**Files:**
- Create: `engine/src/margin_engine/scoring/opportunity_classifier.py`
- Test: `engine/tests/scoring/test_opportunity_classifier.py`

**Step 1: Write failing tests**

```python
"""Tests for Opportunity Type classifier."""

import pytest
from margin_engine.models.scoring import OpportunityType
from margin_engine.scoring.opportunity_classifier import classify_opportunity_type


class TestClassifyOpportunityType:
    def test_compounder(self):
        """High stable ROIC + high reinvestment = Compounder."""
        result = classify_opportunity_type(
            roic_5yr_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_intrinsic_ratio=0.9,  # slightly below IV
            has_catalyst=False,
            roic_improving=False,
        )
        assert result == OpportunityType.COMPOUNDER

    def test_mispricing(self):
        """Deep discount + quality floor + catalyst = Mispricing."""
        result = classify_opportunity_type(
            roic_5yr_median=0.10,
            roic_cv=0.40,
            reinvestment_rate=0.15,
            price_to_intrinsic_ratio=0.5,  # 50% of IV
            has_catalyst=True,
            roic_improving=True,
        )
        assert result == OpportunityType.MISPRICING

    def test_both(self):
        """Meets both criteria = Both."""
        result = classify_opportunity_type(
            roic_5yr_median=0.25,
            roic_cv=0.10,
            reinvestment_rate=0.50,
            price_to_intrinsic_ratio=0.5,
            has_catalyst=True,
            roic_improving=False,
        )
        assert result == OpportunityType.BOTH

    def test_neither(self):
        """Meets neither = Neither."""
        result = classify_opportunity_type(
            roic_5yr_median=0.06,
            roic_cv=0.50,
            reinvestment_rate=0.10,
            price_to_intrinsic_ratio=0.8,
            has_catalyst=False,
            roic_improving=False,
        )
        assert result == OpportunityType.NEITHER
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/test_opportunity_classifier.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/opportunity_classifier.py`:

```python
"""Opportunity Type classifier — Compounder, Mispricing, Both, or Neither.

Compounder requires:
    - 5yr median ROIC > 15%
    - Reinvestment Rate > 30%
    - ROIC CV < 0.30

Mispricing requires:
    - Price / Intrinsic Value < 0.60
    - Quality floor: 5yr median ROIC > 8% OR improving ROIC trajectory
    - At least one active catalyst
"""

from __future__ import annotations

from margin_engine.models.scoring import OpportunityType

# Compounder thresholds
_COMPOUNDER_ROIC_MIN = 0.15
_COMPOUNDER_RR_MIN = 0.30
_COMPOUNDER_CV_MAX = 0.30

# Mispricing thresholds
_MISPRICING_PRICE_RATIO_MAX = 0.60
_MISPRICING_ROIC_FLOOR = 0.08


def classify_opportunity_type(
    roic_5yr_median: float,
    roic_cv: float,
    reinvestment_rate: float,
    price_to_intrinsic_ratio: float,
    has_catalyst: bool,
    roic_improving: bool,
) -> OpportunityType:
    """Classify a stock's opportunity type based on quantitative criteria."""
    is_compounder = (
        roic_5yr_median > _COMPOUNDER_ROIC_MIN
        and reinvestment_rate > _COMPOUNDER_RR_MIN
        and roic_cv < _COMPOUNDER_CV_MAX
    )

    quality_floor_met = roic_5yr_median > _MISPRICING_ROIC_FLOOR or roic_improving

    is_mispricing = (
        price_to_intrinsic_ratio < _MISPRICING_PRICE_RATIO_MAX
        and quality_floor_met
        and has_catalyst
    )

    if is_compounder and is_mispricing:
        return OpportunityType.BOTH
    if is_compounder:
        return OpportunityType.COMPOUNDER
    if is_mispricing:
        return OpportunityType.MISPRICING
    return OpportunityType.NEITHER
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_opportunity_classifier.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/opportunity_classifier.py \
       engine/tests/scoring/test_opportunity_classifier.py
git commit -m "feat: add opportunity type classifier (compounder/mispricing/both/neither)"
```

---

## Phase 4: Anti-Mediocrity Gate & Updated Filter Pipeline

---

### Task 14: Anti-Mediocrity elimination gate

**Files:**
- Create: `engine/src/margin_engine/scoring/filters/mediocrity_gate.py`
- Test: `engine/tests/scoring/filters/test_mediocrity_gate.py`

**Step 1: Write failing tests**

```python
"""Tests for Anti-Mediocrity Gate."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import FilterResult
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate


def _make_period(year: int, ebit: Decimal = Decimal("200"),
                 revenue: Decimal = Decimal("1000"),
                 cfo: Decimal = Decimal("250"),
                 gross_margin_pct: float = 0.40) -> FinancialPeriod:
    cogs = revenue * Decimal(str(1 - gross_margin_pct))
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cogs,
            gross_profit=revenue - cogs, ebit=ebit,
            net_income=ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"), total_equity=Decimal("500"),
            long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("100"),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo, capital_expenditures=Decimal("-50"),
        ),
    )


class TestMediocrityGate:
    def test_quality_business_passes(self):
        """Business with ROIC > 8%, GM > 20%, consistent FCF passes."""
        history = FinancialHistory(
            ticker="GOOD",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True

    def test_low_roic_fails(self):
        """5yr median ROIC < 8% = mediocre."""
        history = FinancialHistory(
            ticker="WEAK",
            periods=[_make_period(y, ebit=Decimal("20")) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert "roic" in result.detail.lower()

    def test_low_gross_margin_fails(self):
        """Gross margin < 20% = commodity business."""
        history = FinancialHistory(
            ticker="COMM",
            periods=[_make_period(y, gross_margin_pct=0.12) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False

    def test_utilities_lower_gm_threshold(self):
        """Utilities have lower GM threshold (10%)."""
        history = FinancialHistory(
            ticker="UTIL",
            periods=[_make_period(y, gross_margin_pct=0.15) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.UTILITIES)
        assert result.passed is True  # 15% > 10% threshold for utilities
```

**Step 2: Run to verify fail**

Run: `uv run pytest engine/tests/scoring/filters/test_mediocrity_gate.py -v`

**Step 3: Implement**

Create `engine/src/margin_engine/scoring/filters/mediocrity_gate.py`:

```python
"""Anti-Mediocrity Gate — pre-scoring filter removing businesses not worth evaluating.

Thresholds:
    - 5yr median ROIC > 8%
    - Gross margin > 20% (sector-adjusted: Utilities > 10%, Energy > 15%)
    - Positive FCF in 4 of last 5 years
    - Revenue not declining 3+ consecutive years
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, GICSSector
from margin_engine.models.scoring import FilterResult

_ROIC_THRESHOLD = 0.08
_DEFAULT_GM_THRESHOLD = 0.20
_UTILITIES_GM_THRESHOLD = 0.10
_ENERGY_GM_THRESHOLD = 0.15
_MIN_FCF_POSITIVE_YEARS = 4
_MAX_REVENUE_DECLINE_YEARS = 3


def _sector_gm_threshold(sector: GICSSector) -> float:
    if sector == GICSSector.UTILITIES:
        return _UTILITIES_GM_THRESHOLD
    if sector == GICSSector.ENERGY:
        return _ENERGY_GM_THRESHOLD
    return _DEFAULT_GM_THRESHOLD


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


def mediocrity_gate(
    history: FinancialHistory,
    sector: GICSSector,
) -> FilterResult:
    """Run anti-mediocrity gate. Returns FilterResult (passed=True/False)."""
    failures: list[str] = []

    # 1. ROIC check (5yr median > 8%)
    roics = [r for p in history.periods if (r := _compute_roic(p)) is not None]
    if roics:
        median_roic = statistics.median(roics)
        if median_roic <= _ROIC_THRESHOLD:
            failures.append(f"median_ROIC={median_roic:.4f} <= {_ROIC_THRESHOLD}")
    else:
        failures.append("no valid ROIC periods")

    # 2. Gross margin check (sector-adjusted)
    gm_threshold = _sector_gm_threshold(sector)
    gms = [p.current_income.gross_margin for p in history.periods]
    if gms:
        median_gm = statistics.median(gms)
        if median_gm <= gm_threshold:
            failures.append(f"median_GM={median_gm:.4f} <= {gm_threshold}")

    # 3. FCF consistency (4 of last 5 years positive)
    recent = history.periods[-5:] if len(history.periods) >= 5 else history.periods
    fcf_positive = sum(1 for p in recent if p.current_cash_flow.free_cash_flow > 0)
    if len(recent) >= 5 and fcf_positive < _MIN_FCF_POSITIVE_YEARS:
        failures.append(f"FCF positive {fcf_positive}/{len(recent)} years (need {_MIN_FCF_POSITIVE_YEARS})")

    # 4. Revenue trend (not declining 3+ consecutive years)
    if len(history.periods) >= _MAX_REVENUE_DECLINE_YEARS:
        revenues = [float(p.current_income.revenue) for p in history.periods]
        consecutive_declines = 0
        max_declines = 0
        for i in range(1, len(revenues)):
            if revenues[i] < revenues[i - 1]:
                consecutive_declines += 1
                max_declines = max(max_declines, consecutive_declines)
            else:
                consecutive_declines = 0
        if max_declines >= _MAX_REVENUE_DECLINE_YEARS:
            failures.append(f"revenue declined {max_declines} consecutive years")

    passed = len(failures) == 0
    detail = "All gates passed" if passed else "; ".join(failures)

    return FilterResult(
        name="mediocrity_gate",
        passed=passed,
        detail=detail,
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/filters/test_mediocrity_gate.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/mediocrity_gate.py \
       engine/tests/scoring/filters/test_mediocrity_gate.py
git commit -m "feat: add anti-mediocrity gate (ROIC, GM, FCF, revenue trend)"
```

---

## Phase 5: Two-Track Composite Scorers

---

### Task 15: Conviction Gates module

**Files:**
- Create: `engine/src/margin_engine/scoring/conviction_gates.py`
- Test: `engine/tests/scoring/test_conviction_gates.py`

Tests and implementation for absolute quality gates that must be met IN ADDITION to percentile thresholds. Follow the same TDD pattern as above. The gate functions take computed metrics and return pass/fail with detail strings.

**Commit message:** `feat: add absolute conviction gates for Track A (compounder) and Track B (mispricing)`

---

### Task 16: Position Sizing module

**Files:**
- Create: `engine/src/margin_engine/scoring/position_sizing.py`
- Test: `engine/tests/scoring/test_position_sizing.py`

Maps asymmetry ratio + conviction level to max position %. Follow same TDD pattern.

**Commit message:** `feat: add asymmetry-based position sizing signal`

---

### Task 17: Track A Composite (Compounder)

**Files:**
- Create: `engine/src/margin_engine/scoring/composite_compounder.py`
- Test: `engine/tests/scoring/test_composite_compounder.py`

Assembles Quality (50%) + Value (30%) + Capital Allocation (20%) using weighted sub-factors. Returns a CompositeScore with `winning_track="compounder"`.

**Commit message:** `feat: add Track A (compounder) composite scorer`

---

### Task 18: Track B Composite (Mispricing)

**Files:**
- Create: `engine/src/margin_engine/scoring/composite_mispricing.py`
- Test: `engine/tests/scoring/test_composite_mispricing.py`

Assembles Value (45%) + Quality Floor (25%) + Catalyst (30%) using weighted sub-factors. Returns a CompositeScore with `winning_track="mispricing"`.

**Commit message:** `feat: add Track B (mispricing) composite scorer`

---

### Task 19: Dual-Track Orchestrator

**Files:**
- Create: `engine/src/margin_engine/scoring/dual_track.py`
- Test: `engine/tests/scoring/test_dual_track.py`

Runs both Track A and Track B, picks the higher score, applies conviction gates, assigns opportunity type, computes position sizing and timing overlay. This is the new top-level scoring entry point.

**Commit message:** `feat: add dual-track orchestrator (picks best of compounder vs mispricing)`

---

### Task 20: Timing Overlay

**Files:**
- Create: `engine/src/margin_engine/scoring/timing_overlay.py`
- Test: `engine/tests/scoring/test_timing_overlay.py`

Takes momentum percentile, SUE percentile, and sentiment. Returns timing signal: "buy_now", "add_on_pullback", or "wait_for_catalyst". Inverts interpretation for Track B (negative momentum = positive for mispricing).

**Commit message:** `feat: add timing overlay (momentum as entry signal, not conviction)`

---

### Task 21: Update scoring package exports

**Files:**
- Modify: `engine/src/margin_engine/scoring/__init__.py`

Add exports for all new modules. Retain existing exports for backward compatibility.

**Commit message:** `feat: update scoring package exports for v2 dual-track engine`

---

### Task 22: Integration test — full pipeline Costco golden value test

**Files:**
- Create: `engine/tests/fixtures/golden_costco_2024.py`
- Create: `engine/tests/scoring/test_dual_track_integration.py`

Hand-verified Costco data (5yr ROIC series, financials, prices). Verify it surfaces as Track A Compounder with Exceptional or High conviction. This is the ultimate acceptance test.

**Commit message:** `test: add Costco golden value integration test for dual-track engine`

---

Plan complete and saved to `docs/plans/2026-02-16-conviction-engine-redesign-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?