# Tier A: Engine v2 — Finishing Touches

Technical design doc for 6 items remaining from the Tier 1 scoring overhaul.
(A6 and A7 merged into a single Optuna-based optimization pass.)

---

## A1: v3 Cascade Trajectory Detection

**Effort: Medium**

### Problem

`v3_cascade.py` hardcodes `conditional=False` when calling threshold functions and in
the returned `V3TrackResult`. The threshold functions in `v3_thresholds.py` already
handle `conditional=True` correctly (cap EXCEPTIONAL → HIGH). The conviction gates in
`conviction_gates.py` already have full trajectory detection logic. But the v3 cascades
never detect trajectory conditions — a turnaround company with low median ROIC but
rapidly improving fundamentals can reach EXCEPTIONAL conviction, which should be
capped at HIGH until the turnaround is proven.

### Current State

**Hardcoded conditional=False** in `v3_cascade.py`:
- Line 183: `assess_track_a_conviction(..., conditional=False)`
- Line 194: `V3TrackResult(..., conditional=False)`
- Line 358: `assess_track_b_conviction(..., conditional=False)`
- Line 368: `V3TrackResult(..., conditional=False)`

**Trajectory detection exists** in `conviction_gates.py`:
- `_check_trajectory_override(roic_quarterly, min_delta, min_periods)` — returns True
  if ROIC improved by `min_delta` for `min_periods` consecutive quarters
- `_roic_conditional_reinvestment_required(roic_median, config)` — returns -1.0 sentinel
  when ROIC < 8% (trajectory override needed)

**Threshold functions ready** in `v3_thresholds.py`:
- `assess_track_a_conviction(..., conditional=False)` — when True, caps EXCEPTIONAL → HIGH
- `assess_track_b_conviction(..., conditional=False)` — same behavior

**Config ready** in `v3_scoring_config.py`:
- `ConvictionGateConfig.trajectory_min_delta = 0.02` (200bps/Q)
- `ConvictionGateConfig.trajectory_min_periods = 3` (3 consecutive quarters)
- `ConvictionGateConfig.track_b_roic_hard_floor = 0.06`
- `ConvictionGateConfig.track_b_improving_min_delta = 0.02`
- `ConvictionGateConfig.track_b_improving_min_periods = 2`

### Design

Compute ROIC series inline from `inputs.history.periods` (the cascade already accesses
this data for the capital-light bypass). **Zero changes** to `TrackAInputs`,
`TrackBInputs`, `v3_pipeline.py`, or `v4_pipeline.py`.

**Rename `_check_trajectory_override` → `check_trajectory_override`** in
`conviction_gates.py` to make it a public API. Update the 2 existing internal call
sites (lines 133, 202) and import cleanly into `v3_cascade.py`.

**New helper** in `v3_cascade.py`:
```python
def _compute_roic_series(history: FinancialHistory) -> list[float]:
    """Compute ROIC per period. Reuses _nopat_and_ic from v3_intermediates."""
    roics: list[float] = []
    for p in history.periods:
        nopat_p, ic_p = _nopat_and_ic(p)
        if ic_p > 0:
            roics.append(nopat_p / ic_p)
    return roics
```

Replace inline ROIC loop in capital-light bypass (lines 96-103) with this helper.

**Track A trajectory detection** (after capital-light bypass):
- Compute `median_roic` from `_compute_roic_series()`
- If `median_roic < ConvictionGateConfig().roic_minimum` (0.08) and `len(roic_series) >= 2`:
  call `check_trajectory_override(roic_series, config.trajectory_min_delta, config.trajectory_min_periods)`
- If trajectory fires → `conditional = True`
- Pass `conditional` to `assess_track_a_conviction()` and into `V3TrackResult`

**Track B trajectory detection** (after quality_floor computation):
- Compute `roic_series` and `median_roic` from history
- If `median_roic` in `[track_b_roic_hard_floor, 0.08)` and `len(roic_series) >= 2`:
  call `check_trajectory_override()` with Track B thresholds (200bps for 2Q)
- Pass `conditional` to `assess_track_b_conviction()` and into `V3TrackResult`

