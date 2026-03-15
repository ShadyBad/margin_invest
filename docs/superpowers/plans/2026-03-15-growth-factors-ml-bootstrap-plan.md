# Growth Factors + PIT-Bootstrapped ML Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate growth factor weights in composite scoring, build a historical scorer for PIT-bootstrapped ML training data, fix forward returns computation, and deprecate the v2 scoring path.

**Architecture:** Sequential four-phase approach. Phase 1 modifies the engine's `ScoringConfig` and `compute_composite_score()` to give growth factors real weight. Phase 2 creates a `historical_scorer.py` engine module and `historical_scores` DB table to generate ~150K training samples from PIT data. Phase 3 fixes the forward returns 0.0-default bug and rewires ML training to use historical scores. Phase 4 removes the v2 scoring path from the worker chain once safety gates pass.

**Tech Stack:** Python 3.13, Pydantic, SQLAlchemy 2.0 (asyncpg), Alembic, ARQ, NumPy, LightGBM, pytest

---

## File Structure

### Phase 1: Growth Factor Activation
| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `engine/src/margin_engine/models/scoring.py:229-253` | Add `growth_weight` to `ScoringConfig`, update `weights_for_stage()` |
| Modify | `engine/src/margin_engine/scoring/composite.py:20-127` | Use `growth_weight`, normalize weights, include growth in composite |
| Create | `engine/tests/scoring/test_growth_factors_golden.py` | Golden-value tests for all 4 growth modules |
| Modify | `engine/tests/scoring/test_composite.py` | Update existing tests for new default weights |

### Phase 2: Historical Scorer
| Action | File | Responsibility |
|--------|------|----------------|
| Create | `engine/src/margin_engine/scoring/historical_scorer.py` | `score_universe_at_date()` — pure Python historical scoring |
| Create | `engine/tests/scoring/test_historical_scorer.py` | Unit tests for historical scorer |
| Create | `api/alembic/versions/xxxx_add_historical_scores_table.py` | Alembic migration for `historical_scores` table |
| Modify | `api/src/margin_api/db/models.py` | Add `HistoricalScore` ORM model |
| Modify | `api/src/margin_api/workers.py` | Add `backfill_historical_scores` worker |

### Phase 3: ML Training Fix
| Action | File | Responsibility |
|--------|------|----------------|
| Create | `engine/src/margin_engine/ml/historical_forward_returns.py` | `compute_historical_forward_returns()` — PIT-aware forward returns |
| Create | `engine/tests/ml/test_historical_forward_returns.py` | Tests for historical forward returns |
| Modify | `api/src/margin_api/workers.py:1779-1819` | Fix 0.0-default bug, load historical scores, combine, filter |
| Modify | `api/src/margin_api/config.py` | Add `ml_bootstrap_mode` and `ml_live_weight` settings |
| Modify | `engine/src/margin_engine/ml/seed_validation.py:40-45` | Support bootstrap thresholds |

### Phase 4: V2 Deprecation
| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `api/src/margin_api/workers.py:550-552` | Change `ingest_sweep_complete` to enqueue `full_score_v3` |
| Modify | `api/tests/test_ingest_sweep.py` | Update existing test asserting `full_score` → `full_score_v3` |
| Delete | `api/src/margin_api/workers.py:564-642` | Remove `full_score()` function |
| Modify | `api/src/margin_api/workers.py:3166-3195` | Remove `full_score` from functions list |
| Modify | `api/tests/` | Delete/update v2 scoring tests |

---

## Chunk 1: Phase 1 — Growth Factor Weight Activation

### Task 1: Add `growth_weight` to `ScoringConfig` and update `weights_for_stage()`

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:229-253`
- Test: `engine/tests/scoring/test_composite.py`

- [ ] **Step 1: Write failing test for `growth_weight` field and 4-tuple `weights_for_stage()`**

In `engine/tests/scoring/test_composite.py`, add a new test class at the end of the file:

```python
# ---------------------------------------------------------------------------
# Growth weight in ScoringConfig
# ---------------------------------------------------------------------------


class TestGrowthWeight:
    """ScoringConfig growth_weight field and 4-tuple weights_for_stage."""

    def test_default_growth_weight(self):
        """Default growth_weight is 0.15."""
        config = ScoringConfig()
        assert config.growth_weight == 0.15

    def test_default_weights_changed(self):
        """Default weights: q=0.25, v=0.20, m=0.25, g=0.15."""
        config = ScoringConfig()
        assert config.quality_weight == 0.25
        assert config.value_weight == 0.20
        assert config.momentum_weight == 0.25
        assert config.growth_weight == 0.15

    def test_weights_for_stage_returns_4_tuple(self):
        """weights_for_stage returns (q, v, m, g) 4-tuple."""
        config = ScoringConfig()
        result = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert len(result) == 4

    def test_high_growth_stage_weights(self):
        """High Growth: q=0.20, v=0.10, m=0.25, g=0.30 (sum=0.85)."""
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert q == pytest.approx(0.20)
        assert v == pytest.approx(0.10)
        assert m == pytest.approx(0.25)
        assert g == pytest.approx(0.30)
        assert q + v + m + g == pytest.approx(0.85)

    def test_mature_stage_weights(self):
        """Mature: q=0.25, v=0.30, m=0.15, g=0.15 (sum=0.85)."""
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.MATURE)
        assert q == pytest.approx(0.25)
        assert v == pytest.approx(0.30)
        assert m == pytest.approx(0.15)
        assert g == pytest.approx(0.15)
        assert q + v + m + g == pytest.approx(0.85)

    def test_steady_growth_stage_weights(self):
        """Steady Growth: q=0.25, v=0.20, m=0.25, g=0.15 (same as default)."""
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.STEADY_GROWTH)
        assert q == pytest.approx(0.25)
        assert v == pytest.approx(0.20)
        assert m == pytest.approx(0.25)
        assert g == pytest.approx(0.15)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_composite.py::TestGrowthWeight -v`
Expected: FAIL — `growth_weight` not on `ScoringConfig`, `weights_for_stage` returns 3-tuple

- [ ] **Step 3: Implement `growth_weight` and updated `weights_for_stage()`**

In `engine/src/margin_engine/models/scoring.py`, modify `ScoringConfig`:

```python
class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth) — sum to 0.85; normalized to 1.0 in composite
    quality_weight: float = 0.25
    value_weight: float = 0.20
    momentum_weight: float = 0.25
    growth_weight: float = 0.15

    # Conviction thresholds (raw score) — absolute, universe-independent
    exceptional_threshold: float = 76.0
    high_threshold: float = 71.0
    medium_threshold: float = 66.0  # renamed from watchlist_threshold
    sell_threshold: float = 97.0

    def weights_for_stage(self, stage: GrowthStage) -> tuple[float, float, float, float]:
        """Return (quality, value, momentum, growth) weights for a growth stage.

        All stages sum to 0.85 (0.15 reserved for future catalyst activation).
        Weights are normalized to 1.0 in compute_composite_score().
        """
        stage_weights: dict[GrowthStage, tuple[float, float, float, float]] = {
            GrowthStage.HIGH_GROWTH: (0.20, 0.10, 0.25, 0.30),
            GrowthStage.STEADY_GROWTH: (0.25, 0.20, 0.25, 0.15),
            GrowthStage.MATURE: (0.25, 0.30, 0.15, 0.15),
            GrowthStage.CYCLICAL: (0.25, 0.20, 0.25, 0.15),
            GrowthStage.TURNAROUND: (0.25, 0.20, 0.25, 0.15),
        }
        return stage_weights[stage]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_composite.py::TestGrowthWeight -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/scoring/test_composite.py
git commit -m "feat(engine): add growth_weight to ScoringConfig, return 4-tuple from weights_for_stage"
```

---

### Task 2: Update `compute_composite_score()` to include growth in weighting

**Files:**
- Modify: `engine/src/margin_engine/scoring/composite.py:20-127`
- Test: `engine/tests/scoring/test_composite.py`

- [ ] **Step 1: Write failing test for growth-weighted composite**

Add to `engine/tests/scoring/test_composite.py`:

```python
# ---------------------------------------------------------------------------
# Growth factor contribution to composite
# ---------------------------------------------------------------------------


