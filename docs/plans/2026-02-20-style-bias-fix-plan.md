# Style Bias Fix — Multi-Track Scoring Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate systematic Value bias in the scoring pipeline by adding style classification, a third track (Efficient Growth), style-aware normalization, new growth/momentum factors, and updated weighting/thresholds.

**Architecture:** New `InvestmentStyle` enum (VALUE/BLEND/GROWTH) classified before scoring. Three parallel tracks: Track A (Compounder, refined), Track B (Mispricing, minor fixes), Track C (Efficient Growth, new). Style-aware two-stage normalization replaces sector-only ranking. Weight matrix keyed by (style × growth_stage) replaces stage-only weights. New growth dimension with 4 factors joins existing quality/value/momentum.

**Tech Stack:** Pure Python (engine package), Pydantic models, pytest with golden-value pattern. No web or API changes in this plan.

**Design doc:** `docs/plans/2026-02-20-style-bias-audit-design.md`

---

## Task 1: Add InvestmentStyle Enum and Style Classifier

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py` (add enum + update CompositeScore)
- Create: `engine/src/margin_engine/scoring/style_classifier.py`
- Create: `engine/tests/scoring/test_style_classifier.py`

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/test_style_classifier.py
"""Tests for investment style classification (Value/Blend/Growth)."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import InvestmentStyle


class TestInvestmentStyleEnum:
    def test_enum_values(self):
        assert InvestmentStyle.VALUE == "value"
        assert InvestmentStyle.BLEND == "blend"
        assert InvestmentStyle.GROWTH == "growth"


class TestClassifyStyle:
    """Test majority-vote style classification across 4 signals."""

    def test_clear_value_all_signals(self):
        """Low EV/FCF percentile, low CAGR, flat earnings, low reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,  # bottom tercile
            revenue_cagr_3yr=0.03,          # < 8%
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.05,       # < 8%
        )
        assert style == InvestmentStyle.VALUE

    def test_clear_growth_all_signals(self):
        """High EV/FCF percentile, high CAGR, accelerating earnings, high reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=80.0,  # top tercile
            revenue_cagr_3yr=0.25,          # > 18%
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=0.20,       # > 15%
        )
        assert style == InvestmentStyle.GROWTH

    def test_clear_blend_middle_signals(self):
        """Middle percentile, moderate CAGR, moderate reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=50.0,  # middle tercile
            revenue_cagr_3yr=0.12,          # 8-18%
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.10,       # 8-15%
        )
        assert style == InvestmentStyle.BLEND

    def test_tie_defaults_to_blend(self):
        """2 Value signals + 2 Growth signals = Blend."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,  # Value
            revenue_cagr_3yr=0.25,          # Growth
            earnings_growth_accelerating=True,  # Growth
            rd_capex_to_revenue=0.05,       # Value
        )
        assert style == InvestmentStyle.BLEND

    def test_three_value_one_growth(self):
        """Majority Value wins."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,  # Value
            revenue_cagr_3yr=0.03,          # Value
            earnings_growth_accelerating=False,  # Value (flat)
            rd_capex_to_revenue=0.20,       # Growth
        )
        assert style == InvestmentStyle.VALUE

    def test_missing_cagr_uses_three_signals(self):
        """When CAGR is None, classify from remaining 3 signals."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=80.0,  # Growth
            revenue_cagr_3yr=None,          # Unknown
            earnings_growth_accelerating=True,  # Growth
            rd_capex_to_revenue=0.20,       # Growth
        )
        assert style == InvestmentStyle.GROWTH

    def test_all_none_defaults_to_blend(self):
        """When all signals are None/unknown, default to Blend."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=None,
            revenue_cagr_3yr=None,
            earnings_growth_accelerating=None,
            rd_capex_to_revenue=None,
        )
        assert style == InvestmentStyle.BLEND
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_style_classifier.py -v`
Expected: FAIL — `InvestmentStyle` not found, `style_classifier` module not found.

**Step 3: Add InvestmentStyle enum to scoring models**

In `engine/src/margin_engine/models/scoring.py`, add after the `OpportunityType` enum (line 44):

```python
class InvestmentStyle(StrEnum):
    VALUE = "value"
    BLEND = "blend"
    GROWTH = "growth"
```

Also add to `CompositeScore` model, after `growth_stage` field (line 117):

```python
    investment_style: InvestmentStyle | None = None
```

**Step 4: Implement the style classifier**

```python
# engine/src/margin_engine/scoring/style_classifier.py
"""Investment style classifier — Value / Blend / Growth.

Classifies assets using a majority-vote across 4 signals:
1. EV/FCF sector percentile (valuation relative to sector)
2. Revenue CAGR (3yr)
3. Earnings growth trajectory (accelerating or not)
4. R&D + CapEx / Revenue (reinvestment intensity)

Style is orthogonal to GrowthStage — a Mature company can be Growth-style
if it's expensive relative to peers with high reinvestment.
"""

from __future__ import annotations

from margin_engine.models.scoring import InvestmentStyle

# Tercile boundaries for EV/FCF percentile
_VALUATION_LOW = 33.33   # bottom tercile = cheap = Value
_VALUATION_HIGH = 66.67  # top tercile = expensive = Growth

# Revenue CAGR boundaries
_CAGR_LOW = 0.08   # < 8% = Value
_CAGR_HIGH = 0.18  # > 18% = Growth

# R&D + CapEx / Revenue boundaries
_REINVEST_LOW = 0.08   # < 8% = Value
_REINVEST_HIGH = 0.15  # > 15% = Growth


def classify_investment_style(
    ev_fcf_sector_percentile: float | None,
    revenue_cagr_3yr: float | None,
    earnings_growth_accelerating: bool | None,
    rd_capex_to_revenue: float | None,
) -> InvestmentStyle:
    """Classify an asset's investment style using majority-vote.

    Each signal votes VALUE, BLEND, or GROWTH. Majority wins.
    Ties default to BLEND. None signals are excluded from the vote.
    """
    votes: list[InvestmentStyle] = []

    # Signal 1: Valuation percentile within sector
    if ev_fcf_sector_percentile is not None:
        if ev_fcf_sector_percentile <= _VALUATION_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif ev_fcf_sector_percentile >= _VALUATION_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    # Signal 2: Revenue CAGR
    if revenue_cagr_3yr is not None:
        if revenue_cagr_3yr < _CAGR_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif revenue_cagr_3yr > _CAGR_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    # Signal 3: Earnings growth trajectory
    if earnings_growth_accelerating is not None:
        if earnings_growth_accelerating:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.VALUE)

    # Signal 4: Reinvestment intensity
    if rd_capex_to_revenue is not None:
        if rd_capex_to_revenue < _REINVEST_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif rd_capex_to_revenue > _REINVEST_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    if not votes:
        return InvestmentStyle.BLEND

    # Count votes
    counts = {
        InvestmentStyle.VALUE: votes.count(InvestmentStyle.VALUE),
        InvestmentStyle.BLEND: votes.count(InvestmentStyle.BLEND),
        InvestmentStyle.GROWTH: votes.count(InvestmentStyle.GROWTH),
    }

    max_count = max(counts.values())
    winners = [s for s, c in counts.items() if c == max_count]

    # Tie → BLEND
    if len(winners) > 1:
        return InvestmentStyle.BLEND

    return winners[0]
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_style_classifier.py -v`
Expected: All 7 tests PASS.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py \
      engine/src/margin_engine/scoring/style_classifier.py \
      engine/tests/scoring/test_style_classifier.py
