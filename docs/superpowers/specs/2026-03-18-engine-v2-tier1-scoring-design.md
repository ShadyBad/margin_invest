# Engine v2 Tier 1: Scoring Formula, Conviction Gates, Mediocrity Trajectory

## Status: APPROVED (spec review passed — issues fixed)

## Problem Statement

The Margin Invest scoring engine structurally penalizes the exact profile of generational investment opportunities. Three specific flaws:

1. **Multiplicative zero-kill** (`v3_composite.py`): `moat × compounding × capalloc × growth_gap`. Any factor at 0.0 produces a composite of 0.0. Amazon (2001) with capalloc=0 scores 0.0. Balanced mediocrity (all 0.5) scores 0.0625 — higher than any unbalanced excellence.

2. **Rigid conviction gates** (`conviction_gates.py`): Track A requires reinvestment rate > 30% regardless of ROIC level. This eliminates Apple (ROIC ~40%, reinvestment ~12%), Visa (ROIC ~35%, reinvestment ~8%), and every capital-light compounder. Track B's "ROIC > 8% OR improving" is too permissive — any positive trajectory qualifies.

3. **Binary mediocrity gate** (`filters/mediocrity_gate.py`): Hard pass/fail with no trajectory awareness. ROIC > 8%, GM > 20%, 4/5yr positive FCF — all binary. Turnarounds at inflection points (FCF just turning positive, ROIC accelerating from 5% to 8%) are eliminated before scoring.

## Solution Overview

Three contained changes to core scoring math. No new data dependencies, no new infrastructure, no external APIs.

### Design Principles

- **Gate-local CONDITIONAL_PASS**: Each gate independently reports conditional status. Effects are scoped to the gate that issued them — not a global conviction cap.
- **Configurable everything**: All thresholds live in Pydantic config models with sensible defaults. Tunable via backtest without code changes.
- **Backward compatible signatures**: All modified functions accept an optional `config` parameter. Without it, new defaults apply (geometric mean with floor, ROIC-conditional gates, trajectory overrides).

---

## §1 — v3 Composite: Weighted Geometric Mean with Floor

### File: `engine/src/margin_engine/scoring/v3_composite.py` (modify in place)

### Current Behavior
```python
def compute_track_a_score(moat, compounding, capalloc, growth_gap):
    return moat * compounding * capalloc * growth_gap
```
Pure multiplication. Zero in any factor → zero composite.

### New Behavior
Weighted geometric mean with configurable floor:
```
score = exp(Σ weight_i × ln(max(factor_i, floor)))
```

- **Factor floor** (default 0.05): Each factor is floored before the geometric mean. A zero factor contributes `ln(0.05)` instead of `ln(0)` → `-∞`.
- **Composite floor** (default 0.01): Output never falls below this.
- **Per-track weights** (default 0.25 each): Configurable via `V3CompositeConfig`. Equal weights by default.
- **Balance bonus** (stubbed): Config fields `balance_bonus_threshold` and `balance_bonus_multiplier` present, defaulting to `1.0` (no-op). Ready to activate later.
- **Track B asymmetry cap**: `min(asymmetry_ratio, 20.0)` is preserved — applied before the geometric mean.

### Config Model

New file: `engine/src/margin_engine/scoring/v3_config.py`

```python
class TrackWeights(BaseModel):
    """Per-factor weights for a single track. Must sum to 1.0."""
    weights: dict[str, float]

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> Self:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self

class V3CompositeConfig(BaseModel):
    factor_floor: float = 0.05
    composite_floor: float = 0.01
    track_a_weights: TrackWeights = TrackWeights(weights={
        "moat_durability": 0.25,
        "compounding_power": 0.25,
        "capital_allocation": 0.25,
        "growth_gap": 0.25,
    })
    track_b_weights: TrackWeights = TrackWeights(weights={
        "asymmetry_ratio": 0.25,
        "catalyst_strength": 0.25,
        "quality_floor_factor": 0.25,
        "valuation_convergence": 0.25,
    })
    track_c_weights: TrackWeights = TrackWeights(weights={
        "growth_efficiency": 0.25,
        "unit_economics": 0.25,
        "capital_efficiency": 0.25,
        "growth_durability": 0.25,
    })
    # Stubbed — balance bonus (default no-op)
    balance_bonus_threshold: float = 0.40
    balance_bonus_multiplier: float = 1.0  # no-op until activated
```

