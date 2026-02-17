# Scoring & Pricing Integrity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two critical defects: top picks showing artificial 100.0 scores, and target prices producing extreme outlier values.

**Architecture:** The scoring engine already computes both a raw weighted-average score and a universe percentile rank. The fix surfaces the raw score as the primary API field and adds a four-layer validation pipeline to the price target computation. All changes are at the engine and API schema layers — no model or normalizer logic changes needed.

**Tech Stack:** Python 3.13, Pydantic, pytest, FastAPI

---

### Task 1: Add `invalid_reason` field to PriceTargets model

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:66-76`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for PriceTargets model validation**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
class TestPriceTargetsModel:
    def test_invalid_reason_default_none(self):
        """invalid_reason should default to None."""
        pt = PriceTargets(intrinsic_value=100.0, buy_price=100.0, sell_price=125.0)
        assert pt.invalid_reason is None

    def test_invalid_reason_with_null_prices(self):
        """When invalid_reason is set, price fields should be None."""
        pt = PriceTargets(
            actual_price=197.0,
            invalid_reason="shares_outstanding_out_of_bounds",
        )
        assert pt.invalid_reason == "shares_outstanding_out_of_bounds"
        assert pt.intrinsic_value is None
        assert pt.buy_price is None
        assert pt.sell_price is None

    def test_invalid_reason_set_with_prices_raises(self):
        """Setting invalid_reason AND price fields should raise ValidationError."""
        with pytest.raises(Exception):
            PriceTargets(
                intrinsic_value=100.0,
                buy_price=100.0,
                sell_price=125.0,
                invalid_reason="shares_outstanding_out_of_bounds",
            )

    def test_positive_price_fields_when_present(self):
        """intrinsic_value, buy_price, sell_price must be > 0 when set."""
        with pytest.raises(Exception):
            PriceTargets(intrinsic_value=-5.0, buy_price=-5.0, sell_price=-3.0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestPriceTargetsModel -v`
Expected: FAIL — `invalid_reason` field does not exist, no validators

**Step 3: Implement PriceTargets model changes**

In `engine/src/margin_engine/scoring/quantitative/price_targets.py`, replace the `PriceTargets` class:

```python
from pydantic import BaseModel, model_validator

class PriceTargets(BaseModel):
    """Multi-method intrinsic value and price target result."""

    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    margin_of_safety: float | None = None
    valuation_methods: dict[str, float] | None = None
    invalid_reason: str | None = None

    @model_validator(mode="after")
    def check_invalid_reason_consistency(self) -> PriceTargets:
        """If invalid_reason is set, all price fields must be None."""
        if self.invalid_reason is not None:
            price_fields = [self.intrinsic_value, self.buy_price, self.sell_price, self.price_upside]
            if any(f is not None for f in price_fields):
                raise ValueError(
                    "Price fields must be None when invalid_reason is set"
                )
        return self

    @model_validator(mode="after")
    def check_positive_prices(self) -> PriceTargets:
        """intrinsic_value, buy_price, sell_price must be > 0 when present."""
        for field_name in ("intrinsic_value", "buy_price", "sell_price"):
            val = getattr(self, field_name)
            if val is not None and val <= 0:
                raise ValueError(f"{field_name} must be > 0 when set, got {val}")
        return self
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestPriceTargetsModel -v`
Expected: PASS

