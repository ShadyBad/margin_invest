# Confidence Threshold Triggers — Technical Design & Risk Analysis

**Date**: 2026-02-26
**Status**: Analysis complete — recommends narrow implementation (consistency detection only)

## Context

The Margin Invest scoring pipeline executes deterministic binary logic gates (elimination filters) and continuous factor scoring without assessing upstream data confidence. This document evaluates whether introducing explicit confidence threshold triggers at each logic gate would improve system robustness.

The analysis is forward-looking. No acute data quality failures have been observed, but the pipeline currently lacks defense against silent provider errors (plausible but wrong values).

## Conceptual Model

### Signal Confidence vs Rule Confidence

**Signal confidence**: How trustworthy is this input value? Example: yfinance returns `P/E = 14.2` — is that number correct, current, and consistently calculated?

**Rule confidence**: Given trusted inputs, is this rule meaningful for this asset? Example: Altman Z-Score applied to a SaaS company with negative tangible assets. The inputs are correct but the model wasn't designed for the asset class.

The current pipeline handles both implicitly:
- `FilterResult.insufficient_data` → signal confidence (missing inputs)
- `FilterResult.warning` / sector exemptions → rule confidence (model applicability)
- `data_quality_gate.py` → signal confidence (coverage < 0.60 forces NONE conviction)

### Confidence Propagation

In a multi-stage pipeline (ingestion → filters → factors → composite → conviction), confidence compounds. Naive multiplication creates a death spiral: 0.9 × 0.85 × 0.92 × 0.88 = 0.62, which looks unreliable despite each stage being individually solid.

The correct approach: track confidence dimensions independently and collapse only at decision boundaries (conviction assignment, position sizing).

### What Confidence Is Not

Confidence scoring here is not a Bayesian posterior about investment merit. It expresses uncertainty about whether the data feeding deterministic rules is trustworthy enough for those rules to produce meaningful output. It's orthogonal to scoring — it doesn't change what rules compute, only whether we trust the computation.

## Architecture Design

### Attachment Level

Three options evaluated:

- **Field-level** (every Decimal gets a shadow confidence value): ~60 fields × N periods = hundreds of values. Pydantic models double in size. **Overkill.**
- **Record-level** (one confidence struct per `FinancialPeriod`): Matches existing `data_coverage` pattern but richer. **Right level.**
- **Decision-level** (confidence only on `FilterResult` and `CompositeScore`): Cheapest, but can't diagnose root cause. **Too coarse.**

Recommendation: Record-level with selective field-level overrides for known-unreliable fields (e.g., `shares_outstanding` from yfinance after stock splits).

### Confidence Dimensions

| Dimension | Measures | Computation |
|-----------|----------|-------------|
| Freshness | Data age vs expected cadence | `1.0 - (days_since_filing / max_acceptable_days)` clamped to [0,1] |
| Completeness | Non-null field fraction | Existing `data_coverage` extended to input layer |
| Source tier | Provider reliability | Static mapping: FMP=0.95, SEC EDGAR=0.98, yfinance=0.75, Finnhub=0.80 |
| Consistency | Cross-period / cross-provider agreement | Flag when current period deviates >3σ from trailing 5-year pattern |

Composite confidence = **minimum** of dimensions (weakest-link model), not average.

### Pipeline Integration Points

1. **Ingestion**: Compute `DataConfidence` when `FinancialPeriod` is constructed from JSONB. Store alongside `FinancialData`.
2. **Elimination filters**: Filters receive confidence. If composite confidence < threshold, filter returns INCONCLUSIVE even with sufficient data.
3. **Factor scoring**: `FactorScore` gains optional `input_confidence: float`. Does not change `raw_value` or `percentile_rank`.
4. **Composite scoring**: `CompositeScore.data_coverage` supplemented by richer `DataConfidence` struct. Quality gate generalizes to consider minimum confidence dimension.
5. **Conviction**: No change. Confidence gating happens before conviction assignment.

