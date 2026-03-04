# Scoring Engine Audit & Calibration Design

**Date:** 2026-03-03
**Status:** Draft — pending approval
**Scope:** Full technical audit of scoring engine, backtesting calibration, factor system, and API alignment

---

## I. Executive Verdict

**Does the system currently justify the "once-in-a-generation" claim?**

**No.** Three structural reasons:

1. **Zero empirical validation exists.** PIT tables are empty. No walk-forward backtest has executed against real historical data. Every threshold (76/71/66 composite cutoffs, Track A power>0.15/moat>=3/gap>0.08, Track B asymmetry>5.0/catalyst>55) is a first-principles guess.

2. **The V1/V2 additive scoring path is structurally incapable of extreme selectivity.** A weighted average of percentile ranks (`Q×0.35 + V×0.30 + M×0.35`) regresses toward the mean. This architecture cannot distinguish "generational" from "above average."

3. **Critical V3/V4 inputs are zeroed or stubbed.** Sentiment returns 0.0 for all stocks. Earnings revision returns 0.0. The contrarian bonus (primary mechanism for narrative–fundamental divergence detection) is permanently disabled because it requires `sentiment < 0.0`.

**However:** The V3/V4 multiplicative gate cascade is correctly designed for extreme selectivity. The engineering quality is high. The path to a credible product is clear, and the path to genuine alpha research is plausible with 2-3 iterations.

---

## II. Critical Gaps (Ranked by Expected Alpha Impact)

### Gap 1: No Empirical Calibration — Backtesting Never Executed

**Why it matters:** Every threshold is theoretical. The 76/71/66 composite cutoffs were chosen without empirical support. Track A's `compounding_power > 0.15` for EXCEPTIONAL could be trivially easy or impossibly hard. The system could surface 0 or 200 EXCEPTIONAL names — neither outcome would be surprising because no one has checked.

**Quantified impact:** Uncalibrated thresholds dominate all other issues. If the EXCEPTIONAL gate passes 0.1% of the universe, you get 0-1 names (useless). If 15%, you get 75+ (not selective). Academic literature suggests optimal concentrated factor portfolios hold 20-50 names; the "3-8 EXCEPTIONAL/month" target requires empirical confirmation.

**Expected alpha impact:** All of it. Without calibration, expected alpha is undefined.

**Implementation complexity:** Medium. Infrastructure exists (simulator, replay orchestrator, walk-forward engine, PIT schema, cost model). Blocked by PIT data population.

### Gap 2: Sentinel Factor Stubs — Sentiment (0.0) and Earnings Revision (0.0)

**Why it matters:** Two of nine momentum sub-factors return hardcoded 0.0 for every stock.

- **Sentiment at 0.0** normalizes to 5.0/10.0 midpoint. The contrarian bonus never fires (requires `clamped < 0.0` at `sentiment_score.py:58`). The primary mechanism for detecting narrative–fundamental divergence is permanently disabled.

- **Earnings revision at 0.0** removes the most predictive short-term alpha signal in academic literature (PEAD, typical Rank IC 0.05-0.08).

- Both zeros **dilute the momentum FactorBreakdown average.** With 9 sub-factors and 2 at 0.0, `average_percentile` is pulled down for every stock with strong real momentum.

**Quantified impact:** Removing two zero-valued factors from a 9-factor average raises effective momentum percentile by ~11% for strong-momentum stocks. For Track B, the catalyst gate would gain a third signal leg, reducing false negatives by an estimated 15-25%.

**Expected alpha impact:** High. PEAD is the most robust equity anomaly.

**Implementation complexity:** Medium (earnings revision). High (sentiment LLM pipeline).

### Gap 3: Additive V1/V2 Composite Structurally Guarantees Mediocrity

**Why it matters:** The V1 composite formula (`composite.py:73-77`):

```python
composite_percentile = (
    quality.average_percentile * 0.35
    + value.average_percentile * 0.30
    + momentum.average_percentile * 0.35
)
```

This rewards consistency over extremity. A deep-value turnaround with value=99th, quality=60th, momentum=20th gets composite `60×0.35 + 99×0.30 + 20×0.35 = 57.7` — classified NONE. V3 Track B would correctly flag this as high-asymmetry mispricing.