### Function Signatures (updated)

```python
def compute_track_a_score(
    moat_durability: float,
    compounding_power: float,
    capital_allocation: float,
    growth_gap: float,
    config: V3CompositeConfig | None = None,
) -> float:

def compute_track_b_score(
    asymmetry_ratio: float,
    catalyst_strength: float,
    quality_floor_factor: float,
    valuation_convergence: float,
    config: V3CompositeConfig | None = None,
) -> float:

def compute_track_c_score(
    growth_efficiency: float,
    unit_economics: float,
    capital_efficiency: float,
    growth_durability: float,
    config: V3CompositeConfig | None = None,
) -> float:
```

### Core Implementation

Shared helper used by all three track functions:

```python
import math

def _weighted_geometric_mean(
    factors: dict[str, float],
    weights: dict[str, float],
    floor: float,
) -> float:
    log_sum = sum(
        weights[k] * math.log(max(factors[k], floor))
        for k in weights
    )
    return math.exp(log_sum)
```

### Example Outputs

Verified math: `score = exp(0.25 × (ln(max(f1, 0.05)) + ln(max(f2, 0.05)) + ln(max(f3, 0.05)) + ln(max(f4, 0.05))))`

| Profile | Old (multiplicative) | New (geometric mean, floor=0.05) |
|---------|---------------------|----------------------------------|
| Amazon 2001: (0.30, 0.90, 0.0, 0.95) | **0.0** | **~0.34** |
| Balanced mediocrity: (0.50, 0.50, 0.50, 0.50) | 0.0625 | ~0.50 |
| Balanced excellence: (0.80, 0.85, 0.70, 0.75) | 0.357 | ~0.77 |
| One weak factor: (0.90, 0.90, 0.10, 0.85) | 0.069 | ~0.51 |

**Key properties:**
1. **Zero-kill eliminated**: Amazon goes from 0.0 to 0.34 — penalized for the weak factor but meaningfully scored. Under the old formula, Amazon was invisible to the engine. Now it enters the scoring universe.
2. **Geometric mean naturally rewards balance**: Balanced mediocrity (0.50) > Amazon (0.34). This is correct behavior — balance IS better, all else equal. The fix is not that unbalanced profiles should outscore balanced ones, it's that unbalanced profiles should not be **eliminated entirely**.
3. **The old formula was strictly worse**: Under multiplication, Amazon scored 0.0 AND balanced mediocrity scored 0.0625. The geometric mean preserves the correct ordering while keeping both alive.

### Callers to Update

- `engine/src/margin_engine/scoring/v3_cascade.py` — passes config to `compute_track_a_score`, `compute_track_b_score`
- `engine/src/margin_engine/scoring/v3_track_c_cascade.py` — passes config to `compute_track_c_score`

---

## §2 — Conviction Gates: ROIC-Conditional + Trajectory Override

### Architecture Note: v2 vs v3 Gate Systems

The codebase has **two parallel gate systems**:

1. **v2 system** (`conviction_gates.py`): `check_track_a_gates()` / `check_track_b_gates()` — binary gate checks with rigid thresholds. Used by `dual_track.py` and test files.
2. **v3 system** (`v3_cascade.py` + `v3_thresholds.py`): Inline gate checks with threshold-based conviction assessment via `assess_track_a_conviction()` / `assess_track_b_conviction()`. This is the **production pipeline**.

**Both systems need modification.** The v2 system gets the ROIC-conditional reinvestment and trajectory override for backward compatibility and tests. The v3 system gets CONDITIONAL_PASS support wired through `v3_cascade.py` → `v3_thresholds.py`.