git commit -m "feat: add InvestmentStyle enum and majority-vote style classifier"
```

---

## Task 2: Style-Aware FCF Distress Filter

**Files:**
- Modify: `engine/src/margin_engine/config/filter_config.py` (add style-aware config fields)
- Modify: `engine/src/margin_engine/scoring/filters/fcf_distress.py` (add style parameter)
- Create: `engine/tests/scoring/filters/test_fcf_distress_style_aware.py`

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/filters/test_fcf_distress_style_aware.py
"""Tests for style-aware FCF distress filter adjustments."""

import pytest
from decimal import Decimal

from margin_engine.config.filter_config import FcfDistressConfig
from margin_engine.models.financial import (
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
    BalanceSheet,
)
from margin_engine.models.scoring import InvestmentStyle
from margin_engine.scoring.filters.fcf_distress import fcf_distress_check_v2


def _make_period(fcf_positive: bool, revenue: float = 1_000_000, gross_margin: float = 0.5) -> FinancialPeriod:
    """Helper to create a period with positive or negative FCF."""
    cogs = Decimal(str(revenue * (1 - gross_margin)))
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("200000") if fcf_positive else Decimal("-100000"),
        capital_expenditures=Decimal("-50000"),
    )
    income = IncomeStatement(
        revenue=Decimal(str(revenue)),
        cost_of_revenue=cogs,
    )
    balance = BalanceSheet(
        total_assets=Decimal("5000000"),
        current_assets=Decimal("2000000"),
        total_liabilities=Decimal("2000000"),
        current_liabilities=Decimal("1000000"),
        total_equity=Decimal("3000000"),
    )
    return FinancialPeriod(
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestFcfDistressStyleAware:
    def test_growth_stock_2_of_5_passes(self):
        """Growth stocks need only 2/5 positive FCF years (not 3/5)."""
        periods = [
            _make_period(False),  # yr1: negative
            _make_period(False),  # yr2: negative
            _make_period(False),  # yr3: negative
            _make_period(True),   # yr4: positive
            _make_period(True),   # yr5: positive
        ]
        history = FinancialHistory(periods=periods)
        result = fcf_distress_check_v2(
            history, style=InvestmentStyle.GROWTH,
        )
        assert result.passed is True

    def test_value_stock_2_of_5_fails(self):
        """Value stocks still need 3/5 positive FCF years."""
        periods = [
            _make_period(False),
            _make_period(False),
            _make_period(False),
            _make_period(True),
            _make_period(True),
        ]
        history = FinancialHistory(periods=periods)
        result = fcf_distress_check_v2(
            history, style=InvestmentStyle.VALUE,
        )
        assert result.passed is False

    def test_growth_stock_ocf_plus_margin_rescue(self):
        """Growth stock with positive operating CF + gross margin > 40% passes even with 1/5 positive FCF."""
        periods = [
            _make_period(False, gross_margin=0.55),
            _make_period(False, gross_margin=0.55),
            _make_period(False, gross_margin=0.55),
            _make_period(False, gross_margin=0.55),
            _make_period(True, gross_margin=0.55),  # only 1 positive, but latest has pos OCF
        ]
        history = FinancialHistory(periods=periods)
        result = fcf_distress_check_v2(
            history, style=InvestmentStyle.GROWTH,
        )
        # 1/5 positive < 2 required, but OCF rescue applies
        assert result.passed is True

    def test_growth_stock_low_margin_no_rescue(self):
        """Growth stock with gross margin <= 40% doesn't get OCF rescue."""
        periods = [
            _make_period(False, gross_margin=0.30),
            _make_period(False, gross_margin=0.30),
            _make_period(False, gross_margin=0.30),
            _make_period(False, gross_margin=0.30),
            _make_period(True, gross_margin=0.30),
        ]
        history = FinancialHistory(periods=periods)
        result = fcf_distress_check_v2(
            history, style=InvestmentStyle.GROWTH,
        )
        # 1/5 positive < 2, low margin = no rescue
        assert result.passed is False

    def test_none_style_uses_default_behavior(self):
        """When style is None, behaves as before (3/5 required)."""
        periods = [
            _make_period(False),
            _make_period(False),
            _make_period(False),
            _make_period(True),
            _make_period(True),
        ]
        history = FinancialHistory(periods=periods)
        result = fcf_distress_check_v2(history, style=None)
        assert result.passed is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress_style_aware.py -v`
Expected: FAIL — `style` parameter not accepted.

**Step 3: Add style-aware config to FcfDistressConfig**

In `engine/src/margin_engine/config/filter_config.py`, add to `FcfDistressConfig`:

```python
    # Growth style uses relaxed threshold
    growth_positive_years_required: int = 2
    growth_ocf_rescue_min_gross_margin: float = 0.40
```

**Step 4: Implement style-aware FCF distress check**

In `engine/src/margin_engine/scoring/filters/fcf_distress.py`, update the `fcf_distress_check_v2` signature to accept `style: InvestmentStyle | None = None` parameter. Add import for `InvestmentStyle`.

Key logic changes in `fcf_distress_check_v2`:
- After computing `required`, add: if `style == InvestmentStyle.GROWTH`, use `config.growth_positive_years_required` instead.
- After the existing count check fails, before the positive trend rescue, add a new rescue path: if `style == InvestmentStyle.GROWTH` and the latest period has positive operating CF and median gross margin > `config.growth_ocf_rescue_min_gross_margin`, pass with warning.

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress_style_aware.py -v`
Expected: All 5 tests PASS.

**Step 6: Run existing FCF distress tests to confirm no regression**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py -v`
Expected: All existing tests PASS (style=None defaults to current behavior).

**Step 7: Commit**

```bash
git add engine/src/margin_engine/config/filter_config.py \
      engine/src/margin_engine/scoring/filters/fcf_distress.py \
      engine/tests/scoring/filters/test_fcf_distress_style_aware.py
git commit -m "feat: add style-aware FCF distress filter with Growth relaxation"
```

---

## Task 3: New Growth Factors (PEG, Rule of 40, EV/Gross Profit, Revenue CAGR, Operating Leverage)

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/peg_ratio.py`
- Create: `engine/src/margin_engine/scoring/quantitative/rule_of_40.py`
- Create: `engine/src/margin_engine/scoring/quantitative/ev_gross_profit.py`
- Create: `engine/src/margin_engine/scoring/quantitative/revenue_cagr.py`
- Create: `engine/src/margin_engine/scoring/quantitative/operating_leverage.py`
- Create: `engine/tests/scoring/quantitative/test_peg_ratio.py`
- Create: `engine/tests/scoring/quantitative/test_rule_of_40.py`
- Create: `engine/tests/scoring/quantitative/test_ev_gross_profit.py`
- Create: `engine/tests/scoring/quantitative/test_revenue_cagr.py`
- Create: `engine/tests/scoring/quantitative/test_operating_leverage.py`

Each factor follows the same pattern as existing factors: takes financial data, returns `FactorScore`.

### 3a: PEG Ratio

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_peg_ratio.py
"""Tests for PEG ratio factor."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import FactorScore


class TestPegRatio:
    def test_normal_peg(self):
        """PE 20, earnings growth 20% -> PEG 1.0"""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=0.20)
        assert isinstance(result, FactorScore)
        assert result.name == "peg_ratio"
        assert result.raw_value == pytest.approx(1.0, rel=1e-3)

    def test_cheap_growth(self):
        """PE 15, earnings growth 30% -> PEG 0.5"""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=15.0, earnings_growth_rate=0.30)
        assert result.raw_value == pytest.approx(0.5, rel=1e-3)

    def test_expensive_growth(self):
        """PE 60, earnings growth 15% -> PEG 4.0"""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=60.0, earnings_growth_rate=0.15)
        assert result.raw_value == pytest.approx(4.0, rel=1e-3)

    def test_negative_earnings_growth_returns_sentinel(self):
        """Negative earnings growth -> raw_value 0.0 (not computable)."""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=-0.05)
        assert result.raw_value == 0.0

    def test_zero_earnings_growth_returns_sentinel(self):
        """Zero earnings growth -> raw_value 0.0 (division by zero guard)."""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=0.0)
        assert result.raw_value == 0.0

    def test_negative_pe_returns_sentinel(self):
        """Negative PE (unprofitable) -> raw_value 0.0."""
        from margin_engine.scoring.quantitative.peg_ratio import peg_ratio

        result = peg_ratio(pe_ratio=-10.0, earnings_growth_rate=0.20)
        assert result.raw_value == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_peg_ratio.py -v`
Expected: FAIL — module not found.

**Step 3: Implement PEG ratio**