**Critical problem:** `CompositeScore.composite_tier` is a property reading `composite_raw_score` against 76/71/66 thresholds (`models/scoring.py:152-159`). V3/V4 conviction lives in `V3TrackResult.conviction` / `V4Result.conviction`. Two tier assignments can coexist for the same stock.

**Quantified impact:** Additive composites with 3 factors at ~0.33 weights compress output standard deviation to ~58% of individual factor distributions (CLT). This mathematically restricts tail access.

**Expected alpha impact:** Moderate in isolation (V3/V4 already addresses this). But any code path routing through V1 composite → tier produces inferior classifications.

**Implementation complexity:** Low. Architectural decision.

### Gap 4: Missing Structural Alpha Sources for Asymmetric Discovery

**Why it matters:** 42 quantitative factors, but almost all measure fundamentals, valuation, or price momentum. Signals most associated with extreme mispricings are structural/behavioral:

| Missing Signal | Evidence | Implementation Complexity |
|---|---|---|
| Forced selling (index deletions, fund liquidations, spin-offs) | Strong (Greenblatt 2006) | High |
| Short interest crowding | Moderate (Desai et al 2002, IC ~0.03) | Low |
| Analyst coverage gaps | Strong (Hong/Lim/Stein 2000) | Low |
| 13D activist filings | Strong (Brav et al 2008, avg +7% around filing) | Medium |
| Management inflection (new CEO/CFO) | Moderate (practitioner) | Medium |
| Small/mid-cap neglect | Strong (size + information premium) | Low |

**Quantified impact:** Adding 2-3 signals to Track B's catalyst gate could increase true positive rate for asymmetric opportunities by 30-50%.

**Expected alpha impact:** High for Track B.

**Implementation complexity:** Varies. Short interest and coverage gap are Low (days). Forced selling and 13D are Medium-High (weeks).

### Gap 5: Sector Normalization Inflation in Small Sectors

**Why it matters:** `sector_neutral_ranks()` ranks within each GICS sector independently. In a 5-stock sector, ranks are {20, 40, 60, 80, 100}. Top stock gets 100th percentile regardless of absolute quality.

V4's `calibrate_cross_bucket()` partially addresses this with z-score normalization, but with 5-stock buckets z-scores have high variance.

**Quantified impact:** Sector sizes range from ~20 (Utilities) to ~80 (Technology). The inflation is most pronounced in small sectors and can push borderline stocks from HIGH to EXCEPTIONAL across three factors.

**Expected alpha impact:** Low-moderate. V3/V4 gate-based conviction uses absolute thresholds, not percentiles.

**Implementation complexity:** Low. Add `min_sector_size` fallback to universe-wide ranking.

---

## III. Architectural Judgment

**Choice: C) Hybrid with strict hierarchy**

### Option A rejected: Keep dual scoring as-is

Four parallel scoring philosophies with ambiguous authority:
- V1 additive → `composite_raw_score` → `CompositeScore.composite_tier` property
- V2 dual-track → its own tier via `dual_track.py`
- V3 multiplicative cascade → tier via `assess_track_a/b_conviction()`
- V4 three-track → tier via `orchestrate_v4()`

`CompositeScore.composite_tier` reads `composite_raw_score` against 76/71/66. V3/V4 returns `CompositeTier` from absolute gates stored separately. Two tier assignments coexist — this is a latent bug.

### Option B rejected: Deprecate V1/V2 entirely

Premature. V1/V2 serve two purposes V3/V4 cannot replace today:

1. **Screening.** Additive composite produces a continuous [0, 100] score for full-universe sorting. V3/V4 produces categorical tiers with no within-tier ordering.
2. **Backtest compatibility.** `TOP_PERCENTILE` selection mode needs a continuous sort variable.

### Recommended: Hybrid with strict hierarchy

**Rule 1: Tier assignment flows only through V4.** Remove `CompositeScore.composite_tier` property's authority. Add `conviction_override: CompositeTier | None` field. When set (by V4 orchestrator), this is the tier. Fallback to threshold logic only when `None`, with deprecation warning.

