# Style Bias Audit & Multi-Track Scoring Redesign

**Date**: 2026-02-20
**Status**: Approved
**Scope**: Engine scoring pipeline — eliminate systematic Value bias, add Growth/Blend coverage

## Problem Statement

Only Value assets are appearing as matches. Blend and Growth rarely/never surface. The hypothesis — confirmed by code audit — is that the scoring architecture, valuation methods, normalization, and hard thresholds systematically favor Value, making Growth/Blend uncompetitive.

## Design Decisions

| Decision | Answer |
|----------|--------|
| Style labels | Derived internally from own metrics |
| Drop-off point | Unknown — audit will identify |
| Style goal | Equal opportunity across all styles |
| Architecture | Open to full restructure (v4 clean break) |
| Audit data | Historical scored data exists in DB |
| Compatibility | Clean break — new v4, no migration from v3 |

---

## 1. Bias Audit Checklist

### 1.1 Selection-Rate Parity Test

| Step | What to do | What it proves |
|------|-----------|----------------|
| 1a | Classify every asset in eligible universe by style (Value/Blend/Growth) using internal metrics | Baseline style distribution |
| 1b | Count how many from each style reached HIGH+ conviction | Selection rate per style |
| 1c | Compute selection rate ratio: `(% selected from Growth) / (% selected from Value)` | Disparate impact if < 0.8 (4/5ths rule) |
| 1d | Repeat per sector to check for sector confounding | Is "Value dominance" actually sector tilt? |

### 1.2 Score Distribution Analysis

| Step | What to do | What it proves |
|------|-----------|----------------|
| 2a | Plot histograms of composite raw scores, split by style | Are Growth/Blend distributions shifted left? |
| 2b | Plot ECDF of final scores by style | Stochastic dominance check |
| 2c | Compute median score gap: `median(Value scores) - median(Growth scores)` | Magnitude of systematic shift |
| 2d | KS-test or Mann-Whitney U between Value and Growth distributions | Statistical significance |

### 1.3 Factor Contribution Decomposition

| Step | What to do | What it proves |
|------|-----------|----------------|
| 3a | Decompose composite into: `quality_contrib + value_contrib + momentum_contrib` | Which factor dimension drives the gap |
| 3b | Compute mean factor contribution by style | Quantify per-dimension advantage |
| 3c | For Track A/B: log which gates each style passes/fails | Exact gate(s) where Growth drops |
| 3d | Count gate pass rates by style | Pinpoints the killing gate |

### 1.4 Threshold Sensitivity Analysis

| Step | What to do | What it proves |
|------|-----------|----------------|
| 4a | Sweep Track B IV gate from 0.40x to 0.90x in 0.05 steps | Style mix sensitivity to 0.60x cutoff |
| 4b | Sweep ROIC quality floor from 0% to 12% | Does lowering admit Growth names? |
| 4c | Sweep FCF distress filter from 1/5 to 4/5 positive years | Are Growth names failing FCF distress? |
| 4d | Sweep conviction thresholds 65/72/79 +/- 5 points | Is final threshold the bottleneck? |

### 1.5 Sector Confounding Check

| Step | What to do | What it proves |
|------|-----------|----------------|
| 5a | Cross-tabulate style x sector for eligible universe | Growth stock sector concentration |
| 5b | Within Tech only: compare Value-Tech vs Growth-Tech selection rates | Within-sector style bias |
| 5c | Recompute asset floors with uniform 0.5x multiplier | Liquidation multiple impact |

### 1.6 Temporal Robustness

| Step | What to do | What it proves |
|------|-----------|----------------|
| 6a | Run above tests on 3 distinct time windows (bull, bear, sideways) | Regime-dependent vs structural |
| 6b | Check if Growth selection rate improves in any regime | If never, bias is hardcoded |

---

## 2. Root Cause Hypotheses (Ranked)

### Hypothesis 1: Valuation Gate (60% IV) — CRITICAL

**Mechanism**: Track B requires `price < 0.60 x ensemble_IV`. All 4 IV methods (DCF, Owner Earnings, Asset Floor, Peer EV/EBIT) are cash-flow-today or asset-based. Growth stocks derive value from distant future cash flows that get discounted heavily.

**Confirm**: Gate-pass analysis (audit 3d). If <10% of Growth stocks pass Track B Gate 1 while >40% of Value stocks pass.
**Refute**: If Growth stocks pass Gate 1 at similar rates.

### Hypothesis 2: Owner Earnings Penalizes Reinvestment — CRITICAL

**Mechanism**: `OE = CFO - 1.1 x depreciation`. Treats all CapEx as maintenance. Growth companies with heavy R&D and expansion CapEx get IV crushed.

