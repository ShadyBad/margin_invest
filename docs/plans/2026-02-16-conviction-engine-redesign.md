# Conviction Engine Redesign — From Screener to Concentrated Capital Allocator

**Date**: 2026-02-16
**Version**: 2.0
**Status**: Approved
**Supersedes**: Scoring engine sections of `2026-02-12-margin-invest-v1-design.md`

## Problem Statement

The v1 scoring engine is a competent quantitative screener. It surfaces the top 2% of a ~7,700 stock universe ranked by a blend of quality, value, and momentum metrics. What it actually finds: reasonably good businesses at fair-to-cheap prices with positive momentum.

It does not find generational bets. It cannot distinguish a decade-long compounder from a business having a good year. It cannot detect asymmetric mispricing. It compresses the right tail through percentile averaging. It gives momentum — a timing signal — equal weight to business quality. It has no concept of moat durability, reinvestment power, capital allocation excellence, runway, or downside structure.

This redesign transforms the engine from "rank everything and take the top" to "identify two specific types of extraordinary opportunities and reject everything else."

## Two Opportunity Archetypes

The system must surface both:

1. **Compounders** — Businesses with durable moats reinvesting at high incremental ROIC for decades. The bet is on the business, not the price. (Costco, ASML, Constellation Software, Copart)
2. **Asymmetric Mispricings** — Businesses temporarily misunderstood or mispriced where downside is structurally limited but upside is uncapped. (Apple 2016, any quality business in a temporary drawdown)

A stock that qualifies as both is the rarest and highest-conviction signal.

---

## Architecture Overview

```
STAGE 1: ELIMINATION          ~7,700 → ~1,500
STAGE 2: CLASSIFICATION        Type assignment (Compounder / Mispricing / Both)
STAGE 3: TWO-TRACK SCORING     Track A (Compounder) and Track B (Mispricing)
STAGE 4: CONVICTION GATES      Absolute + relative thresholds
STAGE 5: POSITION SIZING       Asymmetry-based allocation signal
STAGE 6: TIMING OVERLAY        Momentum as entry timing, not conviction
```

---

## Stage 1: Elimination Filters

### Existing Filters (Retained)

All six current filters remain unchanged:

1. **Liquidity Check** — Market cap floors ($300M default, $1B utilities, $500M energy), $1M daily dollar volume, 5yr history, exclude Financials/REITs
2. **Beneish M-Score** — M > -1.78 = FAIL (earnings manipulation)
3. **Altman Z''** — Z'' < 1.1 = FAIL (financial distress, utilities exempt)
4. **FCF Distress** — Negative FCF = FAIL
5. **Interest Coverage** — Below sector-adjusted threshold = FAIL
6. **Current Ratio** — Below sector-adjusted threshold = FAIL

### New Filter: Anti-Mediocrity Gate

Applied after existing filters. Purpose: reduce the scoring universe to businesses worth evaluating for concentrated capital.

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| 5yr Median ROIC | > 8% (OR improving 3yr trajectory for Track B candidates) | Must earn above cost of capital over a cycle |
| Gross Margin | > 20% (sector-adjusted: Utilities > 10%, Energy > 15%) | Must have pricing power, not commodity economics |
| FCF Consistency | Positive FCF in 4 of last 5 years | Consistent cash generation |
| Revenue Trend | Not declining 3+ consecutive years (unless Turnaround classified) | Secular decline is not opportunity |

**Expected impact:** ~7,700 → ~1,500-2,000 stocks survive to scoring.

### Repurposed: Piotroski F-Score as Filter

Move F-Score from quality scoring pillar to elimination filters:
- F-Score <= 3 = FAIL (fundamentally weak business)
- F-Score 4-5 = WARNING (flagged but not eliminated)
- F-Score >= 6 = PASS

---

## Stage 2: Classification

### Growth Stage (Retained)

Current classifier unchanged. Priority order: Turnaround > High Growth > Cyclical > Mature > Steady Growth.

### New: Opportunity Type Assignment

Each surviving stock is classified into an opportunity type based on quantitative criteria:

**COMPOUNDER** — All three required:
- 5yr median ROIC > 15%
- Reinvestment Rate > 30% (where Reinvestment Rate = (Growth CapEx + Change in Working Capital) / NOPAT)
- ROIC Coefficient of Variation (5yr) < 0.30

**MISPRICING** — All three required:
- Trading below 0.6x reinvestment-driven intrinsic value
- Quality floor met (5yr median ROIC > 8% OR 3yr improving ROIC trajectory)
- At least one active catalyst (insider cluster buying score > 0 OR net institutional accumulation > 0)

