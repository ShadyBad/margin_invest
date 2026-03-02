# Scoring Factors Tier 2: Engine Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 engine-level methodology issues identified in the institutional accuracy audit: average Invested Capital for ROIC, volatility-normalized momentum, SUE minimum quarters, moat durability label fix, and position-size weighted institutional accumulation.

**Architecture:** Pure engine changes with TDD. Each task is isolated and independently testable. No API or frontend changes.

**Tech Stack:** Python 3.13, Pydantic, pytest, Decimal precision for financial values

---

### Task 1: Implement Average Invested Capital in `compute_roic()`

The institutional standard (Bloomberg, FactSet, S&P) uses average of beginning and ending IC to avoid bias from companies growing or shrinking capital during the period. Currently all ROIC calculations use end-of-period IC only.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/roic_wacc.py:23-43`
- Test: `engine/tests/scoring/quantitative/test_roic_wacc.py`

**Step 1: Write failing test for average IC**

Add to `engine/tests/scoring/quantitative/test_roic_wacc.py`:

```python
def test_compute_roic_uses_average_ic(self):
    """Average of beginning and ending IC should be used when prior balance available."""
    # Current period: equity=100, debt=50, cash=10 → IC=140
    # Prior period: equity=80, debt=40, cash=10 → IC=110
    # Average IC = (140 + 110) / 2 = 125
    # EBIT=30, tax=21% → NOPAT=23.7
    # ROIC = 23.7 / 125 = 0.1896
    period = _make_period(
        ebit=Decimal("30"),
        total_equity=Decimal("100"),
        total_debt=Decimal("50"),
        cash=Decimal("10"),
    )
    # Add prior balance sheet
    period.prior_balance = BalanceSheet(
        total_assets=Decimal("200"),
        current_assets=Decimal("50"),
        cash_and_equivalents=Decimal("10"),
        total_liabilities=Decimal("120"),
        current_liabilities=Decimal("30"),
        total_equity=Decimal("80"),
        long_term_debt=Decimal("30"),
        short_term_debt=Decimal("10"),
        retained_earnings=Decimal("60"),
    )
    roic = compute_roic(period)
    # NOPAT = 30 * (1 - 0.21) = 23.7
    # Avg IC = (140 + 110) / 2 = 125
    # ROIC = 23.7 / 125 = 0.1896
    assert roic == pytest.approx(0.1896, abs=0.001)


def test_compute_roic_falls_back_to_current_ic_when_no_prior(self):
    """Without prior balance, use current IC only (backward compat)."""
    period = _make_period(
        ebit=Decimal("30"),
        total_equity=Decimal("100"),
        total_debt=Decimal("50"),
        cash=Decimal("10"),
    )
    # No prior_balance set
    roic = compute_roic(period)
    # NOPAT = 23.7, IC = 140
    # ROIC = 23.7 / 140 = 0.16929
    assert roic == pytest.approx(0.16929, abs=0.001)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_roic_wacc.py -v -k "average_ic or falls_back" 2>&1 | tail -10`
Expected: FAIL (compute_roic doesn't use prior_balance yet)

**Step 3: Implement average IC in compute_roic()**

In `engine/src/margin_engine/scoring/quantitative/roic_wacc.py`, update `compute_roic()`:

```python
def compute_roic(period: FinancialPeriod) -> float:
    """Compute Return on Invested Capital using average IC when prior period available."""
    inc = period.current_income
    bal = period.current_balance

    ebit = float(inc.ebit or 0)
    if ebit <= 0:
        return 0.0

    tax_rate = float(inc.effective_tax_rate)
    nopat = ebit * (1.0 - tax_rate)

    total_equity = float(bal.total_equity or 0)
    total_debt = float(bal.total_debt)
    cash = float(bal.cash_and_equivalents or 0)
    current_ic = total_equity + total_debt - cash

    # Use average IC when prior balance sheet available (institutional standard)
    if period.prior_balance is not None:
        prior_bal = period.prior_balance
        prior_equity = float(prior_bal.total_equity or 0)
        prior_debt = float(prior_bal.total_debt)
        prior_cash = float(prior_bal.cash_and_equivalents or 0)
        prior_ic = prior_equity + prior_debt - prior_cash
        if prior_ic > 0 and current_ic > 0:
            invested_capital = (current_ic + prior_ic) / 2.0
        elif current_ic > 0:
            invested_capital = current_ic
        else:
            return 0.0
    else:
        invested_capital = current_ic

    if invested_capital <= 0:
        return 0.0

    return nopat / invested_capital