**Rule 2: V1 composite percentile becomes a sort key only.** Rename semantically to `screening_score`. Used for: within-tier ranking, backtesting TOP_PERCENTILE, user-facing "overall score." Never determines conviction tier.

**Rule 3: V3/V4 multiplicative score is the within-tier sort key for CONVICTION_MOS.** `V3TrackResult.score` provides ordering within EXCEPTIONAL and HIGH tiers.

**Rule 4: V2 dual-track logic is absorbed into V3/V4.** V2's conviction gates are replicated more rigorously in V3. V2 becomes dead code, flagged for removal after backtest validation.

---

## IV. Concrete Technical Recommendations

### Phase 1: Credible V1 (Weeks 1-4)

#### Rec 1.1: Populate PIT data and run first calibration backtest

```bash
# 1. EDGAR backfill (26 XBRL fields, 2009-2025)
uv run python -m margin_api.cli edgar-backfill --start-year 2009

# 2. Price backfill (OHLCV)
uv run python -m margin_api.cli price-backfill --start-date 2009-01-01

# 3. Wire DatabasePITProvider to replay_orchestrator
# 4. Execute walk-forward backtest:
#    5yr train / 1yr test, 2009-2025, monthly rebalance
#    CONVICTION_MOS selection, transaction costs ON
```

Extract: EXCEPTIONAL/HIGH/MEDIUM/NONE count distribution, Rank IC per factor, excess CAGR/Sharpe/Sortino/drawdown by tier, regime-segmented performance.

#### Rec 1.2: Sever the tier-assignment ambiguity

In `engine/src/margin_engine/models/scoring.py`:

1. Add `conviction_override: CompositeTier | None = None` field to `CompositeScore`
2. Modify `composite_tier` property: return `conviction_override` when set, fall back to threshold logic with deprecation warning when `None`
3. In `v4_pipeline.py`, set `conviction_override` on `CompositeScore` to V4 orchestrator result's conviction
4. ~20 line change, eliminates most dangerous architectural ambiguity

#### Rec 1.3: Exclude zeroed factors from momentum average

Two options (choose one):

**Option A (cleaner):** Add `stub: bool = False` to `FactorScore`. Mark sentiment and earnings revision with `stub=True`. Modify `average_percentile` to exclude stubs.

**Option B (simpler):** Remove sentiment and earnings revision from `momentum_scores` list in the scoring pipeline until they're wired. Add them back when real data flows.

#### Rec 1.4: Recalibrate product claims

- ~~"Once-in-a-generation"~~ → "Systematic high-conviction stock selection"
- ~~"3-8 EXCEPTIONAL names"~~ → "Top-tier opportunities identified by multi-gate quantitative analysis"
- Keep EXCEPTIONAL/HIGH/MEDIUM tier language; do not attach return expectations until backtested

#### Rec 1.5: API endpoint alignment

**Problem:** The API has three scoring paths with inconsistent tier sourcing:

- `GET /api/v1/scores/{ticker}` tries V4 (published) → V4 (any) → V2 fallback
- `GET /api/v3/scores/{ticker}` returns V3-specific response
- `GET /api/public/score/{ticker}` returns lightweight summary

After the architectural change (Rec 1.2), the API must reflect V4 as the single authority.

**Changes required:**

1. **`GET /api/v1/scores/{ticker}` — make V4 the only path.**
   - Remove V2 (Score table) fallback entirely. If no V4Score exists for a ticker, return 404 rather than falling back to stale V2 data with different tier semantics.
   - In `routes/scores.py`, the current fallback chain (`v4_published → v4_any → score_v2`) becomes `v4_published → v4_any → 404`.
   - Add `scoring_version: str` field to `ScoreResponse` (always `"v4"`) so clients can verify.

2. **`GET /api/v1/scores` — filter exclusively on V4Score table.**
   - The `conviction` query parameter currently filters on `conviction_level` from the Score table. Change to filter on V4Score's `conviction` column.
   - Ensure `composite_tier` in response is sourced from V4's `conviction` field, not from the `CompositeScore.composite_tier` property.