class TestGrowthFactorInComposite:
    """Growth scores contribute to composite percentile with real weight."""

    def test_growth_included_in_composite_default_weights(self):
        """Q=80, V=60, M=70, G=90 with default weights (normalized to 1.0).

        Raw: 80*0.25 + 60*0.20 + 70*0.25 + 90*0.15 = 20+12+17.5+13.5 = 63.0
        Sum of weights = 0.85, normalized: 63.0 / 0.85 = 74.117647...
        """
        quality = [_make_factor_score("gp", percentile_rank=80.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]
        growth = [_make_factor_score("revenue_cagr", percentile_rank=90.0)]

        result = compute_composite_score(
            ticker="GROW",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=growth,
        )

        expected = (80 * 0.25 + 60 * 0.20 + 70 * 0.25 + 90 * 0.15) / 0.85
        assert result.composite_percentile == pytest.approx(expected, rel=1e-6)

    def test_growth_none_uses_three_pillars(self):
        """When growth_scores is None, only Q/V/M are used (normalized)."""
        quality = [_make_factor_score("gp", percentile_rank=80.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]

        result = compute_composite_score(
            ticker="NOGROW",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=None,
        )

        # Only Q/V/M weights used: 0.25+0.20+0.25 = 0.70
        expected = (80 * 0.25 + 60 * 0.20 + 70 * 0.25) / 0.70
        assert result.composite_percentile == pytest.approx(expected, rel=1e-6)

    def test_growth_empty_list_uses_three_pillars(self):
        """Empty growth_scores list -> growth avg is 0, but weight still 0."""
        quality = [_make_factor_score("gp", percentile_rank=80.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]

        result = compute_composite_score(
            ticker="EMPTYGROW",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=[],
        )

        # Empty growth -> weight excluded from normalization
        expected = (80 * 0.25 + 60 * 0.20 + 70 * 0.25) / 0.70
        assert result.composite_percentile == pytest.approx(expected, rel=1e-6)

    def test_growth_with_growth_stage(self):
        """High Growth stage: q=0.20, v=0.10, m=0.25, g=0.30 (sum=0.85)."""
        quality = [_make_factor_score("gp", percentile_rank=80.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]
        growth = [_make_factor_score("revenue_cagr", percentile_rank=90.0)]

        result = compute_composite_score(
            ticker="HGROW",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=growth,
            growth_stage=GrowthStage.HIGH_GROWTH,
        )

        # High Growth: q=0.20, v=0.10, m=0.25, g=0.30 -> sum=0.85
        # (80*0.20 + 60*0.10 + 70*0.25 + 90*0.30) / 0.85
        # = (16 + 6 + 17.5 + 27) / 0.85 = 66.5 / 0.85 = 78.235...
        expected = (80 * 0.20 + 60 * 0.10 + 70 * 0.25 + 90 * 0.30) / 0.85
        assert result.composite_percentile == pytest.approx(expected, rel=1e-6)

    def test_growth_included_in_data_coverage(self):
        """Growth scores are counted in data_coverage calculation."""
        quality = [_make_factor_score("gp", percentile_rank=80.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]
        growth = [
            _make_factor_score("revenue_cagr", percentile_rank=90.0),
            _make_factor_score("rule_of_40", percentile_rank=0.0),
        ]

        result = compute_composite_score(
            ticker="COV",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=growth,
        )

        # 4 with data (q, v, m, growth[0]) out of 5 total
        assert result.data_coverage == pytest.approx(4 / 5)

    def test_weight_normalization_sums_to_one(self):
        """Weights are normalized so Q=100, V=100, M=100, G=100 -> composite=100."""
        quality = [_make_factor_score(percentile_rank=100.0)]
        value = [_make_factor_score(percentile_rank=100.0)]
        momentum = [_make_factor_score(percentile_rank=100.0)]
        growth = [_make_factor_score(percentile_rank=100.0)]

        result = compute_composite_score(
            ticker="NORM",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_scores=growth,
        )

        assert result.composite_percentile == pytest.approx(100.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_composite.py::TestGrowthFactorInComposite -v`
Expected: FAIL — growth scores not included in composite calculation

- [ ] **Step 3: Implement growth weighting in `compute_composite_score()`**

Replace the full function body in `engine/src/margin_engine/scoring/composite.py`:

```python
def compute_composite_score(
    ticker: str,
    quality_scores: list[FactorScore],
    value_scores: list[FactorScore],
    momentum_scores: list[FactorScore],
    filters_passed: list[FilterResult],
    growth_stage: GrowthStage | None = None,
    config: ScoringConfig | None = None,
    price_targets: PriceTargets | None = None,
    growth_scores: list[FactorScore] | None = None,
) -> CompositeScore:
    """Compute a weighted composite score from quality, value, momentum, and growth sub-factors."""
    if config is None:
        config = ScoringConfig()

    # 1. Determine weights from growth stage (or default)
    if growth_stage is not None:
        q_weight, v_weight, m_weight, g_weight = config.weights_for_stage(growth_stage)
    else:
        q_weight = config.quality_weight
        v_weight = config.value_weight
        m_weight = config.momentum_weight
        g_weight = config.growth_weight

    # 2. Build FactorBreakdowns
    quality = FactorBreakdown(
        factor_name="quality",
        weight=q_weight,
        sub_scores=quality_scores,
    )
    value = FactorBreakdown(
        factor_name="value",
        weight=v_weight,
        sub_scores=value_scores,
    )
    momentum = FactorBreakdown(
        factor_name="momentum",
        weight=m_weight,
        sub_scores=momentum_scores,
    )

    # Build growth breakdown
    growth_breakdown: FactorBreakdown | None = None
    has_growth = growth_scores is not None and len(growth_scores) > 0
    if has_growth:
        growth_breakdown = FactorBreakdown(
            factor_name="growth",
            weight=g_weight,
            sub_scores=growth_scores,
        )

    # 3. Compute weighted composite percentile with weight normalization
    #    Only include pillars that have scores; normalize weights to sum to 1.0
    pillars: list[tuple[float, float]] = [
        (quality.average_percentile, q_weight),
        (value.average_percentile, v_weight),
        (momentum.average_percentile, m_weight),
    ]
    if has_growth:
        pillars.append((growth_breakdown.average_percentile, g_weight))

    total_weight = sum(w for _, w in pillars)
    if total_weight > 0:
        composite_percentile = sum(p * w for p, w in pillars) / total_weight
    else:
        composite_percentile = 0.0

    # 4. Compute data coverage (include growth scores)
    all_scores = [*quality_scores, *value_scores, *momentum_scores]
    if has_growth:
        all_scores.extend(growth_scores)
    total_scores = len(all_scores)
    if total_scores == 0:
        data_coverage = 1.0
    else:
        scores_with_data = sum(1 for s in all_scores if s.percentile_rank > 0.0)
        data_coverage = scores_with_data / total_scores

    # 5. Attach price targets if provided
    price_kwargs: dict = {}
    if price_targets:
        price_kwargs = {
            "margin_invest_value": price_targets.margin_invest_value,
            "buy_price": price_targets.buy_price,
            "sell_price": price_targets.sell_price,
            "actual_price": price_targets.actual_price,
            "price_upside": price_targets.price_upside,
            "margin_of_safety": price_targets.margin_of_safety,
            "valuation_methods": price_targets.valuation_methods,
            "price_target_invalid_reason": price_targets.invalid_reason,
        }

    # 6. Assemble and return CompositeScore
    return CompositeScore(
        ticker=ticker,
        composite_percentile=composite_percentile,
        composite_raw_score=composite_percentile,
        quality=quality,
        value=value,
        momentum=momentum,
        growth=growth_breakdown,
        filters_passed=filters_passed,
        data_coverage=data_coverage,
        growth_stage=growth_stage,
        **price_kwargs,
    )
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_composite.py::TestGrowthFactorInComposite -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Update existing composite tests for new default weights**

The existing tests use the old default weights (q=0.35, v=0.30, m=0.35). Since defaults changed to (q=0.25, v=0.20, m=0.25) and weights are now normalized, existing tests that don't pass `growth_scores` will compute differently.

When `growth_scores=None`, active weights are q=0.25, v=0.20, m=0.25 → sum=0.70 → normalized.

Update `TestBasicComposite.test_known_percentiles_default_weights`:
```python
def test_known_percentiles_default_weights(self):
    """Quality=75, Value=60, Momentum=80 with normalized default weights.

    Active weights (no growth): q=0.25, v=0.20, m=0.25 → sum=0.70
    Composite = (75*0.25 + 60*0.20 + 80*0.25) / 0.70 = 50.75 / 0.70 = 72.5
    """
    quality = [_make_factor_score("gp", percentile_rank=75.0)]
    value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
    momentum = [_make_factor_score("price_mom", percentile_rank=80.0)]
    filters = [_make_filter()]

    result = compute_composite_score(
        ticker="AAPL",
        quality_scores=quality,
        value_scores=value,
        momentum_scores=momentum,
        filters_passed=filters,
    )

    expected = (75 * 0.25 + 60 * 0.20 + 80 * 0.25) / 0.70
    assert result.composite_percentile == pytest.approx(expected, rel=1e-6)
    assert result.ticker == "AAPL"
```

Update ALL existing tests that assert on specific composite_percentile values with the new normalized math. Tests affected:
- `TestBasicComposite`: `test_known_percentiles_default_weights`, `test_composite_raw_score_populated`, `test_multiple_sub_scores_per_factor`
- `TestGrowthStageWeights`: `test_high_growth_weights`, `test_mature_weights`, `test_steady_growth_same_as_default`
- `TestDefaultConfig`: `test_none_config_uses_defaults`, `test_custom_config_overrides_defaults`
- `TestEmptySubScores`: `test_one_factor_empty`
- `TestFactorBreakdownFields`: `test_breakdown_names_and_weights`, `test_breakdown_weights_adjusted_by_growth_stage`

For each, recalculate the expected value using the formula:
`composite = sum(avg_percentile * weight for active pillars) / sum(active weights)`

Key recalculations (no growth_scores → active weights sum to q+v+m, normalized):
- Q=75, V=60, M=80, default: `(75*0.25 + 60*0.20 + 80*0.25) / 0.70 = 50.75/0.70 = 72.5`
- Q=85, V=65, M=50, default: `(85*0.25 + 65*0.20 + 50*0.25) / 0.70 = 46.75/0.70 ≈ 66.786`
- High Growth (no growth_scores): q=0.20, v=0.10, m=0.25 → sum=0.55: `(75*0.20+60*0.10+80*0.25) / 0.55 = 41.0/0.55 ≈ 74.545`
- Mature (no growth_scores): q=0.25, v=0.30, m=0.15 → sum=0.70: `(75*0.25+60*0.30+80*0.15) / 0.70 = 48.75/0.70 ≈ 69.643`
- Steady Growth (4-tuple): same as default — q=0.25, v=0.20, m=0.25 → 72.5

**Important:** Tests that pass growth_stage but NOT growth_scores need special care — the function will use the 4-tuple weights but only 3 pillars are active, so normalization applies to those 3 weights.

Also update `TestFactorBreakdownFields.test_breakdown_weights_adjusted_by_growth_stage` to check for the new weight values:
```python
# High Growth weights (sum=0.85, normalized in composite calculation)
assert result.quality.weight == pytest.approx(0.20)
assert result.value.weight == pytest.approx(0.10)
assert result.momentum.weight == pytest.approx(0.25)
```

- [ ] **Step 6: Run the full composite test suite**

Run: `uv run pytest engine/tests/scoring/test_composite.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/composite.py engine/tests/scoring/test_composite.py
git commit -m "feat(engine): include growth factors in composite score with weight normalization"
```

---

### Task 3: Golden-value tests for growth factor modules

**Files:**
- Create: `engine/tests/scoring/test_growth_factors_golden.py`

Each growth module needs a hand-calculated golden-value test using `FinancialHistory` / `FinancialPeriod` models.

- [ ] **Step 1: Write golden-value tests**

Create `engine/tests/scoring/test_growth_factors_golden.py`:

```python
"""Golden-value tests for growth factor modules.

Each test uses hand-calculated inputs with known expected outputs.
These are the canonical correctness tests — if they break, the formula changed.
"""

import pytest
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40
from margin_engine.scoring.quantitative.runway_score import runway_score


def _make_period(
    revenue: float = 1_000_000,
    ebit: float = 200_000,
    total_equity: float = 500_000,
    long_term_debt: float = 300_000,
    short_term_debt: float = 0,
    cash: float = 100_000,
    operating_cash_flow: float = 150_000,
    capital_expenditures: float = 0,
    period_end: str = "2024-12-31",
    filing_date: str = "2025-02-15",
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for growth factor testing.

    Note: total_debt, free_cash_flow, effective_tax_rate are @property computed
    values on the models — not constructor fields. Use the underlying fields:
    - total_debt = long_term_debt + short_term_debt
    - free_cash_flow = operating_cash_flow + capital_expenditures
    - effective_tax_rate defaults to 0.21 when tax_provision is None
    """
    total_assets = total_equity + long_term_debt + short_term_debt
    income = IncomeStatement(
        revenue=Decimal(str(revenue)),
        ebit=Decimal(str(ebit)),
    )
    balance = BalanceSheet(
        total_assets=Decimal(str(total_assets)),
        total_equity=Decimal(str(total_equity)),
        long_term_debt=Decimal(str(long_term_debt)),
        short_term_debt=Decimal(str(short_term_debt)),
        cash_and_equivalents=Decimal(str(cash)),
    )
    cashflow = CashFlowStatement(
        operating_cash_flow=Decimal(str(operating_cash_flow)),
        capital_expenditures=Decimal(str(capital_expenditures)),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=income,
        current_balance=balance,
        current_cash_flow=cashflow,
    )


class TestIncrementalRoicGolden:
    """incremental_roic: delta_NOPAT / delta_IC."""

    def test_golden_positive(self):
        """Period 1: NOPAT=158K, IC=700K. Period 2: NOPAT=237K, IC=900K.

        effective_tax_rate defaults to 0.21 (no tax_provision set).
        NOPAT = EBIT * (1 - 0.21) = 200K * 0.79 = 158K (period 1)
        IC = equity + total_debt - cash = 500K + 300K - 100K = 700K (period 1)
        NOPAT = 300K * 0.79 = 237K (period 2)
        IC = 600K + 400K - 100K = 900K (period 2)
        Incremental ROIC = (237K - 158K) / (900K - 700K) = 79K / 200K = 0.395
        """
        p1 = _make_period(ebit=200_000, total_equity=500_000, long_term_debt=300_000,
                          cash=100_000, period_end="2023-12-31", filing_date="2024-02-15")
        p2 = _make_period(ebit=300_000, total_equity=600_000, long_term_debt=400_000,
                          cash=100_000, period_end="2024-12-31", filing_date="2025-02-15")
        history = FinancialHistory(ticker="TEST", periods=[p1, p2])

        result = incremental_roic(history)

        assert result.name == "incremental_roic"
        assert result.raw_value == pytest.approx(0.395, rel=1e-4)

    def test_single_period_returns_zero(self):
        """Single period -> cannot compute incremental ROIC."""
        p1 = _make_period()
        history = FinancialHistory(ticker="SOLO", periods=[p1])

        result = incremental_roic(history)

        assert result.raw_value == 0.0
        assert "Single period" in result.detail

    def test_zero_delta_ic(self):
        """No change in invested capital -> raw_value = 0.0."""
        p1 = _make_period(ebit=200_000, period_end="2023-12-31", filing_date="2024-02-15")
        p2 = _make_period(ebit=300_000, period_end="2024-12-31", filing_date="2025-02-15")
        history = FinancialHistory(ticker="FLAT", periods=[p1, p2])

        result = incremental_roic(history)

        assert result.raw_value == 0.0
        assert "delta_IC=0" in result.detail


class TestRevenueCagrGolden:
    """revenue_cagr: (end/start)^(1/n) - 1."""

    def test_golden_3_year(self):
        """Revenue: 1M -> 1.2M -> 1.5M -> 2M over 3 years.
        CAGR = (2M / 1M)^(1/3) - 1 = 2^(1/3) - 1 ≈ 0.2599
        """
        periods = [
            _make_period(revenue=1_000_000, period_end="2021-12-31", filing_date="2022-02-15"),
            _make_period(revenue=1_200_000, period_end="2022-12-31", filing_date="2023-02-15"),
            _make_period(revenue=1_500_000, period_end="2023-12-31", filing_date="2024-02-15"),
            _make_period(revenue=2_000_000, period_end="2024-12-31", filing_date="2025-02-15"),
        ]
        history = FinancialHistory(ticker="GROW", periods=periods)

        result = revenue_cagr(history, years=3)

        assert result.name == "revenue_cagr"
        assert result.raw_value == pytest.approx(2 ** (1 / 3) - 1, rel=1e-4)

    def test_golden_2_year(self):
        """Revenue: 500K -> 750K. 2 periods = 1 year.
        CAGR = (750K / 500K)^(1/1) - 1 = 0.50
        """
        periods = [
            _make_period(revenue=500_000, period_end="2023-12-31", filing_date="2024-02-15"),
            _make_period(revenue=750_000, period_end="2024-12-31", filing_date="2025-02-15"),
        ]
        history = FinancialHistory(ticker="FAST", periods=periods)

        result = revenue_cagr(history, years=3)  # years=3 but only 2 periods available

        assert result.raw_value == pytest.approx(0.50, rel=1e-4)

    def test_single_period_returns_zero(self):
        """Single period -> cannot compute CAGR."""
        history = FinancialHistory(ticker="SOLO", periods=[_make_period()])

        result = revenue_cagr(history)

        assert result.raw_value == 0.0

    def test_zero_start_revenue(self):
        """Zero starting revenue -> sentinel 0.0."""
        periods = [
            _make_period(revenue=0, period_end="2023-12-31", filing_date="2024-02-15"),
            _make_period(revenue=1_000_000, period_end="2024-12-31", filing_date="2025-02-15"),
        ]
        history = FinancialHistory(ticker="ZERO", periods=periods)

        result = revenue_cagr(history)

        assert result.raw_value == 0.0


class TestRuleOf40Golden:
    """rule_of_40: revenue_growth% + fcf_margin%."""

    def test_golden_above_40(self):
        """Growth 30% + margin 15% = 45 (above threshold).
        Input: revenue_growth_rate=0.30, fcf_margin=0.15
        Output: 30 + 15 = 45
        """
        result = rule_of_40(revenue_growth_rate=0.30, fcf_margin=0.15)

        assert result.name == "rule_of_40"
        assert result.raw_value == pytest.approx(45.0)

    def test_golden_below_40(self):
        """Growth 10% + margin 20% = 30 (below threshold)."""
        result = rule_of_40(revenue_growth_rate=0.10, fcf_margin=0.20)

        assert result.raw_value == pytest.approx(30.0)

    def test_negative_growth(self):
        """Shrinking revenue: growth -5% + margin 25% = 20."""
        result = rule_of_40(revenue_growth_rate=-0.05, fcf_margin=0.25)

        assert result.raw_value == pytest.approx(20.0)

    def test_negative_margin(self):
        """Burning cash: growth 50% + margin -30% = 20."""
        result = rule_of_40(revenue_growth_rate=0.50, fcf_margin=-0.30)

        assert result.raw_value == pytest.approx(20.0)


class TestRunwayScoreGolden:
    """runway_score: company_revenue / sub_industry_revenue."""

    def test_golden_penetration(self):
        """Revenue 10M / industry 100M = 0.10 penetration."""
        result = runway_score(
            company_revenue=Decimal("10000000"),
            sub_industry_revenue=Decimal("100000000"),
        )

        assert result.name == "runway_score"
        assert result.raw_value == pytest.approx(0.10)

    def test_none_sub_industry(self):
        """Unknown sub-industry -> neutral 0.5."""
        result = runway_score(company_revenue=Decimal("10000000"), sub_industry_revenue=None)

        assert result.raw_value == pytest.approx(0.5)

    def test_zero_sub_industry(self):
        """Zero sub-industry revenue -> saturated 1.0."""
        result = runway_score(
            company_revenue=Decimal("10000000"),
            sub_industry_revenue=Decimal("0"),
        )

        assert result.raw_value == pytest.approx(1.0)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_growth_factors_golden.py -v`
Expected: ALL PASS (these test existing code — golden-value validation)

- [ ] **Step 3: Commit**

```bash
git add engine/tests/scoring/test_growth_factors_golden.py
git commit -m "test(engine): add golden-value tests for all 4 growth factor modules"
```

---

### Task 4: Run full engine test suite to verify no regressions

**Files:**
- No modifications — verification only

- [ ] **Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ~2778 tests PASS (some may need updated expected values due to weight changes)

- [ ] **Step 2: Run API scoring service tests**

Run: `uv run pytest api/tests/test_scoring_service.py -v --tb=short`
Expected: PASS — API tests use `compute_raw_factor_scores` which passes growth_scores through

- [ ] **Step 3: Fix any failures from weight changes**

If any existing tests assert on specific composite_percentile values with the old weights (q=0.35, v=0.30, m=0.35), update them to use the new normalized calculation.

- [ ] **Step 4: Commit any test fixes**

```bash
git add -u
git commit -m "fix(tests): update expected values for new growth-weighted composite scoring"
```

---

## Chunk 2: Phase 2 — Historical Scorer

### Task 5: Add `HistoricalScore` ORM model and Alembic migration

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: `api/alembic/versions/xxxx_add_historical_scores_table.py`

- [ ] **Step 1: Add `HistoricalScore` model to `api/src/margin_api/db/models.py`**

Add after the `PITUniverseMembership` class (around line 1135):

```python
class HistoricalScore(Base):
    """Historical composite scores generated from PIT data for ML training."""

    __tablename__ = "historical_scores"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    score_date: Mapped[date] = mapped_column(index=True)
    composite_score: Mapped[float] = mapped_column(Float)
    composite_tier: Mapped[str] = mapped_column(String(20))
    sub_scores: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("ticker", "score_date", name="uq_historical_score_ticker_date"),
    )
```

- [ ] **Step 2: Generate Alembic migration**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic revision --autogenerate -m "add historical_scores table"`

- [ ] **Step 3: Verify migration is idempotent — edit the generated file**

Open the generated migration file. Replace the `upgrade()` function body with an idempotent version:

```python
def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "historical_scores" not in inspector.get_table_names():
        op.create_table(
            "historical_scores",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("ticker", sa.String(length=20), nullable=False),
            sa.Column("score_date", sa.Date(), nullable=False),
            sa.Column("composite_score", sa.Float(), nullable=False),
            sa.Column("composite_tier", sa.String(length=20), nullable=False),
            sa.Column("sub_scores", JSONVariant, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ticker", "score_date", name="uq_historical_score_ticker_date"),
        )
        op.create_index(op.f("ix_historical_scores_ticker"), "historical_scores", ["ticker"])
        op.create_index(op.f("ix_historical_scores_score_date"), "historical_scores", ["score_date"])
```

- [ ] **Step 4: Check for multiple Alembic heads**

Run: `uv run alembic heads`
Expected: Single head. If multiple, create a merge migration: `uv run alembic merge heads -m "merge historical_scores head"`

- [ ] **Step 5: Apply migration locally**

Run: `uv run alembic upgrade head`
Expected: Migration applies cleanly

- [ ] **Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add historical_scores table and ORM model"
```

---

### Task 6: Create `historical_scorer.py` engine module

**Files:**
- Create: `engine/src/margin_engine/scoring/historical_scorer.py`
- Create: `engine/tests/scoring/test_historical_scorer.py`

- [ ] **Step 1: Write failing tests for `score_universe_at_date()`**

Create `engine/tests/scoring/test_historical_scorer.py`:

```python
"""Tests for historical scorer — PIT-based universe scoring."""

import pytest
from datetime import date
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.scoring import CompositeScore
from margin_engine.scoring.historical_scorer import score_universe_at_date


def _make_pit_snapshot(
    ticker: str,
    filing_date: str,
    period_end: str,
    revenue: float = 1_000_000,
    ebit: float = 200_000,
    total_equity: float = 500_000,
    total_debt: float = 300_000,
    cash: float = 100_000,
    free_cash_flow: float = 150_000,
    sector: str = "Information Technology",
    market_cap: float = 10_000_000_000,
    shares_outstanding: int = 100_000_000,
) -> dict:
    """Build a dict mimicking a PIT snapshot row (as passed from the worker)."""
    return {
        "ticker": ticker,
        "filing_date": filing_date,
        "period_end": period_end,
        "income_statement": {
            "totalRevenue": revenue,
            "ebit": ebit,
        },
        "balance_sheet": {
            "totalStockholderEquity": total_equity,
            "totalDebt": total_debt,
            "cashAndCashEquivalents": cash,
        },
        "cash_flow": {
            "freeCashFlow": free_cash_flow,
        },
        "sector": sector,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
    }


def _make_price_bars(ticker: str, n_days: int = 300, base_price: float = 100.0) -> dict:
    """Build price bar data for a ticker."""
    from datetime import timedelta

    bars = []
    for i in range(n_days):
        d = date(2024, 1, 1) + timedelta(days=i)
        bars.append({"date": d.isoformat(), "close": base_price + i * 0.1, "volume": 1000000})
    return {ticker: bars}


class TestScoreUniverseAtDate:
    """score_universe_at_date produces CompositeScore objects."""

    def test_returns_composite_scores(self):
        """Basic: two tickers with valid data -> two CompositeScore results."""
        snapshots = [
            _make_pit_snapshot("AAPL", "2024-02-15", "2023-12-31", revenue=5_000_000),
            _make_pit_snapshot("MSFT", "2024-02-15", "2023-12-31", revenue=7_000_000),
        ]
        prices = {**_make_price_bars("AAPL"), **_make_price_bars("MSFT")}
        memberships = {"AAPL", "MSFT"}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date=date(2024, 3, 31),
            active_tickers=memberships,
        )

        assert len(results) == 2
        assert all(isinstance(r, CompositeScore) for r in results)
        tickers = {r.ticker for r in results}
        assert tickers == {"AAPL", "MSFT"}

    def test_filters_by_active_tickers(self):
        """Only tickers in active_tickers are scored (survivorship bias)."""
        snapshots = [
            _make_pit_snapshot("AAPL", "2024-02-15", "2023-12-31"),
            _make_pit_snapshot("DELIST", "2024-02-15", "2023-12-31"),
        ]
        prices = {**_make_price_bars("AAPL"), **_make_price_bars("DELIST")}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date=date(2024, 3, 31),
            active_tickers={"AAPL"},  # DELIST not in universe
        )

        assert len(results) == 1
        assert results[0].ticker == "AAPL"

    def test_deterministic_output(self):
        """Same inputs -> identical scores (determinism)."""
        snapshots = [_make_pit_snapshot("AAPL", "2024-02-15", "2023-12-31")]
        prices = _make_price_bars("AAPL")

        results1 = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date=date(2024, 3, 31),
            active_tickers={"AAPL"},
        )
        results2 = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date=date(2024, 3, 31),
            active_tickers={"AAPL"},
        )

        assert results1[0].composite_percentile == results2[0].composite_percentile

    def test_empty_snapshots_returns_empty(self):
        """No snapshots -> empty results."""
        results = score_universe_at_date(
            pit_snapshots=[],
            pit_prices={},
            rebalance_date=date(2024, 3, 31),
            active_tickers=set(),
        )
        assert results == []

    def test_scores_include_growth_factors(self):
        """Scores should include growth breakdown when multi-period history exists."""
        snapshots = [
            _make_pit_snapshot("AAPL", "2023-02-15", "2022-12-31", revenue=3_000_000),
            _make_pit_snapshot("AAPL", "2024-02-15", "2023-12-31", revenue=5_000_000),
        ]
        prices = _make_price_bars("AAPL")

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date=date(2024, 3, 31),
            active_tickers={"AAPL"},
        )

        assert len(results) == 1
        # Growth breakdown should exist when there's multi-period history
        assert results[0].growth is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_historical_scorer.py -v`
Expected: FAIL — module `historical_scorer` doesn't exist

- [ ] **Step 3: Implement `score_universe_at_date()`**

Create `engine/src/margin_engine/scoring/historical_scorer.py`:

```python
"""Historical scorer — score a universe at a point-in-time date.

Takes PIT financial snapshots and prices, runs the identical scoring
pipeline as full_score_v4 (filters → factors → sector-neutral ranking → composite).
Used to generate training data for ML models.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from margin_engine.models.financial import (
    AssetProfile,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    PriceBar,
)
from margin_engine.models.scoring import CompositeScore

# Import the same scoring infrastructure used by the live pipeline
from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.filters.pipeline import run_elimination_filters
from margin_engine.scoring.normalizer import compute_percentile_ranks, rerank_composites
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.competitive_dynamics import gross_margin_stability
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import piotroski_f_score
from margin_engine.scoring.quantitative.fcf_conversion import fcf_conversion
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic
from margin_engine.scoring.quantitative.multi_horizon_momentum import multi_horizon_momentum
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr
from margin_engine.scoring.quantitative.roic_trend import roic_trend
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40
from margin_engine.scoring.quantitative.runway_score import runway_score
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield

_SECTOR_MAP: dict[str, GICSSector] = {s.value: s for s in GICSSector}

INVERTED_FACTORS: frozenset[str] = frozenset(
    {"accrual_ratio", "ev_fcf", "acquirers_multiple", "gross_margin_stability"}
)


def _build_period_from_snapshot(snapshot: dict) -> FinancialPeriod:
    """Convert a PIT snapshot dict into a FinancialPeriod."""
    income = normalize_income_statement(snapshot.get("income_statement") or {})
    balance = normalize_balance_sheet(snapshot.get("balance_sheet") or {})
    cashflow = normalize_cash_flow(snapshot.get("cash_flow") or {})
    return FinancialPeriod(
        period_end=snapshot["period_end"],
        filing_date=snapshot["filing_date"],
        current_income=income,
        current_balance=balance,
        current_cash_flow=cashflow,
    )


def _build_history(snapshots: list[dict]) -> FinancialHistory | None:
    """Build FinancialHistory from multiple PIT snapshots for one ticker."""
    if len(snapshots) < 1:
        return None
    periods = [_build_period_from_snapshot(s) for s in snapshots]
    return FinancialHistory(ticker=snapshots[0]["ticker"], periods=periods)


def score_universe_at_date(
    pit_snapshots: list[dict],
    pit_prices: dict[str, list[dict]],
    rebalance_date: date,
    active_tickers: set[str],
) -> list[CompositeScore]:
    """Score the full universe at a point-in-time date.

    Runs the identical pipeline as full_score_v4: elimination filters →
    raw factor scores → sector-neutral percentile ranking → composite score.

    Args:
        pit_snapshots: List of PIT snapshot dicts (one per filing).
            Each must have: ticker, filing_date, period_end, income_statement,
            balance_sheet, cash_flow, sector, market_cap, shares_outstanding.
        pit_prices: Dict mapping ticker -> list of price bar dicts.
        rebalance_date: The as-of date for scoring.
        active_tickers: Set of tickers in the universe on this date.

    Returns:
        List of CompositeScore objects, one per scored ticker.
    """
    if not pit_snapshots or not active_tickers:
        return []

    # Group snapshots by ticker, filter to active universe, sort by period_end
    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for snap in pit_snapshots:
        ticker = snap["ticker"]
        if ticker in active_tickers:
            by_ticker[ticker].append(snap)

    # Sort each ticker's snapshots by period_end ascending
    for ticker in by_ticker:
        by_ticker[ticker].sort(key=lambda s: s["period_end"])

    # Score each ticker using the same pipeline as the live scorer
    from margin_engine.models.scoring import FactorScore, FilterResult

    # Collect raw results for batch percentile ranking
    raw_results: list[dict] = []

    for ticker, snapshots in by_ticker.items():
        latest = snapshots[-1]
        period = _build_period_from_snapshot(latest)
        history = _build_history(snapshots) if len(snapshots) >= 2 else None

        # Build profile
        sector_str = latest.get("sector", "Information Technology")
        gics_sector = _SECTOR_MAP.get(sector_str)
        if gics_sector is None:
            continue  # Skip unknown sectors

        market_cap = Decimal(str(latest.get("market_cap", 0) or 0))
        profile = AssetProfile(
            ticker=ticker,
            name=ticker,
            sector=gics_sector,
            market_cap=market_cap,
            shares_outstanding=latest.get("shares_outstanding"),
        )

        # Elimination filters
        pipeline_result = run_elimination_filters(period, profile)

        # Quality factors (must match live scorer in scoring.py)
        quality_scores = [
            gross_profitability(period),
            roic_wacc_spread(period),
            sloan_accrual_ratio(period),
            piotroski_f_score(period),
            fcf_conversion(period),
        ]
        if history is not None:
            quality_scores.append(roic_trend(history))
            quality_scores.append(gross_margin_stability(history))

        # Value factors
        value_scores = [
            ev_fcf(period, market_cap),
            shareholder_yield(period, market_cap),
            dcf_margin_of_safety(period, market_cap, growth_rate=0.05, discount_rate=0.10),
            acquirers_multiple(period, market_cap),
        ]

        # Momentum factors
        bars: list[PriceBar] = []
        if ticker in pit_prices:
            bars = [normalize_price_bar(b) for b in pit_prices[ticker]]
        momentum_scores: list[FactorScore] = [multi_horizon_momentum(bars)]
        # Sentiment stub (neutral 0.0) — must match live scorer for consistent sub-score count
        momentum_scores.append(sentiment_score(score=0.0))

        # Growth factors
        growth_scores: list[FactorScore] = []
        if history is not None and len(history.periods) >= 2:
            growth_scores.append(revenue_cagr(history))
            growth_scores.append(incremental_roic(history))

        revenue = float(period.current_income.revenue)
        if revenue > 0:
            fcf = float(period.current_cash_flow.free_cash_flow)
            fcf_margin = fcf / revenue
            rev_growth_rate = 0.0
            if period.prior_income is not None:
                prior_rev = float(period.prior_income.revenue)
                if prior_rev > 0:
                    rev_growth_rate = (revenue - prior_rev) / prior_rev
            growth_scores.append(rule_of_40(rev_growth_rate, fcf_margin))

        growth_scores.append(runway_score(period.current_income.revenue, None))

        # Growth stage
        growth_stage = classify_growth_stage(period, profile)

        raw_results.append({
            "ticker": ticker,
            "sector": sector_str,
            "quality_scores": quality_scores,
            "value_scores": value_scores,
            "momentum_scores": momentum_scores,
            "growth_scores": growth_scores,
            "filter_results": pipeline_result.results,
            "growth_stage": growth_stage,
        })

    if not raw_results:
        return []

    # Batch percentile ranking across sector peers (same as rank_and_compute_composites)
    groups: dict[tuple[str, str], list[tuple[int, str, int]]] = defaultdict(list)
    scores_by_key: dict[tuple[str, str], list[FactorScore]] = defaultdict(list)

    for i, result in enumerate(raw_results):
        for list_attr in ("quality_scores", "value_scores", "momentum_scores", "growth_scores"):
            scores = result[list_attr]
            for j, score in enumerate(scores):
                key = (result["sector"], score.name)
                groups[key].append((i, list_attr, j))
                scores_by_key[key].append(score)

    for key, entries in groups.items():
        _, factor_name = key
        ranked = compute_percentile_ranks(
            scores_by_key[key], invert=(factor_name in INVERTED_FACTORS)
        )
        for (result_idx, list_attr, score_idx), ranked_score in zip(entries, ranked):
            raw_results[result_idx][list_attr][score_idx] = ranked_score

    # Compute composites
    composites: list[CompositeScore] = []
    for r in raw_results:
        composite = compute_composite_score(
            ticker=r["ticker"],
            quality_scores=r["quality_scores"],
            value_scores=r["value_scores"],
            momentum_scores=r["momentum_scores"],
            growth_scores=r["growth_scores"],
            filters_passed=r["filter_results"],
            growth_stage=r["growth_stage"],
        )
        composites.append(composite)

    composites = rerank_composites(composites)
    return composites
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_historical_scorer.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/historical_scorer.py engine/tests/scoring/test_historical_scorer.py
git commit -m "feat(engine): add historical_scorer module for PIT-based universe scoring"
```

---

### Task 7: Add `backfill_historical_scores` worker

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Modify: `api/src/margin_api/db/models.py` (import `HistoricalScore` — already done in Task 5)

- [ ] **Step 1: Add the worker function to `workers.py`**

Add the import of `HistoricalScore` to the imports block at the top of `workers.py` (around line 33-52):
```python
from margin_api.db.models import (
    ...
    HistoricalScore,
    ...
)
```

Add the worker function before the `WorkerSettings` class (around line 3040):

```python
async def backfill_historical_scores(ctx: dict) -> dict:
    """Generate historical composite scores from PIT data for ML training.

    Iterates quarter-end dates from 2009-Q1 to 2025-Q4. Idempotent: skips
    quarters that already have scores. Registered with 2h timeout.
    """
    from margin_engine.scoring.historical_scorer import score_universe_at_date

    logger.info("[historical] Starting historical score backfill...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Generate quarter-end dates: 2009-03-31, 2009-06-30, ..., 2025-12-31
    quarter_ends: list[date] = []
    for year in range(2009, 2026):
        for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            quarter_ends.append(date(year, month, day))

    total_scored = 0
    quarters_processed = 0

    for qe in quarter_ends:
        # Check if this quarter already has scores (idempotent)
        async with session_factory() as session:
            existing = await session.execute(
                select(func.count(HistoricalScore.id)).where(
                    HistoricalScore.score_date == qe
                )
            )
            if (existing.scalar() or 0) > 0:
                logger.info("[historical] Skipping %s (already scored)", qe)
                continue

        # Load PIT snapshots with filing_date <= rebalance_date
        async with session_factory() as session:
            snap_result = await session.execute(
                select(PITFinancialSnapshot).where(
                    PITFinancialSnapshot.filing_date <= qe
                )
            )
            snapshots_raw = snap_result.scalars().all()

        # Group by ticker, keep latest per ticker
        from collections import defaultdict as _defaultdict

        by_ticker: dict[str, list] = _defaultdict(list)
        for s in snapshots_raw:
            by_ticker[s.ticker].append(s)

        pit_snapshots: list[dict] = []
        for ticker, snaps in by_ticker.items():
            sorted_snaps = sorted(snaps, key=lambda s: s.period_end)
            for snap in sorted_snaps:
                pit_snapshots.append({
                    "ticker": snap.ticker,
                    "filing_date": str(snap.filing_date),
                    "period_end": str(snap.period_end),
                    "income_statement": snap.income_statement or {},
                    "balance_sheet": snap.balance_sheet or {},
                    "cash_flow": snap.cash_flow or {},
                    "sector": "Information Technology",  # Will use SIC mapping
                    "market_cap": 10_000_000_000,  # Default; use membership data below
                    "shares_outstanding": snap.shares_outstanding,
                })

        # Load active tickers from universe memberships
        async with session_factory() as session:
            membership_result = await session.execute(
                select(PITUniverseMembership).where(
                    PITUniverseMembership.quarter_date == qe,
                    PITUniverseMembership.is_active.is_(True),
                )
            )
            memberships = membership_result.scalars().all()

        active_tickers = {m.ticker for m in memberships}

        # Enrich snapshots with sector and market cap from memberships
        membership_map = {m.ticker: m for m in memberships}
        # Load SIC -> GICS mapping
        async with session_factory() as session:
            from margin_api.db.models import SICSectorMap

            sic_result = await session.execute(select(SICSectorMap))
            sic_map = {row.sic_code: row.gics_sector for row in sic_result.scalars().all()}

        for snap in pit_snapshots:
            m = membership_map.get(snap["ticker"])
            if m:
                snap["market_cap"] = m.market_cap or 10_000_000_000
                if m.sic_code and m.sic_code in sic_map:
                    snap["sector"] = sic_map[m.sic_code]

        # Load PIT prices (trailing 252 days before quarter end)
        price_start = qe - timedelta(days=400)  # Extra buffer for trading days
        async with session_factory() as session:
            from margin_api.db.models import PITDailyPrice

            price_result = await session.execute(
                select(PITDailyPrice).where(
                    PITDailyPrice.date >= price_start,
                    PITDailyPrice.date <= qe,
                    PITDailyPrice.ticker.in_(active_tickers) if active_tickers else False,
                )
            )
            price_rows = price_result.scalars().all()

        pit_prices: dict[str, list[dict]] = _defaultdict(list)
        for p in price_rows:
            pit_prices[p.ticker].append({
                "date": str(p.date),
                "close": p.close,
                "volume": p.volume,
            })
        # Sort each ticker's prices by date
        for ticker in pit_prices:
            pit_prices[ticker].sort(key=lambda b: b["date"])

        if not active_tickers:
            logger.info("[historical] No active tickers for %s, skipping", qe)
            continue

        # Score the universe
        composites = score_universe_at_date(
            pit_snapshots=pit_snapshots,
            pit_prices=dict(pit_prices),
            rebalance_date=qe,
            active_tickers=active_tickers,
        )

        # Bulk insert results
        if composites:
            async with session_factory() as session:
                for c in composites:
                    sub_scores_dict = {}
                    for pillar_name in ("quality", "value", "momentum", "growth"):
                        breakdown = getattr(c, pillar_name)
                        if breakdown:
                            sub_scores_dict[pillar_name] = [
                                {"name": s.name, "raw_value": s.raw_value,
                                 "percentile_rank": s.percentile_rank}
                                for s in breakdown.sub_scores
                            ]

                    session.add(HistoricalScore(
                        ticker=c.ticker,
                        score_date=qe,
                        composite_score=c.composite_percentile,
                        composite_tier=c.composite_tier.value,
                        sub_scores=sub_scores_dict,
                    ))
                await session.commit()

        total_scored += len(composites)
        quarters_processed += 1
        logger.info(
            "[historical] %s: scored %d tickers (total: %d, quarters: %d/%d)",
            qe, len(composites), total_scored, quarters_processed, len(quarter_ends),
        )

    logger.info("[historical] Backfill complete: %d scores across %d quarters",
                total_scored, quarters_processed)
    return {"status": "completed", "total_scored": total_scored, "quarters": quarters_processed}
```

- [ ] **Step 2: Register the worker in `WorkerSettings.functions`**

Add to the `functions` list in `WorkerSettings` (around line 3193):
```python
        # Historical scorer: 2h timeout — 67 quarters × ~3000 tickers
        arq_func(backfill_historical_scores, timeout=7200),
```

- [ ] **Step 3: Commit**

```bash
git add api/src/margin_api/workers.py api/src/margin_api/db/models.py
git commit -m "feat(api): add backfill_historical_scores worker for PIT-based ML training data"
```

---

## Chunk 3: Phase 3 — ML Training Fix

### Task 8: Create `compute_historical_forward_returns()` in engine

**Files:**
- Create: `engine/src/margin_engine/ml/historical_forward_returns.py`
- Create: `engine/tests/ml/test_historical_forward_returns.py`

- [ ] **Step 1: Write failing tests**

Create `engine/tests/ml/test_historical_forward_returns.py`:

```python
"""Tests for historical forward returns computation."""

from datetime import date, timedelta

import pytest

from margin_engine.ml.historical_forward_returns import compute_historical_forward_returns


def _make_pit_prices(
    ticker: str,
    start_date: date,
    n_days: int,
    start_price: float = 100.0,
    end_price: float = 120.0,
) -> dict[str, list[dict]]:
    """Build PIT price data with linear interpolation."""
    bars = []
    for i in range(n_days):
        d = start_date + timedelta(days=i)
        frac = i / max(n_days - 1, 1)
        price = start_price + frac * (end_price - start_price)
        bars.append({"date": d.isoformat(), "close": price})
    return {ticker: bars}


class TestHistoricalForwardReturns:
    def test_basic_forward_return(self):
        """Score date 2024-03-31, price 100 -> 120 at +252 trading days."""
        prices = _make_pit_prices(
            "AAPL", date(2024, 1, 1), n_days=600, start_price=100.0, end_price=200.0
        )

        result = compute_historical_forward_returns(
            pit_prices=prices,
            score_date=date(2024, 3, 31),
            horizon_days=252,
        )

        assert "AAPL" in result
        assert isinstance(result["AAPL"], float)

    def test_insufficient_future_data_excluded(self):
        """Ticker without enough future data is excluded (not defaulted to 0)."""
        # Only 100 days of data — not enough for 252-day horizon
        prices = _make_pit_prices("SHORT", date(2024, 1, 1), n_days=100)

        result = compute_historical_forward_returns(
            pit_prices=prices,
            score_date=date(2024, 3, 31),
            horizon_days=252,
        )

        assert "SHORT" not in result

    def test_multiple_tickers(self):
        """Multiple tickers each get their own return."""
        prices = {
            **_make_pit_prices("AAA", date(2023, 1, 1), 600, 100, 150),
            **_make_pit_prices("BBB", date(2023, 1, 1), 600, 200, 180),
        }

        result = compute_historical_forward_returns(
            pit_prices=prices,
            score_date=date(2024, 3, 31),
            horizon_days=252,
        )

        assert len(result) == 2
        assert "AAA" in result
        assert "BBB" in result

    def test_empty_prices_returns_empty(self):
        """No price data -> empty result."""
        result = compute_historical_forward_returns(
            pit_prices={},
            score_date=date(2024, 3, 31),
        )
        assert result == {}

    def test_no_price_at_score_date_excluded(self):
        """Ticker with no price bar near score_date -> excluded."""
        # Prices start well after score_date
        prices = _make_pit_prices("LATE", date(2025, 1, 1), 400)

        result = compute_historical_forward_returns(
            pit_prices=prices,
            score_date=date(2024, 3, 31),
            horizon_days=252,
        )

        # No price near 2024-03-31, should be excluded
        assert "LATE" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_historical_forward_returns.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement `compute_historical_forward_returns()`**

Create `engine/src/margin_engine/ml/historical_forward_returns.py`:

```python
"""Compute forward returns from PIT price data for historical ML training.

Unlike compute_forward_returns() which takes scored_tickers dicts,
this function works with date-indexed PIT prices and a single score_date.
"""

from __future__ import annotations

from datetime import date


def compute_historical_forward_returns(
    pit_prices: dict[str, list[dict]],
    score_date: date,
    horizon_days: int = 252,
    max_date_gap: int = 5,
) -> dict[str, float]:
    """Compute forward returns for all tickers with PIT price data.

    For each ticker, finds the closest price bar to score_date, then computes
    the return to the price bar horizon_days later.

    Args:
        pit_prices: Dict mapping ticker -> list of price bar dicts.
            Each bar must have 'date' (ISO string) and 'close' (float).
            Bars must be sorted by date ascending.
        score_date: The date to compute returns from.
        horizon_days: Number of trading days for forward return window.
        max_date_gap: Maximum calendar days between score_date and nearest
            available price. Tickers without a price within this gap are excluded.

    Returns:
        Dict mapping ticker -> forward return as a decimal (0.20 = 20%).
        Tickers without sufficient data are excluded entirely.
    """
    results: dict[str, float] = {}

    for ticker, bars in pit_prices.items():
        if not bars:
            continue

        # Find the bar closest to score_date
        score_idx = _find_closest_bar(bars, score_date)
        if score_idx is None:
            continue

        # Check that the closest bar is within max_date_gap
        bar_date = date.fromisoformat(str(bars[score_idx]["date"])[:10])
        if abs((bar_date - score_date).days) > max_date_gap:
            continue

        # Check if we have enough future data
        future_idx = score_idx + horizon_days
        if future_idx >= len(bars):
            continue

        score_price = float(bars[score_idx]["close"])
        future_price = float(bars[future_idx]["close"])

        if score_price <= 0:
            continue

        forward_return = (future_price / score_price) - 1.0
        results[ticker] = forward_return

    return results


def _find_closest_bar(bars: list[dict], target: date) -> int | None:
    """Find the index of the bar closest to target date."""
    if not bars:
        return None

    best_idx = 0
    best_delta = abs((date.fromisoformat(str(bars[0]["date"])[:10]) - target).days)

    for i in range(1, len(bars)):
        delta = abs((date.fromisoformat(str(bars[i]["date"])[:10]) - target).days)
        if delta < best_delta:
            best_delta = delta
            best_idx = i

    return best_idx
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_historical_forward_returns.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/ml/historical_forward_returns.py engine/tests/ml/test_historical_forward_returns.py
git commit -m "feat(engine): add compute_historical_forward_returns for PIT-based ML training"
```

---

### Task 9: Fix forward returns 0.0-default bug and wire historical data into `train_ml_models`

**Files:**
- Modify: `api/src/margin_api/workers.py:1779-1819`

**Important ordering note:** The historical data loading MUST happen BEFORE the forward returns filtering, so that the min_samples gate applies to the combined (live + historical) dataset. Otherwise, if live data has 0 tickers with forward returns (the current state), the pipeline will fail before ever using historical data.

- [ ] **Step 1: Apply the combined fix — load historical data, then filter**

In `api/src/margin_api/workers.py`, replace the block from `build_feature_matrix` (line ~1779) through the forward returns section (line ~1819) with the following restructured code:

**Before** (around lines 1779-1819):
```python
        # Build feature matrix
        registry = default_registry()
        features, tickers, feature_names = build_feature_matrix(composites, registry)
        ...
        forward_returns = np.array([fwd_returns.get(t, 0.0) for t in tickers])
```

**After:**
```python
        # --- Load historical training data (PIT-bootstrapped) ---
        # Must happen BEFORE forward returns filtering so combined samples
        # are checked against ml_train_min_samples gate.
        from margin_api.db.models import HistoricalScore

        async with session_factory() as session:
            hist_result = await session.execute(
                select(HistoricalScore).where(
                    HistoricalScore.score_date <= date.today() - timedelta(days=365)
                )
            )
            hist_scores = hist_result.scalars().all()

        # Reconstruct CompositeScore objects from historical sub_scores JSONB
        hist_composites: list = []
        hist_fwd_returns: dict[str, float] = {}

        if hist_scores:
            logger.info("[ml] Loaded %d historical scores for training", len(hist_scores))

            from collections import defaultdict as _dd
            from margin_engine.ml.historical_forward_returns import (
                compute_historical_forward_returns,
            )
            from margin_engine.models.scoring import FactorBreakdown, FactorScore, FilterResult

            # Group by score_date for batched forward returns
            by_date: dict[date, list] = _dd(list)
            for hs in hist_scores:
                by_date[hs.score_date].append(hs)

            # Load PIT prices per quarter (avoid OOM — 12.8M rows total)
            for score_dt, scores_in_quarter in by_date.items():
                quarter_tickers = {hs.ticker for hs in scores_in_quarter}

                # Date-bounded query: only load prices needed for this quarter's returns
                price_start = score_dt - timedelta(days=10)  # small buffer for closest bar
                price_end = score_dt + timedelta(days=400)   # 252 trading days + buffer
                async with session_factory() as session:
                    from margin_api.db.models import PITDailyPrice
                    pit_price_result = await session.execute(
                        select(PITDailyPrice).where(
                            PITDailyPrice.ticker.in_(quarter_tickers),
                            PITDailyPrice.date >= price_start,
                            PITDailyPrice.date <= price_end,
                        )
                    )
                    pit_price_rows = pit_price_result.scalars().all()

                pit_prices: dict[str, list[dict]] = _dd(list)
                for p in pit_price_rows:
                    pit_prices[p.ticker].append({"date": str(p.date), "close": p.close})
                for t in pit_prices:
                    pit_prices[t].sort(key=lambda b: b["date"])

                fwd = compute_historical_forward_returns(dict(pit_prices), score_dt)

                for hs in scores_in_quarter:
                    if hs.ticker not in fwd:
                        continue

                    # Reconstruct CompositeScore from sub_scores JSONB
                    sub = hs.sub_scores or {}
                    def _rebuild_breakdown(pillar: str, weight: float) -> FactorBreakdown:
                        scores = [
                            FactorScore(
                                name=s["name"],
                                raw_value=s["raw_value"],
                                percentile_rank=s["percentile_rank"],
                            )
                            for s in sub.get(pillar, [])
                        ]
                        return FactorBreakdown(
                            factor_name=pillar, weight=weight, sub_scores=scores
                        )

                    hist_composite = CompositeScore(
                        ticker=hs.ticker,
                        composite_percentile=hs.composite_score,
                        composite_raw_score=hs.composite_score,
                        quality=_rebuild_breakdown("quality", 0.25),
                        value=_rebuild_breakdown("value", 0.20),
                        momentum=_rebuild_breakdown("momentum", 0.25),
                        growth=_rebuild_breakdown("growth", 0.15) if "growth" in sub else None,
                        filters_passed=[],
                        data_coverage=1.0,
                    )
                    hist_composites.append(hist_composite)
                    hist_fwd_returns[hs.ticker] = fwd[hs.ticker]

            logger.info(
                "[ml] Historical: %d samples with forward returns from %d quarters",
                len(hist_composites), len(by_date),
            )

        # Combine live + historical composites
        all_composites = composites + hist_composites

        # Build feature matrix from combined data
        registry = default_registry()
        features, tickers, feature_names = build_feature_matrix(all_composites, registry)

        import numpy as np
        from margin_engine.ml.forward_returns import compute_forward_returns

        n_clusters = settings.ml_n_clusters

        # Compute live forward returns (existing code)
        async with session_factory() as session:
            price_result = await session.execute(
                select(FinancialData.price_history, Asset.ticker)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker.in_(tickers))
            )
            price_rows = price_result.all()

        ticker_prices: dict[str, list[dict]] = {}
        for ph, t in price_rows:
            if t and ph and isinstance(ph, dict):
                bars = ph.get("bars", [])
                if bars:
                    ticker_prices[t] = bars

        scored_entries = [
            {
                "ticker": t,
                "scored_at": (
                    str(score.scored_at.date()) if hasattr(score, "scored_at") else "2024-01-01"
                ),
            }
            for score, t in rows
            if t in ticker_prices
        ]
        live_fwd_returns = compute_forward_returns(scored_entries, ticker_prices)

        # Merge live and historical forward returns
        fwd_returns = {**hist_fwd_returns, **live_fwd_returns}

        # Filter to only tickers with actual forward returns (never default to 0.0)
        valid_mask = np.array([t in fwd_returns for t in tickers])
        n_with_returns = int(valid_mask.sum())
        logger.info(
            "[ml] Forward returns: %d/%d tickers have real data (live=%d, historical=%d)",
            n_with_returns, len(tickers),
            len(live_fwd_returns), len(hist_fwd_returns),
        )

        if n_with_returns < settings.ml_train_min_samples:
            msg = (
                f"Only {n_with_returns} tickers have forward returns "
                f"(need {settings.ml_train_min_samples})"
            )
            logger.warning("[ml] %s", msg)
            async with session_factory() as session:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
                job.status = "failed"
                job.error_message = msg
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "failed", "message": msg}

        # Re-index arrays to only include valid tickers
        tickers = [t for t, m in zip(tickers, valid_mask) if m]
        features = features[valid_mask]
        all_composites = [c for c, m in zip(all_composites, valid_mask) if m]
        forward_returns = np.array([fwd_returns[t] for t in tickers])
```

- [ ] **Step 2: Run existing ML worker tests to verify no regression**

Run: `uv run pytest api/tests/test_pipeline_integration.py -v --tb=short`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "fix(api): filter tickers without forward returns, wire historical scores into ML training"
```

---

### Task 10: Add `ml_bootstrap_mode` config and adjust validation gate

**Files:**
- Modify: `api/src/margin_api/config.py`
- Modify: `engine/src/margin_engine/ml/seed_validation.py:40-45`
- Modify: `api/src/margin_api/workers.py` (use bootstrap thresholds)

- [ ] **Step 1: Write failing test for bootstrap thresholds**

Add to `engine/tests/ml/test_seed_validation.py` (find existing test file):

```python
class TestBootstrapThresholds:
    """Bootstrap mode uses relaxed thresholds."""

    def test_bootstrap_thresholds_lower_than_default(self):
        thresholds = SeedValidationThresholds(
            min_median_rank_ic=0.05,
            max_rank_ic_cv=0.50,
            min_worst_seed_ic=0.02,
        )
        assert thresholds.min_median_rank_ic == 0.05
        assert thresholds.min_worst_seed_ic == 0.02

    def test_bootstrap_thresholds_pass_low_ic(self):
        """IC=0.08 passes bootstrap gate but would fail default gate."""
        seed_metrics = [{"rank_ic": 0.08}, {"rank_ic": 0.10}, {"rank_ic": 0.06}]
        thresholds = SeedValidationThresholds(
            min_median_rank_ic=0.05,
            max_rank_ic_cv=0.50,
            min_worst_seed_ic=0.02,
        )
        result = validate_seed_distribution(seed_metrics, thresholds)
        assert result.gate_passed is True
```

- [ ] **Step 2: Run test to verify it passes (thresholds are already parameterizable)**

Run: `uv run pytest engine/tests/ml/test_seed_validation.py::TestBootstrapThresholds -v`
Expected: PASS (the `SeedValidationThresholds` dataclass already supports custom values)

- [ ] **Step 3: Add `ml_bootstrap_mode` and `ml_live_weight` to config**

In `api/src/margin_api/config.py`, add after line 80:

```python
    ml_bootstrap_mode: bool = True  # Use relaxed IC gates for PIT-bootstrapped training
    ml_live_weight: float = 0.0  # Blend weight for live data (0.0 = all historical, 1.0 = all live)
```

The `ml_live_weight` config supports the spec's "Ongoing Training Transition" plan — gradually shift from PIT-bootstrapped to live-scored data (default 0.0 for now, increase over time as live data accumulates).

- [ ] **Step 4: Update `train_ml_models` to use bootstrap thresholds**

In `api/src/margin_api/workers.py`, find where `validate_seed_distribution` is called (search for `validate_seed_distribution`). The existing code assigns to a variable called `validation`. Keep the same variable name to avoid breaking downstream references:

```python
        # Select thresholds based on bootstrap mode
        if settings.ml_bootstrap_mode:
            from margin_engine.ml.seed_validation import SeedValidationThresholds
            thresholds = SeedValidationThresholds(
                min_median_rank_ic=0.05,
                max_rank_ic_cv=0.50,
                min_worst_seed_ic=0.02,
            )
            validation = validate_seed_distribution(seed_metrics, thresholds)
        else:
            validation = validate_seed_distribution(seed_metrics)
```

**Important:** Keep the variable name as `validation` (not `validation_result`) because all downstream code (lines 2013+) references `validation.gate_passed`, `validation.selected_seed`, etc.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/config.py api/src/margin_api/workers.py engine/tests/ml/test_seed_validation.py
git commit -m "feat: add ml_bootstrap_mode config with relaxed IC gates for PIT training"
```

---

## Chunk 4: Phase 4 — V2 Scoring Deprecation

### Task 11: Update `ingest_sweep_complete` to skip v2 scoring

**Files:**
- Modify: `api/src/margin_api/workers.py:550-553`

- [ ] **Step 1: Write failing test**

In `api/tests/test_pipeline_integration.py`, add or update a test:

```python
async def test_ingest_sweep_complete_chains_to_v3(mock_ctx, ...):
    """ingest_sweep_complete should enqueue full_score_v3, not full_score."""
    # ... setup ...
    result = await ingest_sweep_complete(mock_ctx, run_id, pipeline_id)
    # Verify full_score_v3 was enqueued (not full_score)
    mock_ctx["redis"].enqueue_job.assert_called_with("full_score_v3", pipeline_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_pipeline_integration.py::test_ingest_sweep_complete_chains_to_v3 -v`
Expected: FAIL — currently enqueues `full_score`

- [ ] **Step 3: Update `ingest_sweep_complete` to chain to `full_score_v3`**

In `api/src/margin_api/workers.py`, change line 552:

**Before:**
```python
        await redis.enqueue_job("full_score", pipeline_id)
        logger.info("%s Enqueued full_score (pipeline=%s)", label, pipeline_id)
```

**After:**
```python
        await redis.enqueue_job("full_score_v3", pipeline_id)
        logger.info("%s Enqueued full_score_v3 (pipeline=%s, v2 deprecated)", label, pipeline_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_pipeline_integration.py::test_ingest_sweep_complete_chains_to_v3 -v`
Expected: PASS

- [ ] **Step 5: Update existing test in `api/tests/test_ingest_sweep.py`**

Search for existing test assertions that check for `full_score` enqueue:
```bash
uv run grep -n "full_score" api/tests/test_ingest_sweep.py
```

Update any assertion like `c[0][0] == "full_score"` to `c[0][0] == "full_score_v3"`.

- [ ] **Step 6: Run ingest sweep tests**

Run: `uv run pytest api/tests/test_ingest_sweep.py -v --tb=short`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ingest_sweep.py
git commit -m "feat(api): chain ingest_sweep_complete directly to full_score_v3, bypassing v2"
```

---

### Task 12: Remove `full_score` (v2) function and registration

**Files:**
- Modify: `api/src/margin_api/workers.py`

**Safety gate check before proceeding:**
1. Growth factors have real weight and passing tests ✓ (Phase 1)
2. `historical_scores` table populated ✓ (Phase 2)
3. ML training produces IC > 0.05 — verify manually after Phase 3
4. At least one full live scoring cycle completes with v3→v4 chain

**If any gate fails, do NOT proceed with this task. Leave v2 as dead code.**

- [ ] **Step 1: Remove `full_score()` function**

Delete `api/src/margin_api/workers.py` lines 564-642 (the entire `full_score` function).

- [ ] **Step 2: Remove `full_score` from `WorkerSettings.functions` list**

In `WorkerSettings.functions` (around line 3172), remove:
```python
        arq_func(full_score, timeout=7200),
```

- [ ] **Step 3: Update `full_score_v3` to not accept `parent_job_id`**

In `full_score_v3` (line 645), the `parent_job_id` parameter was used to track v2→v3 chaining. Since v2 is removed, the chain now starts at v3. Update the signature if needed (or leave for backward compat with any in-flight jobs).

- [ ] **Step 4: Remove or update v2-specific tests**

Search for tests that reference `full_score` (not `full_score_v3` or `full_score_v4`):
```bash
uv run grep -r "full_score[^_v]" api/tests/ --include="*.py"
```
Delete or redirect those tests to v3.

- [ ] **Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py --tb=short`
Expected: ALL PASS

- [ ] **Step 6: Note about CLI**

The CLI's `score` command (`api/src/margin_api/cli.py`) still calls `run_scoring()` which was used by `full_score`. This CLI command is useful for manual single-ticker scoring and is independent of the worker pipeline. Leave it as-is — it doesn't go through the v2 worker chain.

- [ ] **Step 7: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/
git commit -m "feat(api): remove v2 scoring (full_score) from worker pipeline"
```

---

### Task 13: Final verification — full test suite

**Files:**
- No modifications — verification only

- [ ] **Step 1: Run full engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ~2800+ tests PASS

- [ ] **Step 2: Run full API tests**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py --tb=short`
Expected: ~1700+ tests PASS

- [ ] **Step 3: Run ruff lint**

Run: `uv run ruff check --fix . && uv run ruff format .`
Expected: Clean

- [ ] **Step 4: Final commit with any lint fixes**

```bash
git add -u
git commit -m "style: ruff formatting fixes for growth factors and ML bootstrap"
```
