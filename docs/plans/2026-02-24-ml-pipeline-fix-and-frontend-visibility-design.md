# ML Pipeline Fix & Frontend Visibility Design

**Date:** 2026-02-24
**Status:** Approved

## Overview

The ML V4 scoring pipeline is built and merged but disconnected from production. Models train on stub data (all 50th percentile), the API still serves v2 scores, and zero ML intelligence is visible to users. This design fixes the pipeline, cuts over the API to V4Score, and adds an ML Audit Panel to the asset detail page.

## Approach: Backend-First, Then Frontend

Fix ML training quality and API layer completely before building UI. Each layer is testable in isolation, and the frontend gets real data from day one.

## Section 1: ML Training Quality Fixes

### 1a. Fix CompositeScore Reconstruction

**Problem:** `train_ml_models` in `workers.py` builds feature matrices from stub `FactorBreakdown` objects (all 50th percentile). The `score_detail` JSONB already contains real factor breakdowns but they're not unpacked.

**Fix:** Replace stub-factor reconstruction with real JSONB unpacking. Parse `score_detail` into real `FactorBreakdown` objects (quality, value, momentum with sub_scores) so `build_feature_matrix()` receives actual factor percentiles.

**Fallback:** If a score's JSONB is missing or malformed, skip that sample rather than inject stubs.

### 1b. Remove Phantom Percentiles

**Problem:** `insider_percentile` and `institutional_percentile` are hardcoded at 50.0 in `TickerV4Data` construction. No data source exists for these fields.

**Fix:** Remove `insider_percentile` and `institutional_percentile` from `TickerV4Data` and Track B cascade inputs. Track B still functions on its remaining gates (valuation, catalyst, capital allocation). Re-add when a 13F data pipeline exists.

### 1c. Fix composite_score (Always 0.0)

**Problem:** `V4ResultWithML.composite_score` is always 0.0 — the V4 orchestrator assigns conviction levels but never computes a raw score.

**Fix:** Compute as the weighted average of the winning track's gate scores, matching how v2 computes `composite_raw_score`.

### 1d. Compute sustainable_growth_rate

**Problem:** Hardcoded at 0.08 in `cli.py`. Used in Track A but never derived from financials.

**Fix:** Compute as `retention_ratio * ROE` from the ticker's financial data. Fall back to 0.08 if data is missing.

## Section 2: API V4 Cutover with Graceful Fallback

### 2a. Score Endpoint Reads V4Score First

Update `_score_response_from_row()` query logic:

1. Look up latest V4Score for the ticker
2. If found: build response from V4Score (including ML fields)
3. If not found: fall back to existing Score table (v2/v3 data)
4. Response shape is identical either way — ML fields are null in fallback

The fallback is per-ticker, not global. As the V4 pipeline scores the full universe nightly, the fallback window shrinks to zero.

### 2b. New Fields on ScoreResponse

| Field | Type | Source |
|-------|------|--------|
| `ml_alpha` | `float \| None` | V4Score.ml_alpha |
| `ml_confidence` | `float \| None` | V4Score.ml_confidence |
| `ml_override` | `str \| None` | V4Score.ml_override ("promoted"/"demoted"/"none") |
| `rules_conviction` | `str \| None` | V4Score.rules_conviction (pre-ML conviction) |
| `style` | `str \| None` | V4Score.style ("value"/"blend"/"growth") |
| `regime` | `str \| None` | V4Score.regime |
| `track_a` | `dict \| None` | V4Score.track_a (cascade detail JSONB) |
| `track_b` | `dict \| None` | V4Score.track_b |
| `track_c` | `dict \| None` | V4Score.track_c |
| `ml_model_qualified` | `bool \| None` | From latest MlModelRun |
| `ml_model_rank_ic` | `float \| None` | From latest MlModelRun |
| `ml_model_trained_at` | `str \| None` | From latest MlModelRun |

All nullable. Null when serving v2 fallback data or when no ML model exists.

### 2c. Lightweight Fields on PickSummary (Dashboard)