**Confirm**: Compute OE for known Growth names (CRM, SNOW, DDOG). If OE near-zero while companies are clearly profitable on adjusted basis.
**Refute**: If OE tracks adjusted earnings reasonably for Growth names.

### Hypothesis 3: 8% ROIC Quality Floor — HIGH

**Mechanism**: Track B Gate 4 requires ROIC >= 8%. Many Growth companies in heavy investment phases show ROIC < 8% because invested capital denominator is inflated by growth CapEx.

**Confirm**: ROIC distribution by style. If median Growth ROIC < 8% while median Value ROIC > 8%.
**Refute**: If Growth names generally exceed 8%.

### Hypothesis 4: FCF Distress Filter — HIGH

**Mechanism**: Requires 3+ positive FCF years in 5. High-growth companies with aggressive reinvestment often have negative FCF in 2-3 years.

**Confirm**: Filter pass rates by style. If Growth fails at 2x+ the rate of Value.
**Refute**: If pass rates comparable across styles.

### Hypothesis 5: No Growth-Appropriate Valuation Framework — HIGH

**Mechanism**: Missing PEG, Rule of 40, revenue multiples, reinvestment-adjusted ROIC, unit economics. Growth stocks evaluated only by Value-native methods.

**Confirm**: Code inspection — confirmed, none exist.

### Hypothesis 6: Sector Liquidation Multiples — MEDIUM

**Mechanism**: Tech 0.3x, Healthcare 0.4x vs Utilities 0.8x, Staples 0.7x. Deflates downside floor for Growth, worsens asymmetry ratio.

**Confirm**: Recompute asymmetry with uniform 0.5x. If Growth ratios meaningfully improve.
**Refute**: If asset floor negligible relative to price for Growth names.

### Hypothesis 7: Single Momentum Factor — MEDIUM

**Mechanism**: Only 12-1 month price return. Missing earnings revision breadth, revenue acceleration, relative strength vs style peers.

**Confirm**: Add earnings revision breadth; if Growth composite scores meaningfully improve.
**Refute**: If adding momentum factors doesn't change style composition.

### Hypothesis 8: Growth Stage Classifier Too Restrictive — MEDIUM

**Mechanism**: "High Growth" requires revenue CAGR > 20% AND gross margin > 40% AND market cap > $2B. Excludes many legitimate growth companies.

**Confirm**: If < 5% of universe classified High Growth.
**Refute**: If 15-25% are classified High Growth.

### Hypothesis 9: Style-Blind Normalization — LOW-MEDIUM

**Mechanism**: Percentile ranks within sector only, not within style. Growth-Tech with PE 35 ranked against Value-Tech with PE 12.

**Confirm**: Compute percentiles within-sector-AND-style. If Growth percentiles meaningfully improve.
**Refute**: If within-sector already adequately separates.

### Hypothesis 10: Reverse DCF Solver Bounds — LOW

**Mechanism**: Bisection solver bounds at +/-10% to 50%. Hypergrowth companies may exceed upper bound, clipping growth gap.

**Confirm**: Check if assets hit the 50% solver bound.
**Refute**: If no assets approach 50%.

---

## 3. Architecture Redesign — Three-Track System

### 3.1 High-Level Flow

```
Universe
  |
  v
Elimination Filters (style-aware adjustments)
  |
  v
Style Classification (Value / Blend / Growth)
  |
  v
+------------------+-------------------+-------------------+
|   Track A        |   Track B          |   Track C          |
|   COMPOUNDER     |   MISPRICING       |   EFFICIENT GROWTH |
|                  |                    |                    |
|   Durable moats  |   Deep value +     |   Capital-efficient|
|   + compounding  |   catalyst-driven  |   hypergrowth      |
|   power          |   convergence      |                    |
|                  |                    |                    |
|   4 gates        |   4 gates          |   4 gates (new)    |
+--------+---------+--------+----------+--------+-----------+
         |                  |                    |
         v                  v                    v
    Style-Aware Normalization (sector x style bucket)
         |                  |                    |
         v                  v                    v
    Track Scores -> Cross-Track Ranking -> Conviction Assignment
         |
         v
    Portfolio Construction (max 10, diversification constraints)
```

### 3.2 Style Classification

Determined before track scoring using composite of relative valuation + growth profile:

| Signal | Value | Blend | Growth |
|--------|-------|-------|--------|
| EV/FCF percentile (within sector) | Bottom tercile | Middle tercile | Top tercile |
| Revenue CAGR (3yr) | < 8% | 8-18% | > 18% |
| Earnings growth trajectory | Flat/declining | Moderate | Accelerating |
| R&D + CapEx / Revenue | < 8% | 8-15% | > 15% |

