# Scoring Factors Tier 3: Significant Engine Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Three institutional-grade engine improvements: company-specific WACC (CAPM-based), cyclical normalization for valuation multiples (7-year median), and PEAD time decay for SUE.

**Architecture:** New scoring modules with backward-compatible optional parameters. Existing factor functions gain optional `history`/`config` params. Sector WACC remains as fallback.

**Tech Stack:** Python 3.13, Pydantic, pytest, statistics, Decimal

---

## 3.1 Company-Specific WACC

### Task 1: Add beta field to AssetProfile and compute_beta() helper

**Context:** Currently no beta data exists in the model. We need beta for CAPM cost of equity. Compute from price history (60-month returns vs market).

**Files:**
- Modify: `engine/src/margin_engine/models/financial.py:210-225`
- Create: `engine/src/margin_engine/scoring/quantitative/beta.py`
- Create: `engine/tests/scoring/quantitative/test_beta.py`

**Step 1: Write failing test**

```python
# engine/tests/scoring/quantitative/test_beta.py
import datetime
from decimal import Decimal
import pytest
from margin_engine.models.financial import PriceBar
from margin_engine.scoring.quantitative.beta import compute_beta

def _make_bar(date_str: str, close: float) -> PriceBar:
    price = Decimal(str(close))
    return PriceBar(date=date_str, open=price, high=price, low=price, close=price, volume=1000000)

class TestComputeBeta:
    def test_perfect_correlation_beta_one(self):
        """Stock moving exactly with market → beta ≈ 1.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            price = 100.0 + i * 0.1  # both grow linearly
            stock_bars.append(_make_bar(d, price))
            market_bars.append(_make_bar(d, price))
        result = compute_beta(stock_bars, market_bars)
        assert result == pytest.approx(1.0, abs=0.05)

    def test_double_volatility_beta_two(self):
        """Stock with 2x market moves → beta ≈ 2.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            market_price = 100.0 + i * 0.1
            stock_price = 100.0 + i * 0.2  # 2x moves
            stock_bars.append(_make_bar(d, stock_price))
            market_bars.append(_make_bar(d, market_price))
        result = compute_beta(stock_bars, market_bars)
        assert result == pytest.approx(2.0, abs=0.1)

    def test_insufficient_data_returns_one(self):
        """Fewer than 60 bars → fallback beta = 1.0."""
        bars = [_make_bar(f"2024-01-{i+1:02d}", 100.0) for i in range(30)]
        result = compute_beta(bars, bars)
        assert result == 1.0

    def test_beta_clamped_to_range(self):
        """Beta clamped to [0.3, 3.0]."""
        # Extreme negative correlation would give very negative beta
        # but clamped to 0.3 minimum
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            market_bars.append(_make_bar(d, 100.0 + i * 0.1))
            stock_bars.append(_make_bar(d, 200.0 - i * 0.5))  # inverse
        result = compute_beta(stock_bars, market_bars)
        assert result >= 0.3
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/quantitative/test_beta.py -v -k "perfect_correlation" 2>&1 | tail -10`
Expected: FAIL (module not found)

**Step 3: Implement compute_beta()**

