# Frontend UX Strategy: Forensic Transparency

**Date**: 2026-02-26
**Status**: Approved

## Section 1: High-Level UX Philosophy

### "Show the Work, Not the Conclusion"

Most fintech products lead with a verdict: "BUY" or "Strong Buy" or 4.5/5 stars. The user is expected to trust the rating. Margin Invest inverts this. The UI leads with the *evidence* and lets the verdict emerge from it. The score is the least interesting thing on the page — the elimination gauntlet, the factor breakdown, the sector comparison are the product.

### Three Laws

1. **Every number is verifiable in one interaction.** Hover any metric -> see its formula, source, and the stock's actual calculation. No "proprietary" black boxes. If a user can't reproduce the math with a spreadsheet and the same inputs, the UI has failed.

2. **Elimination is the hero, not scoring.** The emotional core of the product is "70% of equities fail before scoring begins." The gauntlet isn't a detail section — it's the trust anchor. Users remember what the system *rejected*, not what it scored.

3. **Context beats magnitude.** "ROIC: 22.4%" means nothing in isolation. "ROIC: 22.4% — 91st percentile in Technology, sector median is 11.2%" means everything. Every metric gets its context: raw value, percentile, sector comparison.

### Progressive Disclosure Ladder

| Layer | Audience | What They See | Time |
|-------|----------|---------------|------|
| Glance | Everyone | Radar chart + conviction badge + signal | 2 sec |
| Summary | Most users | Pillar percentiles + filter pass/fail | 30 sec |
| Forensic | DIY Quants | Sub-factor tables + formula tooltips + comparison bars | 5 min |
| Audit | Power users | Full valuation scenarios + backtest data + ML confidence | 15 min |

Each layer is complete on its own. A user who never expands anything still gets a trustworthy picture.

---

## Section 2: Asset Detail Page Layout

### Proposed Flow (Passing Ticker)

```
HeroHeader -> EliminationGauntlet -> [NEW] FactorRadar -> ScoringPillars (enhanced) ->
ConvictionEngine -> MLAuditPanel -> InstitutionalPositioning -> ValuationSection -> BacktestTeaser
```

### Proposed Flow (Eliminated Ticker)

```
[ENHANCED] EliminatedHero -> EliminationGauntlet (enhanced) -> [NEW] FailedComparison ->
HypotheticalScores (with dimmed radar) -> Sector survivor callout
```

### New Component: `FactorRadar`

**Position**: Between EliminationGauntlet and ScoringPillars. Answers "why Xth percentile?" in under 2 seconds.

**Layout**:
```
+-----------------------------------------------------+
|  Factor Profile                          vs. Sector  |
|                                                      |
|              Quality (87th)                          |
|                  /\                                   |
|                /    \                                 |
|              /   ##   \                               |
|   Momentum /  ######    \ Value                      |
|   (94th)  \  ########   / (72nd)                     |
|              \ ######  /                              |
|                \    /                                 |
|                  \/                                   |
|                                                      |
|  -- Stock (filled)    -- Sector Median (outline)     |
|                                                      |
|  Click any axis for sub-factor breakdown             |
+-----------------------------------------------------+
```

**Behavior**:
- Radar polygon (filled, accent color at 20% opacity) = stock's percentile on each axis
- Second polygon (outline only, muted gray) = sector median (50th percentile)
- Third polygon (dashed outline, subtle) = sector 90th percentile — shows "what great looks like"
- Vertex labels show axis name + percentile in parentheses
- Click any vertex -> smooth scroll to that pillar's expanded sub-factor table below
- Responsive: On mobile, collapses to three horizontal comparison bars (one per pillar)

**Implementation**: Recharts `RadarChart` (already in dependency tree) with custom styling. Three data series: stock, sector median, sector P90.

### Enhanced Component: `ScoringPillars` Sub-Factor Rows

**Current**: Sub-factor table shows Name, Raw Value, Percentile, Rating.

**Enhancement**: Add a sector comparison micro-bar to each sub-factor row:

```
+--------------------------------------------------------------+
|  ROIC-WACC Spread          22.4%     91st     Strong          |
|  +-------------------------#-----------------------+          |
|  |         Sector Median: 11.2%       ^ You        |          |
|  +------------------------------------------------------+    |
|                                                               |
|  Sloan Accrual Ratio  (i)  -0.03     78th     Strong          |
|  +-----------------#---------------------------------------+  |
|  |    Sector Median: -0.01  ^ You                           |  |
|  +------------------------------------------------------+    |
+--------------------------------------------------------------+
```