### Threshold Methodology

Static thresholds recommended (no adaptive thresholds without labeled outcomes):
- Freshness < 0.3 (filing > 200 days old) → flag
- Completeness < 0.6 → force NONE conviction (existing gate)
- Source tier < 0.7 → flag for cross-validation
- Consistency < 0.5 (major deviation) → flag

Adaptive thresholds require ground truth (real portfolio returns). Until PIT backtesting is live, static is honest.

### Human-Review Routing

No human review queue. Solo operator with automated pipeline — a queue becomes an ignored backlog. Instead:

- `min(confidence) < HARD_FLOOR` → show with explicit "low confidence" badge
- `min(confidence) < SOFT_FLOOR` → show with caveat
- Otherwise → normal pipeline

Low-confidence results surfaced transparently to end users, consistent with "forensic transparency" positioning.

## Failure Mode Prevention

### Garbage-In-Garbage-Out Vectors

**Vector 1 — Silent provider errors** (e.g., wrong `shares_outstanding` after stock split):
- Current defense: None.
- Confidence gating: Consistency dimension catches >3σ cross-period deviations.
- Assessment: **Strongest argument for this feature.** Only genuine gap in current pipeline.

**Vector 2 — Stale data** (provider returns old quarter):
- Current defense: Freshness tiers in `freshness.py` (fresh/stale/expired).
- Confidence gating: Makes freshness continuous instead of categorical. Marginal improvement.

**Vector 3 — Missing data** (None values — zero or absent?):
- Current defense: `insufficient_data`, `data_coverage` < 0.6 forces NONE.
- Confidence gating: Adds almost nothing new. Completeness dimension is a rename.

### Contradictory Data

Provider fallback chain (FMP → yfinance → EDGAR) takes first success and stops. Cross-validation requires running multiple providers in parallel — doubles API costs.

Pragmatic middle ground: cross-validate only the ~5 fields critical to elimination filters (revenue, total_assets, operating_income, free_cash_flow, interest_expense), only when primary provider has source_tier < 0.9.

### Cascading Uncertainty

When >50% of elimination filters return INCONCLUSIVE, treat the entire filter stage as low-confidence and propagate to composite score via the quality gate. Don't invent a new elimination rule.

## System-Level Implications

### Determinism and Reproducibility

Confidence computation is a pure function of (data values, filing dates, provider name, historical values). **Determinism preserved.**

Subtle UX threat: confidence can cause the same ticker to appear flagged on Tuesday and clean on Wednesday as new data arrives. Mitigation: always show the score with its confidence badge — never silently suppress.

### Latency and Computational Overhead

| Dimension | Overhead |
|-----------|----------|
| Freshness | ~0 (datetime math) |
| Completeness | ~0 (already computed) |
| Source tier | ~0 (dict lookup) |
| Consistency | **Moderate** — requires loading 5 prior periods |

- Per-ticker: ~5-15ms additional (consistency check DB reads)
- Full universe (500 tickers): ~2.5-7.5s additional on batch scoring
- Relative to 1200s ingest_batch timeout: negligible

### Lines-of-Code Estimate (Full Framework)

| Component | Lines |
|-----------|-------|
| `DataConfidence` model | ~40 |
| Confidence computation service | ~150-200 |
| `FinancialPeriod` construction changes | ~30 |
| Filter modifications (6 filters × ~10 lines) | ~60 |
| `CompositeScore` changes | ~20 |
| Generalized `data_quality_gate.py` | ~30 |
| Frontend confidence badge | ~80 |
| Tests | ~400-500 |
| **Total** | **~850-1000** |

Test surface expansion: ~40-50 new test cases (~2% increase on 2124 engine tests).

### Feedback Loop Effects

Self-reinforcing quality gradient: good-data tickers get scored → get attention → get re-ingested → stay good. Poor-data tickers get suppressed → deprioritized → stay poor. Acceptable for this product (not aiming for total coverage), but creates natural large-cap skew.