**New imports** in `v3_cascade.py`:
```python
from margin_engine.config.v3_scoring_config import ConvictionGateConfig
from margin_engine.scoring.conviction_gates import check_trajectory_override
```

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/conviction_gates.py` | Rename `_check_trajectory_override` → `check_trajectory_override`, update 2 internal call sites |
| `engine/src/margin_engine/scoring/v3_cascade.py` | Add `_compute_roic_series` helper, trajectory detection in both tracks |

### Test Strategy

New file: `engine/tests/scoring/test_v3_cascade_trajectory.py`

Use `_period_with_roic(target_roic, period_end)` helper to build histories with specific
ROIC trajectories.

**Track A tests:**
- Low ROIC (median <8%) + improving 200bps/Q for 3Q → `conditional=True`
- Low ROIC + flat trajectory → `conditional=False`
- Normal ROIC (>=8%) → trajectory skipped, `conditional=False`
- Single period → guard prevents check, `conditional=False`

**Track B tests:**
- ROIC in [6%, 8%) + improving 200bps/Q for 2Q → `conditional=True`
- ROIC in [6%, 8%) + flat → `conditional=False`
- ROIC >= 8% → `conditional=False`
- ROIC < 6% (hard floor) → `conditional=False`

**Conviction cap test:**
- Build inputs that would reach EXCEPTIONAL without conditional → verify capped to HIGH

**Backward compatibility:** Default test financial data has ROIC ~21% → trajectory
detection never fires → existing tests unchanged.

---

## A2: Growth Stage Passthrough to Mediocrity Gate

**Effort: Small**

### Problem

`mediocrity_gate()` in `filters/mediocrity_gate.py:139` accepts a `growth_stage` parameter
that enables the TURNAROUND/HIGH_GROWTH trajectory override. But `run_elimination_filters()`
in `filters/pipeline.py:200-206` never passes it — `growth_stage` is always `None`.

The trajectory override at `mediocrity_gate.py:224` checks:
```python
if _check_growth_stage_override(roic_q, growth_stage, cfg):
    trajectory_reasons.append("growth_stage_override")
```
This never fires in production because `growth_stage` is `None`.

### Current State

- `GrowthStage` enum in `models/scoring.py:37-42`: HIGH_GROWTH, STEADY_GROWTH, MATURE,
  CYCLICAL, TURNAROUND
- Growth stage classifier at `scoring/classifier.py` — classifies via priority rules
  (Turnaround → High Growth → Cyclical → Mature → Steady Growth)
- `classify_growth_stage(period, profile, ...)` signature requires `FinancialPeriod` and
  `AssetProfile`, plus optional `revenue_cagr_3yr`, `fcf_yield`, `revenue_stddev_5yr`
- `MediocracyTrajectoryConfig.trajectory_stages = ["turnaround", "high_growth"]` — controls
  which stages qualify for the override

### Design

Thread `growth_stage` through the filter pipeline.

In `filters/pipeline.py`, `run_elimination_filters()`:
1. Import `classify_growth_stage` from `scoring/classifier.py`
2. Compute `growth_stage = classify_growth_stage(period, profile)` — both are already
   available as parameters to `run_elimination_filters()`
3. Pass `growth_stage=growth_stage` to `mediocrity_gate()`

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/filters/pipeline.py` | Import classifier, compute growth stage, pass to mediocrity_gate |

### Config/Data Dependencies

None — `classify_growth_stage()` uses `FinancialPeriod` and `AssetProfile` which are
already parameters of `run_elimination_filters()`.

### Test Strategy

- Add test to `test_mediocrity_trajectory.py`: construct TURNAROUND history that fails
  static gate but passes trajectory override → verify `conditional=True` when called
  through `run_elimination_filters()`
- Verify backward compat: existing pipeline tests still pass

---

## A3: Track B ROIC Boundary: > vs >= at 8%

**Effort: Tiny**

### Problem

`conviction_gates.py:198` uses strict `>` for the 8% boundary:
```python
if roic_median > _B_ROIC_FLOOR:  # _B_ROIC_FLOOR = 0.08
    pass  # unconditional pass
```