```python
# engine/src/margin_engine/scoring/quantitative/beta.py
"""Beta computation from price history (CAPM)."""
from __future__ import annotations
import statistics
from margin_engine.models.financial import PriceBar

_MIN_BARS = 60
_MIN_BETA = 0.3
_MAX_BETA = 3.0

def compute_beta(
    stock_bars: list[PriceBar],
    market_bars: list[PriceBar],
) -> float:
    """Compute stock beta vs market from price bars.
    Returns 1.0 if insufficient data. Clamped to [0.3, 3.0].
    """
    if len(stock_bars) < _MIN_BARS or len(market_bars) < _MIN_BARS:
        return 1.0

    stock_sorted = sorted(stock_bars, key=lambda b: b.date)
    market_sorted = sorted(market_bars, key=lambda b: b.date)

    # Align by date
    market_by_date = {b.date: float(b.close) for b in market_sorted}
    aligned = [(float(b.close), market_by_date[b.date])
               for b in stock_sorted if b.date in market_by_date]

    if len(aligned) < _MIN_BARS:
        return 1.0

    # Compute daily returns
    stock_returns = []
    market_returns = []
    for i in range(1, len(aligned)):
        if aligned[i-1][0] > 0 and aligned[i-1][1] > 0:
            stock_returns.append(aligned[i][0] / aligned[i-1][0] - 1.0)
            market_returns.append(aligned[i][1] / aligned[i-1][1] - 1.0)

    if len(stock_returns) < 30:
        return 1.0

    # Beta = Cov(stock, market) / Var(market)
    mean_s = statistics.mean(stock_returns)
    mean_m = statistics.mean(market_returns)
    cov = sum((s - mean_s) * (m - mean_m) for s, m in zip(stock_returns, market_returns)) / len(stock_returns)
    var_m = sum((m - mean_m) ** 2 for m in market_returns) / len(market_returns)

    if var_m == 0:
        return 1.0

    beta = cov / var_m
    return max(_MIN_BETA, min(beta, _MAX_BETA))
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_beta.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/beta.py engine/tests/scoring/quantitative/test_beta.py
git commit -m "$(cat <<'EOF'
feat(engine): add beta computation from price history for CAPM

Computes stock beta vs market using aligned daily returns.
Minimum 60 bars, clamped to [0.3, 3.0], fallback to 1.0.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Create company-specific WACC computation

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/wacc_company.py`
- Create: `engine/tests/scoring/quantitative/test_wacc_company.py`

**Step 1: Write failing test**

```python
# engine/tests/scoring/quantitative/test_wacc_company.py
from decimal import Decimal
import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialPeriod, IncomeStatement, AssetProfile, GICSSector,
)
from margin_engine.scoring.quantitative.wacc_company import compute_company_wacc

def _make_period(*, interest_expense=Decimal("10"), total_equity=Decimal("500"),
                 long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
                 ebit=Decimal("100")) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=Decimal("1000"), ebit=ebit, interest_expense=interest_expense,
        net_income=Decimal("80"), shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1000"), total_equity=total_equity,
        long_term_debt=long_term_debt, short_term_debt=short_term_debt,
        cash_and_equivalents=Decimal("50"), shares_outstanding=100,
    )
    cf = CashFlowStatement(operating_cash_flow=Decimal("120"), capital_expenditures=Decimal("-20"))
    return FinancialPeriod(period_end="2024-09-28", filing_date="2024-11-01",
                           current_income=income, current_balance=balance, current_cash_flow=cf)

class TestCompanyWACC:
    def test_basic_wacc_computation(self):
        """WACC = (E/V * Ke) + (D/V * Kd * (1-t))."""
        period = _make_period()
        profile = AssetProfile(ticker="TEST", name="Test", sector=GICSSector.TECHNOLOGY,
                               market_cap=Decimal("5000"))
        wacc = compute_company_wacc(period=period, profile=profile, beta=1.2)
        # E = 5000 (market cap), D = 300 (total debt), V = 5300
        # Ke = 0.0425 + 1.2 * 0.055 = 0.1085
        # Kd = interest_expense / total_debt = 10/300 = 0.0333
        # Tax = 0.21 (default)
        # WACC = (5000/5300)*0.1085 + (300/5300)*0.0333*(1-0.21)
        # WACC = 0.9434*0.1085 + 0.0566*0.0263 = 0.1024 + 0.0015 = 0.1039
        assert wacc == pytest.approx(0.1039, abs=0.005)

    def test_high_leverage_higher_wacc(self):
        """More debt → higher WACC (more risk)."""
        profile = AssetProfile(ticker="TEST", name="Test", sector=GICSSector.TECHNOLOGY,
                               market_cap=Decimal("5000"))
        low_debt = _make_period(long_term_debt=Decimal("100"), short_term_debt=Decimal("50"))
        high_debt = _make_period(long_term_debt=Decimal("2000"), short_term_debt=Decimal("1000"))
        wacc_low = compute_company_wacc(period=low_debt, profile=profile, beta=1.0)
        wacc_high = compute_company_wacc(period=high_debt, profile=profile, beta=1.0)
        assert wacc_high > wacc_low

    def test_high_beta_higher_wacc(self):
        """Higher beta → higher cost of equity → higher WACC."""
        period = _make_period()
        profile = AssetProfile(ticker="TEST", name="Test", sector=GICSSector.TECHNOLOGY,
                               market_cap=Decimal("5000"))
        wacc_low = compute_company_wacc(period=period, profile=profile, beta=0.8)
        wacc_high = compute_company_wacc(period=period, profile=profile, beta=1.5)
        assert wacc_high > wacc_low

    def test_fallback_to_sector_wacc(self):
        """When beta=None and no interest data, fallback to sector WACC."""
        period = _make_period(interest_expense=None)
        profile = AssetProfile(ticker="TEST", name="Test", sector=GICSSector.TECHNOLOGY,
                               market_cap=Decimal("5000"))
        wacc = compute_company_wacc(period=period, profile=profile, beta=None,
                                     sector_fallback=0.10)
        assert wacc == 0.10

    def test_zero_debt_wacc_equals_cost_of_equity(self):
        """No debt → WACC = cost of equity."""
        period = _make_period(long_term_debt=Decimal("0"), short_term_debt=Decimal("0"),
                              interest_expense=Decimal("0"))
        profile = AssetProfile(ticker="TEST", name="Test", sector=GICSSector.TECHNOLOGY,
                               market_cap=Decimal("5000"))
        wacc = compute_company_wacc(period=period, profile=profile, beta=1.0)
        # Ke = 0.0425 + 1.0 * 0.055 = 0.0975
        assert wacc == pytest.approx(0.0975, abs=0.001)
```