3. **Deprecate `GET /api/v3/scores` routes.**
   - V3 is an intermediate version superseded by V4. The `/api/v3/scores` endpoint should return a 301 redirect to `/api/v1/scores` with a deprecation header, or be removed.
   - Timeline: mark deprecated in Phase 1, remove in Phase 2.

4. **`GET /api/public/score/{ticker}` — source from V4Score.**
   - Currently builds `PublicScoreResponse` from Score (V2) table. Switch to V4Score.
   - `composite_tier` sourced from V4's `conviction` field.
   - Add `opportunity_type` to public response (helps free-tier users understand the scoring thesis).

5. **`ScoreResponse` schema changes:**
   - Add `scoring_version: str` field (value: `"v4"`)
   - Add `conviction_source: str` field (value: `"v4_gate_cascade"` or `"v1_percentile_threshold"` during transition)
   - Ensure `composite_tier` is populated from V4's conviction, not derived from `composite_raw_score`
   - Keep `score` (the V1 additive composite) as `screening_score` for backwards compatibility — add alias in schema

6. **`GET /api/v1/scores/{ticker}/history` — handle version transitions.**
   - Historical scores may span V2 and V4 eras. Add `scoring_version` per `ScoreHistoryPoint`.
   - Frontend can display a visual marker where scoring methodology changed.

7. **Backtest endpoints — wire to real PIT data.**
   - `GET /api/v1/backtest/default` currently returns synthetic metrics from `_build_synthetic_metrics()`. After PIT data population and first backtest execution, this must return real persisted results from `backtest_runs` table.
   - `POST /api/v1/backtest/replay` must validate that PIT data exists for the requested date range before enqueueing.
   - Add `GET /api/v1/backtest/calibration-status` endpoint returning: PIT data coverage (date range, ticker count), last backtest run timestamp, validation result (pass/fail per metric), current threshold config.

8. **Admin endpoints — add calibration controls.**
   - `POST /admin/calibration/sweep` — enqueue threshold sensitivity sweep (Rec 2.4). Returns job ID.
   - `GET /admin/calibration/results/{job_id}` — retrieve sweep results (threshold → metric mapping).
   - `POST /admin/calibration/apply` — write validated thresholds to `thresholds.yaml` and trigger re-scoring.
   - `GET /admin/scoring/factor-ic` — return Rank IC per factor from latest backtest run. Essential for monitoring factor decay.

9. **Frontend type updates (`web/src/lib/api/types.ts`):**
   - Add `scoring_version: string` to `ScoreData` type
   - Add `conviction_source: string` to `ScoreData` type
   - Rename `score` to `screening_score` (keep `score` as alias for backwards compat)
   - Add `CalibrationStatus` type for new calibration endpoint
   - Remove V3-specific types after V3 route deprecation

---

### Phase 2: Alpha Foundation (Weeks 5-12)

#### Rec 2.1: Wire earnings revision signal

Highest-ROI missing factor. PEAD has strongest out-of-sample evidence.

1. Data: yfinance earnings data (already fetched) or Finnhub estimate revision endpoint
2. Signal: `revision_score = (current_consensus - consensus_90d_ago) / std(estimate_changes)`
3. Integrate into momentum sub-factors with weight 1.5x
4. Add to Track B catalyst gate as third component alongside SUE and institutional accumulation

Expected Rank IC: 0.04-0.08.

#### Rec 2.2: Add short interest signal

Lowest-complexity new alpha source.

1. Data: FINRA short interest (biweekly, free) or yfinance `info['shortPercentOfFloat']`
2. Signal: `short_squeeze_score = short_pct_float × (quality_percentile / 100)`
3. Track B catalyst amplifier: if `short_pct_float > 15%` AND quality floor passes AND momentum turning positive → boost catalyst by 1.5x

Expected Rank IC: 0.02-0.04.

#### Rec 2.3: Add analyst coverage gap signal

Trivially implementable from existing data.

1. Count analysts from existing price target data
2. Signal: `coverage_gap = 1.0 if analysts <= 2, 0.5 if analysts <= 5, 0.0 otherwise`
3. Track B catalyst modifier — mispricings in under-covered names are more likely real
4. Combine with neglect score: `neglect_score = coverage_gap × (1.0 - market_cap_percentile / 100)`