```

**Step 4: Update roic_wacc_spread() to use compute_roic()**

In the same file, update `roic_wacc_spread()` to call `compute_roic(period)` instead of duplicating the IC calculation inline. Remove the duplicate IC computation.

**Step 5: Update golden value test if needed**

The Apple FY2024 golden test may need updating if Apple's FinancialPeriod fixture includes prior_balance. Check the fixture — if it doesn't have prior_balance, the test should still pass unchanged (falls back to current IC).

**Step 6: Run all ROIC tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_roic_wacc.py -v 2>&1 | tail -20`
Expected: All PASS

**Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/roic_wacc.py engine/tests/scoring/quantitative/test_roic_wacc.py
git commit -m "fix(engine): use average Invested Capital in ROIC computation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Propagate Average IC to roic_stability and incremental_roic

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/roic_stability.py:24-41`
- Modify: `engine/src/margin_engine/scoring/quantitative/incremental_roic.py:21-35`
- Test: `engine/tests/scoring/quantitative/test_roic_stability.py`
- Test: `engine/tests/scoring/quantitative/test_incremental_roic.py`

**Step 1: Update `_period_roic()` in roic_stability.py**

The `_period_roic()` helper computes ROIC for each period in history. Update it to use the prior period's balance sheet for average IC:

```python
def _period_roic(period: FinancialPeriod, prior_period: FinancialPeriod | None = None) -> float | None:
    """Compute ROIC for a single period, using average IC when prior available."""
    inc = period.current_income
    bal = period.current_balance
    ebit = float(inc.ebit or 0)
    if ebit <= 0:
        return None
    tax_rate = float(inc.effective_tax_rate)
    nopat = ebit * (1.0 - tax_rate)
    total_equity = float(bal.total_equity or 0)
    total_debt = float(bal.total_debt)
    cash = float(bal.cash_and_equivalents or 0)
    current_ic = total_equity + total_debt - cash

    if prior_period is not None:
        prior_bal = prior_period.current_balance
        prior_equity = float(prior_bal.total_equity or 0)
        prior_debt = float(prior_bal.total_debt)
        prior_cash = float(prior_bal.cash_and_equivalents or 0)
        prior_ic = prior_equity + prior_debt - prior_cash
        if prior_ic > 0 and current_ic > 0:
            invested_capital = (current_ic + prior_ic) / 2.0
        elif current_ic > 0:
            invested_capital = current_ic
        else:
            return None
    else:
        invested_capital = current_ic

    if invested_capital <= 0:
        return None
    return nopat / invested_capital
```

Update the caller in `roic_stability()` to pass prior periods:

```python
periods = history.periods
roics: list[float] = []
for i, period in enumerate(periods):
    prior = periods[i - 1] if i > 0 else None
    val = _period_roic(period, prior)
    if val is not None:
        roics.append(val)
```

**Step 2: Update incremental_roic.py similarly**

The `_nopat_and_ic()` helper returns (NOPAT, IC) per period. For incremental ROIC, the formula is delta_NOPAT / delta_IC, which is already correct conceptually — it measures marginal return on marginal capital. No average IC needed here since it's measuring the change, not the level. Skip this file.

**Step 3: Write tests and verify**

Add a test for the prior-period-aware ROIC stability calculation. Update golden values if needed.

Run: `uv run pytest engine/tests/scoring/quantitative/test_roic_stability.py engine/tests/scoring/quantitative/test_incremental_roic.py -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/roic_stability.py engine/tests/scoring/quantitative/test_roic_stability.py
git commit -m "fix(engine): use average IC in ROIC stability per-period calculation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Add Volatility Normalization to Price Momentum