The design spec (`2026-03-18-engine-v2-tier1-scoring-design.md:207`) says "ROIC ≥ 8% → PASS".
Track A tiers use `>=` consistently (`roic_median >= config.roic_exceptional`, etc.).

A company at exactly 8.0% ROIC falls into the 6-8% "improving zone" instead of passing
unconditionally.

### Design

Change `>` to `>=` at `conviction_gates.py:198`:
```python
if roic_median >= _B_ROIC_FLOOR:
```

Update boundary test in `test_conviction_gates.py` to verify ROIC exactly 0.08 passes
unconditionally.

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/conviction_gates.py` | Line 198: `>` → `>=` |

### Test Strategy

- Update existing boundary test: `roic_median=0.08` should now pass (not enter improving zone)
- Add explicit boundary test: `roic_median=0.0799` enters improving zone, `0.08` passes

---

## A4: failed_filters Semantic Gap

**Effort: Small**

### Problem

`FilterResult` and `PipelineResult` have inconsistent semantics for conditional passes:

| Property | Conditional Result (passed=False, conditional=True) | Behavior |
|----------|------------------------------------------------------|----------|
| `FilterResult.verdict` | Returns `FAIL` | Only checks `passed` |
| `PipelineResult.passed` | Returns `True` | Checks `r.passed or r.conditional` |
| `PipelineResult.failed_filters` | **Includes** conditional result | Checks `not r.passed` |

A filter that is conditionally rescued is simultaneously "FAIL" (verdict) and "PASS"
(pipeline). Callers checking `failed_filters` see conditional results as failures.

### Current State

`models/scoring.py`:
```python
class FilterVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"

@property
def verdict(self) -> FilterVerdict:
    if self.insufficient_data:
        return FilterVerdict.INCONCLUSIVE
    return FilterVerdict.PASS if self.passed else FilterVerdict.FAIL
```

`filters/pipeline.py`:
```python
@property
def failed_filters(self) -> list[FilterResult]:
    return [r for r in self.results if not r.passed]
```

### Design

1. Add `CONDITIONAL_PASS` to `FilterVerdict`:
```python
class FilterVerdict(StrEnum):
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
```

2. Update `FilterResult.verdict`:
```python
@property
def verdict(self) -> FilterVerdict:
    if self.insufficient_data:
        return FilterVerdict.INCONCLUSIVE
    if self.passed:
        return FilterVerdict.PASS
    if self.conditional:
        return FilterVerdict.CONDITIONAL_PASS
    return FilterVerdict.FAIL
```

3. Add `conditional_filters` property to `PipelineResult`:
```python
@property
def conditional_filters(self) -> list[FilterResult]:
    return [r for r in self.results if not r.passed and r.conditional]
```

4. Update `failed_filters` to exclude conditional passes:
```python
@property
def failed_filters(self) -> list[FilterResult]:
    return [r for r in self.results if not r.passed and not r.conditional]
```

5. Update `replay_orchestrator.py` (lines ~200, ~459) to log `conditional_filters`
   separately. The orchestrator currently iterates `failed_filters` for diagnostics —
   after this change, conditional filters would silently disappear from logs without
   this update:
```python
for f in filter_result.failed_filters:
    ...  # log as failure (unchanged)
for f in filter_result.conditional_filters:
    ...  # log as conditional pass (new)
failed = [f.name for f in filter_result.failed_filters]
conditional = [f.name for f in filter_result.conditional_filters]
```

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/models/scoring.py` | Add CONDITIONAL_PASS, update verdict |
| `engine/src/margin_engine/scoring/filters/pipeline.py` | Add conditional_filters, update failed_filters |
| `engine/src/margin_engine/backtesting/replay_orchestrator.py` | Log conditional_filters separately (~lines 200, 459) |

### Test Strategy

- Test `FilterResult.verdict` returns CONDITIONAL_PASS for (passed=False, conditional=True)
- Test `PipelineResult.failed_filters` excludes conditional results
- Test `PipelineResult.conditional_filters` returns only conditional results
- Verify replay orchestrator logs conditional filters in backtest output

---