#### Rec 2.4: Run threshold sensitivity sweep

After first backtest (Rec 1.1), use existing `threshold_sensitivity.py`:

1. Sweep Track A: `compounding_power` ∈ {0.05, 0.08, 0.10, 0.12, 0.15, 0.20}, `moat_durability` ∈ {2, 3}, `growth_gap` ∈ {0.02, 0.04, 0.06, 0.08, 0.10}
2. Sweep Track B: `asymmetry_ratio` ∈ {2.0, 3.0, 4.0, 5.0, 7.0}, `catalyst_percentile` ∈ {30, 40, 50, 55, 60}
3. Per configuration: count EXCEPTIONAL names per rebalance, excess CAGR, Sharpe, max drawdown
4. Select thresholds producing 3-15 EXCEPTIONAL names/month with excess CAGR > 5%, Sharpe > 1.0
5. Store in `engine/config/thresholds.yaml`

#### Rec 2.5: API enhancements for Phase 2 signals

1. **`ScoreResponse` additions:** Add `short_interest_pct: float | None`, `analyst_count: int | None`, `coverage_gap_score: float | None` to the response schema.
2. **Track B detail enrichment:** When `opportunity_type == "mispricing"`, include `catalyst_components` sub-object: `{ sue_percentile, accumulation_percentile, revision_score, short_squeeze_score, coverage_gap }`.
3. **Factor IC monitoring endpoint:** `GET /api/v1/scores/factor-health` returning per-factor Rank IC, staleness, and data coverage. Helps users understand which signals are active vs stubbed.

---

### Phase 3: Genuine Alpha Research (Months 3-6)

#### Rec 3.1: Implement deterministic sentiment pipeline

1. Source: SEC 10-K/10-Q MD&A sections (EDGAR pipeline) + earnings call transcripts (new data source needed)
2. LLM: Claude API, temperature=0. Output: `{ sentiment_score: float [-5, +5], key_risks: list[str], management_tone: str }`
3. Contrarian detection: `sentiment < -2.0` AND `momentum_percentile < 30` AND `quality_percentile > 70` → `has_contrarian_signal = True`
4. Cache per (ticker, filing_date). Estimated cost: ~$40/year for 500 stocks quarterly

#### Rec 3.2: Build forced selling event detector

1. Index deletions: S&P reconstitution announcements (quarterly). ~5-7% selling pressure over 5 days
2. Spin-offs: SEC Form 10-12B filings
3. Fund liquidation: 13F disappearances
4. Signal: binary flag per event type, 30-day decay window, weight by estimated selling pressure

#### Rec 3.3: Deprecate V2 after backtest validation

1. Run V2 and V4 in parallel for one scoring cycle, compare tier assignments
2. If V4 matches V2's EXCEPTIONAL/HIGH for >95% of names, V2 is redundant
3. Remove `dual_track.py`, `composite_compounder.py`, `composite_mispricing.py`
4. Remove V2 Score table fallback from all API routes
5. Simplify: elimination filters → V4 orchestrator → screening score

#### Rec 3.4: API cleanup for Phase 3

1. **Remove V3 routes entirely** (`routes/v3_scores.py`). All consumers should use `/api/v1/scores`.
2. **Remove V2 fallback** from `GET /api/v1/scores/{ticker}`. V4-only.
3. **Add sentiment fields to `ScoreResponse`:** `sentiment_score: float | None`, `contrarian_signal: bool`, `management_tone: str | None`.
4. **Add forced selling event endpoint:** `GET /api/v1/events/forced-selling` returning active events with affected tickers, event type, estimated selling pressure, and decay timeline.
5. **Backtest endpoint evolution:** `GET /api/v1/backtest/default` should return real validated results. Add `calibration_validated: bool` and `last_calibration_date: str` to response.

---

## V. Validation Framework

### Backtest Design

**Primary backtest:**

