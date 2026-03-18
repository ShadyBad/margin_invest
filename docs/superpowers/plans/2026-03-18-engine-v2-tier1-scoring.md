# Engine v2 Tier 1: Scoring Formula, Conviction Gates, Mediocrity Trajectory

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan one task at a time.

**Goal:** Replace the multiplicative zero-kill composite formula with weighted geometric mean, add ROIC-conditional conviction gates with trajectory overrides, and add trajectory-aware mediocrity gate.

**Architecture:** Three layered changes: (1) config models, (2) core formula/gate logic with TDD, (3) pipeline wiring. Changes touch both v2 (conviction_gates.py) and v3/v4 production pipeline (v3_cascade.py, v3_thresholds.py).

**Tech Stack:** Python 3.13, Pydantic BaseModel, pytest

**Spec:** docs/superpowers/specs/2026-03-18-engine-v2-tier1-scoring-design.md

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| engine/src/margin_engine/config/v3_scoring_config.py | Config models: V3CompositeConfig, ConvictionGateConfig, MediocracyTrajectoryConfig |
| engine/tests/scoring/test_v3_composite_geometric.py | Golden-value tests for geometric mean formula |
| engine/tests/scoring/test_conviction_gates_conditional.py | Tests for ROIC-conditional gates and trajectory override |
| engine/tests/scoring/test_mediocrity_trajectory.py | Tests for mediocrity gate trajectory override |
| engine/tests/scoring/test_tier1_integration.py | End-to-end regression tests |

### Modified Files
| File | What Changes |
|------|-------------|
| engine/src/margin_engine/models/scoring.py | Add conditional: bool = False to FilterResult |
| engine/src/margin_engine/scoring/conviction_gates.py | Add conditional to ConvictionGateResult, ROIC-conditional reinvestment, trajectory override, Track B tightening |
| engine/src/margin_engine/scoring/v3_composite.py | Replace multiplication with weighted geometric mean |
| engine/src/margin_engine/scoring/filters/mediocrity_gate.py | Add trajectory override with 4 conditions |
| engine/src/margin_engine/scoring/filters/pipeline.py | Wire mediocrity_gate as 7th filter, handle conditional in PipelineResult.passed |
| engine/src/margin_engine/scoring/v3_cascade.py | Pass composite config through, propagate conditional flag |
| engine/src/margin_engine/scoring/v3_track_c_cascade.py | Same config passthrough and conditional propagation |
| engine/src/margin_engine/scoring/v3_thresholds.py | Accept conditional param, cap at HIGH when True |
| engine/src/margin_engine/scoring/v3_track_c_thresholds.py | Same conditional cap |
| engine/src/margin_engine/scoring/v3_orchestrator.py | Add conditional: bool = False to V3TrackResult |

---

### Task 1: Create Config Models

**Files:**
- Create: engine/src/margin_engine/config/v3_scoring_config.py
- Test: engine/tests/config/test_v3_scoring_config.py