MSCI Momentum Index divides raw 12-1 month return by trailing 36-month volatility. This prevents high-beta stocks from dominating the momentum signal.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_momentum.py`
- Test: `engine/tests/scoring/quantitative/test_price_momentum.py`

**Step 1: Write failing test**

Add to `engine/tests/scoring/quantitative/test_price_momentum.py`:

```python
def test_risk_adjusted_momentum_dampens_volatile_stock(self):
    """High-volatility stock should have lower risk-adjusted momentum than
    a low-volatility stock with the same raw return."""
    base_date = datetime(2024, 12, 15)
    # Low-vol stock: steady climb from 100 to 120 (20% raw momentum)
    low_vol_bars = []
    for i in range(400):
        d = base_date - timedelta(days=400 - i)
        price = Decimal("100") + Decimal(str(i * 20 / 400))
        low_vol_bars.append(PriceBar(
            date=d.strftime("%Y-%m-%d"),
            open=price, high=price, low=price, close=price,
            volume=Decimal("1000000"),
        ))

    # High-vol stock: same start/end but with ±10% swings
    import math
    high_vol_bars = []
    for i in range(400):
        d = base_date - timedelta(days=400 - i)
        trend = 100 + i * 20 / 400
        noise = 10 * math.sin(i * 0.3)  # oscillation
        price = Decimal(str(max(trend + noise, 1)))
        high_vol_bars.append(PriceBar(
            date=d.strftime("%Y-%m-%d"),
            open=price, high=price, low=price, close=price,
            volume=Decimal("1000000"),
        ))

    low_vol_result = price_momentum(low_vol_bars)
    high_vol_result = price_momentum(high_vol_bars)

    # Both should have similar raw momentum (~20%), but risk-adjusted
    # the low-vol stock should score higher
    assert low_vol_result.raw_value > high_vol_result.raw_value
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_momentum.py -v -k "risk_adjusted" 2>&1 | tail -10`
Expected: FAIL (raw returns will be similar)

**Step 3: Implement volatility normalization**

In `engine/src/margin_engine/scoring/quantitative/price_momentum.py`:

```python
import statistics

_VOL_LOOKBACK_DAYS = 252  # ~1 year of trading days for volatility


def price_momentum(price_bars: list[PriceBar]) -> FactorScore:
    """12-1 month risk-adjusted price momentum (Jegadeesh & Titman 1993, MSCI-style)."""
    # ... existing validation and date lookups ...

    # Raw 12-1 momentum
    momentum = (price_t1 / price_t12) - 1.0

    # Volatility normalization (MSCI-style)
    # Compute daily log returns over the 12-month lookback
    closes = [float(bar.close) for bar in sorted_bars if float(bar.close) > 0]
    if len(closes) >= 60:  # minimum for meaningful vol estimate
        daily_returns = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes))]
        vol = statistics.pstdev(daily_returns)
        annualized_vol = vol * (252 ** 0.5) if vol > 0 else 1.0
        risk_adjusted = momentum / annualized_vol if annualized_vol > 0.01 else momentum
    else:
        risk_adjusted = momentum  # fallback to raw if insufficient data

    return FactorScore(
        raw_value=risk_adjusted,
        detail=f"12-1m raw={momentum:.4f}, vol={annualized_vol:.4f}, risk_adj={risk_adjusted:.4f}",
    )
```

**Step 4: Update existing golden value tests**

Existing tests expect raw momentum values. Update them to expect risk-adjusted values. The steady-climb tests will have low vol so risk-adjusted will be higher than raw. The key is that the tests still validate the directional behavior.

**Step 5: Run all momentum tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_momentum.py -v 2>&1 | tail -20`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_momentum.py engine/tests/scoring/quantitative/test_price_momentum.py
git commit -m "feat(engine): add MSCI-style volatility normalization to price momentum

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Increase SUE Minimum to 4 Quarters

Academic SUE studies use 4-8 quarters minimum for stable standard deviation estimates. Current minimum is 2 (too lenient — pstdev of 2 values is unreliable).

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/sue.py:37-43`
- Test: `engine/tests/scoring/quantitative/test_sue.py`

**Step 1: Write failing test**

Add to `engine/tests/scoring/quantitative/test_sue.py`:

```python
def test_three_quarters_returns_zero(self):
    """3 quarters is below the new minimum of 4."""
    surprises = [
        EarningsSurprise(quarter="2024-Q1", actual_eps=Decimal("1.50"), expected_eps=Decimal("1.40")),
        EarningsSurprise(quarter="2024-Q2", actual_eps=Decimal("1.60"), expected_eps=Decimal("1.50")),
        EarningsSurprise(quarter="2024-Q3", actual_eps=Decimal("1.70"), expected_eps=Decimal("1.55")),
    ]
    result = sue_score(surprises)
    assert result.raw_value == 0.0
    assert "insufficient" in result.detail.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_sue.py -v -k "three_quarters" 2>&1 | tail -10`
Expected: FAIL (current minimum is 2, so 3 quarters passes)

**Step 3: Update minimum in sue.py**

Change the minimum check from `< 2` to `< 4`:

```python
_MIN_QUARTERS = 4