**Rule**: Majority-vote across 4 signals. Ties go to Blend. Style is a label for normalization and track routing — does not restrict track eligibility. Any asset can be evaluated by any/all tracks.

### 3.3 Elimination Filters — Style-Aware Adjustments

| Filter | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| FCF Distress | 3/5 positive FCF years | Value/Blend: 3/5. Growth: 2/5 OR positive operating CF + gross margin > 40% | Growth companies reinvest through FCF; operating CF + margin stability is better signal |
| Interest Coverage | 1.5x (sector-adjusted) | Add: Growth companies with zero debt auto-pass | Many Growth companies are un-levered; filter is irrelevant |

All other filters unchanged (liquidity, Beneish, Altman, current ratio).

### 3.4 Track A: Compounder (Refined)

| Gate | Current | Change |
|------|---------|--------|
| 1. Moat Durability | >= 2 signatures | No change |
| 2. Compounding Power | > 0.04 | Add reinvestment-adjusted ROIC: `ROIC_adj = ROIC + (growth_capex / invested_capital) x expected_ROIC_on_new_capital` |
| 3. Capital Allocation | > 0.5 | Adjust SBC dilution: weight by `SBC / revenue` instead of absolute shares |
| 4. Growth Gap | > 0.0 + regime adj | Widen solver bounds to +/-5% to 80%. Add PEG sanity check |

Scoring: `moat x power x cap_alloc x growth_gap` (unchanged formula).

### 3.5 Track B: Mispricing (Kept for Deep Value)

Stays focused on its thesis. This is legitimately a Value strategy.

| Gate | Current | Change |
|------|---------|--------|
| 1. Valuation | price < 0.60 x IV | No change |
| 2. Downside | max loss < 50% | No change |
| 3. Catalyst | strength > 60 | No change |
| 4. Quality Floor | ROIC >= 8% | Lower to ROIC >= 6% OR improving for 3+ quarters |

Add 5th IV method: **Earnings Power Value (EPV)** = `normalized_earnings / WACC`, adjusted for reinvestment. Convergence stays at >= 3 within 30% of median.

### 3.6 Track C: Efficient Growth (New)

Captures capital-efficient high-growth companies that Value methods systematically miss.

**Thesis**: Companies growing revenue rapidly while demonstrating capital efficiency and improving unit economics. Not "growth at any price."

| Gate | Threshold | Measures |
|------|-----------|---------|
| 1. Growth Efficiency | Rule of 40 >= 30 OR (Revenue CAGR > 25% AND gross margin > 50%) | Combined growth + profitability |
| 2. Unit Economics | Gross margin stable/expanding (3yr trend >= -2pp) AND operating leverage positive | Business model scales |
| 3. Capital Efficiency | Incremental ROIC > WACC OR (pre-profit: gross margin > 60% AND NRR > 110%) | Earning above cost of capital on new investments |
| 4. Growth Durability | Deceleration < -5pp AND TAM headroom > 3x current revenue | Room to run, not falling off cliff |

**Scoring** (multiplicative):

```
score = growth_efficiency x unit_economics x capital_efficiency x growth_durability
```

Continuous gate scores:
- Growth Efficiency: `min(rule_of_40 / 40, 2.0)`
- Unit Economics: `(1 + gross_margin_trend) x operating_leverage_ratio`
- Capital Efficiency: `min(incremental_ROIC / WACC, 3.0)`
- Growth Durability: `min(TAM_headroom / 3.0, 2.0) x (1 - max(deceleration, 0) / 20)`

**Conviction**:

```
EXCEPTIONAL: gates >= 4 AND rule_of_40 >= 50 AND inc_ROIC > 2xWACC AND TAM > 5x
HIGH:        gates >= 4 AND rule_of_40 >= 30 AND inc_ROIC > WACC
MEDIUM:      gates >= 3
NONE:        gates < 3
```

### 3.7 Cross-Track Ranking

| Scenario | Result |
|----------|--------|
| HIGH+ on one track only | Use that track's conviction and score |
| HIGH+ on Track A + Track C | Promote to EXCEPTIONAL ("compounding growth") |
| HIGH+ on Track A + Track B | Promote to EXCEPTIONAL ("both" — existing rule) |
| HIGH+ on Track B + Track C | Use higher score |
| HIGH+ on all three | EXCEPTIONAL with max position size |

### 3.8 Position Sizing

