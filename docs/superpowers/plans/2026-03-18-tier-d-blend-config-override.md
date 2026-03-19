# Tier D: BlendConfig + 2-Level ML Override Implementation Plan

**Goal:** Introduce a unified BlendConfig and extend ML ensemble override to support 2-level conviction changes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Architecture:** Two independent changes: (1) BlendConfig Pydantic model replaces raw float defaults in blend.py; (2) OverrideConfig plus promote()/demote() in ensemble_override.py. Engine-only, no DB migrations.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, margin_engine

**Spec:** `docs/superpowers/specs/2026-03-18-tier-d-ml-backtesting.md` (D2 + D3)

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `engine/src/margin_engine/config/blend_config.py` | BlendConfig Pydantic model |
| Modify | `engine/src/margin_engine/ml/blend.py` | New blend_from_config() as public API; old functions become deprecated wrappers |
| Modify | `engine/src/margin_engine/ml/ensemble_override.py` | OverrideConfig, promote(), demote(), 2-level support |
| Create | `engine/tests/config/test_blend_config.py` | Tests for BlendConfig validation |
| Modify | `engine/tests/ml/test_blend.py` | Tests for config-based blend |
| Modify | `engine/tests/ml/test_ensemble_override.py` | Tests for 2-level override |

---

### Task 1: BlendConfig model

**Files:**
- Create: `engine/src/margin_engine/config/blend_config.py`
- Create: `engine/tests/config/test_blend_config.py`

- [ ] **Step 1: Write failing tests for BlendConfig**

Create `engine/tests/config/test_blend_config.py` with tests for:
- Default values (composite=0.70, gbm=0.30, vae=0.0, shadow_mode=True, horizon={252:1.0})
- Valid weights (sum to 1.0) accepted
- Invalid weights (sum != 1.0) raise ValidationError
- Invalid horizon weights raise ValidationError
- VAE enabled with shadow_mode=False
- 50/50 blend config
- Multi-horizon weights (4 horizons)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/config/test_blend_config.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement BlendConfig**

Create `engine/src/margin_engine/config/blend_config.py`:
- BlendConfig(BaseModel) with: composite_weight(0.70), gbm_weight(0.30), vae_weight(0.0), vae_shadow_mode(True), horizon_weights({252:1.0})
- model_validator: composite+gbm+vae must sum to 1.0; horizon_weights must sum to 1.0

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/config/test_blend_config.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

`git commit -m "feat(engine): add BlendConfig model for unified blend weight management"`

---

### Task 2: Config-based blend functions

**Files:**
- Modify: `engine/src/margin_engine/ml/blend.py`
- Modify: `engine/tests/ml/test_blend.py`

- [ ] **Step 1: Write failing tests for blend_from_config**

Add TestBlendFromConfig class to test_blend.py:
- Default BlendConfig() produces same result as old blend_alpha(ml_weight=0.30): 0.70*composite + 0.30*gbm
- 50/50 config: BlendConfig(composite_weight=0.50, gbm_weight=0.50)
- VAE enabled (shadow_mode=False): includes VAE weight in blend
- Shadow mode ignores VAE: forces vae_weight=0.0, composite absorbs remainder
- Uncertainty passthrough: vae_var returned unchanged

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_blend.py::TestBlendFromConfig -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement blend_from_config**

Add to blend.py:
- `blend_from_config(composite_alpha, gbm_alpha, vae_mean, vae_var, config: BlendConfig) -> tuple[float, float]`
- When config.vae_shadow_mode is True: force vae_w=0.0, composite_w = 1.0 - gbm_w
- When False: use config weights directly
- `blend_from_config` is the new public API. Old `blend_alpha()` and `blend_with_vae()` become deprecated wrappers (keep for backward compat but new code should use `blend_from_config`)
- Shadow mode enforcement happens inside `blend_from_config` -- this is the caller boundary where the spec says to suppress VAE

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_blend.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

`git commit -m "feat(engine): add blend_from_config() accepting BlendConfig"`

---

### Task 3: OverrideConfig and promote/demote helpers

**Files:**
- Modify: `engine/src/margin_engine/ml/ensemble_override.py`
- Modify: `engine/tests/ml/test_ensemble_override.py`