- Thin horizontal line (4px height) showing stock position relative to sector distribution
- Markers for: sector P10, sector median (P50), sector P90, and the stock's position
- Only visible when the pillar is expanded (progressive disclosure)
- The (i) icon on metric names triggers the FormulaTooltip

### Enhanced Component: `EliminatedHero`

**Enhancement for recognizable tickers** (market cap > $100B): Protective framing.

```
+---------------------------------------------------------------+
|  TSLA  .  Tesla, Inc.  .  $248.50  .  Consumer Discretionary   |
|                                                                 |
|  ## ELIMINATED -- 2 of 6 forensic filters failed                |
|                                                                 |
|  "Tesla is the 7th largest company by market cap.               |
|   Our filters don't care. Two forensic signals flagged          |
|   elevated risk -- the same signals that preceded 67% of        |
|   major accounting restatements in academic studies."            |
|                                                                 |
|  If it passed: Would have scored in the 74th percentile.        |
+---------------------------------------------------------------+
```

**Logic**:
- Market cap > $100B: Protective framing with company acknowledgment + "our filters don't care"
- All others: Clinical. "2 of 6 forensic filters failed. See below."
- One-liner hypothetical: "If it passed, would have scored in the Xth percentile" from HypotheticalScores data

### New Component: `FailedComparison` (Eliminated Flow Only)

**Position**: After EliminationGauntlet, before HypotheticalScores.

Shows what passed on the same filters where this stock failed:

```
+-------------------------------------------------------------------+
|  Where TSLA Failed, Others Passed                                  |
|                                                                     |
|  Beneish M-Score                                                   |
|  TSLA: -1.42  ##################..  FAIL (threshold: -1.78)       |
|  AAPL: -2.91  ##########..........  PASS                           |
|  Sector median: -2.44                                               |
|                                                                     |
|  Sloan Accrual Ratio                                                |
|  TSLA: +0.12  ..............######  FAIL (threshold: 0.10)         |
|  AAPL: -0.04  ######..............  PASS                           |
|  Sector median: +0.02                                               |
|                                                                     |
|  Comparison stock: AAPL (highest-scoring in same sector)            |
+-------------------------------------------------------------------+
```

**Logic**:
- Only shows for filters the stock *failed* (not all 6)
- Comparison stock = highest-scoring passing ticker in the same GICS sector
- If no passing ticker in the sector, use nearest sector or skip
- Factual, no editorializing

**API requirement**: New endpoint or field returning a "sector champion" ticker for each failed filter.

### Dimmed Radar on `HypotheticalScores`