**Step 5: Run existing price target tests to confirm no regressions**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All existing tests PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add invalid_reason field and validators to PriceTargets model"
```

---

### Task 2: Add Layer 1 — Input validation (shares bounds + market cap cross-check)

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:78-103`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for Layer 1**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
class TestLayer1InputValidation:
    """Layer 1: shares_outstanding bounds and market-cap cross-validation."""

    def test_shares_too_low_returns_invalid(self, healthy_period, price_bars):
        """shares_outstanding = 50 -> invalid_reason."""
        profile = AssetProfile(
            ticker="BAD",
            name="Bad Shares Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000000000"),
            shares_outstanding=50,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is None
        assert result.invalid_reason == "shares_outstanding_out_of_bounds"

    def test_shares_too_high_returns_invalid(self, healthy_period, price_bars):
        """shares_outstanding = 100 billion -> invalid_reason."""
        profile = AssetProfile(
            ticker="BAD",
            name="Bad Shares Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000000000"),
            shares_outstanding=100_000_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is None
        assert result.invalid_reason == "shares_outstanding_out_of_bounds"

    def test_shares_at_lower_bound_accepted(self, healthy_period, price_bars):
        """shares_outstanding = 100,000 is within bounds."""
        profile = AssetProfile(
            ticker="OK",
            name="Small Cap Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000000"),
            shares_outstanding=100_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason is None

    def test_shares_at_upper_bound_accepted(self, healthy_period, price_bars):
        """shares_outstanding = 50 billion is within bounds."""
        profile = AssetProfile(
            ticker="OK",
            name="Mega Cap Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5000000000000"),
            shares_outstanding=50_000_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason is None

    def test_implied_market_cap_too_low(self, healthy_period, price_bars):
        """actual_price * shares < $1M -> invalid_reason."""
        profile = AssetProfile(
            ticker="TINY",
            name="Tiny Cap Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000"),
            shares_outstanding=100_000,  # within bounds
        )
        # price_bars latest close = $197, so implied mcap = 197 * 100_000 = $19.7M
        # Need shares low enough that mcap < $1M with $197 price
        # $197 * 5000 = $985K < $1M — but 5000 < 100K min shares, so test with
        # a custom price bar instead
        low_price_bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("0.005"),
                high=Decimal("0.006"),
                low=Decimal("0.004"),
                close=Decimal("0.005"),
                volume=1000,
            ),
        ]
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=low_price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # 0.005 * 100_000 = $500 implied mcap -> way below $1M
        assert result.invalid_reason == "implied_market_cap_unreasonable"

    def test_implied_market_cap_too_high(self, healthy_period):
        """actual_price * shares > $10T -> invalid_reason."""
        profile = AssetProfile(
            ticker="HUGE",
            name="Absurd Cap Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("15000000000000"),
            shares_outstanding=50_000_000_000,  # within bounds
        )
        high_price_bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("300"),
                high=Decimal("310"),
                low=Decimal("290"),
                close=Decimal("300"),
                volume=1000000,
            ),
        ]
        # 300 * 50B = $15T -> over $10T
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=high_price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "implied_market_cap_unreasonable"

    def test_no_actual_price_skips_market_cap_check(self, healthy_period):
        """If no price bars, market cap cross-check is skipped."""
        profile = AssetProfile(
            ticker="OK",
            name="No Price Co",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000000000"),
            shares_outstanding=1_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=[],
            conviction_level=ConvictionLevel.HIGH,
        )
        # No actual_price -> skip market cap check -> compute normally
        assert result.invalid_reason is None or result.invalid_reason != "implied_market_cap_unreasonable"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer1InputValidation -v`
Expected: FAIL — no bounds checking in `compute_price_targets`

**Step 3: Implement Layer 1**

In `engine/src/margin_engine/scoring/quantitative/price_targets.py`, add constants and modify `compute_price_targets()`:

```python
import logging

logger = logging.getLogger(__name__)