- [ ] **Step 1: Write failing tests for OverrideConfig and helpers**

Add TestOverrideConfig: default values match spec (top_1=85, bottom_1=15, conf_1=0.75, top_2=95, bottom_2=5, conf_2=0.80, max_levels=2, early_exit=0.60). Test max_override_levels=1 disables 2-level.

Add TestPromoteDemote: promote 1 level (MEDIUM->HIGH), 2 levels (MEDIUM->EXCEPTIONAL), promote(HIGH, 2) capped at EXCEPTIONAL, promote(EXCEPTIONAL, 1) stays, demote 1 (HIGH->MEDIUM), 2 (EXCEPTIONAL->MEDIUM), demote(MEDIUM, 2) floored at NONE, demote(NONE, 1) stays, unknown tier returns unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_ensemble_override.py::TestOverrideConfig -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement OverrideConfig and promote/demote**

Add to ensemble_override.py above apply_ml_override:
- OverrideConfig(BaseModel) with fields: top_1_percentile(85.0), bottom_1_percentile(15.0), min_confidence_1(0.75), top_2_percentile(95.0), bottom_2_percentile(5.0), min_confidence_2(0.80), max_override_levels(2), early_exit_confidence(0.60)
- promote(tier, levels): index-based, capped at EXCEPTIONAL, guard for unknown tiers
- demote(tier, levels): index-based, floored at NONE, guard for unknown tiers

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_ensemble_override.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

`git commit -m "feat(engine): add OverrideConfig, promote(), demote() helpers"`

---

### Task 4: Refactor apply_ml_override for 2-level support

**Files:**
- Modify: `engine/src/margin_engine/ml/ensemble_override.py`
- Modify: `engine/tests/ml/test_ensemble_override.py`

- [ ] **Step 1: Write failing tests for 2-level override**

Add TestTwoLevelOverride:
- 2-level promote: top 5% + confidence 0.90 -> MEDIUM to EXCEPTIONAL
- 2-level demote: bottom 5% + confidence 0.90 -> EXCEPTIONAL to MEDIUM
- 1-level when confidence between gates: top 5% + confidence 0.76 -> MEDIUM to HIGH only
- No override below 0.75: bottom 5% + confidence 0.70 -> unchanged
- 2-level disabled (max_override_levels=1): top 5% + confidence 0.90 -> 1 level only
- Backward compat: no config kwarg uses defaults, same as existing tests

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_ensemble_override.py::TestTwoLevelOverride -v`
Expected: Most tests FAIL with TypeError (unexpected keyword argument 'config'). The backward-compat test (no config kwarg) will PASS -- this is expected.

- [ ] **Step 3: Refactor apply_ml_override**

Add optional `config: OverrideConfig | None = None` parameter.
Logic: (1) model_qualifies gate, (2) compute ml_signal via blend_with_vae internal 60/40, (3) confidence from vae_variance, (4) early exit if confidence < config.early_exit_confidence, (5) percentile rank, (6) 2-level check first (stricter), (7) 1-level check, (8) no override. Use promote()/demote() helpers.

**IMPORTANT:** Do NOT change the internal `blend_with_vae(gbm_weight=0.60, vae_weight=0.40)` call inside apply_ml_override. This is a SEPARATE internal blend (GBM vs VAE within the ML signal) and must NOT use BlendConfig. Only the top-level composite/ML blend uses BlendConfig.

- [ ] **Step 4: Run ALL override tests**

Run: `uv run pytest engine/tests/ml/test_ensemble_override.py -v`
Expected: All PASS

- [ ] **Step 5: Run full ML test suite**

Run: `uv run pytest engine/tests/ml/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

`git commit -m "feat(engine): support 2-level ML conviction override with OverrideConfig"`

---

### Task 5: Final integration check

- [ ] **Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All ~2778+ tests PASS

- [ ] **Step 2: Run linter**

Run: `uv run ruff check --fix . && uv run ruff format .`
Expected: Clean

- [ ] **Step 3: Commit any lint fixes**

`git commit -m "style: lint and format BlendConfig + override changes"`