### File: `engine/src/margin_engine/scoring/conviction_gates.py` (modify — v2 system)

### Current Behavior (v2)

**Track A** — 5 binary gates:
- ROIC median > 15%
- ROIC CV < 0.30
- Reinvestment rate > 30% ← **the problem**
- Price/IV ≤ 2.0
- Data coverage > 85%

**Track B** — quality floor: ROIC > 8% OR improving (any positive delta) ← **too permissive**

### New Behavior (v2)

#### Track A: ROIC-Conditional Reinvestment

The reinvestment gate becomes ROIC-dependent:

| ROIC Level | Reinvestment Requirement | Rationale |
|------------|-------------------------|-----------|
| ≥ 25% | None (auto-pass) | Capital-light compounder — high ROIC proves capital is deployed well even at low reinvestment |
| 15-25% | > 10% | Strong ROIC, modest reinvestment sufficient |
| 10-15% | > 20% | Adequate ROIC, need more reinvestment to demonstrate compounding |
| 8-10% | > 30% | Low ROIC, full reinvestment required (current behavior preserved) |
| < 8% | Fail (unless trajectory override) | Below quality floor |

**Trajectory override**: If `roic_quarterly` shows 200bps+ improvement for 3 consecutive quarters → CONDITIONAL_PASS. This catches turnarounds with genuine momentum.

Other 4 gates (ROIC median, ROIC CV, price/IV, data coverage) unchanged.

#### Track B: Tightened Quality Floor

Replace `ROIC > 8% OR improving` with:
- ROIC ≥ 8% → PASS (unchanged)
- ROIC 6-8% → must show 200bps+ improvement over 2+ consecutive quarters → CONDITIONAL_PASS
- ROIC < 6% → hard FAIL (structural value trap, no trajectory saves this)

### Return Type Change

```python
class ConvictionGateResult(BaseModel):
    passed: bool
    conditional: bool = False  # NEW — True means CONDITIONAL_PASS
    failures: list[str]
```

### CONDITIONAL_PASS Semantics (Gate-Local)

When `conditional=True` on a conviction gate result:
- **That specific track** is capped at HIGH conviction (cannot reach EXCEPTIONAL)
- **Other tracks** are unaffected — if Track A conditionally passes but Track B fully passes, Track B can still reach EXCEPTIONAL
- **Multi-track promotions** in `v4_orchestrator.py` (A+B→EXCEPTIONAL, A+C→EXCEPTIONAL, all_three→EXCEPTIONAL) can still fire if at least one participating track fully passed

### Config Model

Added to `engine/src/margin_engine/scoring/v3_config.py`:

```python
class ConvictionGateConfig(BaseModel):
    # Track A ROIC-conditional reinvestment tiers
    roic_exceptional: float = 0.25   # ROIC ≥ 25%: no reinvestment needed
    roic_strong: float = 0.15        # ROIC 15-25%: reinvestment > 10%
    roic_adequate: float = 0.10      # ROIC 10-15%: reinvestment > 20%
    roic_minimum: float = 0.08       # ROIC 8-10%: reinvestment > 30%

    # Reinvestment thresholds per ROIC tier
    reinvestment_strong: float = 0.10
    reinvestment_adequate: float = 0.20
    reinvestment_minimum: float = 0.30

    # Trajectory override
    trajectory_min_delta: float = 0.02   # 200bps per quarter
    trajectory_min_periods: int = 3       # consecutive quarters

    # Track B tightening
    track_b_roic_hard_floor: float = 0.06
    track_b_improving_min_delta: float = 0.02   # 200bps
    track_b_improving_min_periods: int = 2       # consecutive quarters
```

### Function Signatures (updated)

