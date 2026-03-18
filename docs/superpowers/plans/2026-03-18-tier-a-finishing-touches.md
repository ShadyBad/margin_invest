# Tier A: Engine v2 Finishing Touches

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Complete 6 remaining items from the Tier 1 scoring overhaul: trajectory detection in cascades, growth stage wiring, boundary fix, filter semantic cleanup, DRY refactor, and Optuna-based weight tuning.

**Architecture:** All changes in the engine package (pure Python, zero web deps). Items 1-5 are deterministic code fixes with TDD. Item 8 adds an optimization CLI command with Optuna. No API or frontend changes.

**Tech stack:** Python 3.13, Pydantic, pytest, Optuna (optional dep for tuning)

**Spec:** `docs/superpowers/specs/2026-03-18-tier-a-finishing-touches.md`

---

## Ordering Rationale

1. **Item 1 (A3)** -- Tiny boundary fix, zero dependencies, good warmup
2. **Item 2 (A1 prep)** -- Rename private function to public, required before Item 3
3. **Item 3 (A1)** -- Cascade trajectory detection, uses public function from Item 2
4. **Item 4 (A4)** -- Filter semantic gap, independent
5. **Item 5 (A2)** -- Growth stage passthrough, independent
6. **Item 6 (A5 part 1)** -- Extract TickerDataBase, required before Item 7
7. **Item 7 (A5 part 2)** -- Extract pipeline helpers, uses TickerDataBase from Item 6
8. **Item 8 (A6)** -- Optuna weight + bonus tuning CLI (independent of Items 6-7)

---

### Item 1: Track B ROIC Boundary Fix (A3)

**Files:**
- Modify: `engine/src/margin_engine/scoring/conviction_gates.py:198`
- Test: `engine/tests/scoring/test_conviction_gates.py`

- [ ] **Step 1: Write the failing boundary test**

In `engine/tests/scoring/test_conviction_gates.py`, add `test_track_b_roic_exactly_at_floor_passes` (ROIC=0.08 should pass unconditionally with >=) and `test_track_b_roic_just_below_floor_enters_improving_zone` (ROIC=0.0799 enters improving zone).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_conviction_gates.py::test_track_b_roic_exactly_at_floor_passes -v`

- [ ] **Step 3: Fix the boundary operator**

In `conviction_gates.py` line 198: change `if roic_median > _B_ROIC_FLOOR:` to `if roic_median >= _B_ROIC_FLOOR:`

- [ ] **Step 4: Run both tests to verify they pass**

- [ ] **Step 5: Run full conviction gates test suite**

Run: `uv run pytest engine/tests/scoring/test_conviction_gates.py -v`

- [ ] **Step 6: Commit**

---

### Item 2: Make `check_trajectory_override` Public (A1 prep)

**Files:**
- Modify: `engine/src/margin_engine/scoring/conviction_gates.py`

- [ ] **Step 1: Rename the function**

Rename `_check_trajectory_override` to `check_trajectory_override` (line 47). Update 2 internal call sites (lines 133, 202).

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `uv run pytest engine/tests/scoring/test_conviction_gates.py -v`

- [ ] **Step 3: Commit**

---

### Item 3: v3 Cascade Trajectory Detection (A1)

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Create: `engine/tests/scoring/test_v3_cascade_trajectory.py`

- [ ] **Step 1: Write test helper and Track A trajectory tests**

Create test file with `_period_with_roic(target_roic, period_end)` helper that builds a FinancialPeriod with a specific ROIC (fix IC=1000, tax_rate=0.25, compute EBIT accordingly). Add `_build_track_a_inputs(roic_trajectory)` helper.

Track A tests:
- Low ROIC (median <8%) + improving 200bps/Q for 3Q -> conditional=True
- Low ROIC + flat trajectory -> conditional=False
- Normal ROIC (>=8%) -> trajectory detection skipped, conditional=False
- Single period -> guard prevents check, conditional=False

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add `_compute_roic_series` helper and Track A trajectory detection**

Add imports: `ConvictionGateConfig`, `check_trajectory_override`.

Add `_compute_roic_series(history)` helper using `_nopat_and_ic` from v3_intermediates.

Replace inline ROIC loop in capital-light bypass (lines 96-103) with the helper. Reuse `roic_series` and `median_roic` for trajectory detection.

Trajectory detection: if median_roic < 0.08 and len(roic_series) >= 2, call `check_trajectory_override`. Set conditional=True if it fires.

Pass `conditional` to `assess_track_a_conviction()` and into `V3TrackResult`.

- [ ] **Step 4: Run Track A tests to verify they pass**

- [ ] **Step 5: Write Track B trajectory tests**

Add `_build_track_b_inputs(roic_trajectory)` helper. Track B tests:
- ROIC in [6%, 8%) + improving 200bps/Q for 2Q -> conditional=True
- ROIC in [6%, 8%) + flat -> conditional=False
- ROIC >= 8% -> conditional=False
- ROIC < 6% (hard floor) -> conditional=False

- [ ] **Step 6: Run Track B tests to verify they fail**

- [ ] **Step 7: Add Track B trajectory detection**

After quality_floor computation, add trajectory detection using `_compute_roic_series`. Check if median_roic is in [track_b_roic_hard_floor, 0.08). Pass `conditional` to conviction and result.

- [ ] **Step 8: Run all trajectory tests**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade_trajectory.py -v`