**Step 2: Run to verify failure**

**Step 3: Implement**

```python
# engine/src/margin_engine/scoring/quantitative/wacc_company.py
"""Company-specific WACC computation (CAPM-based)."""
from __future__ import annotations
from decimal import Decimal
from margin_engine.models.financial import AssetProfile, FinancialPeriod

_RISK_FREE_RATE = 0.0425    # US 10Y Treasury (update quarterly)
_MARKET_RISK_PREMIUM = 0.055  # Historical US equity risk premium
_MIN_COST_OF_DEBT = 0.01
_MAX_COST_OF_DEBT = 0.15

def compute_company_wacc(
    period: FinancialPeriod,
    profile: AssetProfile,
    beta: float | None = None,
    sector_fallback: float | None = None,
    risk_free_rate: float = _RISK_FREE_RATE,
    market_risk_premium: float = _MARKET_RISK_PREMIUM,
) -> float:
    """Compute company-specific WACC using CAPM.

    WACC = (E/V × Ke) + (D/V × Kd × (1-t))
    Ke = risk_free_rate + beta × market_risk_premium

    Falls back to sector_fallback if beta is None and cost of debt unavailable.
    """
    if beta is None:
        if sector_fallback is not None:
            return sector_fallback
        return 0.09  # default fallback

    # Cost of equity (CAPM)
    cost_of_equity = risk_free_rate + beta * market_risk_premium

    # Cost of debt
    cb = period.current_balance
    total_debt = float(cb.total_debt)
    interest = float(period.current_income.interest_expense or Decimal("0"))

    if total_debt > 0 and interest > 0:
        cost_of_debt = max(_MIN_COST_OF_DEBT, min(interest / total_debt, _MAX_COST_OF_DEBT))
    elif sector_fallback is not None:
        cost_of_debt = sector_fallback * 0.6  # rough pre-tax debt cost estimate
    else:
        cost_of_debt = risk_free_rate + 0.02  # risk-free + 200bps spread

    # Tax rate
    tax_rate = period.current_income.effective_tax_rate

    # Capital structure weights
    market_cap = float(profile.market_cap)
    if market_cap <= 0:
        if sector_fallback is not None:
            return sector_fallback
        return 0.09

    total_value = market_cap + total_debt
    equity_weight = market_cap / total_value
    debt_weight = total_debt / total_value

    wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
    return max(wacc, 0.02)  # floor at 2%
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_wacc_company.py -v`

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/wacc_company.py engine/tests/scoring/quantitative/test_wacc_company.py
git commit -m "$(cat <<'EOF'
feat(engine): add company-specific WACC computation (CAPM-based)