**BOTH** — Meets criteria for both Compounder and Mispricing. Rare. Highest conviction.

**NEITHER** — Does not meet either set of criteria. Scored but capped at WATCHLIST maximum conviction level.

---

## Stage 3: Two-Track Scoring

Each stock is scored on both tracks. The higher-scoring track determines the stock's conviction level.

### Track A: Compounder Score

Weights: Quality 50% / Value 30% / Capital Allocation 20%

#### Quality Pillar (50% of Track A)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| ROIC Stability | 30% | 5yr median ROIC, penalized by CV. Score = median_ROIC * (1 - CV) | No |
| Incremental ROIC | 20% | (NOPAT_current - NOPAT_3yr_ago) / (Invested_Capital_current - Invested_Capital_3yr_ago) | No |
| Reinvestment Engine | 20% | ROIC * Reinvestment_Rate (organic growth power) | No |
| Gross Profitability | 15% | (Revenue - COGS) / Total Assets (Novy-Marx) | No |
| Earnings Quality | 15% | (Net Income - CFO) / Total Assets (Sloan Accrual) | Yes |

#### Value Pillar (30% of Track A)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| Reinvestment-Driven DCF | 30% | Two-stage DCF where growth_rate = ROIC * Reinvestment_Rate (capped at 25%). MoS = (IV - Price) / IV | No |
| Owner Earnings Yield | 25% | (CFO - Maintenance CapEx) / EV. Maintenance CapEx estimated as Depreciation * 1.1 | No |
| Acquirer's Multiple | 20% | EV / EBIT | Yes |
| Runway Score | 25% | Company revenue / sub-industry total revenue (from SEC EDGAR aggregates). Lower penetration = more runway | Yes |

#### Capital Allocation Pillar (20% of Track A)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| Organic Reinvestment Ratio | 30% | (CapEx - Depreciation + R&D Growth) / (CapEx + Buybacks + Dividends + Acquisitions). Higher = reinvesting vs. distributing | No |
| Buyback Effectiveness | 25% | (Total Repurchases / Shares Reduced) vs avg stock price over same period. Ratio < 1.0 = buying below average | Yes |
| Insider Ownership | 25% | Officers + directors % ownership (from proxy filings) | No |
| Debt Discipline | 20% | Net Debt / EBITDA trend (5yr slope). Declining or stable < 2x = disciplined | Yes (lower/declining = better) |

### Track B: Mispricing Score

Weights: Value 45% / Quality Floor 25% / Catalyst 30%

#### Value Pillar (45% of Track B)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| Reinvestment-Driven DCF | 30% | Same as Track A | No |
| Owner Earnings Yield | 25% | Same as Track A | No |
| Acquirer's Multiple | 25% | Same as Track A | Yes |
| Asymmetry Ratio | 20% | (Intrinsic Value - Price) / (Price - Downside Floor). Where floor = max(Net Cash per Share, Tangible Book per Share) | No |

#### Quality Floor Pillar (25% of Track B)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| ROIC Trajectory | 40% | 3yr ROIC slope (linear regression). Positive slope = improving business | No |
| Gross Profitability | 30% | Same as Track A | No |
| Earnings Quality | 30% | Same as Track A | Yes |

#### Catalyst Pillar (30% of Track B)

| Sub-Factor | Weight | Formula | Invert? |
|-----------|--------|---------|---------|
| Insider Cluster Buying | 35% | 3+ insiders buying within 90 days, purchases > $100K, CEO/CFO weighted 2x | No |
| Institutional Accumulation | 35% | Smart money 13F scoring (same as v1) | No |
| Contrarian Signal | 30% | negative_momentum_score * quality_score. High quality + negative price momentum = contrarian opportunity | No |

### Sub-Factor Ranking

Within each pillar, sub-factors are **weighted** (not equal-weighted). Percentile ranking uses the same algorithm as v1:
- Rank within sector first (sector-neutral)
- Handle ties by averaging
- Invert where specified

Pillar scores are computed as **weighted average** of sub-factor percentile ranks (using the weights specified above, not simple average).

### Composite Score

For each track:
```
Track A Score = Quality_Pillar * 0.50 + Value_Pillar * 0.30 + Capital_Allocation_Pillar * 0.20
Track B Score = Value_Pillar * 0.45 + Quality_Floor_Pillar * 0.25 + Catalyst_Pillar * 0.30
```

Growth stage weight adjustments (retained from v1, applied to Track A only):