| Classification | EXCEPTIONAL | HIGH |
|----------------|-------------|------|
| Compounder (A only) | 15% | 8% |
| Mispricing (B only) | 12% | 6% |
| Efficient Growth (C only) | 12% | 7% |
| Compounder + Growth (A+C) | 20% | 10% |
| Compounder + Mispricing (A+B) | 20% | 10% |
| All three | 20% | 12% |

MEDIUM = 0% across all tracks.

---

## 4. Normalization, Weighting, and Factor Framework

### 4.1 Style-Aware Normalization (Two-Stage)

**Stage 1**: Rank within (sector x style) bucket.
- "How does this Growth-Tech stock compare to other Growth-Tech stocks?"
- Minimum bucket size: 5 assets. If fewer, fall back to sector-only.

**Stage 2**: Z-score standardization across all buckets.
- `z = (percentile - global_mean) / global_std`, converted back to 0-100.
- Ensures no bucket is systematically advantaged.

### 4.2 Revised Factor Inventory

#### Valuation Factors (style-conditional usage)

| Factor | Used By | Direction | Status |
|--------|---------|-----------|--------|
| EV/FCF | Value, Blend | Lower = better | Existing |
| Acquirer's Multiple | Value, Blend | Lower = better | Existing |
| Shareholder Yield | Value, Blend | Higher = better | Existing |
| DCF MoS | Value, Blend | Higher = better | Existing |
| PEG Ratio | Growth, Blend | Lower = better | NEW |
| EV/Revenue | Growth | Lower = better | NEW |
| Rule of 40 | Growth | Higher = better | NEW |
| EV/Gross Profit | Growth | Lower = better | NEW |

#### Quality Factors

| Factor | Used By | Direction | Status |
|--------|---------|-----------|--------|
| Gross Profitability | All | Higher = better | Existing |
| Piotroski F-Score | All | Higher = better | Existing |
| Accrual Ratio | All | Lower = better | Existing |
| ROIC-WACC Spread | All | Higher = better | Existing |
| Incremental ROIC | All (esp. Growth) | Higher = better | NEW |
| Gross Margin Stability | All | Lower vol = better | NEW |
| SBC-Adjusted FCF Margin | Growth, Blend | Higher = better | NEW |

#### Momentum Factors

| Factor | Used By | Direction | Status |
|--------|---------|-----------|--------|
| Price Momentum (12-1mo) | All | Higher = better | Existing |
| Earnings Revision Breadth | All | Higher = better | NEW |
| Revenue Acceleration | Growth, Blend | Higher = better | NEW |
| Relative Strength vs Style | All | Higher = better | NEW |

#### Growth Factors (new category)

| Factor | Used By | Direction | Status |
|--------|---------|-----------|--------|
| Revenue CAGR (3yr) | All | Higher = better | NEW |
| Operating Leverage | Growth, Blend | Higher = better | NEW |
| Net Revenue Retention | Growth (SaaS) | Higher = better | NEW |
| TAM Headroom | Growth | Higher = better | NEW |

### 4.3 Weight Matrix (Style x Growth Stage)

| Style x Stage | Quality | Valuation | Momentum | Growth |
|---------------|---------|-----------|----------|--------|
| Value x Mature | 0.25 | 0.35 | 0.25 | 0.15 |
| Value x Steady | 0.25 | 0.30 | 0.25 | 0.20 |
| Value x Cyclical | 0.25 | 0.30 | 0.25 | 0.20 |
| Blend x Mature | 0.30 | 0.25 | 0.25 | 0.20 |
| Blend x Steady | 0.30 | 0.20 | 0.25 | 0.25 |
| Blend x High Growth | 0.25 | 0.15 | 0.25 | 0.35 |
| Growth x High Growth | 0.20 | 0.10 | 0.25 | 0.45 |
| Growth x Steady | 0.25 | 0.15 | 0.25 | 0.35 |
| Turnaround (any) | 0.30 | 0.25 | 0.25 | 0.20 |

Properties:
- No cell exceeds 0.45
- Momentum constant at 0.25 (style-neutral alpha)
- Quality always 0.20-0.30 (earnings quality floor)

### 4.4 Within-Dimension Factor Weighting (Examples)

**Growth x High Growth — Valuation (10% total)**:
- PEG Ratio: 40% of 10% = 4%
- EV/Gross Profit: 30% of 10% = 3%
- EV/Revenue: 20% of 10% = 2%
- Rule of 40: 10% of 10% = 1%

**Value x Mature — Valuation (35% total)**:
- EV/FCF: 30% of 35% = 10.5%
- Acquirer's Multiple: 25% of 35% = 8.75%
- Shareholder Yield: 25% of 35% = 8.75%
- DCF MoS: 20% of 35% = 7.0%

### 4.5 Composite Score