- Miniature FactorRadar at 60% opacity with dashed lines
- No sector comparison overlay (just the stock's hypothetical shape)
- Label: "Hypothetical factor profile -- this stock did not pass filters"

---

## Section 3: "Near Miss" Component Design

### The Near Miss Journey (User Flow)

```
User searches "TSLA" -> GlobalSearch -> /asset/TSLA -> API returns eliminated status
    |
    v
EliminatedHero (enhanced)
    - Protective framing (mega-cap) or clinical (everything else)
    - One-line hypothetical teaser
    |
    v
EliminationGauntlet
    - Failed filters sort to top (existing)
    - Each failed FilterCard gets:
        . Value vs. Threshold bar (existing)
        . "WHY THIS MATTERS" block (existing)
        . [NEW] Sector context line: "68% of stocks in this sector pass this filter"
    |
    v
FailedComparison
    - Side-by-side with sector champion on failed filters only
    |
    v
HypotheticalScores (enhanced)
    - Dimmed FactorRadar showing what-if profile
    - [NEW] Rank sentence: "This would place TSLA at #47 out of 312 scored stocks"
    |
    v
Sector Survivor Callout
    - "X stocks in Consumer Discretionary passed all filters. See the top picks ->"
```

### Emotional Design Principles for Near Misses

1. **Acknowledge, don't dismiss.** The user searched this ticker because they care about it. The protective framing says: "We see why you're interested. Here's what the data says."

2. **Make the elimination tangible, not abstract.** "Beneish M-Score: -1.42" is abstract. "This M-Score is worse than 73% of companies in this sector" is tangible. The FailedComparison makes this even more concrete.

3. **Reward the search, don't punish it.** HypotheticalScores shows the system did analyze the stock fully. "We did the work. We just can't recommend it."

4. **Bridge to what passed.** Sector survivor callout is the conversion moment. Curiosity takes over.

### FilterCard Enhancement: Sector Context Line

Each failed filter gains one line of context:

```
Before:
  Beneish M-Score: -1.42    Threshold: -1.78    FAIL
  "WHY THIS MATTERS: Elevated earnings manipulation risk..."

After:
  Beneish M-Score: -1.42    Threshold: -1.78    FAIL
  68% of Consumer Discretionary stocks pass this filter.
  "WHY THIS MATTERS: Elevated earnings manipulation risk..."
```

**API requirement**: Each `FilterResultResponse` needs a `sector_pass_rate` field (float, 0-1) representing the percentage of stocks in the same GICS sector that pass this filter.

### What the Near Miss Is NOT

- Not a leaderboard of failures (no "top 10 eliminated stocks" page)
- Not a gotcha moment (never adversarial toward the stock)
- Not a debate (shows data, "the system has no opinion")

---

## Section 4: Transparency & Trust Mechanisms

### The Formula Tooltip System

A single, consistent component used everywhere a financial metric appears. One pattern, learned once, trusted everywhere.

**Component: `FormulaTooltip`**

```
+---------------------------------------------+
|  Sloan Accrual Ratio                        |
|                                             |
|  (Net Income - CFO - CFI) / Total Assets    |
|                                             |
|  Sloan (1996)                               |
|  Lower is better. Negative = cash earnings  |
|  exceed reported earnings.                  |
+---------------------------------------------+
```

**Structure** (4 lines, always):
1. **Metric name** — bold, primary text
2. **Formula** — monospace, the actual math
3. **Source** — italic, academic citation (author, year)
4. **One-liner** — plain English interpretation ("lower is better", "above X signals risk")

**Trigger**: Hover on desktop, tap on mobile. Popover anchored to metric name. Consistent (i) icon (small, muted) next to every metric with a formula.

**Where it appears**:

| Component | Metrics |
|-----------|---------|
| FilterCard | M-Score, Z-Score, FCF, Interest Coverage, Current Ratio, Liquidity |
| PillarCard sub-factors | ROIC-WACC, Accrual Ratio, Piotroski, EV/FCF, Shareholder Yield, etc. |
| ConvictionEngine | Asymmetry Ratio, Max Position %, Timing Signal |
| ValuationSection | DCF, EV/FCF implied, EV/EBIT implied, Shareholder Yield implied |
| FactorRadar | Each axis label (Quality, Value, Momentum composites) |

**Data structure**:
```typescript
interface FormulaDefinition {
  name: string;           // "Sloan Accrual Ratio"
  formula: string;        // "(Net Income - CFO - CFI) / Total Assets"
  source: string;         // "Sloan (1996)"
  interpretation: string; // "Lower is better. Negative = cash earnings exceed reported earnings."
}
```

Static data — shipped as a constant map in the frontend, not fetched from the API.

### Trust Calibration: Metadata Ribbon Enhancement

Color-code the freshness indicator:

| Data Age | Color | Label |
|----------|-------|-------|
| < 4 hours | `--color-bullish` | Live |
| 4-24 hours | `--color-text-primary` | Today |
| 1-3 days | `--color-warning` | X days ago |
| > 3 days | `--color-bearish` | Stale -- X days ago |

Add tooltip on data coverage %: "87% means 87 of 100 data fields were available from the source. Missing fields are excluded from scoring, not imputed."

### Sector-Neutral Methodology Callout

Promote from PillarCard footer to a banner at the top of ScoringPillars:

```
+---------------------------------------------------------------+
|  O  Sector-neutral scoring: all factors ranked within          |
|     Technology (GICS 4510) before cross-sector combination.    |
|     This stock is compared to 847 Technology peers.  [Why?] i  |
+---------------------------------------------------------------+
```

The [Why?] tooltip: "Comparing a tech company's ROIC to a utility's ROIC is meaningless. Sector-neutral ranking ensures fair comparison within peer groups."

### Determinism Badge

Small, persistent element on every asset detail page:

```
# Deterministic -- same inputs produce this exact output. No human override.
```

- Positioned below HeroHeader, above EliminationGauntlet
- Small, monospace, muted text
- Tooltip: "This score was computed algorithmically with zero human intervention. The same financial data inputs will always produce this exact same score, percentile, and signal."

### Formula Tooltip Implementation Notes

- Use Radix UI Tooltip or Popover
- Monospace font for formula line (`--font-geist-mono`)
- Max width: 320px
- Dismiss: click outside or hover away
- Mobile: tap-to-open, tap-outside-to-close
- Animation: fade in 150ms
- Z-index: above card content, below modals

---

## Section 5: UX Anti-Patterns to Avoid

### 1. "Trust Us" Syndrome
**Anti-pattern**: Showing a score without the math.
**Defense**: FormulaTooltip on every metric. Sector comparison micro-bars. FactorRadar showing score shape.

### 2. Gamification of Investing
**Anti-pattern**: Leaderboards, streaks, confetti. Turns investing into gambling.
**Defense**: No celebratory animations. Clinical labels (Exceptional/High/Medium), not hype (Hot Pick/Fire). Warm, muted palette.

### 3. The Black Box Score
**Anti-pattern**: Single number with no decomposition (Zacks Rank #1).
**Defense**: FactorRadar decomposes into 3 axes. Each expands to sub-factors. Each sub-factor has formula tooltip. Three clicks to full math.

### 4. Selective Transparency
**Anti-pattern**: Showing methodology only when flattering.
**Defense**: Eliminated hero flow is as detailed as passing flow. HypotheticalScores shows what score would have been.

### 5. False Precision
**Anti-pattern**: 87.43rd percentile to suggest scientific rigor.
**Defense**: Percentiles as integers. Raw values to appropriate significant figures. Radar without fine gridlines.

### 6. Overwhelming the Non-Expert
**Anti-pattern**: All 20+ sub-factors, all formulas simultaneously.
**Defense**: Progressive disclosure enforced architecturally. Default view = 3 percentile numbers + radar shape.

### 7. Hype-Adjacent Language
**Anti-pattern**: "Hidden Gem," "Don't Miss This Stock."
**Defense**: Clinical vocabulary: "Exceptional Conviction," "Mispricing Opportunity." Signals classified as BUY/HOLD/SELL with position size guardrails.

### 8. Hiding Negative Results
**Anti-pattern**: Only showing winners.
**Defense**: Empty dashboard explains why. Overvalued picks show negative upside %. System says "no" as loudly as "yes."

### 9. Tooltip Hell
**Anti-pattern**: So many tooltips the interface feels like a textbook.
**Defense**: Tooltips only on metric names, not values. (i) icon small (12px), muted, hover-revealed. Tooltip always exactly 4 lines.

### 10. Comparison Without Context
**Anti-pattern**: "ROIC: 22.4% vs AAPL: 18.1%" without sector context.
**Defense**: FailedComparison states comparison basis. Sector-neutral callout before scoring data. Radar overlays sector-relative.

---

## Implementation Summary

### New Components
1. `FactorRadar` — Recharts radar chart with 3 overlays (stock, sector median, sector P90)
2. `FailedComparison` — Side-by-side filter comparison for eliminated tickers
3. `FormulaTooltip` — Standardized 4-line tooltip with formula, source, interpretation
4. `SectorNeutralBanner` — Promoted methodology callout
5. `DeterminismBadge` — Persistent "no human override" indicator

### Enhanced Components
1. `EliminatedHero` — Protective framing for mega-caps, hypothetical teaser line
2. `ScoringPillars` sub-factor rows — Sector comparison micro-bars
3. `FilterCard` — Sector pass rate context line on failed filters
4. `HypotheticalScores` — Dimmed radar + universe rank sentence
5. `HeroHeader` metadata ribbon — Color-coded freshness, coverage tooltip

### API Requirements
1. `sector_pass_rate` field on `FilterResultResponse` (float, 0-1)
2. Sector champion ticker endpoint for FailedComparison
3. Sector percentile distribution data (P10, P50, P90) for sub-factor micro-bars
4. Sector peer count for SectorNeutralBanner

### Static Data
- `FormulaDefinition` map: ~30 entries covering all metrics across filters, pillars, conviction, and valuation