def sue_score(surprises: list[EarningsSurprise]) -> FactorScore:
    if len(surprises) < _MIN_QUARTERS:
        return FactorScore(
            raw_value=0.0,
            detail=f"Insufficient data: {len(surprises)} quarters (minimum {_MIN_QUARTERS})",
        )
```

**Step 4: Update existing "exactly 2 quarters" test**

The existing test that validates 2 quarters should now expect 0.0 (insufficient). Update it.

**Step 5: Run all SUE tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_sue.py -v 2>&1 | tail -20`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/sue.py engine/tests/scoring/quantitative/test_sue.py
git commit -m "fix(engine): increase SUE minimum from 2 to 4 quarters for statistical reliability

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Fix Moat Durability Switching Cost Label

The `_detect_switching_costs()` function measures whether revenue grows faster than costs — this is operating leverage, not switching costs. Rename it honestly.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/moat_durability.py:65-108`
- Test: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Step 1: Write test with new name**

Add to `engine/tests/scoring/quantitative/test_moat_durability.py`:

```python
def test_operating_leverage_detected(self):
    """Revenue growth > cost growth indicates operating leverage (formerly switching_costs)."""
    # Same fixture as test_switching_costs_detected but verify new naming
    periods = _make_history([
        {"revenue": 100, "cogs": 60, "ebit": 20, "equity": 80, "debt": 20, "cash": 5},
        {"revenue": 110, "cogs": 64, "ebit": 24, "equity": 85, "debt": 20, "cash": 5},
        {"revenue": 121, "cogs": 68, "ebit": 28, "equity": 90, "debt": 20, "cash": 5},
    ])
    result = moat_durability_score(periods)
    assert "operating_leverage" in result.detail.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_moat_durability.py -v -k "operating_leverage" 2>&1 | tail -10`
Expected: FAIL (detail still says "switching_costs")

**Step 3: Rename in moat_durability.py**

1. Rename `_detect_switching_costs()` to `_detect_operating_leverage()`
2. Update the signature name in the weights dict from `"switching_costs"` to `"operating_leverage"`
3. Update the detail string in `moat_durability_score()` that lists detected signatures
4. Keep the same weight (1.5) — operating leverage IS a durable competitive signal, just mislabeled

**Step 4: Update existing tests**

Update any tests that reference "switching_costs" in assertions to use "operating_leverage".

**Step 5: Run all moat tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_moat_durability.py -v 2>&1 | tail -20`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/moat_durability.py engine/tests/scoring/quantitative/test_moat_durability.py
git commit -m "fix(engine): rename switching_costs to operating_leverage in moat durability

The revenue-vs-cost-growth proxy measures operating leverage, not
switching costs. Switching costs require customer retention data not
available from financial statements.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Add Position-Size Weighting to Institutional Accumulation