```
composite = sum(dimension_weight x dimension_percentile)
where dimension_percentile = sum(factor_weight_within_dim x style_aware_percentile)
```

### 4.6 Conviction Thresholds (Unified)

```
EXCEPTIONAL: composite >= 79 AND track_gates >= 4
HIGH:        composite >= 72 AND track_gates >= 4
MEDIUM:      composite >= 65 AND track_gates >= 3
NONE:        below any of above
```

---

## 5. Acceptance Criteria & Monitoring

### 5.1 Style Distribution Targets

```
Disparity ratio = min(selection_rate) / max(selection_rate)
```

| Metric | Fail | Watch | Pass |
|--------|------|-------|------|
| Disparity ratio | < 0.50 | 0.50-0.80 | >= 0.80 |
| Any style 0 selections (>= 20 eligible) | Fail | — | — |
| Highest rate > 3x lowest | Fail | — | — |

These are monitoring thresholds, NOT optimizer constraints.

### 5.2 Performance Metrics (Per-Style + Aggregate)

#### Returns

| Metric | Target | Window |
|--------|--------|--------|
| Hit rate | >= 55% per style | 12-month forward |
| Median return | No style median < 0 | Rolling 3-year |
| Aggregate CAGR | >= S&P 500 | Full backtest |
| Style CAGR | Each style >= its benchmark index | Full backtest |

#### Risk

| Metric | Target | Window |
|--------|--------|--------|
| Max drawdown (aggregate) | < 35% | Full backtest |
| Max drawdown (per style) | < 45% per style | Full backtest |
| Sharpe (aggregate) | >= 0.7 | Full backtest |
| Sharpe (per style) | >= 0.4 per style | Full backtest |
| Information ratio | > 0 per style vs style benchmark | Full backtest |

#### Quality

| Metric | Target |
|--------|--------|
| Precision@10 | >= 60% outperform benchmark over 12mo |
| Style precision | Each style's picks outperform style benchmark |
| Conviction calibration | EXCEPTIONAL > HIGH > MEDIUM (monotonic across styles) |
| Gate pass rate | No style < 15% on any individual gate |

### 5.3 Backtest Validation

**Phase 1 — In-Sample Audit**: Run v3 on full historical universe, classify by style, execute bias audit, document baseline.

**Phase 2 — v4 In-Sample Comparison**: Run v4 on same universe. Compare style distribution, score distributions, gate pass rates, new vs dropped names. Manual review of new picks.

**Phase 3 — Walk-Forward Out-of-Sample**: 70/30 train/holdout split. Run v4 on holdout with frozen thresholds. Key: does style-fair scoring hurt aggregate performance? If Sharpe drops > 15%, investigate. Regime analysis across bull/bear/sideways.

**Phase 4 — Shadow Mode**: Run v3 + v4 in parallel 1-3 months on live data. Weekly comparison. Switch to v4 when: disparity >= 0.80, no style underperforms benchmark, manual review confirms quality.

### 5.4 Production Monitoring

**Weekly**: Style distribution of new picks (alert if 0 for 4 weeks), gate pass rates (alert if drops > 50%), KS-test across style score distributions.

**Monthly**: Selection rate parity trend, factor contribution decomposition, data coverage for new Growth factors, style classification stability.

**Quarterly**: Full bias audit rerun, performance attribution by style, threshold calibration review, factor decay analysis.

### 5.5 Soft Guardrails

```python
def check_style_balance(candidates, universe):
    for style in [Value, Blend, Growth]:
        eligible = [a for a in universe if a.style == style]
        selected = [c for c in candidates if c.style == style]
        if len(eligible) >= 20 and len(selected) == 0:
            log.warning(f"Zero {style} from {len(eligible)} eligible")
        rate = len(selected) / len(eligible) if eligible else 0
        rates[style] = rate
    disparity = min(rates.values()) / max(rates.values())
    if disparity < 0.50:
        log.warning(f"Disparity ratio {disparity:.2f} below 0.50")
```

### 5.6 Before vs After Summary

| v3 (Before) | v4 (After) |
|-------------|------------|
| ~90%+ Value picks | Disparity ratio >= 0.80 |
| Growth fails at elimination or Track B gates | Track C with growth-appropriate gates |
| Sector-only normalization | Two-stage sector x style normalization |
| 3 factor dimensions, valuation-heavy | 4 dimensions, 12 new factors, style-weighted |
| 1 momentum factor | 4 momentum factors |
| 0 growth-native valuation metrics | 4 growth-appropriate valuation metrics |
| No style monitoring | Weekly/monthly/quarterly monitoring |
| Aggregate performance only | Per-style performance with style benchmarks |