WACC = (E/V × Ke) + (D/V × Kd × (1-t)) where Ke = Rf + β × MRP.
Falls back to sector WACC when beta unavailable.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Integrate company WACC into v4_pipeline

**Files:**
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py:239`
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py:159`
- Test: `engine/tests/scoring/test_v4_pipeline.py` (update WACC-dependent assertions)

**Step 1: Write failing test**

Add to the v4 pipeline test file a test that verifies company WACC is used when beta is provided in the ticker data. The exact test will depend on what the TickerV3Data/TickerV4Data model accepts — check if a `beta` field needs to be added.

**Step 2: Add `beta` field to TickerV3Data/TickerV4Data**

Check the model and add `beta: float | None = None`. If the model doesn't have it, add it as an optional field.

**Step 3: Update pipeline to use compute_company_wacc()**

In `v4_pipeline.py:239`, replace:
```python
wacc = get_sector_wacc(td.profile.sector)
```
With:
```python
from margin_engine.scoring.quantitative.wacc_company import compute_company_wacc
wacc = compute_company_wacc(
    period=td.latest_period,
    profile=td.profile,
    beta=td.beta,
    sector_fallback=get_sector_wacc(td.profile.sector),
)
```

Similarly in `v3_pipeline.py:159`.

**Step 4: Run pipeline tests**

Run: `uv run pytest engine/tests/scoring/ -v -k "pipeline" 2>&1 | tail -30`

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v4_pipeline.py engine/src/margin_engine/scoring/v3_pipeline.py engine/tests/scoring/
git commit -m "$(cat <<'EOF'
feat(engine): integrate company-specific WACC into scoring pipeline

Uses CAPM-based WACC when beta available, sector WACC as fallback.
Affects ROIC-WACC spread, reverse DCF, and owner earnings IV.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 3.2 Cyclical Normalization for Valuation Multiples

### Task 4: Create cyclical normalization helper

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/cyclical_normalizer.py`
- Create: `engine/tests/scoring/quantitative/test_cyclical_normalizer.py`

**Step 1: Write failing test**

```python
# engine/tests/scoring/quantitative/test_cyclical_normalizer.py
import pytest
from margin_engine.scoring.quantitative.cyclical_normalizer import normalize_metric

class TestCyclicalNormalizer:
    def test_non_cyclical_returns_current(self):
        """Non-cyclical companies use current value unchanged."""
        result, detail = normalize_metric(
            current_value=100.0,
            historical_values=[80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0],
            is_cyclical=False,
        )
        assert result == 100.0
        assert "current" in detail.lower()

    def test_cyclical_uses_7yr_median(self):
        """Cyclical company uses 7-year median."""
        values = [50.0, 120.0, 30.0, 150.0, 40.0, 130.0, 60.0]  # median = 60
        result, detail = normalize_metric(
            current_value=150.0,  # peak
            historical_values=values,
            is_cyclical=True,
        )
        assert result == pytest.approx(60.0, abs=1.0)  # median of sorted values
        assert "median" in detail.lower()

    def test_cyclical_insufficient_history_uses_current(self):
        """Cyclical with <3 years of history falls back to current."""
        result, detail = normalize_metric(
            current_value=100.0,
            historical_values=[90.0, 110.0],
            is_cyclical=True,
        )
        assert result == 100.0

    def test_cyclical_at_trough(self):
        """At trough, normalized value should be higher than current (more conservative)."""
        values = [100.0, 120.0, 130.0, 110.0, 90.0, 140.0, 30.0]  # trough at 30
        result, _ = normalize_metric(
            current_value=30.0,
            historical_values=values,
            is_cyclical=True,
        )
        assert result > 30.0  # median is higher than trough
```

**Step 2: Implement**

```python
# engine/src/margin_engine/scoring/quantitative/cyclical_normalizer.py
"""Cyclical normalization using 7-year median for valuation factors."""
from __future__ import annotations
import statistics

_MIN_HISTORY = 3  # Need at least 3 periods for meaningful median
_DEFAULT_LOOKBACK = 7  # 7-year median for full business cycle coverage