| Stage | Quality | Value | Capital Allocation |
|-------|---------|-------|--------------------|
| High Growth | 55% | 25% | 20% |
| Steady Growth | 50% | 30% | 20% |
| Mature | 40% | 35% | 25% |
| Cyclical | 45% | 30% | 25% |
| Turnaround | 40% | 35% | 25% |

Track B weights are fixed (mispricing thesis doesn't vary by growth stage).

Final conviction score = max(Track A, Track B) for each stock. The winning track is labeled on the output.

---

## Stage 4: Conviction Gates

### Relative Thresholds (within ~1,500 stock scoring universe)

| Percentile | Label | Expected Count |
|-----------|-------|---------------|
| Top 0.3% | Exceptional Conviction | 3-5 stocks |
| Top 2% | High Conviction | 25-30 stocks |
| Top 7% | Watchlist | ~100 stocks |
| Below 93 | Not shown | Everything else |

### Absolute Gates (must pass IN ADDITION to percentile threshold)

#### For Exceptional/High Conviction via Track A (Compounder):

| Gate | Threshold |
|------|-----------|
| ROIC Stability | 5yr median ROIC > 15% AND CV < 0.30 |
| Reinvestment Engine | Reinvestment Rate > 30% at ROIC > WACC + 5% |
| Valuation Sanity | Not trading above 2x reinvestment-driven intrinsic value |
| Data Quality | data_coverage > 85% |

#### For Exceptional/High Conviction via Track B (Mispricing):

| Gate | Threshold |
|------|-----------|
| Quality Floor | 5yr median ROIC > 8% OR 3yr improving trajectory |
| Valuation Depth | Trading below 0.6x reinvestment-driven intrinsic value |
| Catalyst Present | Insider cluster score > 0 OR institutional accumulation > 0 |
| Downside Floor | Net cash > 50% of market cap OR tangible book > 50% of market cap OR current ratio > 2.0 |

Stocks that hit the relative percentile threshold but fail absolute gates are **capped at WATCHLIST**.

---

## Stage 5: Position Sizing Signal

New output. Based on the Asymmetry Ratio:

```
Asymmetry Ratio = (Intrinsic Value - Current Price) / (Current Price - Downside Floor)
```

Where Downside Floor = max(Net Cash per Share, Tangible Book per Share, or $0 if both negative).

| Asymmetry | Max Position | Rationale |
|-----------|-------------|-----------|
| > 5x | Up to 20% of portfolio | Extraordinary: limited downside, massive upside |
| 3x - 5x | Up to 10% | Strong asymmetry |
| 1.5x - 3x | Up to 5% | Moderate asymmetry |
| < 1.5x | Max 3% | Limited asymmetry, size accordingly |

Conviction level scales within the max:
- Exceptional: 100% of max position
- High: 60% of max position
- Watchlist: 30% of max position

**Output format:** "BUY - Compounder - Up to 12% position" (not just "BUY")

---

## Stage 6: Timing Overlay

Momentum factors are removed from conviction scoring and applied as a post-conviction timing signal.

| Signal | Source | Output |
|--------|--------|--------|
| Price Momentum (12-1 month) | Same as v1 | Positive = "Buy now". Negative = "Add on pullback" |
| SUE (Earnings Momentum) | Same as v1 | Positive = thesis accelerating. Negative = monitor |
| Sentiment (LLM analysis) | Same as v1 | Negative + high conviction = contrarian confirmation. Positive = consensus aligned |

Timing does NOT change the conviction level or position sizing. It provides entry guidance.

**Exception for Track B:** Negative price momentum with a high mispricing score is a *positive* signal (contrarian confirmation), not negative. The timing overlay must invert its interpretation for mispricing opportunities.

---

## New Data Requirements

### Multi-Year Financial Data (5yr rolling)

The redesign requires 5-year rolling financial history per stock. This data is already planned for point-in-time storage in TimescaleDB. The scoring pipeline must be updated to query and compute:

| Metric | Computation | Storage |
|--------|-------------|---------|
| ROIC (5yr series) | NOPAT / Invested Capital per year | Compute at scoring time from stored financials |
| Reinvestment Rate (annual) | (Growth CapEx + Delta WC) / NOPAT | Compute at scoring time |
| Gross Margin (5yr series) | (Rev - COGS) / Rev per year | Compute at scoring time |
| FCF (5yr series) | CFO + CapEx per year | Compute at scoring time |
| Revenue (5yr series) | From income statement | Already stored |

### New Data Points

| Data Point | Source | Frequency |
|-----------|--------|-----------|
| Sub-industry total revenue | SEC EDGAR XBRL aggregates | Quarterly |
| Insider ownership % | SEC proxy filings (DEF 14A) | Annual |
| Depreciation (separate from CapEx) | Income statement / cash flow | Quarterly |
| Goodwill + Intangibles (for tangible book) | Balance sheet | Quarterly |

All required data is available from existing planned providers (yfinance, SEC EDGAR, Finnhub). No new paid providers needed.

---

## Migration Strategy

### What Changes in Existing Code

| File | Change |
|------|--------|
| `models/scoring.py` | Add `OpportunityType` enum, `AsymmetryRatio` field, `position_sizing` field, `winning_track` field to `CompositeScore`. Add `CapitalAllocationScore` model. |
| `scoring/composite.py` | Split into `composite_compounder.py` and `composite_mispricing.py`. New `composite.py` orchestrates both tracks and picks the winner. |
| `scoring/normalizer.py` | Add weighted percentile combination (replace simple average in `FactorBreakdown.average_percentile`). |
| `scoring/classifier.py` | Add `classify_opportunity_type()` function. |
| `scoring/filters/pipeline.py` | Add anti-mediocrity gate and F-Score filter to pipeline. |

### New Files

| File | Purpose |
|------|---------|
| `scoring/quantitative/roic_stability.py` | 5yr median ROIC + CV computation |
| `scoring/quantitative/incremental_roic.py` | Change in NOPAT / change in invested capital |
| `scoring/quantitative/reinvestment_engine.py` | ROIC * Reinvestment Rate |
| `scoring/quantitative/owner_earnings.py` | Buffett-adjusted FCF yield |
| `scoring/quantitative/runway_score.py` | Revenue as % of sub-industry total |
| `scoring/quantitative/capital_allocation.py` | Buyback effectiveness, debt discipline, organic reinvestment, insider ownership |
| `scoring/quantitative/asymmetry.py` | Downside floor, asymmetry ratio |
| `scoring/quantitative/contrarian_signal.py` | Negative momentum * quality score |
| `scoring/composite_compounder.py` | Track A scoring |
| `scoring/composite_mispricing.py` | Track B scoring |
| `scoring/conviction_gates.py` | Absolute gate evaluation |
| `scoring/position_sizing.py` | Asymmetry-based allocation signal |
| `scoring/timing_overlay.py` | Post-conviction momentum/sentiment timing |

### Backward Compatibility

The `CompositeScore` model retains all existing fields. New fields are additive. The API response schema expands but does not break existing clients. The v1 composite percentile remains available as `legacy_composite_percentile` for comparison during transition.

---

## Testing Strategy

### Golden Value Tests

Every new factor gets a hand-calculated golden value test using real 10-K data. Minimum test companies:

| Company | Why | Expected Track |
|---------|-----|---------------|
| Costco (COST) | Steady compounder, high ROIC stability | Track A: Compounder |
| ASML (ASML) | Monopoly moat, high reinvestment | Track A: Compounder |
| AutoZone (AZO) | Capital allocation excellence, low revenue growth | Track A: Compounder (via capital allocation) |
| Constellation Software (CSU.TO) | Acquisition-driven compounder | Track A: Compounder |
| Apple (AAPL) circa 2016 | Misunderstood services runway | Track B: Mispricing (or Both) |
| A generic cyclical at trough | Deep value with catalyst | Track B: Mispricing |

### Determinism Tests

Same inputs must produce same outputs across both tracks. No randomness.

### Regression Tests

Run v1 and v2 scoring on the same universe. Verify:
- v2 surfaces all v1 Exceptional stocks (or explicitly explains why they were dropped)
- v2 surfaces additional stocks that v1 missed (the compounders and mispricings)
- v2 does NOT surface stocks that are merely "pretty good" — mediocre businesses should not reach High Conviction

---

## Success Criteria

The redesigned engine succeeds if:

1. It would have surfaced Costco, ASML, AutoZone, and Constellation Software as Exceptional Conviction Compounders when scored on historical data
2. It would have surfaced Apple in early 2016 as a Mispricing opportunity
3. It does NOT surface a business with < 10% 5yr median ROIC as Exceptional Conviction via Track A
4. The Exceptional list contains <= 5 stocks at any time (concentration, not diversification)
5. Every Exceptional stock has a labeled opportunity type and a position sizing recommendation
6. Backtesting shows the redesigned Top 5 outperforms the v1 Top 5 on 5-year forward excess returns