### Over-Badging Risk

If >25% of universe carries confidence warnings, users stop reading them. Calibrate thresholds so <10% of scored tickers carry warnings in steady state. Requires shadow-mode distribution analysis before setting thresholds.

### New Bias Vectors

1. **Provider-tier bias**: Tickers only covered by yfinance (smaller companies) get systematically lower confidence regardless of accuracy.
2. **Recency bias**: Freshness dimension favors companies with standard fiscal year-ends and prompt reporting.
3. **Sector completeness bias**: Some sectors (Utilities, Energy) have non-standard reporting. Completeness dimension penalizes legitimately N/A fields.

All manageable with sector-aware threshold calibration, but they create new attack surfaces on the "sector-neutral" guarantee.

## Trade-offs

### Precision vs Recall

Confidence gating trades recall for precision. Fewer clean scores, but trustworthy ones. Correct trade direction for investment analysis — a user acting on a confidently-wrong score suffers more than one who sees "insufficient confidence."

Critical question: what fraction of the current universe would trip warnings? <10% = pure win. >25% = product degradation.

### Autonomy vs Oversight

Confidence scoring is deterministic rules applied to data quality — consistent with "no human judgment" principle. But introduces meta-judgments (source tier assignments, threshold calibration) that are harder to backtest than scoring parameters.

### Operational Complexity vs Robustness

Adds ~30% more operational surface: debugging wrong scores requires checking confidence dimensions, adding providers requires assigning source tiers, changing filter thresholds requires confidence recalibration, pipeline monitoring requires confidence distribution tracking.

## Evaluation Framework

### Metrics

1. **False suppression rate**: Fraction of flagged tickers with actually-correct data. Target: <5%.
2. **Missed error rate**: Fraction of discovered data errors that confidence should have caught. Target: >80%.
3. **Confidence distribution stability**: Weekly distribution of min(confidence) across universe. Leftward drift = quality degrading.
4. **Conviction-confidence correlation**: High-conviction + low-confidence = miscalibration signal.

### Simulation Strategy

Shadow-mode analysis before implementation:
1. Take current scored universe
2. Retroactively compute `DataConfidence` for each ticker
3. Identify which would have been flagged
4. Manually inspect flagged set for false positives

This is a spreadsheet exercise, not an engineering project. Validates the feature before writing code.

### Degradation Conditions

1. **Uniform low-quality data**: If yfinance is the only source for most tickers, source tier becomes a constant penalty — flags everything equally, adds noise without information.
2. **Earnings season volatility**: Predictable seasonal freshness drops create waves of degraded scores exactly when users want updated analysis.
3. **Threshold ossification**: Static thresholds set today may not match data patterns in 6 months without periodic recalibration.

## Recommendation

**Do not build the full confidence framework.**

Most of what it would do, the system already handles categorically via `data_coverage`, `insufficient_data`, freshness tiers, and sector exemptions. Making these continuous adds ~1000 lines and ~30% operational complexity for marginal improvement in already-covered dimensions.

**Instead, build only the consistency dimension** — cross-period deviation detection — as a standalone post-ingestion validation step. This targets the one genuine gap (silent provider errors) with:
- ~200 lines instead of ~1000
- No changes to scoring models
- Implementable as a validation pass that flags suspect tickers for re-ingestion from a fallback provider

### Narrow Implementation Scope

A `validate_data_consistency()` function that runs after ingestion:
1. Loads current + 4 prior periods for each ticker
2. Computes z-scores for critical fields (revenue, total_assets, shares_outstanding, operating_income, free_cash_flow)
3. Flags tickers with any field >3σ deviation
4. Triggers re-ingestion from next provider in fallback chain
5. If re-ingestion confirms the value, clears the flag (legitimate business change)
6. If re-ingestion disagrees, attaches a consistency warning to the `FinancialData` record

This approach captures the primary value of confidence gating without the full framework's overhead.