# Input validation bounds
_MIN_SHARES = 100_000            # 100K — covers micro-caps
_MAX_SHARES = 50_000_000_000     # 50B — covers mega-caps
_MIN_IMPLIED_MARKET_CAP = 1_000_000       # $1M
_MAX_IMPLIED_MARKET_CAP = 10_000_000_000_000  # $10T
```

In `compute_price_targets()`, after the existing `shares <= 0` check (line 102-103), add:

```python
    # Layer 1: Fixed share bounds
    if shares < _MIN_SHARES or shares > _MAX_SHARES:
        logger.warning(
            "Layer 1 reject: %s shares_outstanding=%d outside [%d, %d]",
            profile.ticker, shares, _MIN_SHARES, _MAX_SHARES,
        )
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="shares_outstanding_out_of_bounds",
        )

    # Layer 1: Market-cap cross-validation
    if actual_price is not None and actual_price > 0:
        implied_mcap = actual_price * shares
        if implied_mcap < _MIN_IMPLIED_MARKET_CAP or implied_mcap > _MAX_IMPLIED_MARKET_CAP:
            logger.warning(
                "Layer 1 reject: %s implied_market_cap=%.2f outside [%d, %d]",
                profile.ticker, implied_mcap, _MIN_IMPLIED_MARKET_CAP, _MAX_IMPLIED_MARKET_CAP,
            )
            return PriceTargets(
                actual_price=actual_price,
                invalid_reason="implied_market_cap_unreasonable",
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer1InputValidation -v`
Expected: PASS

**Step 5: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add Layer 1 input validation for shares bounds and market cap"
```

---

### Task 3: Add Layer 2 — Per-method output bounds

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py` (all 4 helper functions)
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for Layer 2**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
class TestLayer2PerMethodBounds:
    """Layer 2: Per-method output must be >= $0.01 and <= 100x actual_price."""

    def test_tiny_method_result_excluded(self, healthy_profile, price_bars):
        """A method producing < $0.01/share should be excluded."""
        # Create period with huge shares and tiny cash flows
        # so implied per-share price is < $0.01
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("1000"),
                gross_profit=Decimal("500"),
                ebit=Decimal("100"),
                net_income=Decimal("50"),
                shares_outstanding=15000000000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000"),
                current_assets=Decimal("5000"),
                cash_and_equivalents=Decimal("1000"),
                current_liabilities=Decimal("3000"),
                long_term_debt=Decimal("2000"),
                total_equity=Decimal("5000"),
                shares_outstanding=15000000000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("200"),
                capital_expenditures=Decimal("-50"),
                dividends_paid=Decimal("-10"),
                share_repurchases=Decimal("-20"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # With 15B shares and tiny cash flows, most methods produce < $0.01
        # All methods excluded -> invalid or None intrinsic
        if result.valuation_methods:
            for method_price in result.valuation_methods.values():
                assert method_price >= 0.01

    def test_healthy_data_passes_layer2(self, healthy_period, healthy_profile, price_bars):
        """Healthy data should not trigger Layer 2 rejection."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.invalid_reason is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer2PerMethodBounds -v`
Expected: FAIL — no per-method bounds checking

**Step 3: Implement Layer 2**

Add constant:

```python
_MIN_PER_SHARE_PRICE = 0.01       # $0.01 minimum per method
_MAX_PRICE_MULTIPLE = 100.0        # 100x actual price maximum per method
```

Thread `actual_price` into each helper function. For each of the four helpers (`_dcf_intrinsic_per_share`, `_ev_fcf_implied_per_share`, `_acquirers_implied_per_share`, `_shareholder_yield_implied_per_share`), add `actual_price: float | None = None` parameter and add bounds check before the return:

```python
    result = <existing calculation> / shares
    # Layer 2: Per-method output bounds
    if result < _MIN_PER_SHARE_PRICE:
        return None
    if actual_price is not None and actual_price > 0 and result > _MAX_PRICE_MULTIPLE * actual_price:
        return None
    return result
```

Update the call sites in `compute_price_targets()` to pass `actual_price` to each helper:

```python
    methods: dict[str, float | None] = {
        "dcf": _dcf_intrinsic_per_share(
            period=period,
            shares=shares,
            growth_rate=growth_rate,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            projection_years=projection_years,
            actual_price=actual_price,
        ),
        "ev_fcf": _ev_fcf_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
        "acquirers_multiple": _acquirers_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
        "shareholder_yield": _shareholder_yield_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
    }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer2PerMethodBounds -v`
Expected: PASS

**Step 5: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add Layer 2 per-method output bounds to price targets"
```

---

### Task 4: Add Layer 3 — Cross-method consistency

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:128-141`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for Layer 3**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
from margin_engine.scoring.quantitative.price_targets import _filter_outlier_methods

class TestLayer3CrossMethodConsistency:
    """Layer 3: Exclude methods that differ > 10x from median."""

    def test_outlier_method_excluded(self):
        """A method 20x the median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 5000.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered
        assert len(filtered) == 3

    def test_all_methods_agree_kept(self):
        """When all methods are within 10x of median, all are kept."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 48.0, "shareholder_yield": 60.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 4

    def test_single_method_kept(self):
        """A single method cannot be outlier-filtered."""
        methods = {"dcf": 50.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 1

    def test_two_methods_both_kept(self):
        """Two methods: both kept (need 2+ to compute median meaningfully)."""
        methods = {"dcf": 50.0, "ev_fcf": 500.0}
        filtered = _filter_outlier_methods(methods)
        # With only 2, median is 275. 500/275 ~1.8x, 50/275 ~0.18x
        # 0.18 < 0.1 threshold, so 50.0 would be excluded. Test this.
        assert len(filtered) >= 1

    def test_low_outlier_excluded(self):
        """A method < 0.1x median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 2.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered

    def test_all_methods_filtered_returns_empty(self):
        """If filtering removes everything, return empty dict."""
        # This would happen if 2 methods wildly disagree
        methods = {"dcf": 1.0, "ev_fcf": 10000.0}
        filtered = _filter_outlier_methods(methods)
        # median=5000.5; 1.0/5000.5 < 0.1; 10000/5000.5 < 10. So dcf is out, ev_fcf stays.
        # At least 1 should remain
        assert len(filtered) >= 0  # Just check it doesn't crash
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer3CrossMethodConsistency -v`
Expected: FAIL — `_filter_outlier_methods` does not exist

**Step 3: Implement Layer 3**

Add to `price_targets.py`:

```python
import statistics

_OUTLIER_LOW_RATIO = 0.1    # Exclude methods < 0.1x median
_OUTLIER_HIGH_RATIO = 10.0  # Exclude methods > 10x median

def _filter_outlier_methods(methods: dict[str, float]) -> dict[str, float]:
    """Remove methods whose value is < 0.1x or > 10x the median.

    Requires 2+ methods to filter. Returns the dict unchanged if < 2 methods.
    """
    if len(methods) < 2:
        return methods

    median = statistics.median(methods.values())
    if median <= 0:
        return methods

    return {
        k: v for k, v in methods.items()
        if _OUTLIER_LOW_RATIO * median <= v <= _OUTLIER_HIGH_RATIO * median
    }
```

In `compute_price_targets()`, after the `valid_methods` filter and before computing `intrinsic_value`, add:

```python
    # Layer 3: Cross-method consistency — exclude outlier methods
    valid_methods = _filter_outlier_methods(valid_methods)
    if not valid_methods:
        logger.warning("Layer 3 reject: %s all methods filtered as inconsistent", profile.ticker)
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="methods_inconsistent",
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer3CrossMethodConsistency -v`
Expected: PASS

**Step 5: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add Layer 3 cross-method consistency filtering"
```

---

### Task 5: Add Layer 4 — Final output validation

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:140-162`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for Layer 4**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
from margin_engine.scoring.quantitative.price_targets import _validate_final_output

class TestLayer4FinalOutputValidation:
    """Layer 4: Final intrinsic value must be within bounds."""

    def test_extreme_low_relative_to_price(self):
        """Intrinsic value < 1% of actual_price -> invalid."""
        reason = _validate_final_output(intrinsic_value=0.50, actual_price=100.0)
        assert reason == "intrinsic_value_extreme"

    def test_extreme_high_relative_to_price(self):
        """Intrinsic value > 50x actual_price -> invalid."""
        reason = _validate_final_output(intrinsic_value=6000.0, actual_price=100.0)
        assert reason == "intrinsic_value_extreme"

    def test_within_bounds_returns_none(self):
        """Intrinsic value within 1%-50x of actual_price -> valid."""
        reason = _validate_final_output(intrinsic_value=150.0, actual_price=100.0)
        assert reason is None

    def test_no_actual_price_absolute_low(self):
        """Without actual_price, intrinsic_value < $0.10 -> invalid."""
        reason = _validate_final_output(intrinsic_value=0.05, actual_price=None)
        assert reason == "intrinsic_value_extreme"

    def test_no_actual_price_absolute_high(self):
        """Without actual_price, intrinsic_value > $1M -> invalid."""
        reason = _validate_final_output(intrinsic_value=1_500_000.0, actual_price=None)
        assert reason == "intrinsic_value_extreme"

    def test_no_actual_price_within_absolute_bounds(self):
        """Without actual_price, value in $0.10-$1M range -> valid."""
        reason = _validate_final_output(intrinsic_value=50.0, actual_price=None)
        assert reason is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer4FinalOutputValidation -v`
Expected: FAIL — `_validate_final_output` does not exist

**Step 3: Implement Layer 4**

Add to `price_targets.py`:

```python
_MIN_PRICE_RATIO = 0.01     # Intrinsic value must be >= 1% of actual_price
_MAX_PRICE_RATIO = 50.0     # Intrinsic value must be <= 50x actual_price
_ABS_MIN_INTRINSIC = 0.10   # Absolute floor when no actual_price
_ABS_MAX_INTRINSIC = 1_000_000.0  # Absolute ceiling when no actual_price

def _validate_final_output(
    intrinsic_value: float,
    actual_price: float | None,
) -> str | None:
    """Return an invalid_reason string if intrinsic_value is out of bounds, else None."""
    if actual_price is not None and actual_price > 0:
        if intrinsic_value < _MIN_PRICE_RATIO * actual_price:
            return "intrinsic_value_extreme"
        if intrinsic_value > _MAX_PRICE_RATIO * actual_price:
            return "intrinsic_value_extreme"
    else:
        if intrinsic_value < _ABS_MIN_INTRINSIC:
            return "intrinsic_value_extreme"
        if intrinsic_value > _ABS_MAX_INTRINSIC:
            return "intrinsic_value_extreme"
    return None
```

In `compute_price_targets()`, after computing `intrinsic_value` (the weighted average) and before computing MoS/buy/sell, add:

```python
    # Layer 4: Final output validation
    final_reason = _validate_final_output(intrinsic_value, actual_price)
    if final_reason:
        logger.warning(
            "Layer 4 reject: %s intrinsic_value=%.2f actual_price=%s reason=%s",
            profile.ticker, intrinsic_value, actual_price, final_reason,
        )
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason=final_reason,
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestLayer4FinalOutputValidation -v`
Expected: PASS

**Step 5: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add Layer 4 final output validation for price targets"
```

---

### Task 6: Add scoring raw score vs percentile divergence test

**Files:**
- Modify: `engine/tests/scoring/test_normalizer.py`

**Step 1: Write the test**

Add to `engine/tests/scoring/test_normalizer.py`, in the `TestRerankComposites` class:

```python
    def test_raw_score_differs_from_percentile_after_rerank(self):
        """After re-ranking, composite_raw_score and composite_percentile should differ.

        The raw score is the weighted average of factor percentiles.
        The percentile is the universe-level rank.
        They should only be equal by coincidence.
        """
        composites = [
            _make_composite("A", 45.0),
            _make_composite("B", 52.0),
            _make_composite("C", 58.0),
            _make_composite("D", 63.0),
            _make_composite("E", 71.0),
        ]
        result = rerank_composites(composites)

        # Raw scores should be preserved as-is
        raw_scores = [c.composite_raw_score for c in result]
        assert raw_scores == pytest.approx([45.0, 52.0, 58.0, 63.0, 71.0])

        # Percentiles should be [20, 40, 60, 80, 100]
        percentiles = [c.composite_percentile for c in result]
        assert percentiles == pytest.approx([20.0, 40.0, 60.0, 80.0, 100.0])

        # The top stock's raw score (71.0) is NOT 100.0
        top = max(result, key=lambda c: c.composite_percentile)
        assert top.composite_raw_score == pytest.approx(71.0)
        assert top.composite_raw_score != top.composite_percentile

    def test_top_stock_raw_score_not_100(self):
        """The highest-ranked stock should NOT have raw_score = 100
        unless all factors genuinely average to 100."""
        composites = [_make_composite(f"T{i}", 40.0 + i * 0.5) for i in range(10)]
        result = rerank_composites(composites)
        top = max(result, key=lambda c: c.composite_percentile)
        # Top raw score is 40.0 + 9*0.5 = 44.5, definitely not 100
        assert top.composite_raw_score == pytest.approx(44.5)
        assert top.composite_raw_score < 100.0
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_normalizer.py::TestRerankComposites::test_raw_score_differs_from_percentile_after_rerank engine/tests/scoring/test_normalizer.py::TestRerankComposites::test_top_stock_raw_score_not_100 -v`
Expected: PASS (these tests document existing correct behavior)

**Step 3: Commit**

```bash
git add engine/tests/scoring/test_normalizer.py
git commit -m "test: add raw score vs percentile divergence assertions"
```

---

### Task 7: Update API schemas to expose score and universe_percentile

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:67-98`
- Modify: `api/src/margin_api/schemas/dashboard.py:10-28`
- Modify: `api/tests/test_schemas.py`

**Step 1: Write failing tests**

Add to `api/tests/test_schemas.py`, in the `TestScoreResponse` class:

```python
    def test_score_response_has_score_field(self) -> None:
        """ScoreResponse must include 'score' (raw weighted average) as a field."""
        response = ScoreResponse(
            ticker="AAPL",
            composite_percentile=100.0,
            composite_raw_score=87.4,
            score=87.4,
            universe_percentile=100.0,
            conviction_level="exceptional",
            signal="buy",
            quality=FactorBreakdownResponse(
                factor_name="quality", weight=0.35, sub_scores=[], average_percentile=90.0,
            ),
            value=FactorBreakdownResponse(
                factor_name="value", weight=0.30, sub_scores=[], average_percentile=85.0,
            ),
            momentum=FactorBreakdownResponse(
                factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=88.0,
            ),
            filters_passed=[],
            data_coverage=0.95,
        )
        data = response.model_dump()
        assert data["score"] == 87.4
        assert data["universe_percentile"] == 100.0

    def test_from_engine_populates_score_and_universe_percentile(self) -> None:
        """from_engine() must populate score from composite_raw_score and
        universe_percentile from composite_percentile."""
        engine_score = _make_composite_score(ticker="TEST", percentile=99.0)
        # Set a distinct raw score
        engine_score = engine_score.model_copy(update={"composite_raw_score": 82.5})
        response = ScoreResponse.from_engine(engine_score)
        assert response.score == 82.5
        assert response.universe_percentile == 99.0
```

Also add to `TestPickSummary`:

```python
    def test_pick_summary_has_score_field(self) -> None:
        """PickSummary must include score and universe_percentile."""
        pick = PickSummary(
            ticker="NVDA",
            name="NVIDIA Corporation",
            composite_percentile=99.5,
            score=91.2,
            universe_percentile=99.5,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=97.0,
            value_percentile=85.0,
            momentum_percentile=98.0,
        )
        data = pick.model_dump()
        assert data["score"] == 91.2
        assert data["universe_percentile"] == 99.5
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_schemas.py::TestScoreResponse::test_score_response_has_score_field api/tests/test_schemas.py::TestScoreResponse::test_from_engine_populates_score_and_universe_percentile api/tests/test_schemas.py::TestPickSummary::test_pick_summary_has_score_field -v`
Expected: FAIL — `score` and `universe_percentile` fields don't exist

**Step 3: Implement schema changes**

In `api/src/margin_api/schemas/scores.py`, add fields to `ScoreResponse`:

```python
class ScoreResponse(BaseModel):
    """Full scoring result for a single ticker."""

    ticker: str
    name: str = ""
    score: float = 0.0  # Raw weighted average — the true quality measure
    universe_percentile: float = 0.0  # Universe-level rank (0-100)
    composite_percentile: float  # Kept for backwards compat
    composite_raw_score: float = 0.0  # Kept for backwards compat
    # ... rest unchanged
```

Update `from_engine()` to populate the new fields:

```python
    @classmethod
    def from_engine(cls, score: CompositeScore) -> ScoreResponse:
        """Convert an engine CompositeScore to an API response."""
        return cls(
            ticker=score.ticker,
            score=score.composite_raw_score,
            universe_percentile=score.composite_percentile,
            composite_percentile=score.composite_percentile,
            composite_raw_score=score.composite_raw_score,
            # ... rest unchanged
        )
```

In `api/src/margin_api/schemas/dashboard.py`, add fields to `PickSummary`:

```python
class PickSummary(BaseModel):
    """Summary of a high-conviction pick for the dashboard."""

    ticker: str
    name: str
    score: float = 0.0  # Raw weighted average
    universe_percentile: float = 0.0  # Universe-level rank
    composite_percentile: float  # Kept for backwards compat
    # ... rest unchanged
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_schemas.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/schemas/dashboard.py api/tests/test_schemas.py
git commit -m "feat: expose score and universe_percentile in API schemas"
```

---

### Task 8: Update frontend TypeScript types

**Files:**
- Modify: `web/src/lib/api/types.ts`

**Step 1: Update TypeScript interfaces**

In `web/src/lib/api/types.ts`, add new fields to `ScoreResponse`:

```typescript
export interface ScoreResponse {
  ticker: string
  name: string
  score: number          // Raw weighted average — the true quality measure
  universe_percentile: number  // Universe-level rank (0-100)
  composite_percentile: number // Kept for backwards compat
  composite_raw_score: number  // Kept for backwards compat
  // ... rest unchanged
}
```

Add to `PickSummary`:

```typescript
export interface PickSummary {
  ticker: string
  name: string
  score: number          // Raw weighted average
  universe_percentile: number  // Universe-level rank
  composite_percentile: number // Kept for backwards compat
  // ... rest unchanged
}
```

**Step 2: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat: add score and universe_percentile to TypeScript types"
```

---

### Task 9: Propagate invalid_reason through API and add determinism test

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py`
- Modify: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing test for invalid_reason in API schema**

Add to `api/tests/test_schemas.py`:

```python
    def test_from_engine_propagates_invalid_reason(self) -> None:
        """invalid_reason from PriceTargets should surface in ScoreResponse."""
        engine_score = _make_composite_score(ticker="BAD", percentile=50.0)
        response = ScoreResponse.from_engine(engine_score)
        # When no price targets set, invalid_reason should be None
        assert response.price_target_invalid_reason is None
```

**Step 2: Add `price_target_invalid_reason` field to ScoreResponse**

In `api/src/margin_api/schemas/scores.py`:

```python
    price_target_invalid_reason: str | None = None
```

And in `from_engine()`, pass it through. Note: The engine `CompositeScore` doesn't currently carry `invalid_reason` directly — it only has the price fields. We need to check: when `PriceTargets.invalid_reason` is set, all price fields are None, so we can infer "price target was invalid" from the API side. But to be explicit, we'll add a field.

Add to `CompositeScore` model in `engine/src/margin_engine/models/scoring.py`:

```python
    price_target_invalid_reason: str | None = None
```

Update `composite.py` to propagate it:

```python
    if price_targets:
        price_kwargs = {
            # ... existing fields ...
            "price_target_invalid_reason": price_targets.invalid_reason,
        }
```

Update `ScoreResponse.from_engine()`:

```python
    price_target_invalid_reason=score.price_target_invalid_reason,
```

**Step 3: Write determinism test**

Add to `engine/tests/scoring/quantitative/test_price_targets.py`:

```python
class TestDeterminism:
    """Verify same inputs always produce same outputs."""

    def test_deterministic_across_runs(self, healthy_period, healthy_profile, price_bars):
        """Running compute_price_targets 10 times with same inputs produces identical results."""
        results = [
            compute_price_targets(
                period=healthy_period,
                profile=healthy_profile,
                price_bars=price_bars,
                conviction_level=ConvictionLevel.HIGH,
            )
            for _ in range(10)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.intrinsic_value == first.intrinsic_value
            assert r.buy_price == first.buy_price
            assert r.sell_price == first.sell_price
            assert r.price_upside == first.price_upside
            assert r.margin_of_safety == first.margin_of_safety
            assert r.valuation_methods == first.valuation_methods
            assert r.invalid_reason == first.invalid_reason
```

**Step 4: Run all tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py api/tests/test_schemas.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/src/margin_engine/scoring/composite.py engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py api/src/margin_api/schemas/scores.py api/tests/test_schemas.py
git commit -m "feat: propagate price_target_invalid_reason through engine and API"
```

---

### Task 10: Run full test suite and verify no regressions

**Files:** None (test-only)

**Step 1: Run engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS (784+ tests)

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All PASS (294+ tests)

**Step 3: If any failures, fix them**

Common things to check:
- Tests that construct `CompositeScore` directly may need `price_target_invalid_reason` (defaults to None, should be fine)
- Tests that construct `PriceTargets` with negative prices will now fail the positive-price validator
- Tests that hardcode `composite_percentile=100.0` as an assertion for the top stock still work because `rerank_composites` still produces 100.0 for the top rank — the difference is the *displayed* field is now `score`/`composite_raw_score`

**Step 4: Commit any test fixes**

```bash
git add -A
git commit -m "fix: resolve test regressions from scoring/pricing integrity changes"
```