- [ ] **Step 1: Write config model tests** — TestTrackWeights (equal weights valid, bad sum rejected, custom valid), TestV3CompositeConfig (defaults), TestConvictionGateConfig (defaults + custom), TestMediocracyTrajectoryConfig (defaults)
- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest engine/tests/config/test_v3_scoring_config.py -v`
- [ ] **Step 3: Implement config models** — TrackWeights with sum validation, V3CompositeConfig (floor=0.05, weights=0.25 each, bonus stub=1.0), ConvictionGateConfig (ROIC tiers, trajectory thresholds), MediocracyTrajectoryConfig (trajectory thresholds, multiplier=0.90)
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit** — `feat(engine): add v3 scoring config models`

---

### Task 2: Add conditional Field to Models

**Files:**
- Modify: engine/src/margin_engine/models/scoring.py (FilterResult)
- Modify: engine/src/margin_engine/scoring/conviction_gates.py (ConvictionGateResult)
- Modify: engine/src/margin_engine/scoring/v3_orchestrator.py (V3TrackResult)

- [ ] **Step 1:** Add `conditional: bool = False` to FilterResult after `passed: bool`
- [ ] **Step 2:** Add `conditional: bool = False` to ConvictionGateResult after `passed: bool`
- [ ] **Step 3:** Add `conditional: bool = False` to V3TrackResult after `score: float`
- [ ] **Step 4: Run existing tests for regression** — `uv run pytest engine/tests/ -v --timeout=60 -x -q`
- [ ] **Step 5: Commit** — `feat(engine): add conditional field to FilterResult, ConvictionGateResult, V3TrackResult`

---

### Task 3: Implement Weighted Geometric Mean Composite

**Files:**
- Modify: engine/src/margin_engine/scoring/v3_composite.py
- Create: engine/tests/scoring/test_v3_composite_geometric.py

- [ ] **Step 1: Write golden-value tests** — zero factor nonzero (>0.10), Amazon ~0.34, balanced mediocrity ~0.50, balanced excellence ~0.77, ordering (excellent > mediocre > unbalanced > 0), composite floor, custom weights, asymmetry cap preserved (Track B), balance bonus stub, Track C zero nonzero
- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest engine/tests/scoring/test_v3_composite_geometric.py -v`
- [ ] **Step 3: Implement geometric mean** — `_weighted_geometric_mean(factors, weights, floor, composite_floor, bonus_threshold, bonus_multiplier)` using `math.log` / `math.exp`. Track B preserves `_ASYMMETRY_CAP = 20.0`. All three track functions gain optional `config` param.
- [ ] **Step 4: Run new tests to verify they pass**
- [ ] **Step 5: Run existing tests, fix regressions** — Update golden values in existing tests that asserted multiplicative outputs
- [ ] **Step 6: Commit** — `feat(engine): replace multiplicative composite with weighted geometric mean`

---

### Task 4: Implement ROIC-Conditional Conviction Gates

**Files:**
- Modify: engine/src/margin_engine/scoring/conviction_gates.py
- Create: engine/tests/scoring/test_conviction_gates_conditional.py

- [ ] **Step 1: Write tests** — Apple (ROIC=0.40, reinv=0.12) PASS, Visa (ROIC=0.35, reinv=0.08) PASS, mid-ROIC adequate/insufficient, trajectory override (roic_quarterly accelerating) CONDITIONAL, flat trajectory FAIL, NaN handling, Track B tightened (trivial improvement FAIL, meaningful CONDITIONAL, hard floor FAIL)
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement** — Add `_check_trajectory_override()` helper (filter NaN with `math.isfinite`). Modify `check_track_a_gates`: ROIC-conditional reinvestment tiers + trajectory fallback. Modify `check_track_b_gates`: hard floor at 6%, 6-8% requires meaningful improvement.
- [ ] **Step 4: Run new tests to verify they pass**
- [ ] **Step 5: Run existing conviction tests for regression**
- [ ] **Step 6: Commit** — `feat(engine): ROIC-conditional conviction gates with trajectory override`

---

### Task 5: Implement Mediocrity Gate Trajectory Override

**Files:**
- Modify: engine/src/margin_engine/scoring/filters/mediocrity_gate.py
- Create: engine/tests/scoring/test_mediocrity_trajectory.py

- [ ] **Step 1: Write tests** — Static pass unchanged, ROIC trajectory conditional, FCF inflection conditional, TURNAROUND stage conditional, all trajectory checks fail, backward compatible (no quarterly data)
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement** — Add optional params (roic_quarterly, gm_quarterly, fcf_quarterly, growth_stage, config). After static fail, check 4 trajectory conditions. Set conditional=True if any triggers. Store multiplier in computed_metrics.
- [ ] **Step 4: Run new tests to verify they pass**
- [ ] **Step 5: Run existing mediocrity tests for regression**
- [ ] **Step 6: Commit** — `feat(engine): mediocrity gate trajectory override for turnarounds`

---

### Task 6: Wire Mediocrity Gate into Filter Pipeline

**Files:**
- Modify: engine/src/margin_engine/scoring/filters/pipeline.py

- [ ] **Step 1:** Update PipelineResult.passed: `all(r.passed or r.conditional for r in self.results)`
- [ ] **Step 2:** Add mediocrity_gate as 7th filter in run_elimination_filters()
- [ ] **Step 3: Run pipeline tests for regression**
- [ ] **Step 4: Commit** — `feat(engine): wire mediocrity gate into elimination filter pipeline`