```python
def check_track_a_gates(
    roic_median: float,
    roic_cv: float,
    reinvestment_rate: float,
    price_to_iv_ratio: float,
    data_coverage: float,
    roic_quarterly: list[float] | None = None,  # NEW
    config: ConvictionGateConfig | None = None,  # NEW
) -> ConvictionGateResult:

def check_track_b_gates(
    roic_median: float,
    roic_improving: bool,
    price_to_iv_ratio: float,
    has_catalyst: bool,
    net_cash_pct: float,
    tangible_book_pct: float,
    current_ratio: float,
    roic_quarterly: list[float] | None = None,  # NEW
    config: ConvictionGateConfig | None = None,  # NEW
) -> ConvictionGateResult:
```

### Trajectory Detection Helper

```python
def _check_trajectory_override(
    roic_quarterly: list[float],
    min_delta: float,
    min_periods: int,
) -> bool:
    """True if ROIC improved by min_delta for min_periods consecutive quarters."""
    if len(roic_quarterly) < min_periods + 1:
        return False
    consecutive = 0
    for i in range(1, len(roic_quarterly)):
        if roic_quarterly[i] - roic_quarterly[i - 1] >= min_delta:
            consecutive += 1
            if consecutive >= min_periods:
                return True
        else:
            consecutive = 0
    return False
```

### v3 Pipeline Integration (Production Path)

The v3 cascade (`v3_cascade.py`) runs its own inline gates — it does NOT call `check_track_a_gates` / `check_track_b_gates` from `conviction_gates.py`. The v3 conviction assessment happens via `assess_track_a_conviction()` / `assess_track_b_conviction()` in `v3_thresholds.py`.

**Changes to v3 system:**

1. **`v3_thresholds.py`** — `assess_track_a_conviction()` and `assess_track_b_conviction()` gain a `conditional: bool = False` parameter. When `True`, the returned conviction is capped at `CompositeTier.HIGH` (cannot return EXCEPTIONAL).

2. **`v3_cascade.py`** — `run_track_a_cascade()` detects when trajectory override should apply. During implementation, we must verify whether `compute_compounding_power()` (Gate 2) already handles capital-light compounders. If it incorporates reinvestment rate in a way that penalizes Apple/Visa, the same ROIC-conditional logic must be applied to Gate 2's threshold. The cascade passes `conditional=True` to `assess_track_a_conviction()` when trajectory override fires.

3. **`V3TrackResult`** — gains `conditional: bool = False` field so orchestrators can see which tracks conditionally passed. Multi-track promotion in `v3_orchestrator.py` / `v4_orchestrator.py` can still fire if at least one participating track has `conditional=False`.

4. **`v3_track_c_cascade.py`** — same pattern for Track C.

**Implementation dependency:** During implementation, read `v3_intermediates.py:compute_compounding_power()` to determine whether the capital-light compounder problem exists in v3. If compounding_power already passes Apple/Visa, the v3 Gate 2 may need no changes. Document findings in the implementation plan.

---

## §10 — Mediocrity Gate: Trajectory Override

### File: `engine/src/margin_engine/scoring/filters/mediocrity_gate.py` (modify in place)

### Current Behavior

Binary pass/fail with 4 checks:
1. 5yr median ROIC > 8%
2. Gross margin > 20% (sector-adjusted: Utilities > 10%, Energy > 15%)
3. Positive FCF in 4 of last 5 years
4. Revenue not declining 3+ consecutive years

### New Behavior

If the static gate fails, check four trajectory conditions. **Any one** triggers a trajectory pass:

1. **ROIC trajectory**: ROIC improved 200bps+/quarter for 3 consecutive quarters
2. **Gross margin approaching**: GM within 3% of sector threshold AND expanding 300bps+/year
3. **FCF inflection**: FCF positive in most recent 2 quarters after being negative in prior quarters
4. **Growth stage override**: Asset classified as TURNAROUND or HIGH_GROWTH (from existing `GrowthStage` enum) with any positive ROIC trajectory (most recent > earliest)

### CONDITIONAL_PASS Semantics (Gate-Local)