def normalize_metric(
    current_value: float,
    historical_values: list[float],
    is_cyclical: bool,
    lookback: int = _DEFAULT_LOOKBACK,
) -> tuple[float, str]:
    """Normalize a metric for cyclical companies using lookback-year median.

    For cyclical companies (Energy, Materials, Industrials, Consumer Discretionary),
    replaces current-period values with the median over the lookback window.

    Args:
        current_value: The current-period metric value
        historical_values: Multi-year metric values (oldest first)
        is_cyclical: Whether the company is in a cyclical sector
        lookback: Number of years for median window (default 7)

    Returns:
        (normalized_value, detail_string)
    """
    if not is_cyclical or len(historical_values) < _MIN_HISTORY:
        return current_value, f"using_current={current_value:.4f}"

    window = historical_values[-lookback:] if len(historical_values) >= lookback else historical_values
    # Filter out zero/negative values for valuation metrics
    valid = [v for v in window if v > 0]
    if len(valid) < _MIN_HISTORY:
        return current_value, f"insufficient_valid_history={len(valid)}"

    median_val = statistics.median(valid)
    return median_val, (
        f"7yr_median={median_val:.4f}, current={current_value:.4f}, "
        f"periods_used={len(valid)}"
    )
```

**Step 3: Run and commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/cyclical_normalizer.py engine/tests/scoring/quantitative/test_cyclical_normalizer.py
git commit -m "$(cat <<'EOF'
feat(engine): add cyclical normalization helper (7-year median)

Smooths valuation metrics for cyclical sectors (Energy, Materials,
Industrials, Consumer Discretionary) using 7-year median to avoid
peak/trough mispricing.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Apply cyclical normalization to EV/FCF

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/ev_fcf.py`
- Modify: `engine/tests/scoring/quantitative/test_ev_fcf.py`

**Step 1: Write failing test**

```python
def test_cyclical_company_uses_median_fcf(self):
    """Cyclical company should use 7-year median FCF, not current."""
    from margin_engine.models.financial import FinancialHistory, GICSSector, AssetProfile
    # Current FCF = 500 (peak), historical FCFs = [100, 200, 300, 500, 150, 250, 500]
    # Median = 250
    # EV / 250 should differ from EV / 500
    period = _make_period(operating_cash_flow=Decimal("500"), capital_expenditures=Decimal("0"))
    profile = AssetProfile(ticker="CYC", name="Cyclical Co", sector=GICSSector.ENERGY,
                           market_cap=Decimal("5000"))
    history = _make_history_with_fcfs([100, 200, 300, 500, 150, 250, 500])
    result = ev_fcf(period, Decimal("5000"), history=history, profile=profile)
    # Median FCF = 250, EV ≈ 5000 + debt - cash, ratio should use 250 not 500
    result_no_norm = ev_fcf(period, Decimal("5000"))
    assert result.raw_value > result_no_norm.raw_value  # Higher ratio (more expensive) at median
```

**Step 2: Update ev_fcf() signature**

Add optional `history` and `profile` parameters. When both provided and sector is cyclical, use `normalize_metric()` on FCF.

```python
def ev_fcf(
    period: FinancialPeriod,
    market_cap: Decimal,
    history: FinancialHistory | None = None,
    profile: AssetProfile | None = None,
) -> FactorScore:
```

If `history` and `profile` are provided and `profile.sector.is_cyclical`, extract FCF from each historical period and use `normalize_metric()` to get the 7-year median FCF. Otherwise use current FCF (backward compatible).

**Step 3: Run and commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/ev_fcf.py engine/tests/scoring/quantitative/test_ev_fcf.py
git commit -m "$(cat <<'EOF'
feat(engine): add cyclical normalization to EV/FCF

