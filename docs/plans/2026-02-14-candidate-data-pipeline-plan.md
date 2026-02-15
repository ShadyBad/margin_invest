# Candidate Data Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multi-factor intrinsic value computation, price-aware signal transitions, and enriched frontend components (action pills, price charts, valuation breakdown) to the candidate view.

**Architecture:** Engine computes price targets from 4 value methods (DCF, EV/FCF, Acquirer's Multiple, Shareholder Yield), persists them alongside scores, tracks signal transitions in a new DB table, and serves enriched payloads via existing API routes. Frontend gains action pills, sparklines, expandable price charts, and valuation breakdowns.

**Tech Stack:** Python (Pydantic, SQLAlchemy, Alembic), FastAPI, Next.js 15, Recharts, TypeScript

---

## Task 1: Add `shares_outstanding` to `AssetProfile` Engine Model

**Files:**
- Modify: `engine/src/margin_engine/models/financial.py:206-216`
- Test: `engine/tests/models/test_financial.py`

**Step 1: Write the failing test**

```python
# engine/tests/models/test_financial.py — append to existing file
def test_asset_profile_shares_outstanding():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
        shares_outstanding=15000000000,
    )
    assert profile.shares_outstanding == 15000000000


def test_asset_profile_shares_outstanding_default():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
    )
    assert profile.shares_outstanding is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/models/test_financial.py::test_asset_profile_shares_outstanding -v`
Expected: FAIL — `shares_outstanding` not a valid field

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/models/financial.py`, add to `AssetProfile` class (after line 214):

```python
shares_outstanding: int | None = None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/models/test_financial.py -k "shares_outstanding" -v`
Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/financial.py engine/tests/models/test_financial.py
git commit -m "feat(engine): add shares_outstanding to AssetProfile"
```

---

## Task 2: Create `price_targets.py` Engine Module

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- Create: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write the failing test**

```python
# engine/tests/scoring/quantitative/test_price_targets.py
"""Tests for multi-factor intrinsic value and price target computation."""

from decimal import Decimal

import pytest

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
    PriceBar,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.quantitative.price_targets import (
    PriceTargets,
    compute_price_targets,
)


@pytest.fixture
def healthy_period() -> FinancialPeriod:
    """A realistic financial period with positive FCF, EBIT, dividends."""
    return FinancialPeriod(
        period_end="2025-09-28",
        filing_date="2025-11-01",
        current_income=IncomeStatement(
            revenue=Decimal("100000000000"),
            gross_profit=Decimal("45000000000"),
            ebit=Decimal("30000000000"),
            net_income=Decimal("25000000000"),
            shares_outstanding=15000000000,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("350000000000"),
            current_assets=Decimal("130000000000"),
            cash_and_equivalents=Decimal("60000000000"),
            current_liabilities=Decimal("120000000000"),
            long_term_debt=Decimal("100000000000"),
            total_equity=Decimal("60000000000"),
            shares_outstanding=15000000000,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("110000000000"),
            capital_expenditures=Decimal("-10000000000"),
            dividends_paid=Decimal("-15000000000"),
            share_repurchases=Decimal("-90000000000"),
        ),
    )


@pytest.fixture
def healthy_profile() -> AssetProfile:
    return AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
        shares_outstanding=15000000000,
    )


@pytest.fixture
def price_bars() -> list[PriceBar]:
    return [
        PriceBar(date="2025-09-28", open=Decimal("195"), high=Decimal("198"),
                 low=Decimal("194"), close=Decimal("197"), volume=50000000),
        PriceBar(date="2025-09-27", open=Decimal("193"), high=Decimal("196"),
                 low=Decimal("192"), close=Decimal("195"), volume=48000000),
    ]


class TestComputePriceTargets:
    def test_returns_price_targets_model(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert isinstance(result, PriceTargets)

    def test_intrinsic_value_is_positive(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.intrinsic_value > 0

    def test_buy_price_below_intrinsic(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.buy_price is not None
        assert result.sell_price is not None
        assert result.buy_price < result.sell_price

    def test_actual_price_from_latest_bar(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.actual_price == float(Decimal("197"))

    def test_margin_of_safety_varies_by_conviction(
        self, healthy_period, healthy_profile, price_bars
    ):
        exceptional = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.EXCEPTIONAL,
        )
        watchlist = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.WATCHLIST,
        )
        # Exceptional has tighter MoS => higher buy price
        assert exceptional.buy_price > watchlist.buy_price

    def test_no_price_bars_returns_none_actual(
        self, healthy_period, healthy_profile
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=[],
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.actual_price is None

    def test_negative_fcf_uses_fewer_methods(
        self, healthy_profile, price_bars
    ):
        """When FCF <= 0, DCF and EV/FCF are excluded."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("50000000000"),
                gross_profit=Decimal("10000000000"),
                ebit=Decimal("5000000000"),
                net_income=Decimal("-2000000000"),
                shares_outstanding=15000000000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("200000000000"),
                current_assets=Decimal("80000000000"),
                cash_and_equivalents=Decimal("30000000000"),
                current_liabilities=Decimal("90000000000"),
                long_term_debt=Decimal("60000000000"),
                total_equity=Decimal("50000000000"),
                shares_outstanding=15000000000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("5000000000"),
                capital_expenditures=Decimal("-10000000000"),
                dividends_paid=Decimal("-2000000000"),
                share_repurchases=Decimal("-1000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # Should still produce a result using remaining methods (Acq Mult, ShYield)
        assert result.valuation_methods is not None
        assert "dcf" not in result.valuation_methods
        assert "ev_fcf" not in result.valuation_methods

    def test_no_shares_outstanding_returns_none(
        self, healthy_period, price_bars
    ):
        profile = AssetProfile(
            ticker="AAPL",
            name="Apple Inc.",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("3000000000000"),
            shares_outstanding=None,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is None
        assert result.buy_price is None
        assert result.sell_price is None

    def test_valuation_methods_dict(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        # With healthy data, all 4 methods should contribute
        assert "dcf" in result.valuation_methods
        assert "ev_fcf" in result.valuation_methods
        assert "acquirers_multiple" in result.valuation_methods
        assert "shareholder_yield" in result.valuation_methods

    def test_price_upside_calculation(
        self, healthy_period, healthy_profile, price_bars
    ):
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        if result.intrinsic_value and result.actual_price:
            expected_upside = (
                result.intrinsic_value - result.actual_price
            ) / result.actual_price
            assert abs(result.price_upside - expected_upside) < 0.001
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: FAIL — module `price_targets` not found

**Step 3: Write implementation**

```python
# engine/src/margin_engine/scoring/quantitative/price_targets.py
"""Multi-factor intrinsic value and price target computation.

Synthesizes four valuation methods into a consensus intrinsic value:
- DCF Margin of Safety (35% weight)
- EV/FCF implied price (25% weight)
- Acquirer's Multiple implied price (20% weight)
- Shareholder Yield implied price (20% weight)

Only methods with valid data contribute; weights renormalize.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialPeriod, PriceBar
from margin_engine.models.scoring import ConvictionLevel

# Default weights for each valuation method
_METHOD_WEIGHTS = {
    "dcf": 0.35,
    "ev_fcf": 0.25,
    "acquirers_multiple": 0.20,
    "shareholder_yield": 0.20,
}

# Margin of safety by conviction level
_MOS_BY_CONVICTION = {
    ConvictionLevel.EXCEPTIONAL: 0.15,
    ConvictionLevel.HIGH: 0.20,
    ConvictionLevel.WATCHLIST: 0.25,
    ConvictionLevel.NONE: 0.30,
}


class PriceTargets(BaseModel):
    """Price target output from multi-factor valuation."""

    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    valuation_methods: dict[str, float] | None = None


def compute_price_targets(
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars: list[PriceBar],
    conviction_level: ConvictionLevel,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.025,
    projection_years: int = 10,
) -> PriceTargets:
    """Compute multi-factor price targets for a single asset.

    Args:
        period: Financial data for the asset.
        profile: Asset metadata including shares_outstanding.
        price_bars: Historical OHLCV bars (latest first or any order).
        conviction_level: Determines margin of safety for buy price.
        growth_rate: FCF growth rate for DCF projection (default 5%).
        discount_rate: WACC / discount rate (default 10%).
        terminal_growth_rate: Perpetuity growth rate (default 2.5%).
        projection_years: Number of years to project (default 10).

    Returns:
        PriceTargets with consensus intrinsic value and derived buy/sell targets.
    """
    shares = profile.shares_outstanding
    if not shares or shares <= 0:
        return PriceTargets(
            actual_price=_latest_close(price_bars),
        )

    market_cap = profile.market_cap
    methods: dict[str, float] = {}

    # --- Method 1: DCF intrinsic value ---
    dcf_value = _dcf_intrinsic_per_share(
        period, shares, growth_rate, discount_rate,
        terminal_growth_rate, projection_years,
    )
    if dcf_value is not None:
        methods["dcf"] = dcf_value

    # --- Method 2: EV/FCF implied price ---
    ev_fcf_value = _ev_fcf_implied_per_share(period, market_cap, shares)
    if ev_fcf_value is not None:
        methods["ev_fcf"] = ev_fcf_value

    # --- Method 3: Acquirer's Multiple implied price ---
    acq_value = _acquirers_implied_per_share(period, market_cap, shares)
    if acq_value is not None:
        methods["acquirers_multiple"] = acq_value

    # --- Method 4: Shareholder Yield implied price ---
    shyd_value = _shareholder_yield_implied_per_share(period, market_cap, shares)
    if shyd_value is not None:
        methods["shareholder_yield"] = shyd_value

    actual = _latest_close(price_bars)

    if not methods:
        return PriceTargets(actual_price=actual, valuation_methods={})

    # Weighted consensus
    total_weight = sum(_METHOD_WEIGHTS[k] for k in methods)
    intrinsic = sum(
        methods[k] * _METHOD_WEIGHTS[k] / total_weight for k in methods
    )

    mos = _MOS_BY_CONVICTION.get(conviction_level, 0.25)
    buy = intrinsic * (1 - mos)
    sell = intrinsic  # Fair value = sell target

    upside = None
    if actual and actual > 0:
        upside = (intrinsic - actual) / actual

    return PriceTargets(
        intrinsic_value=round(intrinsic, 2),
        buy_price=round(buy, 2),
        sell_price=round(sell, 2),
        actual_price=actual,
        price_upside=round(upside, 4) if upside is not None else None,
        valuation_methods={k: round(v, 2) for k, v in methods.items()},
    )


def _latest_close(bars: list[PriceBar]) -> float | None:
    """Get the latest close price from price bars."""
    if not bars:
        return None
    # Sort by date descending to find latest
    sorted_bars = sorted(bars, key=lambda b: b.date, reverse=True)
    return float(sorted_bars[0].close)


def _dcf_intrinsic_per_share(
    period: FinancialPeriod,
    shares: int,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    projection_years: int,
) -> float | None:
    """Two-stage DCF intrinsic value per share."""
    fcf = period.current_cash_flow.free_cash_flow
    if fcf <= 0 or discount_rate <= terminal_growth_rate:
        return None

    fcf_float = float(fcf)
    pv_sum = sum(
        fcf_float * (1 + growth_rate) ** t / (1 + discount_rate) ** t
        for t in range(1, projection_years + 1)
    )
    final_fcf = fcf_float * (1 + growth_rate) ** projection_years
    terminal = final_fcf * (1 + terminal_growth_rate) / (
        discount_rate - terminal_growth_rate
    )
    pv_terminal = terminal / (1 + discount_rate) ** projection_years

    total = pv_sum + pv_terminal
    if total <= 0:
        return None
    return total / shares


def _ev_fcf_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_multiple: float = 15.0,
) -> float | None:
    """Implied price from target EV/FCF multiple.

    Uses a conservative target multiple of 15x (sector median proxy).
    implied_ev = target_multiple * FCF
    implied_equity = implied_ev - debt + cash
    implied_price = implied_equity / shares
    """
    fcf = period.current_cash_flow.free_cash_flow
    if fcf <= 0:
        return None

    debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    implied_ev = target_multiple * float(fcf)
    implied_equity = implied_ev - float(debt) + float(cash)
    if implied_equity <= 0:
        return None
    return implied_equity / shares


def _acquirers_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_multiple: float = 12.0,
) -> float | None:
    """Implied price from target EV/EBIT multiple.

    Uses a conservative target multiple of 12x (sector median proxy).
    """
    ebit = period.current_income.ebit
    if ebit <= 0:
        return None

    debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    implied_ev = target_multiple * float(ebit)
    implied_equity = implied_ev - float(debt) + float(cash)
    if implied_equity <= 0:
        return None
    return implied_equity / shares


def _shareholder_yield_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_yield: float = 0.04,
) -> float | None:
    """Implied price from target shareholder yield.

    Uses a 4% target yield (sector median proxy).
    implied_market_cap = total_return / target_yield
    implied_price = implied_market_cap / shares
    """
    dividends = abs(period.current_cash_flow.dividends_paid or Decimal("0"))
    net_buybacks = period.current_cash_flow.net_buybacks
    total_return = float(dividends + net_buybacks)

    if total_return <= 0:
        return None

    implied_market_cap = total_return / target_yield
    return implied_market_cap / shares
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All tests PASS

**Step 5: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All 784+ tests PASS (no regressions)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat(engine): add multi-factor price target computation"
```

---

## Task 3: Add Price Fields to `CompositeScore` Model

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:83-116`
- Test: `engine/tests/models/test_scoring.py`

**Step 1: Write the failing test**

```python
# Append to engine/tests/models/test_scoring.py
def test_composite_score_price_fields():
    score = CompositeScore(
        ticker="AAPL",
        composite_percentile=96.0,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
        intrinsic_value=195.20,
        buy_price=156.16,
        sell_price=195.20,
        actual_price=167.42,
        price_upside=0.166,
        valuation_methods={"dcf": 210.0, "ev_fcf": 185.0},
    )
    assert score.intrinsic_value == 195.20
    assert score.buy_price == 156.16
    assert score.sell_price == 195.20
    assert score.actual_price == 167.42
    assert score.price_upside == 0.166
    assert score.valuation_methods == {"dcf": 210.0, "ev_fcf": 185.0}


def test_composite_score_price_fields_default_none():
    score = CompositeScore(
        ticker="AAPL",
        composite_percentile=50.0,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
    )
    assert score.intrinsic_value is None
    assert score.buy_price is None
    assert score.sell_price is None
    assert score.actual_price is None
    assert score.price_upside is None
    assert score.valuation_methods is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/models/test_scoring.py::test_composite_score_price_fields -v`
Expected: FAIL — unexpected keyword argument

**Step 3: Write implementation**

In `engine/src/margin_engine/models/scoring.py`, add to `CompositeScore` after line 93 (`growth_stage`):

```python
    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    valuation_methods: dict[str, float] | None = None
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/models/test_scoring.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/models/test_scoring.py
git commit -m "feat(engine): add price target fields to CompositeScore"
```

---

## Task 4: Integrate Price Targets into Scoring Pipeline

**Files:**
- Modify: `engine/src/margin_engine/scoring/composite.py:19-96`
- Modify: `api/src/margin_api/services/scoring.py:289-314`
- Test: `engine/tests/scoring/test_composite.py`

**Step 1: Write the failing test**

```python
# Append to engine/tests/scoring/test_composite.py
def test_composite_score_with_price_targets():
    from margin_engine.scoring.quantitative.price_targets import PriceTargets

    targets = PriceTargets(
        intrinsic_value=195.20,
        buy_price=156.16,
        sell_price=195.20,
        actual_price=167.42,
        price_upside=0.166,
        valuation_methods={"dcf": 210.0, "ev_fcf": 185.0},
    )
    score = compute_composite_score(
        ticker="AAPL",
        quality_scores=[FactorScore(name="gp", raw_value=0.5, percentile_rank=80.0)],
        value_scores=[FactorScore(name="ev", raw_value=12.0, percentile_rank=75.0)],
        momentum_scores=[FactorScore(name="pm", raw_value=0.1, percentile_rank=60.0)],
        filters_passed=[],
        price_targets=targets,
    )
    assert score.intrinsic_value == 195.20
    assert score.buy_price == 156.16
    assert score.sell_price == 195.20
    assert score.actual_price == 167.42
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_composite.py::test_composite_score_with_price_targets -v`
Expected: FAIL — unexpected keyword argument `price_targets`

**Step 3: Write implementation**

In `engine/src/margin_engine/scoring/composite.py`, modify `compute_composite_score` to accept an optional `price_targets` parameter:

```python
from margin_engine.scoring.quantitative.price_targets import PriceTargets

def compute_composite_score(
    ticker: str,
    quality_scores: list[FactorScore],
    value_scores: list[FactorScore],
    momentum_scores: list[FactorScore],
    filters_passed: list[FilterResult],
    growth_stage: GrowthStage | None = None,
    config: ScoringConfig | None = None,
    price_targets: PriceTargets | None = None,
) -> CompositeScore:
```

At the end where `CompositeScore` is assembled (around line 87), add price target fields:

```python
    # 6. Attach price targets if provided
    price_kwargs = {}
    if price_targets:
        price_kwargs = {
            "intrinsic_value": price_targets.intrinsic_value,
            "buy_price": price_targets.buy_price,
            "sell_price": price_targets.sell_price,
            "actual_price": price_targets.actual_price,
            "price_upside": price_targets.price_upside,
            "valuation_methods": price_targets.valuation_methods,
        }

    return CompositeScore(
        ticker=ticker,
        composite_percentile=composite_percentile,
        quality=quality,
        value=value,
        momentum=momentum,
        filters_passed=filters_passed,
        data_coverage=data_coverage,
        growth_stage=growth_stage,
        **price_kwargs,
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_composite.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/composite.py engine/tests/scoring/test_composite.py
git commit -m "feat(engine): integrate price targets into composite scorer"
```

---

## Task 5: Update Price-Aware Signal Logic

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:108-115` (the `signal` property)
- Test: `engine/tests/models/test_scoring.py`

**Step 1: Write the failing tests**

```python
# Append to engine/tests/models/test_scoring.py

def _make_score(percentile, actual=None, buy=None, sell=None, growth_stage=None):
    return CompositeScore(
        ticker="TEST",
        composite_percentile=percentile,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
        growth_stage=growth_stage,
        actual_price=actual,
        buy_price=buy,
        sell_price=sell,
    )


def test_signal_buy_when_below_buy_price():
    score = _make_score(96.0, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.BUY


def test_signal_hold_when_between_buy_and_sell():
    score = _make_score(96.0, actual=135.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.HOLD


def test_signal_sell_when_above_sell_price():
    score = _make_score(96.0, actual=155.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.SELL


def test_signal_urgent_sell_when_far_above_sell():
    score = _make_score(96.0, actual=175.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.URGENT_SELL


def test_signal_watch_for_watchlist_conviction():
    score = _make_score(92.0, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.WATCH


def test_signal_no_action_for_low_conviction():
    score = _make_score(50.0, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.NO_ACTION


def test_signal_fallback_buy_when_no_prices():
    """When no price data, fall back to conviction-based signal."""
    score = _make_score(96.0)
    assert score.signal == Signal.BUY
```

**Step 2: Run tests to verify some fail**

Run: `uv run pytest engine/tests/models/test_scoring.py -k "signal" -v`
Expected: HOLD, SELL, URGENT_SELL tests FAIL (those signals aren't produced by current logic)

**Step 3: Write implementation**

Replace the `signal` property in `CompositeScore` (line 108-115):

```python
    @property
    def signal(self) -> Signal:
        level = self.conviction_level
        if level == ConvictionLevel.WATCHLIST:
            return Signal.WATCH
        if level == ConvictionLevel.NONE:
            return Signal.NO_ACTION
        # High/Exceptional conviction: use price-aware signals if available
        if self.actual_price is not None and self.sell_price is not None and self.buy_price is not None:
            if self.actual_price > self.sell_price * 1.15:
                return Signal.URGENT_SELL
            if self.actual_price > self.sell_price:
                return Signal.SELL
            if self.actual_price <= self.buy_price:
                return Signal.BUY
            return Signal.HOLD
        # Fallback: conviction-based
        return Signal.BUY
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/models/test_scoring.py -v`
Expected: All PASS

**Step 5: Run full engine suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All 784+ tests PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/models/test_scoring.py
git commit -m "feat(engine): add price-aware signal logic"
```

---

## Task 6: Add `signal_transitions` DB Table

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: `api/alembic/versions/<auto>_add_price_targets_and_signal_transitions.py`
- Test: `api/tests/db/test_models.py`

**Step 1: Write the failing test**

```python
# Append to api/tests/db/test_models.py
import pytest
from margin_api.db.models import SignalTransition


def test_signal_transition_model_exists():
    """SignalTransition model should be importable."""
    assert SignalTransition.__tablename__ == "signal_transitions"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/db/test_models.py::test_signal_transition_model_exists -v`
Expected: FAIL — `SignalTransition` not importable

**Step 3: Write implementation**

Add to `api/src/margin_api/db/models.py` (after the `Recommendation` class, around line 123):

```python
class SignalTransition(Base):
    """Audit trail for signal changes on scored assets."""

    __tablename__ = "signal_transitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    previous_signal: Mapped[str] = mapped_column(String(20))
    new_signal: Mapped[str] = mapped_column(String(20))
    previous_conviction: Mapped[str] = mapped_column(String(20))
    new_conviction: Mapped[str] = mapped_column(String(20))
    actual_price_at_transition: Mapped[float | None] = mapped_column(nullable=True)
    intrinsic_value_at_transition: Mapped[float | None] = mapped_column(nullable=True)
    composite_percentile: Mapped[float]
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        UniqueConstraint("asset_id", "transitioned_at", name="uq_signal_transition_asset_time"),
    )
```

Also add price columns to the `Score` model (after `score_detail` on line 97):

```python
    intrinsic_value: Mapped[float | None] = mapped_column(nullable=True)
    buy_price: Mapped[float | None] = mapped_column(nullable=True)
    sell_price: Mapped[float | None] = mapped_column(nullable=True)
    actual_price: Mapped[float | None] = mapped_column(nullable=True)
```

**Step 4: Generate Alembic migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add price targets and signal transitions"`

Review the generated migration, then:

Run: `uv run alembic upgrade head`

**Step 5: Run test**

Run: `uv run pytest api/tests/db/test_models.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add signal_transitions table and price columns to scores"
```

---

## Task 7: Update API Schemas with Price Fields

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py`
- Modify: `api/src/margin_api/schemas/dashboard.py`
- Test: `api/tests/schemas/test_scores.py`

**Step 1: Write the failing test**

```python
# api/tests/schemas/test_scores.py
from margin_api.schemas.scores import ScoreResponse, PriceBarResponse, SignalTransitionResponse


def test_score_response_has_price_fields():
    data = {
        "ticker": "AAPL",
        "composite_percentile": 96.0,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 80.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 75.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 60.0},
        "filters_passed": [],
        "data_coverage": 1.0,
        "intrinsic_value": 195.20,
        "buy_price": 156.16,
        "sell_price": 195.20,
        "actual_price": 167.42,
        "price_upside": 0.166,
        "valuation_methods": {"dcf": 210.0},
    }
    resp = ScoreResponse(**data)
    assert resp.intrinsic_value == 195.20
    assert resp.buy_price == 156.16
    assert resp.actual_price == 167.42


def test_score_response_price_fields_default_none():
    data = {
        "ticker": "AAPL",
        "composite_percentile": 50.0,
        "conviction_level": "none",
        "signal": "no_action",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 50.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }
    resp = ScoreResponse(**data)
    assert resp.intrinsic_value is None
    assert resp.buy_price is None
    assert resp.price_history is None


def test_price_bar_response():
    bar = PriceBarResponse(
        date="2025-09-28", open=195.0, high=198.0, low=194.0,
        close=197.0, volume=50000000, adj_close=197.0,
    )
    assert bar.close == 197.0


def test_signal_transition_response():
    t = SignalTransitionResponse(
        previous_signal="watch",
        new_signal="buy",
        previous_conviction="watchlist",
        new_conviction="high",
        actual_price_at_transition=167.42,
        intrinsic_value_at_transition=195.20,
        composite_percentile=96.0,
        transitioned_at="2026-02-14T00:00:00+00:00",
    )
    assert t.new_signal == "buy"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_scores.py -v`
Expected: FAIL — fields not found

**Step 3: Write implementation**

Update `api/src/margin_api/schemas/scores.py`:

```python
"""Score-related API response schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from margin_engine.models.scoring import CompositeScore, FactorBreakdown


class FilterResultResponse(BaseModel):
    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    verdict: str


class FactorScoreResponse(BaseModel):
    name: str
    raw_value: float
    percentile_rank: float
    detail: str = ""


class FactorBreakdownResponse(BaseModel):
    factor_name: str
    weight: float
    sub_scores: list[FactorScoreResponse]
    average_percentile: float


class PriceBarResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None


class SignalTransitionResponse(BaseModel):
    previous_signal: str
    new_signal: str
    previous_conviction: str
    new_conviction: str
    actual_price_at_transition: float | None = None
    intrinsic_value_at_transition: float | None = None
    composite_percentile: float
    transitioned_at: str


class ScoreResponse(BaseModel):
    ticker: str
    name: str = ""
    composite_percentile: float
    conviction_level: str
    signal: str
    quality: FactorBreakdownResponse
    value: FactorBreakdownResponse
    momentum: FactorBreakdownResponse
    filters_passed: list[FilterResultResponse]
    data_coverage: float
    growth_stage: str | None = None
    scored_at: str | None = None
    # Price target fields
    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    valuation_methods: dict[str, float] | None = None
    # Conditionally included via ?include=
    price_history: list[PriceBarResponse] | None = None
    signal_history: list[SignalTransitionResponse] | None = None

    @classmethod
    def from_engine(cls, score: CompositeScore) -> ScoreResponse:
        return cls(
            ticker=score.ticker,
            composite_percentile=score.composite_percentile,
            conviction_level=score.conviction_level.value,
            signal=score.signal.value,
            quality=_breakdown_from_engine(score.quality),
            value=_breakdown_from_engine(score.value),
            momentum=_breakdown_from_engine(score.momentum),
            filters_passed=[
                FilterResultResponse(
                    name=f.name,
                    passed=f.passed,
                    value=f.value,
                    threshold=f.threshold,
                    detail=f.detail,
                    verdict=f.verdict.value,
                )
                for f in score.filters_passed
            ],
            data_coverage=score.data_coverage,
            growth_stage=score.growth_stage.value if score.growth_stage else None,
            intrinsic_value=score.intrinsic_value,
            buy_price=score.buy_price,
            sell_price=score.sell_price,
            actual_price=score.actual_price,
            price_upside=score.price_upside,
            valuation_methods=score.valuation_methods,
        )


class ScoreListResponse(BaseModel):
    scores: list[ScoreResponse]
    total: int
    page: int = 1
    page_size: int = 50


def _breakdown_from_engine(
    breakdown: FactorBreakdown,
) -> FactorBreakdownResponse:
    return FactorBreakdownResponse(
        factor_name=breakdown.factor_name,
        weight=breakdown.weight,
        sub_scores=[
            FactorScoreResponse(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=s.percentile_rank,
                detail=s.detail,
            )
            for s in breakdown.sub_scores
        ],
        average_percentile=breakdown.average_percentile,
    )
```

Update `api/src/margin_api/schemas/dashboard.py` — add price fields to `PickSummary`:

```python
class PickSummary(BaseModel):
    ticker: str
    name: str
    composite_percentile: float
    conviction_level: str
    signal: str
    quality_percentile: float
    value_percentile: float
    momentum_percentile: float
    actual_price: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    price_upside: float | None = None
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/schemas/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/schemas/dashboard.py api/tests/schemas/
git commit -m "feat(api): add price target and signal transition schemas"
```

---

## Task 8: Update API Routes to Serve Price Data

**Files:**
- Modify: `api/src/margin_api/routes/scores.py`
- Modify: `api/src/margin_api/routes/dashboard.py`
- Test: `api/tests/routes/test_scores.py`

**Step 1: Write the failing test**

```python
# Append to api/tests/routes/test_scores.py
import pytest


@pytest.mark.asyncio
async def test_get_score_includes_price_fields(client, seeded_db):
    """Score response should include price target fields."""
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    # Fields exist (may be null)
    assert "intrinsic_value" in data
    assert "buy_price" in data
    assert "sell_price" in data
    assert "actual_price" in data
    assert "price_upside" in data


@pytest.mark.asyncio
async def test_get_score_with_price_history(client, seeded_db):
    """Score response with include=price_history should include bars."""
    resp = await client.get("/api/v1/scores/AAPL?include=price_history")
    assert resp.status_code == 200
    data = resp.json()
    assert "price_history" in data


@pytest.mark.asyncio
async def test_get_score_with_signal_history(client, seeded_db):
    """Score response with include=signal_history should include transitions."""
    resp = await client.get("/api/v1/scores/AAPL?include=signal_history")
    assert resp.status_code == 200
    data = resp.json()
    assert "signal_history" in data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_scores.py -k "price" -v`
Expected: FAIL

**Step 3: Write implementation**

Update `api/src/margin_api/routes/scores.py`:

1. Add `include` query parameter to `get_score`:

```python
@router.get("/{ticker}", response_model=ScoreResponse)
async def get_score(
    ticker: str,
    include: str | None = Query(None, description="Comma-separated: price_history,signal_history"),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
```

2. In the handler, after building the base response, conditionally fetch:

```python
    response = _score_response_from_row(row)

    includes = set((include or "").split(",")) if include else set()

    if "price_history" in includes:
        # Fetch price_history from FinancialData
        from margin_api.db.models import FinancialData
        from margin_api.schemas.scores import PriceBarResponse

        fd_query = (
            select(FinancialData.price_history)
            .where(FinancialData.asset_id == row[0].asset_id)
            .order_by(FinancialData.period_end.desc())
            .limit(1)
        )
        fd_result = await db.execute(fd_query)
        fd_row = fd_result.scalar()
        if fd_row and isinstance(fd_row, dict) and "bars" in fd_row:
            response.price_history = [
                PriceBarResponse(**bar) for bar in fd_row["bars"]
            ]
        else:
            response.price_history = []

    if "signal_history" in includes:
        from margin_api.db.models import SignalTransition
        from margin_api.schemas.scores import SignalTransitionResponse

        st_query = (
            select(SignalTransition)
            .where(SignalTransition.asset_id == row[0].asset_id)
            .order_by(SignalTransition.transitioned_at.desc())
            .limit(50)
        )
        st_result = await db.execute(st_query)
        transitions = st_result.scalars().all()
        response.signal_history = [
            SignalTransitionResponse(
                previous_signal=t.previous_signal,
                new_signal=t.new_signal,
                previous_conviction=t.previous_conviction,
                new_conviction=t.new_conviction,
                actual_price_at_transition=t.actual_price_at_transition,
                intrinsic_value_at_transition=t.intrinsic_value_at_transition,
                composite_percentile=t.composite_percentile,
                transitioned_at=t.transitioned_at.isoformat(),
            )
            for t in transitions
        ]

    return response
```

3. Update `_score_response_from_row` to include price fields from `score_detail` and from Score columns.

4. Update dashboard route to include price fields in `PickSummary` construction:

```python
PickSummary(
    ticker=row.ticker,
    name=row.asset_name,
    composite_percentile=row.Score.composite_percentile,
    conviction_level=row.Score.conviction_level,
    signal=row.Score.signal,
    quality_percentile=row.Score.quality_percentile,
    value_percentile=row.Score.value_percentile,
    momentum_percentile=row.Score.momentum_percentile,
    actual_price=row.Score.actual_price,
    buy_price=row.Score.buy_price,
    sell_price=row.Score.sell_price,
    price_upside=None,  # Compute if both prices available
)
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/routes/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/src/margin_api/routes/dashboard.py api/tests/routes/
git commit -m "feat(api): serve price targets and optional history in score responses"
```

---

## Task 9: Update TypeScript Types

**Files:**
- Modify: `web/src/lib/api/types.ts`

**Step 1: Add new types and update existing interfaces**

```typescript
// Add to types.ts

export interface PriceBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  adj_close: number | null
}

export interface SignalTransition {
  previous_signal: string
  new_signal: string
  previous_conviction: string
  new_conviction: string
  actual_price_at_transition: number | null
  intrinsic_value_at_transition: number | null
  composite_percentile: number
  transitioned_at: string
}
```

Update `ScoreResponse`:

```typescript
export interface ScoreResponse {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
  signal: string
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  filters_passed: FilterResultResponse[]
  data_coverage: number
  growth_stage?: string
  scored_at?: string
  // Price targets
  intrinsic_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  price_upside: number | null
  valuation_methods: Record<string, number> | null
  // Optional includes
  price_history?: PriceBar[] | null
  signal_history?: SignalTransition[] | null
}
```

Update `PickSummary`:

```typescript
export interface PickSummary {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
  signal: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  actual_price: number | null
  buy_price: number | null
  sell_price: number | null
  price_upside: number | null
}
```

**Step 2: Update `getScore` to support `include` parameter**

In `web/src/lib/api/scores.ts`:

```typescript
export async function getScore(
  ticker: string,
  include?: string[],
): Promise<ScoreResponse> {
  const params = include?.length ? `?include=${include.join(',')}` : ''
  return apiFetch<ScoreResponse>(`/api/v1/scores/${ticker.toUpperCase()}${params}`)
}
```

**Step 3: Commit**

```bash
git add web/src/lib/api/types.ts web/src/lib/api/scores.ts
git commit -m "feat(web): update TypeScript types for price targets and signal history"
```

---

## Task 10: Create ActionPill Component

**Files:**
- Create: `web/src/components/ui/action-pill.tsx`
- Modify: `web/src/components/ui/index.ts`

**Step 1: Create component**

```typescript
// web/src/components/ui/action-pill.tsx
interface ActionPillProps {
  signal: string
  buyPrice?: number | null
  sellPrice?: number | null
  actualPrice?: number | null
  intrinsicValue?: number | null
  className?: string
}

const pillConfig: Record<string, { bg: string; text: string; label: string }> = {
  buy: { bg: "bg-bullish/10", text: "text-bullish", label: "BUY" },
  hold: { bg: "bg-accent/10", text: "text-accent", label: "HOLD" },
  sell: { bg: "bg-warning/10", text: "text-warning", label: "SELL" },
  watch: { bg: "bg-text-secondary/10", text: "text-text-secondary", label: "WATCH" },
  urgent_sell: { bg: "bg-bearish/10", text: "text-bearish", label: "SELL" },
  no_action: { bg: "bg-bg-secondary", text: "text-text-tertiary", label: "N/A" },
}

function formatPrice(price: number | null | undefined): string {
  if (price == null) return "N/A"
  return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function getSubtext(
  signal: string,
  buyPrice?: number | null,
  sellPrice?: number | null,
  actualPrice?: number | null,
  intrinsicValue?: number | null,
): string {
  const s = signal.toLowerCase()
  if (s === "buy" && buyPrice != null) return `Below ${formatPrice(buyPrice)}`
  if (s === "hold" && actualPrice != null && intrinsicValue != null) {
    const pct = ((actualPrice - (buyPrice ?? actualPrice)) / (buyPrice ?? actualPrice) * 100)
    return `+${pct.toFixed(1)}%`
  }
  if (s === "sell" && sellPrice != null) return `Above ${formatPrice(sellPrice)}`
  if (s === "urgent_sell" && actualPrice != null && sellPrice != null) {
    const pct = ((actualPrice - sellPrice) / sellPrice * 100)
    return `+${pct.toFixed(0)}% over FV`
  }
  if (s === "watch") return "Monitoring"
  return ""
}

export function ActionPill({
  signal,
  buyPrice,
  sellPrice,
  actualPrice,
  intrinsicValue,
  className = "",
}: ActionPillProps) {
  const config = pillConfig[signal.toLowerCase()] ?? pillConfig.no_action
  const subtext = getSubtext(signal, buyPrice, sellPrice, actualPrice, intrinsicValue)

  return (
    <div
      className={`inline-flex flex-col items-center px-3 py-1.5 rounded-sm ${config.bg} ${className}`}
      data-testid="action-pill"
    >
      <span className={`text-sm font-semibold uppercase tracking-wide ${config.text}`}>
        {config.label}
      </span>
      {subtext && (
        <span className={`text-xs ${config.text} opacity-70`}>{subtext}</span>
      )}
    </div>
  )
}
```

**Step 2: Export from index**

Add to `web/src/components/ui/index.ts`:

```typescript
export { ActionPill } from "./action-pill"
```

**Step 3: Commit**

```bash
git add web/src/components/ui/action-pill.tsx web/src/components/ui/index.ts
git commit -m "feat(web): create ActionPill component with price-aware states"
```

---

## Task 11: Create Sparkline Component

**Files:**
- Create: `web/src/components/ui/sparkline.tsx`
- Modify: `web/src/components/ui/index.ts`

**Step 1: Create component**

```typescript
// web/src/components/ui/sparkline.tsx
import type { PriceBar } from "@/lib/api/types"

interface SparklineProps {
  bars: PriceBar[] | null | undefined
  buyPrice?: number | null
  sellPrice?: number | null
  width?: number
  height?: number
  className?: string
}

export function Sparkline({
  bars,
  buyPrice,
  sellPrice,
  width = 120,
  height = 32,
  className = "",
}: SparklineProps) {
  if (!bars || bars.length < 2) {
    // Null state: flat gray placeholder
    return (
      <svg
        width={width}
        height={height}
        className={className}
        data-testid="sparkline-empty"
      >
        <line
          x1={4}
          y1={height / 2}
          x2={width - 4}
          y2={height / 2}
          stroke="currentColor"
          strokeWidth={1}
          className="text-text-tertiary"
          strokeDasharray="4 2"
        />
      </svg>
    )
  }

  const closes = bars.map((b) => b.close)
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const range = max - min || 1
  const padding = 4

  const points = closes
    .map((c, i) => {
      const x = padding + (i / (closes.length - 1)) * (width - padding * 2)
      const y = padding + (1 - (c - min) / range) * (height - padding * 2)
      return `${x},${y}`
    })
    .join(" ")

  const lastClose = closes[closes.length - 1]
  let strokeColor = "text-text-secondary"
  if (buyPrice != null && lastClose <= buyPrice) strokeColor = "text-bullish"
  if (sellPrice != null && lastClose > sellPrice) strokeColor = "text-bearish"

  return (
    <svg
      width={width}
      height={height}
      className={className}
      data-testid="sparkline"
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        points={points}
        className={strokeColor}
      />
    </svg>
  )
}
```

**Step 2: Export from index**

Add to `web/src/components/ui/index.ts`:

```typescript
export { Sparkline } from "./sparkline"
```

**Step 3: Commit**

```bash
git add web/src/components/ui/sparkline.tsx web/src/components/ui/index.ts
git commit -m "feat(web): create Sparkline component for price trend visualization"
```

---

## Task 12: Update StockCard with Action Pill, Price Row, and Sparkline

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Update imports and fetch call**

Replace the `SignalBadge` import with `ActionPill` and `Sparkline`. Update `getScore` call to include `price_history`:

```typescript
import { ActionPill, Sparkline, PercentileBar, ConvictionBadge } from "@/components/ui"
```

Update the `getScore` call in `handleClick`:

```typescript
const data = await getScore(pick.ticker, ["price_history", "signal_history"])
```

**Step 2: Replace SignalBadge with ActionPill and add price row**

Replace the signal badge area:

```tsx
<div className="flex items-center justify-between mb-4">
  <span className="text-3xl font-bold text-accent">
    {pick.composite_percentile.toFixed(0)}
  </span>
  <ActionPill
    signal={pick.signal}
    buyPrice={pick.buy_price}
    sellPrice={pick.sell_price}
    actualPrice={pick.actual_price}
  />
</div>

{/* Price row */}
<div className="flex items-center justify-between mb-4 text-sm">
  <div className="flex items-center gap-4">
    <span className="text-text-secondary">
      Price:{" "}
      <span className="text-text-primary font-medium">
        {pick.actual_price != null
          ? `$${pick.actual_price.toFixed(2)}`
          : "N/A"}
      </span>
    </span>
    <span className="text-text-secondary">
      Target:{" "}
      <span className="text-text-primary font-medium">
        {pick.sell_price != null
          ? `$${pick.sell_price.toFixed(2)}`
          : "N/A"}
      </span>
    </span>
    {pick.price_upside != null && (
      <span className={pick.price_upside >= 0 ? "text-bullish" : "text-bearish"}>
        {pick.price_upside >= 0 ? "+" : ""}
        {(pick.price_upside * 100).toFixed(1)}%
      </span>
    )}
  </div>
  <Sparkline
    bars={scoreData?.price_history}
    buyPrice={pick.buy_price}
    sellPrice={pick.sell_price}
  />
</div>
```

**Step 3: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): update StockCard with ActionPill, price row, and sparkline"
```

---

## Task 13: Create Price Chart Component

**Files:**
- Create: `web/src/components/dashboard/price-chart.tsx`

**Step 1: Install Recharts** (check if already installed first)

Run: `cd web && grep recharts package.json`

If not present: `npm install recharts`

**Step 2: Create component**

```typescript
// web/src/components/dashboard/price-chart.tsx
"use client"

import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts"
import type { PriceBar } from "@/lib/api/types"

interface PriceChartProps {
  bars: PriceBar[]
  buyPrice?: number | null
  sellPrice?: number | null
  className?: string
}

type TimeRange = "1M" | "3M" | "6M" | "1Y"

const RANGE_DAYS: Record<TimeRange, number> = {
  "1M": 22,
  "3M": 66,
  "6M": 132,
  "1Y": 252,
}

export function PriceChart({
  bars,
  buyPrice,
  sellPrice,
  className = "",
}: PriceChartProps) {
  const [range, setRange] = useState<TimeRange>("3M")

  if (!bars || bars.length === 0) {
    return (
      <div
        className={`h-64 flex items-center justify-center bg-bg-secondary rounded-sm ${className}`}
        data-testid="price-chart-empty"
      >
        <span className="text-sm text-text-tertiary">
          No price data available
        </span>
      </div>
    )
  }

  const sorted = [...bars].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const sliced = sorted.slice(-RANGE_DAYS[range])

  const data = sliced.map((bar) => ({
    date: bar.date.slice(5), // "MM-DD"
    close: bar.close,
    volume: bar.volume,
    open: bar.open,
    high: bar.high,
    low: bar.low,
  }))

  return (
    <div className={className} data-testid="price-chart">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-text-primary">Price History</h4>
        <div className="flex gap-1">
          {(["1M", "3M", "6M", "1Y"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={(e) => {
                e.stopPropagation()
                setRange(r)
              }}
              className={`px-2 py-0.5 text-xs rounded-sm transition-colors ${
                range === r
                  ? "bg-accent text-bg-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            className="text-text-tertiary"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            className="text-text-tertiary"
            width={60}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-elevated)",
              border: "1px solid var(--border-primary)",
              borderRadius: "2px",
              fontSize: "12px",
            }}
            formatter={(value: number, name: string) => [
              name === "volume"
                ? value.toLocaleString()
                : `$${value.toFixed(2)}`,
              name.charAt(0).toUpperCase() + name.slice(1),
            ]}
          />
          <Bar
            dataKey="volume"
            fill="currentColor"
            className="text-text-tertiary"
            opacity={0.15}
            yAxisId="volume"
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <Line
            type="monotone"
            dataKey="close"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            className="text-accent"
          />
          {buyPrice != null && (
            <ReferenceLine
              y={buyPrice}
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-bullish"
              label={{ value: "Buy", position: "left", fontSize: 10 }}
            />
          )}
          {sellPrice != null && (
            <ReferenceLine
              y={sellPrice}
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-warning"
              label={{ value: "Sell", position: "left", fontSize: 10 }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add web/src/components/dashboard/price-chart.tsx
git commit -m "feat(web): create PriceChart component with time range selector"
```

---

## Task 14: Create Valuation Breakdown and Signal Timeline Components

**Files:**
- Create: `web/src/components/dashboard/valuation-breakdown.tsx`
- Create: `web/src/components/dashboard/signal-timeline.tsx`

**Step 1: Create ValuationBreakdown**

```typescript
// web/src/components/dashboard/valuation-breakdown.tsx
interface ValuationBreakdownProps {
  methods: Record<string, number> | null | undefined
  intrinsicValue: number | null | undefined
  className?: string
}

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

export function ValuationBreakdown({
  methods,
  intrinsicValue,
  className = "",
}: ValuationBreakdownProps) {
  if (!methods || Object.keys(methods).length === 0) {
    return (
      <div className={`${className}`} data-testid="valuation-empty">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Valuation</h4>
        <p className="text-sm text-text-tertiary">No valuation data available</p>
      </div>
    )
  }

  const entries = Object.entries(methods)
  const maxValue = Math.max(...entries.map(([, v]) => v))

  return (
    <div className={className} data-testid="valuation-breakdown">
      <h4 className="text-sm font-semibold text-text-primary mb-3">Valuation Methods</h4>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-text-secondary w-28 shrink-0">
              {METHOD_LABELS[key] ?? key}
            </span>
            <div className="flex-1 h-4 bg-bg-secondary rounded-sm overflow-hidden">
              <div
                className="h-full bg-accent/40 rounded-sm"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
            <span className="text-xs text-text-primary font-medium w-16 text-right">
              ${value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
      {intrinsicValue != null && (
        <div className="mt-3 pt-3 border-t border-border-primary flex justify-between text-sm">
          <span className="text-text-secondary">Consensus</span>
          <span className="text-text-primary font-semibold">${intrinsicValue.toFixed(2)}</span>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Create SignalTimeline**

```typescript
// web/src/components/dashboard/signal-timeline.tsx
import type { SignalTransition } from "@/lib/api/types"

interface SignalTimelineProps {
  transitions: SignalTransition[] | null | undefined
  className?: string
}

const signalColor: Record<string, string> = {
  buy: "text-bullish",
  hold: "text-accent",
  sell: "text-warning",
  urgent_sell: "text-bearish",
  watch: "text-text-secondary",
  no_action: "text-text-tertiary",
}

export function SignalTimeline({
  transitions,
  className = "",
}: SignalTimelineProps) {
  if (!transitions || transitions.length === 0) {
    return (
      <div className={className} data-testid="signal-timeline-empty">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Signal History</h4>
        <p className="text-sm text-text-tertiary">No transitions recorded</p>
      </div>
    )
  }

  return (
    <div className={className} data-testid="signal-timeline">
      <h4 className="text-sm font-semibold text-text-primary mb-3">Signal History</h4>
      <div className="space-y-3">
        {transitions.map((t, i) => {
          const date = new Date(t.transitioned_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })
          return (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="text-text-tertiary w-14 shrink-0">{date}</span>
              <span className={`uppercase text-xs font-medium ${signalColor[t.previous_signal] ?? ""}`}>
                {t.previous_signal.replace("_", " ")}
              </span>
              <span className="text-text-tertiary">&rarr;</span>
              <span className={`uppercase text-xs font-medium ${signalColor[t.new_signal] ?? ""}`}>
                {t.new_signal.replace("_", " ")}
              </span>
              {t.actual_price_at_transition != null && (
                <span className="text-text-secondary ml-auto">
                  @${t.actual_price_at_transition.toFixed(2)}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add web/src/components/dashboard/valuation-breakdown.tsx web/src/components/dashboard/signal-timeline.tsx
git commit -m "feat(web): create ValuationBreakdown and SignalTimeline components"
```

---

## Task 15: Update AssetDetail with New Sections

**Files:**
- Modify: `web/src/components/dashboard/asset-detail.tsx`

**Step 1: Import new components and update layout**

```typescript
import { ConvictionBadge } from "@/components/ui"
import { ActionPill } from "@/components/ui"
import { formatAttributeLabel, formatScoredAt } from "@/lib/format"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import { PriceChart } from "./price-chart"
import { ValuationBreakdown } from "./valuation-breakdown"
import { SignalTimeline } from "./signal-timeline"
import type { ScoreResponse } from "@/lib/api/types"
```

**Step 2: Add price chart, valuation, and signal timeline sections**

After the header and before the grid, add the price chart:

```tsx
{/* Price Chart — full width */}
<PriceChart
  bars={score.price_history ?? undefined}
  buyPrice={score.buy_price}
  sellPrice={score.sell_price}
  className="mb-6"
/>
```

In the right column, add valuation and signal timeline:

```tsx
<ValuationBreakdown
  methods={score.valuation_methods}
  intrinsicValue={score.intrinsic_value}
/>

<SignalTimeline transitions={score.signal_history ?? undefined} />
```

Replace `SignalBadge` with `ActionPill` in the header.

**Step 3: Commit**

```bash
git add web/src/components/dashboard/asset-detail.tsx
git commit -m "feat(web): integrate price chart, valuation, and signal timeline into AssetDetail"
```

---

## Task 16: Final Integration Test

**Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: All tests PASS

**Step 3: Run frontend type check**

Run: `cd web && npx tsc --noEmit`
Expected: No type errors

**Step 4: Run frontend build**

Run: `cd web && npm run build`
Expected: Build succeeds

**Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: resolve integration issues from candidate data pipeline"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Engine Model | Add `shares_outstanding` to `AssetProfile` |
| 2 | Engine Module | Create `price_targets.py` with multi-factor valuation |
| 3 | Engine Model | Add price fields to `CompositeScore` |
| 4 | Engine Pipeline | Wire price targets into composite scorer |
| 5 | Engine Logic | Add price-aware signal logic |
| 6 | DB Schema | Add `signal_transitions` table + score price columns |
| 7 | API Schemas | Add price fields to response schemas |
| 8 | API Routes | Serve price data with optional `?include=` |
| 9 | Frontend Types | Update TypeScript interfaces |
| 10 | Frontend UI | Create ActionPill component |
| 11 | Frontend UI | Create Sparkline component |
| 12 | Frontend UI | Update StockCard with new components |
| 13 | Frontend UI | Create PriceChart with Recharts |
| 14 | Frontend UI | Create ValuationBreakdown + SignalTimeline |
| 15 | Frontend UI | Integrate all into AssetDetail |
| 16 | Integration | Full test suite verification |