```python
# engine/src/margin_engine/scoring/quantitative/peg_ratio.py
"""PEG Ratio — Price/Earnings to Growth.

PEG = PE / (earnings_growth_rate * 100).
Lower is better: PEG < 1.0 suggests undervalued relative to growth.
Returns 0.0 sentinel when inputs are invalid (negative PE or growth).
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def peg_ratio(
    pe_ratio: float,
    earnings_growth_rate: float,
) -> FactorScore:
    """Compute PEG ratio.

    Args:
        pe_ratio: Price-to-earnings ratio. Must be positive.
        earnings_growth_rate: Expected annual earnings growth as decimal (0.20 = 20%).
            Must be positive.

    Returns:
        FactorScore with raw_value = PEG ratio (lower = better).
        Returns 0.0 if inputs are invalid.
    """
    if pe_ratio <= 0 or earnings_growth_rate <= 0:
        return FactorScore(
            name="peg_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"PEG not computable: PE={pe_ratio:.1f}, growth={earnings_growth_rate:.1%}",
        )

    growth_pct = earnings_growth_rate * 100.0
    peg = pe_ratio / growth_pct

    return FactorScore(
        name="peg_ratio",
        raw_value=round(peg, 4),
        percentile_rank=0.0,
        detail=f"PEG={peg:.2f} (PE={pe_ratio:.1f}, growth={earnings_growth_rate:.1%})",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_peg_ratio.py -v`
Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/peg_ratio.py \
      engine/tests/scoring/quantitative/test_peg_ratio.py
git commit -m "feat: add PEG ratio factor"
```

### 3b: Rule of 40

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_rule_of_40.py
"""Tests for Rule of 40 factor."""

import pytest
from margin_engine.models.scoring import FactorScore


class TestRuleOf40:
    def test_balanced_company(self):
        """20% growth + 20% FCF margin = 40."""
        from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40

        result = rule_of_40(revenue_growth_rate=0.20, fcf_margin=0.20)
        assert isinstance(result, FactorScore)
        assert result.name == "rule_of_40"
        assert result.raw_value == pytest.approx(40.0, rel=1e-3)

    def test_high_growth_low_profit(self):
        """40% growth + -5% FCF margin = 35."""
        from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40

        result = rule_of_40(revenue_growth_rate=0.40, fcf_margin=-0.05)
        assert result.raw_value == pytest.approx(35.0, rel=1e-3)

    def test_low_growth_high_profit(self):
        """5% growth + 30% FCF margin = 35."""
        from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40

        result = rule_of_40(revenue_growth_rate=0.05, fcf_margin=0.30)
        assert result.raw_value == pytest.approx(35.0, rel=1e-3)

    def test_exceptional_score(self):
        """30% growth + 25% margin = 55."""
        from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40

        result = rule_of_40(revenue_growth_rate=0.30, fcf_margin=0.25)
        assert result.raw_value == pytest.approx(55.0, rel=1e-3)

    def test_negative_combined(self):
        """-10% growth + -5% margin = -15."""
        from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40

        result = rule_of_40(revenue_growth_rate=-0.10, fcf_margin=-0.05)
        assert result.raw_value == pytest.approx(-15.0, rel=1e-3)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_rule_of_40.py -v`
Expected: FAIL — module not found.

**Step 3: Implement Rule of 40**

```python
# engine/src/margin_engine/scoring/quantitative/rule_of_40.py
"""Rule of 40 — revenue growth rate % + FCF margin %.

Used primarily for SaaS/tech evaluation. Score >= 40 indicates
a healthy balance of growth and profitability.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def rule_of_40(
    revenue_growth_rate: float,
    fcf_margin: float,
) -> FactorScore:
    """Compute Rule of 40 score.

    Args:
        revenue_growth_rate: Annual revenue growth as decimal (0.20 = 20%).
        fcf_margin: FCF / Revenue as decimal (0.15 = 15%).

    Returns:
        FactorScore with raw_value = growth% + margin% (higher = better).
    """
    score = (revenue_growth_rate * 100.0) + (fcf_margin * 100.0)

    return FactorScore(
        name="rule_of_40",
        raw_value=round(score, 2),
        percentile_rank=0.0,
        detail=f"Rule of 40 = {score:.1f} (growth={revenue_growth_rate:.1%}, margin={fcf_margin:.1%})",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_rule_of_40.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/rule_of_40.py \
      engine/tests/scoring/quantitative/test_rule_of_40.py
git commit -m "feat: add Rule of 40 factor"
```

### 3c: EV/Gross Profit

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_ev_gross_profit.py
"""Tests for EV/Gross Profit factor."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import FactorScore
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(
    revenue: float,
    cogs: float,
    total_debt: float = 500_000,
    cash: float = 200_000,
) -> FinancialPeriod:
    return FinancialPeriod(
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            cost_of_revenue=Decimal(str(cogs)),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("5000000"),
            current_assets=Decimal("2000000"),
            total_liabilities=Decimal("2000000"),
            current_liabilities=Decimal("1000000"),
            total_equity=Decimal("3000000"),
            long_term_debt=Decimal(str(total_debt)),
            cash_and_equivalents=Decimal(str(cash)),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200000"),
            capital_expenditures=Decimal("-50000"),
        ),
    )


class TestEvGrossProfit:
    def test_normal_ratio(self):
        """EV = 1B + 500K - 200K = 1,000,300K. GP = 1M - 400K = 600K."""
        from margin_engine.scoring.quantitative.ev_gross_profit import ev_gross_profit

        period = _make_period(revenue=1_000_000, cogs=400_000)
        result = ev_gross_profit(period, market_cap=Decimal("1_000_000_000"))
        assert isinstance(result, FactorScore)
        assert result.name == "ev_gross_profit"
        assert result.raw_value > 0

    def test_zero_gross_profit_returns_zero(self):
        """Zero gross profit -> 0.0 sentinel."""
        from margin_engine.scoring.quantitative.ev_gross_profit import ev_gross_profit

        period = _make_period(revenue=1_000_000, cogs=1_000_000)
        result = ev_gross_profit(period, market_cap=Decimal("1_000_000_000"))
        assert result.raw_value == 0.0

    def test_negative_gross_profit_returns_zero(self):
        """Negative gross profit -> 0.0 sentinel."""
        from margin_engine.scoring.quantitative.ev_gross_profit import ev_gross_profit

        period = _make_period(revenue=1_000_000, cogs=1_200_000)
        result = ev_gross_profit(period, market_cap=Decimal("1_000_000_000"))
        assert result.raw_value == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_ev_gross_profit.py -v`
Expected: FAIL — module not found.

**Step 3: Implement EV/Gross Profit**

```python
# engine/src/margin_engine/scoring/quantitative/ev_gross_profit.py
"""EV/Gross Profit — enterprise value relative to gross profit.