Cyclical sectors use 7-year median FCF instead of current-period FCF,
preventing peak/trough mispricing. Non-cyclical sectors unchanged.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Apply cyclical normalization to Acquirer's Multiple

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/acquirers_multiple.py`
- Modify: `engine/tests/scoring/quantitative/test_acquirers_multiple.py`

Same pattern as Task 5 but normalizing EBIT instead of FCF.

**Step 1: Write failing test** — cyclical company with peak EBIT should use median

**Step 2: Update `acquirers_multiple()` signature** — add optional `history` and `profile`

**Step 3: Apply `normalize_metric()` to EBIT** when cyclical

**Step 4: Run and commit**

```bash
git commit -m "$(cat <<'EOF'
feat(engine): add cyclical normalization to Acquirer's Multiple

Cyclical sectors use 7-year median EBIT for EV/EBIT calculation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Apply cyclical normalization to Owner Earnings Yield

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/owner_earnings.py`
- Modify: `engine/tests/scoring/quantitative/test_owner_earnings.py`

Same pattern. Normalize the Owner Earnings (CFO - maintenance capex) for cyclical sectors.

**Step 1: Write failing test**

**Step 2: Update `owner_earnings_yield()` signature** — add optional `history`

**Step 3: Apply normalization to computed owner earnings**

**Step 4: Run and commit**

```bash
git commit -m "$(cat <<'EOF'
feat(engine): add cyclical normalization to Owner Earnings Yield

Cyclical sectors use 7-year median owner earnings for yield calculation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 3.3 PEAD Time Decay for SUE

### Task 8: Add PEAD time decay to SUE scoring

**Context:** Post-Earnings Announcement Drift (Ball & Brown 1968, Bernard & Thomas 1990) shows earnings surprise drift fades over 2-3 quarters. Currently all surprises weighted equally regardless of age.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/sue.py`
- Modify: `engine/tests/scoring/quantitative/test_sue.py`

**Step 1: Write failing test**

```python
def test_recent_surprise_weighted_more_than_old(self):
    """A recent Q4 surprise should produce higher SUE than a stale Q1 surprise
    with the same magnitude, because PEAD decays over time."""
    from datetime import datetime
    # All 4 quarters have same surprise magnitude, but most recent (Q4) gets highest weight
    surprises = [
        _make_surprise("2024-Q1", "1.50", "1.40"),  # +0.10, old
        _make_surprise("2024-Q2", "1.60", "1.50"),  # +0.10, old
        _make_surprise("2024-Q3", "1.55", "1.45"),  # +0.10, recent
        _make_surprise("2024-Q4", "1.70", "1.60"),  # +0.10, most recent
    ]
    # With PEAD decay, the most recent surprise dominates
    result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
    assert result.raw_value > 0  # positive

    # Compare: if most recent was negative, should pull down despite old positives
    surprises_neg = [
        _make_surprise("2024-Q1", "1.50", "1.40"),  # +0.10
        _make_surprise("2024-Q2", "1.60", "1.50"),  # +0.10
        _make_surprise("2024-Q3", "1.55", "1.45"),  # +0.10
        _make_surprise("2024-Q4", "1.50", "1.70"),  # -0.20, negative
    ]
    result_neg = sue_score(surprises_neg, reference_date=datetime(2025, 2, 1))
    assert result_neg.raw_value < result.raw_value  # recent negative pulls it down
```

**Step 2: Run to verify failure** (current sue_score doesn't accept reference_date)

**Step 3: Implement PEAD time decay in sue_score()**

Update `sue_score()` to accept optional `reference_date: datetime | None = None`. When provided, apply exponential decay to each surprise based on its quarter's distance from reference_date.

```python
import math
from datetime import datetime

_MIN_QUARTERS = 4
_PEAD_HALF_LIFE_MONTHS = 6.0  # Drift fades by half every 6 months

def _quarter_end_date(quarter_str: str) -> datetime:
    """Parse 'YYYY-QN' to approximate quarter end date."""
    year_str, q_str = quarter_str.split("-Q")
    year, q = int(year_str), int(q_str)
    month_map = {1: 3, 2: 6, 3: 9, 4: 12}
    return datetime(year, month_map[q], 28)

def _pead_decay(quarter_str: str, reference_date: datetime) -> float:
    """Exponential decay factor: 1.0 for current, 0.5 at half-life."""
    qend = _quarter_end_date(quarter_str)
    elapsed_months = max((reference_date - qend).days / 30.44, 0.0)
    decay = 0.5 ** (elapsed_months / _PEAD_HALF_LIFE_MONTHS)
    return max(decay, 0.05)  # floor at 5%