## A5: DRY Duplicated Pipeline Helpers + TickerDataBase Extraction

**Effort: Small–Medium**

### Problem

6 functions (~81 lines) are copy-pasted between `v3_pipeline.py` and `v4_pipeline.py`:

| Function | Lines | Purpose |
|----------|-------|---------|
| `_conditional_multiplier_for_ticker()` | 18 | Conditional score multiplier from filter results |
| `_compute_ev_ebit()` | 12 | EV/EBIT for valuation |
| `_compute_sector_median_ev_ebit()` | 17 | Sector median EV/EBIT |
| `_compute_peer_comparison_iv()` | 15 | Peer comparison intrinsic value |
| `_compute_owner_earnings_per_share()` | 10 | Owner earnings IV per share |
| `_compute_asset_floor_per_share()` | 9 | Asset floor IV per share |

Additionally, `TickerV3Data` and `TickerV4Data` are independent `BaseModel` subclasses
with 14 overlapping fields but no shared base class. The helpers can't be typed against
`TickerV3Data` because `TickerV4Data` doesn't inherit from it.

### Current State

**Shared fields (14):**
`ticker`, `history`, `latest_period`, `profile`, `current_price`,
`current_fcf_per_share`, `sustainable_growth_rate`, `buyback_yield`,
`insider_ownership_pct`, `sbc_pct`, `recent_acquisition_count`,
`sue_percentile`, `beta`, `momentum_percentile`, `dcf_iv`

**V4-only fields:**
`accumulation_percentile`, `style`, `revenue_growth_rate`, `fcf_margin`

**PIT adapter** (`backtesting/pit_adapter.py`) constructs `TickerV3Data` directly from
`PITSnapshot` — would naturally use the base class.

### Design

**Step 1: Extract `TickerDataBase`** to `engine/src/margin_engine/scoring/ticker_data.py`:
```python
class TickerDataBase(BaseModel):
    """Shared fields for all scoring pipeline ticker data."""
    ticker: str
    history: FinancialHistory
    latest_period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    current_fcf_per_share: float
    sustainable_growth_rate: float
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    sue_percentile: float = 0.0
    beta: float | None = None
    momentum_percentile: float = 50.0
    dcf_iv: float = 0.0
```

**Step 2: Rebase data classes:**
- `TickerV3Data(TickerDataBase)` — empty body (preserves existing type references)
- `TickerV4Data(TickerDataBase)` — adds `accumulation_percentile`, `style`,
  `revenue_growth_rate`, `fcf_margin`