| Parameter | Value | Rationale |
|---|---|---|
| Period | 2009-01-01 to 2025-12-31 | GFC recovery, bull run, COVID, 2022 rate shock, AI rally |
| Walk-forward | 5yr train / 1yr test, rolling 1yr | Existing `walk_forward.py`. 12 out-of-sample windows |
| Universe | S&P 500 constituents as-of-date | PIT universe memberships, survivorship-bias-free |
| Rebalance | Monthly | Product claim cadence |
| Selection | CONVICTION_MOS | Tests actual product thesis |
| Benchmark | S&P 500 total return (SPY) | Standard institutional benchmark |
| Costs | ON (10 bps + spread + sqrt impact) | Existing `cost_model.py` defaults |
| Scoring | V4 orchestrator (Track A + B + C) | Architecture being validated |

**Secondary backtests:**

1. V1 additive TOP_PERCENTILE (top 5%) — does V4 add value over naive selection?
2. V4 with relaxed thresholds (50% of defaults) — is system too tight?
3. V4 Track A only — isolate compounder alpha
4. V4 Track B only — isolate mispricing alpha
5. Equal-weight universe (no selection) — null hypothesis

### Threshold Targets

**Minimum viable product (credible v1):**

| Metric | Target | Failure |
|---|---|---|
| EXCEPTIONAL count/month | 3-15 | <1 or >30 |
| Net excess CAGR (vs SPY) | >3% | <1% |
| Net Sharpe | >0.7 | <0.4 |
| Max drawdown | <40% | >50% |
| Win rate (monthly) | >53% | <48% |
| Rank IC (composite) | >0.03 | <0.01 |
| Regime survival | Positive excess in 3/4 regimes | Negative in Bull AND Bear |

**Research-grade alpha (Phase 3):**

| Metric | Target |
|---|---|
| Net excess CAGR | >7% |
| Net Sharpe | >1.0 |
| Sortino | >1.5 |
| Information ratio | >0.7 |
| Rank IC (Track B) | >0.05 |
| EXCEPTIONAL hit rate | >65% (beat benchmark over 12mo) |
| Max drawdown relative | <0.8× benchmark drawdown |

### Statistical Benchmarks (Per Factor)

| Factor | Expected Rank IC | Minimum Acceptable |
|---|---|---|
| ROIC spread | 0.03-0.05 | 0.02 |
| EV/FCF (inverted) | 0.04-0.06 | 0.02 |
| 12-1 momentum | 0.03-0.05 | 0.02 |
| SUE | 0.05-0.08 | 0.03 |
| Piotroski F-Score | 0.02-0.04 | 0.01 |
| Institutional accumulation | 0.02-0.04 | 0.01 |
| Insider cluster | 0.02-0.03 | 0.01 |
| Composite (V1) | 0.04-0.06 | 0.02 |
| Composite (V4) | 0.06-0.10 | 0.03 |

**Track-level:**
- Track A: lower vol, higher Sortino, outperform in Bull/Sideways
- Track B: higher raw CAGR, higher drawdown, outperform in Bear-recovery/Sideways
- Track C: intermediate profile
- If Track A/B correlation > 0.7: dual-track not adding diversification value

### Failure Criteria

**Hard failures — stop and redesign:**

1. Rank IC < 0.01 for composite. No predictive signal.
2. EXCEPTIONAL produces 0 names in >50% of rebalance periods. Thresholds too tight.
3. EXCEPTIONAL underperforms HIGH or MEDIUM on net excess CAGR. Conviction assessment inverted.
4. Net Sharpe < 0.4 over full period. Indistinguishable from random.
5. Max drawdown > 60%. Risk controls broken.
6. V4 underperforms V1 top-5% on 4/5 core metrics. Gate architecture not adding value.

**Soft failures — investigate:**

7. Win rate < 53% but excess CAGR > 3%. Fat-tailed winners, lumpy returns. Acceptable if disclosed.
8. Track A/B correlation > 0.7. Dual-track not diversifying. Consider merge.
9. Negative performance in Crisis regime. Expected for long-only, but relative drawdown should be < 0.9× benchmark.
10. Factor IC varies >3× across walk-forward windows. Signal is regime-dependent.

### Validation Execution Checklist