def sue_score(
    surprises: list[EarningsSurprise],
    reference_date: datetime | None = None,
) -> FactorScore:
    if len(surprises) < _MIN_QUARTERS:
        return FactorScore(name="sue", raw_value=0.0, percentile_rank=0.0,
                           detail=f"insufficient data: {len(surprises)} quarter(s), need at least {_MIN_QUARTERS}")

    sorted_surprises = sorted(surprises, key=lambda s: s.quarter)
    surprise_values = [float(s.surprise) for s in sorted_surprises]

    if reference_date is not None:
        # Apply PEAD time decay
        weights = [_pead_decay(s.quarter, reference_date) for s in sorted_surprises]
        weighted_values = [v * w for v, w in zip(surprise_values, weights)]

        # Weighted standard deviation
        total_w = sum(weights)
        weighted_mean = sum(weighted_values) / total_w
        variance = sum(w * (v - weighted_mean) ** 2 for w, v in zip(weights, weighted_values)) / total_w
        stddev = variance ** 0.5

        if stddev == 0.0:
            return FactorScore(name="sue", raw_value=0.0, percentile_rank=0.0,
                               detail="stddev=0 after PEAD weighting")

        most_recent_weighted = weighted_values[-1]
        sue = most_recent_weighted / stddev
    else:
        # Original behavior (no decay)
        stddev = pstdev(surprise_values)
        if stddev == 0.0:
            return FactorScore(name="sue", raw_value=0.0, percentile_rank=0.0,
                               detail=f"stddev=0 (all surprises identical)")
        sue = surprise_values[-1] / stddev

    return FactorScore(
        name="sue",
        raw_value=sue,
        percentile_rank=0.0,
        detail=f"SUE={sue:.4f}; pead={'on' if reference_date else 'off'}",
    )
```

**Step 4: Existing tests must still pass** (reference_date=None preserves old behavior)

**Step 5: Run and commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/sue.py engine/tests/scoring/quantitative/test_sue.py
git commit -m "$(cat <<'EOF'
feat(engine): add PEAD time decay to SUE scoring

Applies exponential decay (half-life 6 months) to earnings surprises,
per Ball & Brown (1968) and Bernard & Thomas (1990). More recent
surprises weighted more heavily. Backward compatible when no
reference_date provided.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Run full engine test suite verification

**Step 1:** Run all engine tests

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All PASS

**Step 2:** Run scoring tests specifically

Run: `uv run pytest engine/tests/scoring/ -v 2>&1 | tail -30`

**Step 3:** Fix any regressions

**Step 4:** Final commit if fixes needed

---

## Summary of Changes

| Task | File | What Changes | Impact |
|------|------|-------------|--------|
| 1 | beta.py (NEW) | Beta from price history | Enables CAPM |
| 2 | wacc_company.py (NEW) | Company WACC (CAPM) | Replaces static sector WACC |
| 3 | v4_pipeline.py | Use company WACC | All WACC-dependent factors |
| 4 | cyclical_normalizer.py (NEW) | 7-year median helper | Shared by valuation factors |
| 5 | ev_fcf.py | Cyclical normalization | Cyclical sector EV/FCF |
| 6 | acquirers_multiple.py | Cyclical normalization | Cyclical sector EV/EBIT |
| 7 | owner_earnings.py | Cyclical normalization | Cyclical sector OE Yield |
| 8 | sue.py | PEAD time decay | Recent surprises weighted more |
| 9 | — | Full test verification | Catch regressions |

## Notes for Implementer

- All new parameters are optional with backward-compatible defaults.
- `compute_beta()` requires market price bars — check if these are available in the ingestion pipeline. If not, use `beta=None` (sector WACC fallback) until market data is wired.
- The `is_cyclical` property already exists on `GICSSector`: Energy, Materials, Industrials, Consumer Discretionary.
- `FinancialHistory.periods` is sorted ascending by `period_end`.
- Each task can be approved independently. If any task is rejected, the others still stand.