| Field | Type |
|-------|------|
| `ml_override` | `str \| None` |
| `style` | `str \| None` |

Enough for a badge on stock cards. No heavy ML detail on the dashboard.

### 2d. TypeScript Type Mirrors

Add the same fields to `ScoreResponse` and `PickSummary` interfaces in `web/src/lib/api/types.ts`.

## Section 3: ML Audit Panel (Frontend)

### 3a. MLAuditPanel Component

Placed after the Conviction Engine section in the asset detail page. Three states:

**State 1: No qualified model**

Displays: "ML models are training. Current rank IC ({value}) is below the 0.15 qualification threshold. Scoring is rules-only." Shows last training date.

**State 2: Qualified model, no override**

Displays:
- Model status row: qualified indicator, rank IC, training date
- Three metric cards: ML Alpha (value + universe percentile), Confidence (percentage), Override (none)
- Verdict explanation: why ML didn't override (e.g., "ML signal is moderate (71st pct) but below the 85th threshold for promotion. Rules-based conviction preserved.")

**State 3: Qualified model with override**

Displays:
- Model status row: qualified indicator, rank IC, training date
- Three metric cards: ML Alpha (value + percentile), Confidence (percentage), Override (promoted/demoted with before/after conviction)
- Verdict explanation: why ML overrode (e.g., "ML signal is strong (92nd pct) with high confidence (81%). Conviction promoted from MEDIUM to HIGH.")
- Override rules checklist showing which gates passed:
  - Model qualified (IC > 0.15)
  - Confidence >= 0.75
  - ML percentile >= 85 (promotion) or <= 15 (demotion)

### 3b. Override Badge on Conviction

In the existing Conviction Engine section, add a badge next to the conviction level when ML override is active:
- Promoted: `ML-promoted` in bullish color
- Demoted: `ML-demoted` in bearish color
- None: no badge

### 3c. Style Tag in Hero Header

Display the style classification ("Value" / "Blend" / "Growth") as a tag in the hero metadata ribbon, alongside sector and growth stage.

### 3d. ML Override Badge on Dashboard Stock Cards

Subtle indicator on pick cards when ML-promoted or ML-demoted. Small arrow icon next to conviction. No badge when override is "none."

## Out of Scope

- 13F / insider transaction data pipeline (deferred until data source available)
- Model A/B testing or versioning
- Concept drift detection or alerting
- Online/incremental learning

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| JSONB unpacking | Real factor reconstruction from score_detail | Golden-value test with known JSONB payloads |
| Phantom removal | Track B without insider/institutional inputs | Verify cascade still produces correct convictions |
| composite_score | Weighted track average | Golden-value test against hand-calculated scores |
| sustainable_growth_rate | retention_ratio * ROE computation | Parametrized test with known financial data |
| V4 API cutover | Score endpoint returns V4 data | Integration test with V4Score in test DB |
| V4 fallback | Score endpoint falls back to v2 | Integration test with V4Score absent |
| ML fields in response | All 12 fields populated correctly | Snapshot test of response shape |
| MLAuditPanel states | All 3 states render correctly | Vitest + testing-library for each state |
| Override badge | Badge appears/disappears correctly | Component test with mock ML data |
| Dashboard badge | ML indicator on stock cards | Component test with mock PickSummary |

Coverage targets: engine >= 95%, api >= 90%, web >= 80%.

## Key Design Decisions

1. **V4-first with per-ticker fallback:** Clean cutover without breaking tickers that haven't been V4-scored yet. Fallback is transparent to the frontend.
2. **Remove phantom factors rather than fake them:** Hardcoded 50th percentile is worse than absent. Tightens the signal and maintains transparency.
3. **ML Audit Panel as separate section:** Keeps conviction engine focused on track selection. ML audit tells its own story: "rules decided, then ML reviewed."
4. **Honest empty state:** When no qualified model exists, say so with the actual rank IC number. Consistent with "the system has no opinion" ethos.
5. **Lightweight dashboard fields:** Only `ml_override` and `style` on PickSummary. Heavy ML detail belongs on the asset detail page, not the card grid.