Currently all funds are weighted equally (+3 for new, +1 for addition, -1 for reduction) regardless of position size. A fund adding 1M shares should count more than one adding 1K shares.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py`
- Test: `engine/tests/scoring/quantitative/test_institutional_accumulation.py`

**Step 1: Write failing test**

Add to `engine/tests/scoring/quantitative/test_institutional_accumulation.py`:

```python
def test_large_position_weighted_higher_than_small(self):
    """A fund adding 1M shares should score higher than one adding 1K shares."""
    small_holdings = [
        InstitutionalHolding(
            fund_name="Small Fund",
            quarter="2024-Q3",
            shares_held=Decimal("1000"),
            shares_changed=Decimal("1000"),
            is_new_position=True,
        ),
    ]
    large_holdings = [
        InstitutionalHolding(
            fund_name="Large Fund",
            quarter="2024-Q3",
            shares_held=Decimal("1000000"),
            shares_changed=Decimal("1000000"),
            is_new_position=True,
        ),
    ]
    small_result = institutional_accumulation(small_holdings)
    large_result = institutional_accumulation(large_holdings)
    # Both are new positions, but large should score higher
    assert large_result.raw_value > small_result.raw_value
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_institutional_accumulation.py -v -k "large_position" 2>&1 | tail -10`
Expected: FAIL (both score +3 regardless of size)

**Step 3: Implement position-size weighting**

In `engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py`, update the scoring logic:

```python
def institutional_accumulation(holdings: list[InstitutionalHolding]) -> FactorScore:
    """Score institutional accumulation with position-size weighting."""
    if not holdings:
        return FactorScore(raw_value=0.0, detail="No institutional holdings data")

    most_recent_quarter = max(h.quarter for h in holdings)
    recent = [h for h in holdings if h.quarter == most_recent_quarter]

    if not recent:
        return FactorScore(raw_value=0.0, detail="No holdings in most recent quarter")

    # Compute size-weighted score
    total_score = 0.0
    fund_count = 0
    new_count = 0
    add_count = 0
    reduce_count = 0

    # Compute median position size for normalization
    position_sizes = [abs(float(h.shares_changed)) for h in recent if h.shares_changed != 0]
    median_size = statistics.median(position_sizes) if position_sizes else 1.0
    if median_size == 0:
        median_size = 1.0

    for h in recent:
        shares_changed = float(h.shares_changed)
        # Size weight: ratio of this position to median (capped at 5x to prevent outlier dominance)
        size_weight = min(abs(shares_changed) / median_size, 5.0) if shares_changed != 0 else 0.0

        if h.is_new_position and shares_changed > 0:
            total_score += 3.0 * size_weight
            new_count += 1
        elif shares_changed > 0:
            total_score += 1.0 * size_weight
            add_count += 1
        elif shares_changed < 0:
            total_score -= 1.0 * size_weight
            reduce_count += 1
        fund_count += 1

    detail = (
        f"Q={most_recent_quarter}, funds={fund_count}, "
        f"new={new_count}, add={add_count}, reduce={reduce_count}, "
        f"size_weighted_score={total_score:.2f}"
    )
    return FactorScore(raw_value=total_score, detail=detail)
```

**Step 4: Update existing tests**

Existing tests assume fixed integer scoring (+3, +1, -1). With size weighting relative to median, scores will change. Update golden values:
- When all holdings have the same size, size_weight = 1.0, so scores stay the same
- When sizes differ, larger positions amplify the signal

Update test assertions to match new behavior. For single-fund tests, size_weight = 1.0 (position equals median), so raw values stay the same. For multi-fund tests with equal sizes, all weights = 1.0, unchanged. The key change is tests with varying sizes.

**Step 5: Run all accumulation tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_institutional_accumulation.py -v 2>&1 | tail -20`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py engine/tests/scoring/quantitative/test_institutional_accumulation.py
git commit -m "feat(engine): add position-size weighting to institutional accumulation scoring

Larger positions now amplify the accumulation signal. Size weight is
capped at 5x median to prevent outlier dominance.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Run Full Engine Test Suite

**Step 1: Run all engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All PASS

**Step 2: Run scoring tests specifically**

Run: `uv run pytest engine/tests/scoring/ -v 2>&1 | tail -30`
Expected: All PASS

**Step 3: Fix any regressions found**

If any downstream tests fail (e.g., integration tests that depend on ROIC values), update their golden values to reflect the average IC change.

**Step 4: Final commit if fixes needed**

```bash
git commit -m "fix(engine): update golden values for average IC and risk-adjusted momentum

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary of Changes

| Task | File | What Changes | Impact |
|------|------|-------------|--------|
| 1 | roic_wacc.py | Average IC when prior balance available | All ROIC-WACC spreads |
| 2 | roic_stability.py | Average IC in per-period ROIC | ROIC stability scores |
| 3 | price_momentum.py | Divide raw return by annualized vol | Risk-adjusted momentum |
| 4 | sue.py | Minimum 2 → 4 quarters | Companies with <4 quarters get 0.0 |
| 5 | moat_durability.py | Rename switching_costs → operating_leverage | Label accuracy |
| 6 | institutional_accumulation.py | Size-weight by shares_changed | Larger positions count more |
| 7 | — | Full test suite verification | Catch regressions |

## Notes for Implementer

- All financial values use `Decimal` type. Convert to `float` only for ratio computations.
- The `FinancialPeriod` model has `prior_balance: BalanceSheet | None` — this is already in the model, just unused by ROIC functions.
- The `statistics` module is already imported in most scoring files. Use `statistics.pstdev()` for population std dev.
- Keep detail strings informative — they show up in the API response for debugging.
- Each task can be approved independently. If any task is rejected, the others still stand.