```
□ PIT data populated (EDGAR + prices, 2009-2025)
□ DatabasePITProvider wired to replay_orchestrator
□ Primary V4 backtest executed (monthly, CONVICTION_MOS)
□ Five secondary backtests executed
□ Factor-level Rank IC computed for all 42 factors
□ Composite Rank IC computed for V1 and V4
□ Regime-segmented returns computed
□ Threshold sensitivity sweep executed
□ Hard failure criteria evaluated
□ Optimal thresholds written to thresholds.yaml
□ Track A/B return correlation computed
□ EXCEPTIONAL name count distribution plotted
□ Failure audit run on worst 5 rebalance periods
□ Results persisted to backtest_runs/backtest_results tables
□ Shadow portfolio initialized with current V4 scores
□ API endpoints updated to reflect V4-only tier authority
□ Calibration status endpoint deployed
□ Frontend types updated for scoring_version field
```

---

## VI. API Endpoint Change Summary

### Routes Modified

| Endpoint | Change | Phase |
|---|---|---|
| `GET /api/v1/scores/{ticker}` | Remove V2 fallback; V4-only with 404 if absent | 1 |
| `GET /api/v1/scores` | Filter on V4Score.conviction, not Score.conviction_level | 1 |
| `GET /api/public/score/{ticker}` | Source from V4Score; add opportunity_type | 1 |
| `GET /api/v1/scores/{ticker}/history` | Add scoring_version per history point | 1 |
| `GET /api/v1/backtest/default` | Return real results after PIT population | 1 |
| `POST /api/v1/backtest/replay` | Validate PIT data exists for requested range | 1 |
| `GET /api/v3/scores` | Deprecation header in Phase 1; remove in Phase 3 | 1→3 |

### Routes Added

| Endpoint | Purpose | Phase |
|---|---|---|
| `GET /api/v1/backtest/calibration-status` | PIT coverage, last run, validation pass/fail, thresholds | 1 |
| `POST /admin/calibration/sweep` | Enqueue threshold sensitivity sweep | 2 |
| `GET /admin/calibration/results/{job_id}` | Retrieve sweep results | 2 |
| `POST /admin/calibration/apply` | Write validated thresholds, trigger re-score | 2 |
| `GET /admin/scoring/factor-ic` | Per-factor Rank IC from latest backtest | 2 |
| `GET /api/v1/scores/factor-health` | Public factor IC, staleness, coverage | 2 |
| `GET /api/v1/events/forced-selling` | Active forced-selling events | 3 |

### Schema Changes

| Schema | Field | Change | Phase |
|---|---|---|---|
| `ScoreResponse` | `scoring_version` | Add (string, always "v4") | 1 |
| `ScoreResponse` | `conviction_source` | Add ("v4_gate_cascade" or "v1_percentile_threshold") | 1 |
| `ScoreResponse` | `screening_score` | Add (alias for existing `score` field) | 1 |
| `ScoreHistoryPoint` | `scoring_version` | Add (string) | 1 |
| `ScoreResponse` | `short_interest_pct` | Add (float, nullable) | 2 |
| `ScoreResponse` | `analyst_count` | Add (int, nullable) | 2 |
| `ScoreResponse` | `catalyst_components` | Add (sub-object for Track B detail) | 2 |
| `ScoreResponse` | `sentiment_score` | Add (float, nullable) | 3 |
| `ScoreResponse` | `contrarian_signal` | Add (bool) | 3 |
| `PublicScoreResponse` | `opportunity_type` | Add (string) | 1 |
| `FullBacktestResponse` | `calibration_validated` | Add (bool) | 3 |

### Frontend Type Updates (`web/src/lib/api/types.ts`)

| Type | Change | Phase |
|---|---|---|
| `ScoreData` | Add `scoring_version`, `conviction_source`, `screening_score` | 1 |
| `ScoreHistoryPoint` | Add `scoring_version` | 1 |
| `CalibrationStatus` | New type for calibration endpoint | 1 |
| `ScoreData` | Add `short_interest_pct`, `analyst_count`, `catalyst_components` | 2 |
| `ScoreData` | Add `sentiment_score`, `contrarian_signal` | 3 |
| V3-specific types | Remove after V3 route deprecation | 3 |