When mediocrity gate returns `conditional=True`:
- Ticker enters the scoring pipeline normally
- A **composite score multiplier** of 0.90x is applied (configurable via `MediocracyTrajectoryConfig.conditional_score_multiplier`)
- No conviction tier cap — if the ticker scores well enough on track gates, it can reach any tier
- The multiplier ensures trajectory-pass companies score slightly below companies that pass outright, all else equal

### Return Type Change

```python
class FilterResult(BaseModel):
    name: str
    passed: bool
    conditional: bool = False  # NEW
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    insufficient_data: bool = False
    missing_fields: list[str] | None = None
    computed_metrics: dict[str, float | str] | None = None
    warning: bool = False
    warning_reason: str | None = None
```

Adding `conditional: bool = False` to `FilterResult` in `models/scoring.py`. Default `False` preserves backward compatibility for all existing filters.

### Config Model

Added to `engine/src/margin_engine/scoring/v3_config.py`:

```python
class MediocracyTrajectoryConfig(BaseModel):
    # ROIC trajectory
    roic_min_delta_per_quarter: float = 0.02     # 200bps
    roic_min_consecutive: int = 3                 # quarters

    # Gross margin approaching threshold
    gm_approaching_distance: float = 0.03         # within 3% of sector threshold
    gm_min_annual_expansion: float = 0.03          # 300bps/year

    # FCF inflection
    fcf_positive_recent_quarters: int = 2          # most recent N must be positive
    fcf_lookback_quarters: int = 6                 # look back N quarters for prior negatives

    # Growth stage override
    trajectory_stages: list[str] = ["turnaround", "high_growth"]

    # Score multiplier for conditional pass
    conditional_score_multiplier: float = 0.90
```

### Function Signature (updated)

```python
def mediocrity_gate(
    history: FinancialHistory,
    sector: GICSSector,
    roic_quarterly: list[float] | None = None,     # NEW
    gm_quarterly: list[float] | None = None,        # NEW
    fcf_quarterly: list[float] | None = None,        # NEW
    growth_stage: GrowthStage | None = None,         # NEW
    config: MediocracyTrajectoryConfig | None = None, # NEW
) -> FilterResult:
```

When all new parameters are `None`, behavior is identical to current (static gate only).

### Pipeline Integration

**Current state:** `mediocrity_gate()` exists in `filters/mediocrity_gate.py` but is **NOT wired into the filter pipeline** (`filters/pipeline.py`). The pipeline currently runs 6 filters: liquidity, beneish, altman, fcf_distress, interest_coverage, current_ratio. The mediocrity gate is only called from test files.

**Changes required:**

1. **`filters/pipeline.py`** — Add `mediocrity_gate` as a 7th filter in `run_elimination_filters()`. It runs after the existing 6 filters. Import `mediocrity_gate` and `MediocracyTrajectoryConfig`. The `history` parameter (already accepted by the pipeline) is passed through. The new `roic_quarterly`, `gm_quarterly`, `fcf_quarterly`, and `growth_stage` parameters are extracted from `history` and the scoring context.

2. **`PipelineResult.passed` property** — Currently `all(r.passed for r in self.results)`. Needs to also treat `conditional=True` as passing: `all(r.passed or r.conditional for r in self.results)`. This allows trajectory-pass companies through the elimination pipeline.

3. **Score multiplier application** — When any filter in the pipeline has `conditional=True`, the corresponding `conditional_score_multiplier` is applied to the composite score in `v3_pipeline.py` / `v4_pipeline.py` after track scoring but before conviction tier assignment. The multiplier value is stored in `FilterResult.computed_metrics` for auditability.

4. **Quarterly data extraction** — The pipeline needs quarterly ROIC, GM, and FCF series. These can be computed from `FinancialHistory.periods` using the same helper functions already in `mediocrity_gate.py` (`_compute_roic`) and the existing `FinancialPeriod` fields. A new helper `_extract_quarterly_series(history)` returns the three lists.

---

## Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `engine/src/margin_engine/scoring/v3_config.py` | **CREATE** | Config models: V3CompositeConfig, ConvictionGateConfig, MediocracyTrajectoryConfig |
| `engine/src/margin_engine/scoring/v3_composite.py` | **MODIFY** | Weighted geometric mean with floor (all 3 track functions) |
| `engine/src/margin_engine/scoring/conviction_gates.py` | **MODIFY** | ROIC-conditional reinvestment, trajectory override, Track B tightening, add `conditional` to `ConvictionGateResult` |
| `engine/src/margin_engine/models/scoring.py` | **MODIFY** | Add `conditional: bool = False` to `FilterResult` |
| `engine/src/margin_engine/scoring/filters/mediocrity_gate.py` | **MODIFY** | Trajectory override with 4 conditions |
| `engine/src/margin_engine/scoring/filters/pipeline.py` | **MODIFY** | Wire mediocrity_gate as 7th filter, update `PipelineResult.passed` for conditional |
| `engine/src/margin_engine/scoring/v3_cascade.py` | **MODIFY** | Pass composite config, wire CONDITIONAL_PASS to threshold functions |
| `engine/src/margin_engine/scoring/v3_track_c_cascade.py` | **MODIFY** | Same CONDITIONAL_PASS handling for Track C |
| `engine/src/margin_engine/scoring/v3_thresholds.py` | **MODIFY** | Add `conditional: bool` param → cap at HIGH when True |
| `engine/src/margin_engine/scoring/v3_track_c_thresholds.py` | **MODIFY** | Same conditional cap for Track C |
| `engine/src/margin_engine/scoring/v3_orchestrator.py` | **MODIFY** | `V3TrackResult` gains `conditional: bool` field |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | **MODIFY** | Apply mediocrity conditional_score_multiplier |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | **MODIFY** | Same multiplier application |
| `engine/src/margin_engine/scoring/dual_track.py` | **MODIFY** | Handle `conditional` from ConvictionGateResult (backward compat) |
| `engine/tests/scoring/test_v3_composite_geometric.py` | **CREATE** | Formula golden-value tests |
| `engine/tests/scoring/test_conviction_gates_v2.py` | **CREATE** | Gate logic tests |
| `engine/tests/scoring/test_mediocrity_trajectory.py` | **CREATE** | Trajectory override tests |

## Testing Strategy

### §1 — Composite Formula Tests (`test_v3_composite_geometric.py`)

1. **Zero factor does not zero score**: factor at 0.0 → composite > 0.10 (meaningfully scored, not eliminated)
2. **Zero factor is penalized but not killed**: (0.30, 0.90, 0.0, 0.95) scores ~0.34 — substantially above zero, below balanced profiles (correct ordering)
3. **Balanced excellence is best**: (0.80, 0.85, 0.70, 0.75) ~0.77 > balanced mediocrity ~0.50 > Amazon ~0.34
4. **Equal weights produce expected geometric mean**: known inputs → verified output
5. **Custom weights shift scores**: higher weight on strong factor → higher score
6. **Floor behavior**: factor at 0.0 treated as floor value (0.05)
7. **Composite floor**: all factors at 0.0 → composite ≥ composite_floor (0.01)
8. **Track B asymmetry cap**: asymmetry_ratio > 20 → capped at 20 before geometric mean
9. **All three tracks**: Track A, B, C all use geometric mean consistently
10. **Balance bonus stub**: multiplier=1.0 has no effect; multiplier=1.15 increases score when all factors > threshold

### §2 — Conviction Gate Tests (`test_conviction_gates_v2.py`)