- [ ] **Step 9: Write conviction cap end-to-end test**

Add a test that builds Track A inputs which would reach EXCEPTIONAL conviction without conditional, then sets up a trajectory scenario where conditional=True, and verifies the conviction is capped to HIGH. This confirms the wiring between cascade trajectory detection and `assess_track_a_conviction`'s capping logic.

- [ ] **Step 10: Run full cascade test suite for regressions**

- [ ] **Step 11: Commit**

---

### Item 4: failed_filters Semantic Gap (A4)

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Modify: `engine/src/margin_engine/scoring/filters/pipeline.py`
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py`
- Test: `engine/tests/scoring/filters/test_pipeline.py`

- [ ] **Step 1: Write failing tests for CONDITIONAL_PASS verdict and updated properties**

Add TestConditionalFilterSemantics class with tests:
- verdict returns CONDITIONAL_PASS for (passed=False, conditional=True)
- failed_filters excludes conditional results
- conditional_filters returns only conditional results
- pipeline.passed still counts conditional as passing

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add CONDITIONAL_PASS to FilterVerdict and update verdict property**

In `models/scoring.py`, add `CONDITIONAL_PASS = "conditional_pass"` to FilterVerdict. Update verdict property to check `self.conditional` before returning FAIL.

- [ ] **Step 4: Update PipelineResult properties**

In `filters/pipeline.py`, update `failed_filters` to exclude conditional (`not r.passed and not r.conditional`). Add `conditional_filters` property (`not r.passed and r.conditional`).

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Update replay orchestrator to log conditional filters**

In `replay_orchestrator.py`, update both sync run() (~line 200) and async run_async() (~line 459) to log conditional_filters separately alongside failed_filters.

- [ ] **Step 7: Run full filter and pipeline test suites**

- [ ] **Step 8: Commit**

---

### Item 5: Growth Stage Passthrough to Mediocrity Gate (A2)

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/pipeline.py`
- Test: `engine/tests/scoring/filters/test_mediocrity_trajectory.py`

- [ ] **Step 1: Write integration test**

Create test with turnaround history (4 quarters: 2 negative NI, 2 positive, with improving margins and positive OCF). Run through `run_elimination_filters()`. Verify mediocrity gate result exists.

- [ ] **Step 2: Run test to confirm baseline passes (no crash)**

- [ ] **Step 3: Extend `_extract_quarterly_series` and wire growth stage**

Add `classify_growth_stage` import. Extend `_extract_quarterly_series` to return `"net_income"` series. Before mediocrity_gate call, compute `growth_stage = classify_growth_stage(period, profile, quarterly_net_incomes=..., quarterly_margins=...)`. Pass `growth_stage` to `mediocrity_gate()`.

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Run full pipeline tests for regressions**

- [ ] **Step 6: Commit**

---

### Item 6: Extract TickerDataBase (A5 part 1)

**Files:**
- Create: `engine/src/margin_engine/scoring/ticker_data.py`
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py`
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py`

- [ ] **Step 1: Create TickerDataBase**