---

### Task 7: Wire Composite Config Through v3/v4 Cascades

**Files:**
- Modify: engine/src/margin_engine/scoring/v3_cascade.py
- Modify: engine/src/margin_engine/scoring/v3_track_c_cascade.py

- [ ] **Step 1:** Add composite_config to TrackAInputs, TrackBInputs, TrackCInputs. Pass to compute_track_{a,b,c}_score().
- [ ] **Step 2: Run cascade tests for regression**
- [ ] **Step 3: Commit** — `feat(engine): wire composite config through v3 cascade runners`

---

### Task 8: Wire CONDITIONAL_PASS Through v3 Thresholds

**Files:**
- Modify: engine/src/margin_engine/scoring/v3_thresholds.py
- Modify: engine/src/margin_engine/scoring/v3_track_c_thresholds.py
- Modify: engine/src/margin_engine/scoring/v3_cascade.py
- Modify: engine/src/margin_engine/scoring/v3_track_c_cascade.py

- [ ] **Step 1:** Add conditional: bool = False to assess_track_{a,b,c}_conviction. Cap at HIGH when True.
- [ ] **Step 2:** Propagate conditional from cascade runners to threshold functions and V3TrackResult.
- [ ] **Step 3: Run tests for regression**
- [ ] **Step 4: Commit** — `feat(engine): wire CONDITIONAL_PASS through v3 thresholds and cascades`

---

### Task 9: Wire Mediocrity Multiplier Through v3/v4 Pipeline

**Files:**
- Modify: engine/src/margin_engine/scoring/v3_pipeline.py
- Modify: engine/src/margin_engine/scoring/v4_pipeline.py

- [ ] **Step 1:** After track scoring, before conviction: check filter results for conditional=True. If so, multiply track scores by conditional_score_multiplier (0.90).
- [ ] **Step 2: Run pipeline tests for regression**
- [ ] **Step 3: Commit** — `feat(engine): apply mediocrity conditional score multiplier in pipelines`

---

### Task 10: Integration Regression Tests

**Files:**
- Create: engine/tests/scoring/test_tier1_integration.py

- [ ] **Step 1: Write integration tests** — Amazon nonzero, Apple passes gates, turnaround conditional mediocrity
- [ ] **Step 2: Run full engine test suite** — `uv run pytest engine/tests/ -v --timeout=120`
- [ ] **Step 3: Commit** — `test(engine): add Tier 1 integration regression tests`

---

### Task 11: Investigate compounding_power for Capital-Light Compounders

**Files:**
- Read: engine/src/margin_engine/scoring/v3_intermediates.py:56-120
- Potentially modify: engine/src/margin_engine/scoring/v3_cascade.py (Gate 2)

Research: compute_compounding_power() returns 0.0 when reinvestment_rate <= 0. Capital-light compounders (Visa) may get near-zero reinvestment_rate.

- [ ] **Step 1:** Read compute_compounding_power() fully
- [ ] **Step 2:** Test with Apple-like and Visa-like financial data against Gate 2 threshold (0.04)
- [ ] **Step 3:** If fix needed: make Gate 2 ROIC-conditional (ROIC >= 25% auto-passes)
- [ ] **Step 4:** Document findings and commit

---

## Execution Order

| # | Description | Depends On |
|---|-------------|------------|
| 1 | Config models | None |
| 2 | Add conditional to models | None |
| 3 | Geometric mean composite + tests | 1 |
| 4 | ROIC-conditional conviction gates + tests | 1, 2 |
| 5 | Mediocrity trajectory override + tests | 1, 2 |
| 6 | Wire mediocrity gate into filter pipeline | 2, 5 |
| 7 | Wire composite config through cascades | 1, 3 |
| 8 | Wire CONDITIONAL_PASS through thresholds | 2, 4 |
| 9 | Wire mediocrity multiplier through pipeline | 5, 6 |
| 10 | Integration regression tests | 3-9 |
| 11 | Investigate compounding_power | 3, 7 |

**Parallelizable:** Tasks 3, 4, 5 can run in parallel after 1+2. Tasks 6, 7, 8, 9 are independent of each other.