**Step 3: Extract helpers** to `engine/src/margin_engine/scoring/pipeline_helpers.py`,
typed against `TickerDataBase`:
```python
from margin_engine.scoring.ticker_data import TickerDataBase

def conditional_multiplier_for_ticker(ticker: str, filter_results: ...) -> float: ...
def compute_ev_ebit(td: TickerDataBase) -> float | None: ...
def compute_sector_median_ev_ebit(tickers_data: list[TickerDataBase]) -> dict[GICSSector, float]: ...
def compute_peer_comparison_iv(td: TickerDataBase, sector_median: ...) -> float: ...
def compute_owner_earnings_per_share(td: TickerDataBase) -> float: ...
def compute_asset_floor_per_share(td: TickerDataBase) -> float: ...
```

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/ticker_data.py` | New — `TickerDataBase` |
| `engine/src/margin_engine/scoring/pipeline_helpers.py` | New — 6 extracted helpers typed against `TickerDataBase` |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | `TickerV3Data` extends `TickerDataBase`, remove 6 functions |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | `TickerV4Data` extends `TickerDataBase`, remove 6 functions |

### Test Strategy

- Existing pipeline tests (`test_v3_pipeline.py`, `test_v4_pipeline.py`) should pass
  unchanged — behavior identical, just different import paths
- Add unit tests for `TickerDataBase` construction and inheritance
- Verify PIT adapter still constructs valid `TickerV3Data` (now inherits `TickerDataBase`)

---

## A6: Weight & Balance Bonus Optimization via Optuna

**Effort: Medium–Large**

### Problem

All composite weights are equal (0.25 each) in `V3CompositeConfig`. No empirical basis
for whether factors should be weighted equally. Additionally, `balance_bonus_multiplier`
is 1.0 (no-op) — the balance bonus function is fully wired but dormant.

Both are parameters of the same scoring function and should be optimized jointly.

### Current State

`v3_scoring_config.py` — Track A weights:
```python
"moat_durability": 0.25, "compounding_power": 0.25,
"capital_allocation": 0.25, "growth_gap": 0.25
```

Balance bonus:
```python
balance_bonus_threshold: float = 0.40
balance_bonus_multiplier: float = 1.0  # No-op
```

`v3_composite.py` — weighted geometric mean + balance bonus:
```python
score = exp(sum(w_i * ln(max(f_i, floor))))
# Then: if all factors > threshold, score *= multiplier
```

Backtesting infrastructure: `backtesting/simulator.py` (WalkForwardSimulator),
`backtesting/metrics.py` (Sharpe, IC, Sortino), `backtesting/threshold_sensitivity.py`
(sensitivity analysis). PIT data available: 217K snapshots, 12.8M prices.

### Design

**Joint optimization** using Optuna (Bayesian optimization) instead of exhaustive grid
search. Converges in ~50-100 trials (~8-16 hours) vs ~333 hours for grid sweep.

**Hyperparameter space** (per track):

| Parameter | Range | Constraint |
|-----------|-------|------------|
| Factor weight 1 (e.g., `moat_durability`) | [0.10, 0.50] | 4 weights sum to 1.0 |
| Factor weight 2 | [0.10, 0.50] | " |
| Factor weight 3 | [0.10, 0.50] | " |
| Factor weight 4 | derived | 1.0 - sum(others), reject if outside [0.10, 0.50] |
| `balance_bonus_multiplier` | [1.0, 1.15] | — |
| `balance_bonus_threshold` | [0.25, 0.55] | — |

**Objective function**: Run `WalkForwardSimulator` with PIT data (2015–present),
optimize for Sharpe ratio. Secondary metrics (IC, Sortino) logged per trial but not
used in the objective.

**Per-track optimization**: Tracks A, B, C run independently — each has its own factor
names, weight set, and potentially different optimal balance bonus parameters.

**CLI command** `weight-tune`:
```
uv run python -m margin_api.cli weight-tune \
    --track A \
    --n-trials 100 \
    --metric sharpe
```

Options:
- `--track`: A, B, C, or ALL (runs each independently)
- `--n-trials`: Number of Optuna trials (default 100)
- `--metric`: Objective metric — `sharpe` (default), `ic`, `sortino`
- `--dry-run`: Report top 5 combos without updating config defaults

**Decision gate**: Only update `V3CompositeConfig` defaults if the optimized combo
improves Sharpe by >5% vs equal-weight baseline. Otherwise keep current defaults and
log the result.

**Golden-value test impact**: If weights or bonus multiplier change, existing
golden-value tests need threshold updates. The CLI should output a diff showing old
vs new expected values.

**New dependency**: `optuna` added to engine package.

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/tuning/__init__.py` | New package |
| `engine/src/margin_engine/tuning/weight_optimizer.py` | New — Optuna study setup, objective function, weight constraint |
| `api/src/margin_api/cli.py` | Add `weight-tune` command |
| `engine/src/margin_engine/config/v3_scoring_config.py` | Update defaults if decision gate passes |
| `engine/pyproject.toml` | Add `optuna` dependency |

### Config/Data Dependencies

- Requires PIT data (existing `pit_financial_snapshots`, `pit_daily_prices`)
- Backtest infrastructure already exists (`WalkForwardSimulator`, metrics)
- Optuna stores trial history in SQLite by default — enables resume after interruption

### Test Strategy

- Unit test: weight constraint enforcement (sum to 1.0, all within [0.10, 0.50])
- Unit test: objective function returns valid Sharpe for known inputs
- Unit test: balance bonus parameters included in trial suggestions
- Integration test: run 3-trial optimization on small test universe, verify output format
- Regression: if defaults change, update golden-value tests with new expected values