New file `ticker_data.py` with `TickerDataBase(BaseModel)` containing all 15 shared fields: ticker, history, latest_period, profile, current_price, current_fcf_per_share, sustainable_growth_rate, buyback_yield, insider_ownership_pct, sbc_pct, recent_acquisition_count, sue_percentile, beta, momentum_percentile, dcf_iv.

- [ ] **Step 2: Rebase TickerV3Data**

In `v3_pipeline.py`, make `TickerV3Data(TickerDataBase)` with empty body (pass).

- [ ] **Step 3: Rebase TickerV4Data**

In `v4_pipeline.py`, make `TickerV4Data(TickerDataBase)` adding all 11 V4-only fields: accumulation_percentile, style, revenue_growth_rate, fcf_margin, gross_margin_current, gross_margin_3yr_ago, opex_growth_rate, revenue_growth_rate_for_leverage, incremental_roic, revenue_deceleration, tam_headroom.

- [ ] **Step 4: Run existing pipeline tests**

- [ ] **Step 5: Run full engine test suite**

- [ ] **Step 6: Commit**

---

### Item 7: Extract Pipeline Helpers (A5 part 2)

**Files:**
- Create: `engine/src/margin_engine/scoring/pipeline_helpers.py`
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py`
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py`

- [ ] **Step 1: Create pipeline_helpers.py**

Extract 6 functions from v3_pipeline.py, typed against TickerDataBase: `conditional_multiplier_for_ticker`, `compute_ev_ebit`, `compute_sector_median_ev_ebit`, `compute_peer_comparison_iv`, `compute_owner_earnings_per_share`, `compute_asset_floor_per_share`.

- [ ] **Step 2: Replace functions in v3_pipeline.py with imports**

- [ ] **Step 3: Replace functions in v4_pipeline.py with imports**

- [ ] **Step 4: Run pipeline tests**

- [ ] **Step 5: Run full engine test suite**

- [ ] **Step 6: Commit**

---

### Item 8: Weight and Balance Bonus Optimization via Optuna (A6)

**Files:**
- Create: `engine/src/margin_engine/tuning/__init__.py`
- Create: `engine/src/margin_engine/tuning/weight_optimizer.py`
- Create: `engine/tests/tuning/__init__.py`
- Create: `engine/tests/tuning/test_weight_optimizer.py`
- Modify: `api/src/margin_api/cli.py`
- Modify: `engine/pyproject.toml`

- [ ] **Step 1: Add optuna as optional dependency**

In `engine/pyproject.toml`: `[project.optional-dependencies] tuning = ["optuna>=3.0"]`.

- [ ] **Step 2: Write weight constraint tests**

Test that `suggest_track_weights` produces weights summing to 1.0, all within [0.10, 0.50], and returns None when derived weight is out of bounds.

- [ ] **Step 3: Run tests to verify they fail (ImportError)**

- [ ] **Step 4: Create the weight optimizer module**

Create `tuning/weight_optimizer.py` with: `WeightTuneResult` dataclass, `suggest_track_weights(trial, factor_names, min_weight, max_weight)`, `build_config_from_trial(trial, track, factor_names)`, and `TRACK_FACTORS` dict.

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Commit core optimizer**

- [ ] **Step 7: Add weight-tune CLI command**

Add `weight-tune` command to CLI accepting track (A/B/C/ALL), --n-trials, --metric, --dry-run. Scaffold with study creation and TODO for full backtest wiring.

- [ ] **Step 8: Run CLI help to verify command registers**

- [ ] **Step 9: Commit CLI command**

---

## Summary

| # | Item | Effort | Depends On |
|---|------|--------|------------|
| 1 | A3: ROIC boundary fix | Tiny | None |
| 2 | A1 prep: make trajectory override public | Tiny | None |
| 3 | A1: Cascade trajectory detection | Medium | Item 2 |
| 4 | A4: failed_filters semantic gap | Small | None |
| 5 | A2: Growth stage passthrough | Small | None |
| 6 | A5 part 1: Extract TickerDataBase | Small | None |
| 7 | A5 part 2: Extract pipeline helpers | Small | Item 6 |
| 8 | A6: Optuna weight tuning | Medium | None |