1. **Apple profile**: ROIC=0.40, reinvestment=0.12 → PASS (capital-light path, ROIC ≥ 25%)
2. **Visa profile**: ROIC=0.35, reinvestment=0.08 → PASS (capital-light path)
3. **Mid-ROIC adequate reinvestment**: ROIC=0.12, reinvestment=0.22 → PASS
4. **Mid-ROIC insufficient reinvestment**: ROIC=0.12, reinvestment=0.15 → FAIL (need 0.20)
5. **Low-ROIC with trajectory**: ROIC=0.06, roic_quarterly accelerating 200bps/Q for 3Q → CONDITIONAL_PASS
6. **Low-ROIC without trajectory**: ROIC=0.06, flat roic_quarterly → FAIL
7. **Track B tightened — trivial improvement**: ROIC=0.07, roic improving 50bps → FAIL (need 200bps)
8. **Track B tightened — meaningful improvement**: ROIC=0.07, roic improving 200bps for 2Q → CONDITIONAL_PASS
9. **Track B hard floor**: ROIC=0.05 with trajectory → FAIL (below 6% hard floor)
10. **Regression**: all existing PASS cases remain PASS with default config
11. **No roic_quarterly provided**: trajectory override skipped, backward compatible

### §10 — Mediocrity Trajectory Tests (`test_mediocrity_trajectory.py`)

1. **Static gate passes → no conditional flag**: company meeting all static thresholds → passed=True, conditional=False
2. **ROIC trajectory override**: static fail, ROIC accelerating 200bps/Q for 3Q → conditional=True
3. **GM approaching + expanding**: GM=0.18 (below 0.20), expanding 400bps/yr → conditional=True
4. **FCF inflection**: negative FCF in Q1-Q4, positive Q5-Q6 → conditional=True
5. **Growth stage override**: stage=TURNAROUND, any positive ROIC trajectory → conditional=True
6. **All trajectory checks fail**: static fail, no trajectory signals → passed=False, conditional=False
7. **Sector-adjusted GM threshold**: Utilities with GM=0.08 approaching 0.10 threshold → works correctly
8. **Score multiplier**: conditional=True → `conditional_score_multiplier` (0.90) stored in computed_metrics
9. **No quarterly data provided**: static gate only, backward compatible
10. **Custom config thresholds**: override defaults, verify behavior changes

## Acceptance Criteria

- [ ] No single factor at 0.0 produces a composite score of 0.0 (any track)
- [ ] A zero factor produces a composite score > 0.10 (meaningfully scored, not eliminated)
- [ ] Apple (ROIC ~40%, reinvestment ~12%) passes Track A conviction gates
- [ ] Visa (ROIC ~35%, reinvestment ~8%) passes Track A conviction gates
- [ ] Turnaround with 200bps+ ROIC acceleration for 3Q gets CONDITIONAL_PASS on conviction gates
- [ ] Turnaround with trajectory override on mediocrity gate enters scoring with 0.90x multiplier
- [ ] Structurally broken business (ROIC < 6%) fails Track B hard floor regardless of trajectory
- [ ] All existing tests pass (no regression)
- [ ] All new config models validate correctly (weights sum to 1.0, thresholds are positive)
- [ ] CONDITIONAL_PASS on conviction gate caps only that track at HIGH, not other tracks
- [ ] CONDITIONAL_PASS on mediocrity gate applies score multiplier, does not cap conviction tier

## Edge Cases & Risk Notes

1. **Track B asymmetry range**: Track B's `asymmetry_ratio` can be up to 20.0 (after cap), while other factors are in [0, 1]. Under geometric mean, this asymmetry dominance is intentional — Track B is specifically about valuation asymmetry, and high asymmetry should pull the score up. The cap at 20.0 prevents extreme outliers. No normalization needed.

2. **NaN handling in trajectory detection**: `roic_quarterly` values may contain NaN (yfinance data — see CLAUDE.md gotchas). The `_check_trajectory_override` helper must filter NaN values before computing deltas. Use `math.isfinite()` check on each value.

3. **v3 compounding_power investigation**: During implementation, verify whether `compute_compounding_power()` in `v3_intermediates.py` incorporates reinvestment rate. If it does, the capital-light compounder problem exists in v3 and needs the same ROIC-conditional fix. If it doesn't, only the v2 system needs the reinvestment change.

4. **Serialization of new fields**: `ConvictionGateResult.conditional` and `FilterResult.conditional` will appear in `model_dump()` output. Check if these models are serialized to JSONB in the database — if so, existing rows won't have the field, but Pydantic's default handles reconstruction correctly.