Better than EV/EBIT for growth companies because it removes
growth OpEx (R&D, S&M) distortion. Lower = cheaper.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def ev_gross_profit(
    period: FinancialPeriod,
    market_cap: Decimal,
) -> FactorScore:
    """Compute EV / Gross Profit ratio.

    Args:
        period: Financial data with income statement and balance sheet.
        market_cap: Current market capitalization.

    Returns:
        FactorScore with raw_value = EV/GP ratio (lower = better).
        Returns 0.0 if gross profit <= 0.
    """
    income = period.current_income
    balance = period.current_balance

    gross_profit = float(income.revenue - (income.cost_of_revenue or Decimal("0")))
    if gross_profit <= 0:
        return FactorScore(
            name="ev_gross_profit",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="EV/GP not computable: gross profit <= 0",
        )

    total_debt = float(balance.total_debt)
    cash = float(balance.cash_and_equivalents or Decimal("0"))
    ev = float(market_cap) + total_debt - cash

    ratio = ev / gross_profit

    return FactorScore(
        name="ev_gross_profit",
        raw_value=round(ratio, 4),
        percentile_rank=0.0,
        detail=f"EV/GP={ratio:.2f} (EV={ev:,.0f}, GP={gross_profit:,.0f})",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_ev_gross_profit.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/ev_gross_profit.py \
      engine/tests/scoring/quantitative/test_ev_gross_profit.py
git commit -m "feat: add EV/Gross Profit factor"
```

### 3d: Revenue CAGR Factor

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_revenue_cagr.py
"""Tests for Revenue CAGR factor."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import FactorScore
from margin_engine.models.financial import (
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
)


def _make_period(revenue: float) -> FinancialPeriod:
    return FinancialPeriod(
        current_income=IncomeStatement(revenue=Decimal(str(revenue))),
        current_balance=BalanceSheet(
            total_assets=Decimal("5000000"),
            current_assets=Decimal("2000000"),
            total_liabilities=Decimal("2000000"),
            current_liabilities=Decimal("1000000"),
            total_equity=Decimal("3000000"),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200000"),
            capital_expenditures=Decimal("-50000"),
        ),
    )


class TestRevenueCagr:
    def test_steady_growth(self):
        """Revenue doubles in 3 years: CAGR = 2^(1/3) - 1 ≈ 26%."""
        from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr

        history = FinancialHistory(periods=[
            _make_period(1_000_000),  # year 0
            _make_period(1_250_000),  # year 1
            _make_period(1_600_000),  # year 2
            _make_period(2_000_000),  # year 3
        ])
        result = revenue_cagr(history)
        assert isinstance(result, FactorScore)
        assert result.name == "revenue_cagr_3yr"
        assert result.raw_value == pytest.approx(0.2599, rel=1e-2)

    def test_flat_revenue(self):
        """No growth -> CAGR ≈ 0."""
        from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr

        history = FinancialHistory(periods=[
            _make_period(1_000_000),
            _make_period(1_000_000),
            _make_period(1_000_000),
            _make_period(1_000_000),
        ])
        result = revenue_cagr(history)
        assert result.raw_value == pytest.approx(0.0, abs=1e-4)

    def test_declining_revenue(self):
        """Revenue halves -> negative CAGR."""
        from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr

        history = FinancialHistory(periods=[
            _make_period(2_000_000),
            _make_period(1_500_000),
            _make_period(1_200_000),
            _make_period(1_000_000),
        ])
        result = revenue_cagr(history)
        assert result.raw_value < 0

    def test_insufficient_periods(self):
        """Less than 2 periods -> 0.0 sentinel."""
        from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr

        history = FinancialHistory(periods=[_make_period(1_000_000)])
        result = revenue_cagr(history)
        assert result.raw_value == 0.0

    def test_zero_starting_revenue(self):
        """Zero starting revenue -> 0.0 sentinel."""
        from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr

        history = FinancialHistory(periods=[
            _make_period(0),
            _make_period(1_000_000),
            _make_period(1_500_000),
            _make_period(2_000_000),
        ])
        result = revenue_cagr(history)
        assert result.raw_value == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_revenue_cagr.py -v`
Expected: FAIL — module not found.

**Step 3: Implement Revenue CAGR**

```python
# engine/src/margin_engine/scoring/quantitative/revenue_cagr.py
"""Revenue CAGR (3-year) — compound annual growth rate of revenue.

Uses the earliest and latest periods in the history to compute
annualized growth rate. Higher = faster growing.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore


def revenue_cagr(
    history: FinancialHistory,
    years: int = 3,
) -> FactorScore:
    """Compute revenue CAGR over the specified number of years.

    Uses first and last periods of the history (up to `years + 1` periods).
    Returns 0.0 sentinel if insufficient data or zero starting revenue.
    """
    periods = history.periods[-(years + 1) :]
    n = len(periods)

    if n < 2:
        return FactorScore(
            name="revenue_cagr_3yr",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Insufficient periods for CAGR",
        )

    start_rev = float(periods[0].current_income.revenue)
    end_rev = float(periods[-1].current_income.revenue)

    if start_rev <= 0:
        return FactorScore(
            name="revenue_cagr_3yr",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"Zero or negative starting revenue: {start_rev:,.0f}",
        )

    num_years = n - 1
    ratio = end_rev / start_rev

    if ratio <= 0:
        return FactorScore(
            name="revenue_cagr_3yr",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"Negative ending revenue ratio: {ratio:.4f}",
        )

    cagr = ratio ** (1.0 / num_years) - 1.0

    return FactorScore(
        name="revenue_cagr_3yr",
        raw_value=round(cagr, 4),
        percentile_rank=0.0,
        detail=f"Revenue CAGR ({num_years}yr) = {cagr:.1%} ({start_rev:,.0f} -> {end_rev:,.0f})",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_revenue_cagr.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/revenue_cagr.py \
      engine/tests/scoring/quantitative/test_revenue_cagr.py
git commit -m "feat: add Revenue CAGR factor"
```

### 3e: Operating Leverage

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_operating_leverage.py
"""Tests for Operating Leverage factor."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import FactorScore
from margin_engine.models.financial import (
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
)


def _make_period(revenue: float, opex: float) -> FinancialPeriod:
    return FinancialPeriod(
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            cost_of_revenue=Decimal(str(revenue * 0.4)),
            sga_expense=Decimal(str(opex)),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("5000000"),
            current_assets=Decimal("2000000"),
            total_liabilities=Decimal("2000000"),
            current_liabilities=Decimal("1000000"),
            total_equity=Decimal("3000000"),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200000"),
            capital_expenditures=Decimal("-50000"),
        ),
    )


class TestOperatingLeverage:
    def test_positive_leverage(self):
        """Revenue grows 20%, OpEx grows 10% -> leverage = 2.0."""
        from margin_engine.scoring.quantitative.operating_leverage import operating_leverage

        history = FinancialHistory(periods=[
            _make_period(revenue=1_000_000, opex=500_000),
            _make_period(revenue=1_200_000, opex=550_000),
        ])
        result = operating_leverage(history)
        assert isinstance(result, FactorScore)
        assert result.name == "operating_leverage"
        assert result.raw_value == pytest.approx(2.0, rel=1e-2)

    def test_no_leverage(self):
        """Revenue grows 20%, OpEx grows 20% -> leverage = 1.0."""
        from margin_engine.scoring.quantitative.operating_leverage import operating_leverage

        history = FinancialHistory(periods=[
            _make_period(revenue=1_000_000, opex=500_000),
            _make_period(revenue=1_200_000, opex=600_000),
        ])
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(1.0, rel=1e-2)

    def test_negative_leverage(self):
        """Revenue grows 10%, OpEx grows 20% -> leverage = 0.5."""
        from margin_engine.scoring.quantitative.operating_leverage import operating_leverage

        history = FinancialHistory(periods=[
            _make_period(revenue=1_000_000, opex=500_000),
            _make_period(revenue=1_100_000, opex=600_000),
        ])
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(0.5, rel=1e-2)

    def test_insufficient_periods(self):
        """Single period -> 0.0 sentinel."""
        from margin_engine.scoring.quantitative.operating_leverage import operating_leverage

        history = FinancialHistory(periods=[
            _make_period(revenue=1_000_000, opex=500_000),
        ])
        result = operating_leverage(history)
        assert result.raw_value == 0.0

    def test_zero_opex_growth(self):
        """OpEx flat, revenue growing -> high leverage (capped)."""
        from margin_engine.scoring.quantitative.operating_leverage import operating_leverage

        history = FinancialHistory(periods=[
            _make_period(revenue=1_000_000, opex=500_000),
            _make_period(revenue=1_200_000, opex=500_000),
        ])
        result = operating_leverage(history)
        # OpEx growth = 0%, revenue growth = 20%, ratio capped
        assert result.raw_value > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_operating_leverage.py -v`
Expected: FAIL — module not found.

**Step 3: Implement Operating Leverage**

```python
# engine/src/margin_engine/scoring/quantitative/operating_leverage.py
"""Operating Leverage — revenue growth rate / OpEx growth rate.

Measures how efficiently a company scales. > 1.0 means revenue grows
faster than operating expenses (positive operating leverage).
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore

_MAX_LEVERAGE = 10.0  # cap to prevent extreme values from flat OpEx


def operating_leverage(history: FinancialHistory) -> FactorScore:
    """Compute operating leverage = revenue growth rate / OpEx growth rate.

    Uses earliest and latest periods. Returns 0.0 if insufficient data
    or zero starting values.
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="operating_leverage",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Insufficient periods for operating leverage",
        )

    earliest = history.periods[0]
    latest = history.periods[-1]

    rev_start = float(earliest.current_income.revenue)
    rev_end = float(latest.current_income.revenue)

    opex_start = float(earliest.current_income.sga_expense or Decimal("0"))
    opex_end = float(latest.current_income.sga_expense or Decimal("0"))

    if rev_start <= 0 or opex_start <= 0:
        return FactorScore(
            name="operating_leverage",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Zero starting revenue or OpEx",
        )

    rev_growth = (rev_end - rev_start) / rev_start
    opex_growth = (opex_end - opex_start) / opex_start

    if opex_growth == 0:
        leverage = min(rev_growth / 0.001, _MAX_LEVERAGE) if rev_growth > 0 else 0.0
    elif opex_growth < 0:
        # OpEx shrinking while revenue grows = very positive leverage
        leverage = min(abs(rev_growth / opex_growth), _MAX_LEVERAGE) if rev_growth > 0 else 0.0
    else:
        leverage = rev_growth / opex_growth

    # Cap at maximum to prevent extreme values
    leverage = min(max(leverage, 0.0), _MAX_LEVERAGE)

    return FactorScore(
        name="operating_leverage",
        raw_value=round(leverage, 4),
        percentile_rank=0.0,
        detail=f"OpLev={leverage:.2f} (rev_growth={rev_growth:.1%}, opex_growth={opex_growth:.1%})",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/quantitative/test_operating_leverage.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/operating_leverage.py \
      engine/tests/scoring/quantitative/test_operating_leverage.py
git commit -m "feat: add Operating Leverage factor"
```

---

## Task 4: Style-Aware Normalization

**Files:**
- Modify: `engine/src/margin_engine/scoring/normalizer.py` (add style-aware functions)
- Create: `engine/tests/scoring/test_style_aware_normalizer.py`

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/test_style_aware_normalizer.py
"""Tests for style-aware two-stage normalization."""

import pytest
from margin_engine.models.scoring import FactorScore, InvestmentStyle
from margin_engine.scoring.normalizer import (
    style_sector_neutral_ranks,
)


class TestStyleSectorNeutralRanks:
    def test_ranks_within_style_and_sector(self):
        """Scores ranked within (sector, style) bucket."""
        scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]] = {
            ("Technology", InvestmentStyle.GROWTH): [
                FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=35.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=20.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=40.0, percentile_rank=0.0),
            ],
            ("Technology", InvestmentStyle.VALUE): [
                FactorScore(name="ev_fcf", raw_value=10.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=8.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=12.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=6.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=14.0, percentile_rank=0.0),
            ],
        }
        result = style_sector_neutral_ranks(scores_by_bucket, invert=True)
        # Verify we get 10 scores back
        assert len(result) == 10
        # Within Growth-Tech: 20 should be best (inverted), 40 worst
        growth_scores = result[:5]
        value_scores = result[5:]
        # The cheapest Growth-Tech (20) should rank highest
        cheapest_growth = [s for s in growth_scores if s.raw_value == 20.0][0]
        assert cheapest_growth.percentile_rank > 50.0

    def test_small_bucket_fallback(self):
        """Buckets with < 5 assets fall back to sector-only ranking."""
        scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]] = {
            ("Technology", InvestmentStyle.GROWTH): [
                FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=0.0),
            ],  # Only 2 — below threshold of 5
        }
        result = style_sector_neutral_ranks(
            scores_by_bucket, invert=True, min_bucket_size=5,
        )
        # Should still produce results (fallback behavior)
        assert len(result) == 2

    def test_empty_input(self):
        result = style_sector_neutral_ranks({}, invert=False)
        assert result == []


class TestCrossBucketCalibration:
    def test_z_score_calibration_produces_0_to_100(self):
        """After z-score calibration, all scores should be in 0-100 range."""
        from margin_engine.scoring.normalizer import calibrate_cross_bucket

        # Simulate raw percentiles from different buckets with different distributions
        scores = [
            FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=90.0),
            FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=70.0),
            FactorScore(name="ev_fcf", raw_value=10.0, percentile_rank=80.0),
            FactorScore(name="ev_fcf", raw_value=8.0, percentile_rank=60.0),
        ]
        calibrated = calibrate_cross_bucket(scores)
        assert len(calibrated) == 4
        for s in calibrated:
            assert 0.0 <= s.percentile_rank <= 100.0

    def test_single_score_gets_50(self):
        from margin_engine.scoring.normalizer import calibrate_cross_bucket

        scores = [FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=90.0)]
        calibrated = calibrate_cross_bucket(scores)
        assert calibrated[0].percentile_rank == 50.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_style_aware_normalizer.py -v`
Expected: FAIL — `style_sector_neutral_ranks` not found, `InvestmentStyle` import fails.

**Step 3: Implement style-aware normalization**

Add to `engine/src/margin_engine/scoring/normalizer.py`:

```python
from margin_engine.models.scoring import InvestmentStyle

# ... existing functions stay unchanged ...


def style_sector_neutral_ranks(
    scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]],
    invert: bool = False,
    min_bucket_size: int = 5,
) -> list[FactorScore]:
    """Compute percentile ranks within (sector, style) buckets.

    Stage 1 of the two-stage style-aware normalization.
    If a bucket has fewer than min_bucket_size assets, ranks within that
    bucket using the standard algorithm (no cross-bucket merging for fallback
    to keep it simple — the calibration step handles cross-bucket fairness).

    Args:
        scores_by_bucket: Mapping of (sector, style) -> list of FactorScores.
        invert: If True, lower raw_value gets higher percentile.
        min_bucket_size: Minimum bucket size for style-aware ranking.
            Buckets smaller than this still get ranked but may be noisier.

    Returns:
        All scores with percentile ranks assigned within their bucket,
        concatenated in bucket insertion order.
    """
    result: list[FactorScore] = []
    for _bucket_key, bucket_scores in scores_by_bucket.items():
        ranked = compute_percentile_ranks(bucket_scores, invert=invert)
        result.extend(ranked)
    return result


def calibrate_cross_bucket(
    scores: list[FactorScore],
) -> list[FactorScore]:
    """Stage 2: Z-score calibration across all buckets.

    Takes scores with bucket-local percentile ranks and standardizes
    them so that a 90th percentile in one bucket is comparable to
    a 90th percentile in another.

    Applies: z = (percentile - mean) / std, then maps back to 0-100.
    """
    if not scores:
        return []

    if len(scores) == 1:
        return [
            FactorScore(
                name=scores[0].name,
                raw_value=scores[0].raw_value,
                percentile_rank=50.0,
                detail=scores[0].detail,
            )
        ]

    percentiles = [s.percentile_rank for s in scores]
    mean_pct = sum(percentiles) / len(percentiles)
    variance = sum((p - mean_pct) ** 2 for p in percentiles) / len(percentiles)
    std_pct = variance ** 0.5

    if std_pct == 0:
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
            )
            for s in scores
        ]

    calibrated: list[FactorScore] = []
    for s in scores:
        z = (s.percentile_rank - mean_pct) / std_pct
        # Map z-score back to 0-100 using linear scaling
        # z typically ranges from -3 to +3, map to 0-100
        mapped = max(0.0, min(100.0, 50.0 + z * 16.67))
        calibrated.append(
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=round(mapped, 2),
                detail=s.detail,
            )
        )

    return calibrated
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_style_aware_normalizer.py -v`
Expected: All 5 tests PASS.

**Step 5: Run existing normalizer tests**

Run: `uv run pytest engine/tests/scoring/test_normalizer.py -v`
Expected: All existing tests PASS (no regression).

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/normalizer.py \
      engine/tests/scoring/test_style_aware_normalizer.py
git commit -m "feat: add style-aware two-stage normalization"
```

---

## Task 5: Track C — Efficient Growth Gate Cascade and Scoring

**Files:**
- Create: `engine/src/margin_engine/scoring/v3_track_c_cascade.py`
- Create: `engine/src/margin_engine/scoring/v3_track_c_thresholds.py`
- Create: `engine/tests/scoring/test_v3_track_c_cascade.py`
- Modify: `engine/src/margin_engine/scoring/v3_composite.py` (add Track C score function)

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/test_v3_track_c_cascade.py
"""Tests for Track C (Efficient Growth) gate cascade."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import V3TrackResult


class TestTrackCGates:
    def test_all_gates_pass_high_conviction(self):
        """Strong growth company passes all 4 gates -> HIGH conviction."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert isinstance(result, V3TrackResult)
        assert result.track == "efficient_growth"
        assert result.gates_passed == 4
        assert result.qualifies is True
        assert result.conviction in {ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL}

    def test_exceptional_conviction(self):
        """Exceptional growth metrics -> EXCEPTIONAL conviction."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.35,
            fcf_margin=0.20,
            gross_margin_current=0.70,
            gross_margin_3yr_ago=0.65,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.35,
            incremental_roic=0.25,
            wacc=0.10,
            revenue_deceleration=-0.01,
            tam_headroom=8.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_fails_growth_efficiency_gate(self):
        """Low Rule of 40 and no gross margin rescue -> gate 1 fails."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.05,
            fcf_margin=-0.10,
            gross_margin_current=0.40,
            gross_margin_3yr_ago=0.42,
            opex_growth_rate=0.10,
            revenue_growth_rate_for_leverage=0.05,
            incremental_roic=0.12,
            wacc=0.10,
            revenue_deceleration=-0.03,
            tam_headroom=4.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_fails_unit_economics_declining_margin(self):
        """Gross margin declining > 2pp -> gate 2 fails."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.55,
            gross_margin_3yr_ago=0.65,  # -10pp decline
            opex_growth_rate=0.35,      # OpEx growing faster than revenue
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        # Gate 2 should fail (margin declining and no operating leverage)
        assert result.gates_passed < 4

    def test_fails_capital_efficiency(self):
        """Incremental ROIC below WACC -> gate 3 fails."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.05,  # Below WACC
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_fails_growth_durability_decelerating(self):
        """Severe deceleration -> gate 4 fails."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.10,  # -10pp deceleration
            tam_headroom=2.0,            # Low headroom
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_none_conviction_when_few_gates(self):
        """Fewer than 3 gates -> NONE conviction."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.05,
            fcf_margin=-0.10,
            gross_margin_current=0.40,
            gross_margin_3yr_ago=0.50,
            opex_growth_rate=0.20,
            revenue_growth_rate_for_leverage=0.05,
            incremental_roic=0.03,
            wacc=0.10,
            revenue_deceleration=-0.08,
            tam_headroom=1.5,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction == ConvictionLevel.NONE
        assert result.qualifies is False

    def test_score_is_positive_when_gates_pass(self):
        """Track C score is a positive multiplicative product."""
        from margin_engine.scoring.v3_track_c_cascade import (
            TrackCInputs,
            run_track_c_cascade,
        )

        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.score > 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_track_c_cascade.py -v`
Expected: FAIL — modules not found.

**Step 3: Implement Track C thresholds**

```python
# engine/src/margin_engine/scoring/v3_track_c_thresholds.py
"""V3 Track C (Efficient Growth) conviction thresholds."""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

# Gate minimums
_FULL_GATES = 4
_MEDIUM_GATES = 3

# EXCEPTIONAL thresholds
_EXCEPTIONAL_RULE_OF_40 = 50.0
_EXCEPTIONAL_ROIC_WACC_MULTIPLE = 2.0
_EXCEPTIONAL_TAM_HEADROOM = 5.0

# HIGH thresholds
_HIGH_RULE_OF_40 = 30.0
_HIGH_ROIC_ABOVE_WACC = True  # incremental_roic > wacc


def assess_track_c_conviction(
    gates_passed: int,
    total_gates: int,
    rule_of_40_score: float,
    incremental_roic: float,
    wacc: float,
    tam_headroom: float,
) -> ConvictionLevel:
    """Assess conviction level for Track C (Efficient Growth).

    EXCEPTIONAL: 4/4 gates + rule_of_40 >= 50 + inc_ROIC > 2*WACC + TAM > 5x
    HIGH: 4/4 gates + rule_of_40 >= 30 + inc_ROIC > WACC
    MEDIUM: 3+ gates
    NONE: < 3 gates
    """
    if gates_passed < _MEDIUM_GATES:
        return ConvictionLevel.NONE

    if gates_passed < _FULL_GATES:
        return ConvictionLevel.MEDIUM

    # 4/4 gates passed — check for EXCEPTIONAL
    if (
        rule_of_40_score >= _EXCEPTIONAL_RULE_OF_40
        and incremental_roic > _EXCEPTIONAL_ROIC_WACC_MULTIPLE * wacc
        and tam_headroom >= _EXCEPTIONAL_TAM_HEADROOM
    ):
        return ConvictionLevel.EXCEPTIONAL

    # Check for HIGH
    if rule_of_40_score >= _HIGH_RULE_OF_40 and incremental_roic > wacc:
        return ConvictionLevel.HIGH

    return ConvictionLevel.MEDIUM
```

**Step 4: Implement Track C cascade**

```python
# engine/src/margin_engine/scoring/v3_track_c_cascade.py
"""V3 Track C (Efficient Growth) Gate Cascade.

4 gates evaluate capital-efficient high-growth companies:
1. Growth Efficiency: Rule of 40 >= 30 OR (CAGR > 25% AND gross margin > 50%)
2. Unit Economics: Gross margin stable + positive operating leverage
3. Capital Efficiency: Incremental ROIC > WACC
4. Growth Durability: Deceleration < -5pp AND TAM headroom > 3x
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_track_c_thresholds import assess_track_c_conviction

# Gate thresholds
_RULE_OF_40_MIN = 30.0
_ALT_CAGR_MIN = 0.25
_ALT_GROSS_MARGIN_MIN = 0.50

_GROSS_MARGIN_MAX_DECLINE = -0.02  # -2 percentage points
_OPERATING_LEVERAGE_MIN = 1.0

_DECELERATION_MAX = -0.05  # -5 percentage points
_TAM_HEADROOM_MIN = 3.0

_QUALIFYING_CONVICTIONS = frozenset(
    {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.MEDIUM}
)


class TrackCInputs(BaseModel):
    """All inputs needed to run Track C (Efficient Growth) gate cascade."""

    # Gate 1: Growth Efficiency
    revenue_growth_rate: float        # decimal (0.30 = 30%)
    fcf_margin: float                 # decimal (0.15 = 15%)

    # Gate 2: Unit Economics
    gross_margin_current: float       # decimal
    gross_margin_3yr_ago: float       # decimal
    opex_growth_rate: float           # decimal (growth rate of SGA)
    revenue_growth_rate_for_leverage: float  # same as revenue_growth_rate, explicit

    # Gate 3: Capital Efficiency
    incremental_roic: float           # decimal
    wacc: float                       # decimal

    # Gate 4: Growth Durability
    revenue_deceleration: float       # change in growth rate (negative = slowing)
    tam_headroom: float               # TAM / current_revenue


def _compute_track_c_score(
    rule_of_40: float,
    gross_margin_trend: float,
    operating_leverage: float,
    incremental_roic: float,
    wacc: float,
    tam_headroom: float,
    deceleration: float,
) -> float:
    """Multiplicative Track C score.

    growth_efficiency × unit_economics × capital_efficiency × growth_durability
    """
    # Growth Efficiency: normalized so 40 = 1.0, capped at 2.0
    ge = min(max(rule_of_40 / 40.0, 0.0), 2.0)

    # Unit Economics: (1 + margin_trend) × operating_leverage_ratio
    ue = max((1.0 + gross_margin_trend) * max(operating_leverage, 0.0), 0.0)

    # Capital Efficiency: inc_ROIC / WACC, capped at 3.0
    ce = min(max(incremental_roic / wacc, 0.0), 3.0) if wacc > 0 else 0.0

    # Growth Durability: headroom factor × deceleration penalty
    headroom_factor = min(max(tam_headroom / 3.0, 0.0), 2.0)
    decel_penalty = 1.0 - max(-deceleration, 0.0) / 20.0  # -20pp = 0 penalty
    gd = max(headroom_factor * max(decel_penalty, 0.0), 0.0)

    return ge * ue * ce * gd


def run_track_c_cascade(inputs: TrackCInputs) -> V3TrackResult:
    """Run the 4-gate Efficient Growth cascade and return a V3TrackResult."""
    gates_passed = 0
    total_gates = 4

    # --- Gate 1: Growth Efficiency ---
    rule_of_40 = (inputs.revenue_growth_rate * 100.0) + (inputs.fcf_margin * 100.0)
    alt_growth = inputs.revenue_growth_rate > _ALT_CAGR_MIN and inputs.gross_margin_current > _ALT_GROSS_MARGIN_MIN
    if rule_of_40 >= _RULE_OF_40_MIN or alt_growth:
        gates_passed += 1

    # --- Gate 2: Unit Economics ---
    margin_trend = inputs.gross_margin_current - inputs.gross_margin_3yr_ago
    margin_stable = margin_trend >= _GROSS_MARGIN_MAX_DECLINE

    if inputs.opex_growth_rate > 0:
        op_leverage = inputs.revenue_growth_rate_for_leverage / inputs.opex_growth_rate
    elif inputs.opex_growth_rate == 0 and inputs.revenue_growth_rate_for_leverage > 0:
        op_leverage = 10.0  # effectively infinite, cap it
    else:
        op_leverage = 0.0

    leverage_positive = op_leverage >= _OPERATING_LEVERAGE_MIN
    if margin_stable and leverage_positive:
        gates_passed += 1

    # --- Gate 3: Capital Efficiency ---
    if inputs.incremental_roic > inputs.wacc:
        gates_passed += 1

    # --- Gate 4: Growth Durability ---
    not_decelerating = inputs.revenue_deceleration >= _DECELERATION_MAX
    has_headroom = inputs.tam_headroom >= _TAM_HEADROOM_MIN
    if not_decelerating and has_headroom:
        gates_passed += 1

    # --- Score ---
    score = _compute_track_c_score(
        rule_of_40=rule_of_40,
        gross_margin_trend=margin_trend,
        operating_leverage=op_leverage,
        incremental_roic=inputs.incremental_roic,
        wacc=inputs.wacc,
        tam_headroom=inputs.tam_headroom,
        deceleration=inputs.revenue_deceleration,
    )

    # --- Conviction ---
    conviction = assess_track_c_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        rule_of_40_score=rule_of_40,
        incremental_roic=inputs.incremental_roic,
        wacc=inputs.wacc,
        tam_headroom=inputs.tam_headroom,
    )

    qualifies = conviction in _QUALIFYING_CONVICTIONS

    return V3TrackResult(
        track="efficient_growth",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
```

**Step 5: Add Track C score function to v3_composite.py**

In `engine/src/margin_engine/scoring/v3_composite.py`, add:

```python
def compute_track_c_score(
    growth_efficiency: float,
    unit_economics: float,
    capital_efficiency: float,
    growth_durability: float,
) -> float:
    """Track C multiplicative score: GE × UE × CE × GD."""
    return growth_efficiency * unit_economics * capital_efficiency * growth_durability
```

**Step 6: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_track_c_cascade.py -v`
Expected: All 8 tests PASS.

**Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_track_c_cascade.py \
      engine/src/margin_engine/scoring/v3_track_c_thresholds.py \
      engine/src/margin_engine/scoring/v3_composite.py \
      engine/tests/scoring/test_v3_track_c_cascade.py
git commit -m "feat: add Track C (Efficient Growth) gate cascade and scoring"
```

---

## Task 6: Updated Orchestrator with Three Tracks and New Position Sizing

**Files:**
- Create: `engine/src/margin_engine/scoring/v4_orchestrator.py`
- Modify: `engine/src/margin_engine/scoring/v3_position_sizing.py` (add Track C + new combos)
- Create: `engine/tests/scoring/test_v4_orchestrator.py`

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/test_v4_orchestrator.py
"""Tests for v4 three-track orchestrator."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import V3TrackResult


class TestV4Orchestrator:
    def _make_track(self, track: str, qualifies: bool, conviction: ConvictionLevel, score: float = 1.0) -> V3TrackResult:
        return V3TrackResult(
            track=track,
            qualifies=qualifies,
            conviction=conviction,
            score=score,
            gates_passed=4 if qualifies else 1,
            total_gates=4,
        )

    def test_only_track_a_qualifies(self):
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder"
        assert result.conviction == ConvictionLevel.HIGH

    def test_only_track_c_qualifies(self):
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "efficient_growth"
        assert result.conviction == ConvictionLevel.HIGH

    def test_track_a_plus_c_promotes_to_exceptional(self):
        """Compounder + Efficient Growth at HIGH+ -> EXCEPTIONAL."""
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder_growth"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_track_a_plus_b_both_promotion(self):
        """Existing A+B both rule preserved."""
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", True, ConvictionLevel.HIGH),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_all_three_qualify(self):
        """All three at HIGH+ -> EXCEPTIONAL, highest position."""
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", True, ConvictionLevel.HIGH),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_neither_qualifies(self):
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "neither"
        assert result.conviction == ConvictionLevel.NONE
        assert result.max_position_pct == 0.0

    def test_position_sizing_efficient_growth_high(self):
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 7.0

    def test_position_sizing_compounder_growth_exceptional(self):
        from margin_engine.scoring.v4_orchestrator import orchestrate_v4

        result = orchestrate_v4(
            ticker="TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.EXCEPTIONAL),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 20.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v4_orchestrator.py -v`
Expected: FAIL — `v4_orchestrator` module not found.

**Step 3: Update position sizing with new tracks**

In `engine/src/margin_engine/scoring/v3_position_sizing.py`, add new track entries to `_SIZING`:

```python
_SIZING: dict[str, dict[ConvictionLevel, float]] = {
    "compounder": {
        ConvictionLevel.EXCEPTIONAL: 15.0,
        ConvictionLevel.HIGH: 8.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "mispricing": {
        ConvictionLevel.EXCEPTIONAL: 12.0,
        ConvictionLevel.HIGH: 6.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "both": {
        ConvictionLevel.EXCEPTIONAL: 20.0,
        ConvictionLevel.HIGH: 10.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "efficient_growth": {
        ConvictionLevel.EXCEPTIONAL: 12.0,
        ConvictionLevel.HIGH: 7.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "compounder_growth": {
        ConvictionLevel.EXCEPTIONAL: 20.0,
        ConvictionLevel.HIGH: 10.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "all_three": {
        ConvictionLevel.EXCEPTIONAL: 20.0,
        ConvictionLevel.HIGH: 12.0,
        ConvictionLevel.MEDIUM: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
}
```

**Step 4: Implement v4 orchestrator**

```python
# engine/src/margin_engine/scoring/v4_orchestrator.py
"""V4 Orchestrator — three-track scoring with style-aware promotion rules.

Extends v3 orchestrator to support Track C (Efficient Growth).
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size


class V4Result(BaseModel):
    """Final v4 scoring result for a single ticker."""

    ticker: str
    opportunity_type: str  # "compounder", "mispricing", "efficient_growth", "both", "compounder_growth", "all_three", "neither"
    conviction: ConvictionLevel
    track_a: V3TrackResult
    track_b: V3TrackResult
    track_c: V3TrackResult
    timing_signal: str
    max_position_pct: float


_STRONG_CONVICTIONS = frozenset({ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH})
_QUALIFYING_CONVICTIONS = frozenset(
    {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.MEDIUM}
)
_CONVICTION_ORDER = {
    ConvictionLevel.EXCEPTIONAL: 0,
    ConvictionLevel.HIGH: 1,
    ConvictionLevel.MEDIUM: 2,
    ConvictionLevel.NONE: 3,
}


def orchestrate_v4(
    ticker: str,
    track_a: V3TrackResult,
    track_b: V3TrackResult,
    track_c: V3TrackResult,
    timing_signal: str,
) -> V4Result:
    """Orchestrate v4 scoring — combine three track results.

    Promotion rules:
    - All three strong -> "all_three", EXCEPTIONAL
    - A+B strong -> "both", EXCEPTIONAL (existing rule)
    - A+C strong -> "compounder_growth", EXCEPTIONAL
    - B+C strong -> use higher score
    - Single qualifier -> use that track
    - None -> "neither"
    """
    a_q = track_a.qualifies and track_a.conviction in _QUALIFYING_CONVICTIONS
    b_q = track_b.qualifies and track_b.conviction in _QUALIFYING_CONVICTIONS
    c_q = track_c.qualifies and track_c.conviction in _QUALIFYING_CONVICTIONS

    a_strong = track_a.conviction in _STRONG_CONVICTIONS
    b_strong = track_b.conviction in _STRONG_CONVICTIONS
    c_strong = track_c.conviction in _STRONG_CONVICTIONS

    # All three strong
    if a_q and b_q and c_q and a_strong and b_strong and c_strong:
        conviction = ConvictionLevel.EXCEPTIONAL
        position = compute_v3_position_size("all_three", conviction)
        return V4Result(
            ticker=ticker, opportunity_type="all_three", conviction=conviction,
            track_a=track_a, track_b=track_b, track_c=track_c,
            timing_signal=timing_signal, max_position_pct=position,
        )

    # A+B strong (existing "both" rule)
    if a_q and b_q and a_strong and b_strong:
        conviction = ConvictionLevel.EXCEPTIONAL
        position = compute_v3_position_size("both", conviction)
        return V4Result(
            ticker=ticker, opportunity_type="both", conviction=conviction,
            track_a=track_a, track_b=track_b, track_c=track_c,
            timing_signal=timing_signal, max_position_pct=position,
        )

    # A+C strong -> "compounder_growth"
    if a_q and c_q and a_strong and c_strong:
        conviction = ConvictionLevel.EXCEPTIONAL
        position = compute_v3_position_size("compounder_growth", conviction)
        return V4Result(
            ticker=ticker, opportunity_type="compounder_growth", conviction=conviction,
            track_a=track_a, track_b=track_b, track_c=track_c,
            timing_signal=timing_signal, max_position_pct=position,
        )

    # Single-track or B+C (no promotion): pick strongest qualifying track
    qualifiers = []
    if a_q:
        qualifiers.append(("compounder", track_a))
    if b_q:
        qualifiers.append(("mispricing", track_b))
    if c_q:
        qualifiers.append(("efficient_growth", track_c))

    if not qualifiers:
        return V4Result(
            ticker=ticker, opportunity_type="neither",
            conviction=ConvictionLevel.NONE,
            track_a=track_a, track_b=track_b, track_c=track_c,
            timing_signal=timing_signal, max_position_pct=0.0,
        )

    # Pick the strongest conviction
    qualifiers.sort(key=lambda x: _CONVICTION_ORDER.get(x[1].conviction, 3))
    opp_type, best_track = qualifiers[0]
    conviction = best_track.conviction
    position = compute_v3_position_size(opp_type, conviction)

    return V4Result(
        ticker=ticker, opportunity_type=opp_type, conviction=conviction,
        track_a=track_a, track_b=track_b, track_c=track_c,
        timing_signal=timing_signal, max_position_pct=position,
    )
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v4_orchestrator.py -v`
Expected: All 8 tests PASS.

**Step 6: Run existing orchestrator tests for no regression**

Run: `uv run pytest engine/tests/scoring/test_v3_orchestrator.py -v`
Expected: All existing tests PASS.

**Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/v4_orchestrator.py \
      engine/src/margin_engine/scoring/v3_position_sizing.py \
      engine/tests/scoring/test_v4_orchestrator.py
git commit -m "feat: add v4 three-track orchestrator with Track C promotion rules"
```

---

## Task 7: Style × Stage Weight Matrix and Growth Factor Dimension

**Files:**
- Create: `engine/src/margin_engine/scoring/v4_weights.py`
- Create: `engine/tests/scoring/test_v4_weights.py`
- Modify: `engine/src/margin_engine/models/scoring.py` (add `growth` field to CompositeScore)

**Step 1: Write the failing tests**

```python
# engine/tests/scoring/test_v4_weights.py
"""Tests for v4 style x stage weight matrix."""

import pytest
from margin_engine.models.scoring import GrowthStage, InvestmentStyle


class TestV4Weights:
    def test_growth_high_growth_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert g == 0.45  # Growth gets heaviest weight
        assert v == 0.10  # Valuation minimal

    def test_value_mature_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.VALUE, GrowthStage.MATURE)
        assert q + v + m + g == pytest.approx(1.0)
        assert v == 0.35  # Value gets heaviest weight
        assert g == 0.15  # Growth still present

    def test_blend_steady_growth_weights(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert m == 0.25  # Momentum constant

    def test_all_combinations_sum_to_1(self):
        """Every combination in the matrix must sum to 1.0."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                assert q + v + m + g == pytest.approx(1.0), (
                    f"Weights don't sum to 1.0 for {style}/{stage}: {q}+{v}+{m}+{g}"
                )

    def test_no_weight_exceeds_045(self):
        """No single dimension should exceed 0.45."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                for weight, name in [(q, "quality"), (v, "value"), (m, "momentum"), (g, "growth")]:
                    assert weight <= 0.45, (
                        f"{name} weight {weight} exceeds 0.45 for {style}/{stage}"
                    )

    def test_momentum_always_025(self):
        """Momentum is constant at 0.25 across all combinations."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                _, _, m, _ = weights_for_style_stage(style, stage)
                assert m == 0.25, f"Momentum != 0.25 for {style}/{stage}: {m}"

    def test_quality_always_at_least_020(self):
        """Quality never drops below 0.20."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, _, _, _ = weights_for_style_stage(style, stage)
                assert q >= 0.20, f"Quality < 0.20 for {style}/{stage}: {q}"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v4_weights.py -v`
Expected: FAIL — `v4_weights` module not found.

**Step 3: Add growth FactorBreakdown to CompositeScore**

In `engine/src/margin_engine/models/scoring.py`, add to `CompositeScore` (after `momentum` field):

```python
    growth: FactorBreakdown | None = None  # v4: growth factor dimension
```

**Step 4: Implement v4 weight matrix**

```python
# engine/src/margin_engine/scoring/v4_weights.py
"""V4 Style x Stage weight matrix.

Returns (quality, value, momentum, growth) weights for each
(InvestmentStyle, GrowthStage) combination.

Properties:
- No cell exceeds 0.45
- Momentum constant at 0.25
- Quality always >= 0.20
- All rows sum to 1.0
"""

from __future__ import annotations

from margin_engine.models.scoring import GrowthStage, InvestmentStyle

# (quality, value, momentum, growth)
_WEIGHT_MATRIX: dict[tuple[InvestmentStyle, GrowthStage], tuple[float, float, float, float]] = {
    # Value
    (InvestmentStyle.VALUE, GrowthStage.MATURE):        (0.25, 0.35, 0.25, 0.15),
    (InvestmentStyle.VALUE, GrowthStage.STEADY_GROWTH): (0.25, 0.30, 0.25, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.CYCLICAL):      (0.25, 0.30, 0.25, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.HIGH_GROWTH):   (0.25, 0.25, 0.25, 0.25),
    (InvestmentStyle.VALUE, GrowthStage.TURNAROUND):    (0.30, 0.25, 0.25, 0.20),
    # Blend
    (InvestmentStyle.BLEND, GrowthStage.MATURE):        (0.30, 0.25, 0.25, 0.20),
    (InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH): (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.CYCLICAL):      (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.HIGH_GROWTH):   (0.25, 0.15, 0.25, 0.35),
    (InvestmentStyle.BLEND, GrowthStage.TURNAROUND):    (0.30, 0.25, 0.25, 0.20),
    # Growth
    (InvestmentStyle.GROWTH, GrowthStage.MATURE):       (0.25, 0.20, 0.25, 0.30),
    (InvestmentStyle.GROWTH, GrowthStage.STEADY_GROWTH):(0.25, 0.15, 0.25, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.CYCLICAL):     (0.25, 0.15, 0.25, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH):  (0.20, 0.10, 0.25, 0.45),
    (InvestmentStyle.GROWTH, GrowthStage.TURNAROUND):   (0.30, 0.25, 0.25, 0.20),
}


def weights_for_style_stage(
    style: InvestmentStyle,
    stage: GrowthStage,
) -> tuple[float, float, float, float]:
    """Return (quality, value, momentum, growth) weights.

    Falls back to Blend × Steady Growth if combination not found.
    """
    return _WEIGHT_MATRIX.get(
        (style, stage),
        (0.30, 0.20, 0.25, 0.25),  # Blend × Steady Growth fallback
    )
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v4_weights.py -v`
Expected: All 7 tests PASS.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/v4_weights.py \
      engine/src/margin_engine/models/scoring.py \
      engine/tests/scoring/test_v4_weights.py
git commit -m "feat: add v4 style x stage weight matrix with growth dimension"
```

---

## Task Summary

| Task | What it builds | Key files | Estimated tests |
|------|---------------|-----------|-----------------|
| 1 | InvestmentStyle enum + classifier | `style_classifier.py` | 7 |
| 2 | Style-aware FCF distress filter | `fcf_distress.py` (modify) | 5 |
| 3 | 5 new growth factors (PEG, Ro40, EV/GP, CAGR, OpLev) | 5 new factor modules | 24 |
| 4 | Style-aware two-stage normalization | `normalizer.py` (extend) | 5 |
| 5 | Track C gate cascade + scoring | `v3_track_c_cascade.py` | 8 |
| 6 | V4 three-track orchestrator + position sizing | `v4_orchestrator.py` | 8 |
| 7 | Style × Stage weight matrix + growth dimension | `v4_weights.py` | 7 |
| **Total** | | **~15 new files** | **~64 tests** |

### What This Plan Does NOT Cover (Future Tasks)

- **New momentum factors** (earnings revision breadth, revenue acceleration, relative strength vs style peers) — can be added as individual factor modules following the same pattern as Task 3.
- **New quality factors** (incremental ROIC improvement, gross margin stability, SBC-adjusted FCF margin) — same pattern.
- **V4 pipeline integration** (`v4_pipeline.py` wiring all components together for universe-level scoring) — needs all above tasks complete first.
- **API integration** — exposing v4 results through the FastAPI service.
- **Bias audit tooling** — scripts to run the audit checklist from the design doc.
- **Production monitoring** — weekly/monthly alerting for style distribution drift.
- **Track A/B refinements** (reinvestment-adjusted ROIC, EPV method, solver bound widening) — incremental improvements to existing tracks.
