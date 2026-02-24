# Asset Detail UI Design

**Date:** 2026-02-23
**Status:** Approved
**Author:** Claude (brainstorming session)

## Overview

The Asset Detail page (`/asset/{ticker}`) is an interactive forensic report that builds user trust through radical transparency. It serves two modes from a single route:

1. **Passing tickers** — full audit report (verdict, filters, scoring, conviction, valuation)
2. **Failed tickers** — elimination diagnosis with optional hypothetical scores

The design follows the "Audit Report" approach: a vertically scrolling page that reads like a financial due diligence document. Verdict first, then evidence, in decreasing order of importance.

## Target User

Analytically sophisticated investors who trust math but only if they can verify it. They will test the system by searching familiar names (TSLA, NVDA) and expect to see exactly why those stocks did or did not qualify.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Failed ticker treatment | Tiered reveal: show filter failures first, expandable partial scores below | Respects the gate concept while satisfying power-user curiosity |
| Default info density | Pillar-first with expandable sub-factors | Casual users see three numbers; forensic users drill into 20+ sub-factors |
| Conviction engine | Included as its own section | Sophisticated audience expects opportunity classification and sizing guidance |
| Search entry point | Global search bar; same `/asset/{ticker}` route handles both modes | Single URL pattern, two presentations based on filter outcome |
| Score history | Minimal sparkline in hero card | Communicates trajectory without consuming page real estate |

## Page Structure

### Section 1: Hero Header

Immediately answers: "What's the verdict?"

**Passing ticker:**

```
┌─────────────────────────────────────────────────────────────────┐
│  <- Back to Dashboard                              Search       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AAPL  Apple Inc.                          Technology · Mature  │
│  $187.42  +1.23 (+0.66%)                                       │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Score    │  │ Percentile│  │ Conviction│  │ Signal        │  │
│  │   78.3   │  │ Top 4%   │  │ HIGH     │  │ BUY           │  │
│  │ sparkline│  │ of 2,847 │  │          │  │               │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                 │
│  Data coverage: 94%  ·  Scored: 2h ago  ·  Price: Live         │
└─────────────────────────────────────────────────────────────────┘
```

**Elements:**
- **Global search** in top-right — the "Why Not?" entry point, works from any page
- **Score sparkline** — last ~30 scores as a minimal trend indicator
- **Four metric cards:** Composite score, universe percentile (with universe size), conviction level, trading signal
- **Metadata ribbon:** Data coverage %, when scored, price freshness — preemptively answers "is this data current?"
- **Growth stage + sector** on the name line — tells the user what weight profile is applied

**Failed ticker hero:**

```
┌─────────────────────────────────────────────────────────────────┐
│  TSLA  Tesla Inc.                  Consumer Disc. · High Growth │
│  $241.87  +3.12 (+1.31%)                                       │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ELIMINATED                                               │  │
│  │  Failed 2 of 6 elimination filters.                       │  │
│  │  This stock did not qualify for scoring.                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Data coverage: 91%  ·  Last checked: 4h ago                   │
└─────────────────────────────────────────────────────────────────┘
```

Red elimination banner replaces the four metric cards. No score shown — elimination is absolute.

**Psychology:** Leading with the verdict satisfies the user's primary question instantly. The metadata ribbon preemptively addresses data staleness anxiety.

---

### Section 2: Elimination Gauntlet

The trust anchor of the entire page. Answers: "What did this stock have to survive?"

**Passing ticker — all 6 filters always visible:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ELIMINATION GAUNTLET                          6 of 6 passed   │
│  Every scored stock must survive all six filters.               │
│                                                                 │
│  [Filter Card] LIQUIDITY                                       │
│    Market Cap: $2.89T          Minimum: $200M                  │
│    Max Position: 5.0%          Divergence: Low                 │
│                                                                 │
│  [Filter Card] EARNINGS QUALITY (Beneish M-Score)              │
│    M-Score: -2.87              Red Flag: > -2.22               │
│    Formula: 8-variable composite (DSRI, GMI, AQI, SGI, etc.)  │
│    Trend (3yr): -2.91 -> -2.87 -> -2.83  stable               │
│                                                                 │
│  [Filter Card] FINANCIAL DISTRESS (Altman Z-Score)             │
│    Z-Score: 5.12               Minimum: 1.1                   │
│    Formula: 6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA)        │
│             + 1.05(Equity/TL)                                  │
│                                                                 │
│  [Filter Card] SHORT-TERM LIQUIDITY (Current Ratio)            │
│    Current Ratio: 0.99         Threshold: 0.80 (Tech)         │
│    Formula: Current Assets / Current Liabilities               │
│    Sector-adjusted: Tech threshold is 0.80 (default: 1.0)     │
│                                                                 │
│  [Filter Card] CASH FLOW HEALTH (FCF Distress)                │
│    FCF: $104.3B                Requirement: Positive           │
│    Trend (3yr): Positive in all periods                        │
│                                                                 │
│  [Filter Card] DEBT SERVICE (Interest Coverage)                │
│    Coverage: 29.4x             Sector Median Min: 3.0x        │
│    Formula: EBIT / Interest Expense                            │
└─────────────────────────────────────────────────────────────────┘
```

**Each filter card shows:**
1. Human-readable name + technical name
2. Stock's actual value vs. required threshold — side by side
3. Formula or methodology used
4. Multi-period trend data when available (v2 filters)
5. Sector-adjusted thresholds called out explicitly when they differ from defaults

**Failed ticker gauntlet — failed filters sort to top and expand:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ELIMINATION GAUNTLET                        4 of 6 passed     │
│  TSLA was eliminated. It failed 2 of 6 filters.               │
│                                                                 │
│  [FAILED] FINANCIAL DISTRESS (Altman Z-Score)                  │
│    Z-Score: 1.6                Minimum: 1.1                   │
│    Progress bar: [========------]  1.6 of 1.1 required        │
│                                                                 │
│    WHY THIS MATTERS: The Altman Z-Score predicts bankruptcy    │
│    probability. Scores below 1.1 indicate a company in the    │
│    distress zone.                                              │
│                                                                 │
│    Formula: 6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA)        │
│             + 1.05(Equity/TL)                                  │
│                                                                 │
│  [FAILED] CASH FLOW HEALTH (FCF Distress)                      │
│    FCF: -$2.1B                 Requirement: Positive           │
│    Negative FCF in 2 of last 3 periods.                        │
│                                                                 │
│    WHY THIS MATTERS: Persistent negative free cash flow means  │
│    the company is burning cash. This increases dilution risk   │
│    and limits capital return.                                  │
│                                                                 │
│  [passed] LIQUIDITY (compact)                                  │
│  [passed] EARNINGS QUALITY (compact)                           │
│  [passed] SHORT-TERM LIQUIDITY (compact)                       │
│  [passed] DEBT SERVICE (compact)                               │
└─────────────────────────────────────────────────────────────────┘
```

**Failed ticker differences:**
- Failed filters sort to top with red accent and expanded detail
- Progress bar gives instant visual of distance from threshold
- "WHY THIS MATTERS" block translates raw metric into plain-English risk explanation
- Passed filters collapse to compact single-line form

**Psychology:** "WHY THIS MATTERS" transforms a raw number into a concept. "Z-Score = 1.6" means nothing to most users. "This company is in the distress zone" creates understanding. Failed-first sort order puts the elimination reason at the top of the viewport — creating the "aha" moment immediately.

---

### Section 3: Scoring Pillars

Answers: "Across every dimension we measure, where does this stock rank?"

```
┌─────────────────────────────────────────────────────────────────┐
│  SCORING BREAKDOWN                                              │
│  Weighted by growth stage: Mature (Q:30% · V:40% · M:30%)     │
│                                                                 │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────┐ │
│  │  QUALITY    30%   │ │  VALUE      40%   │ │ MOMENTUM 30%  │ │
│  │      72nd         │ │      81st         │ │    68th       │ │
│  │    percentile     │ │    percentile     │ │  percentile   │ │
│  │  [progress bar]   │ │  [progress bar]   │ │ [progress bar]│ │
│  │  > 8 sub-factors  │ │  > 6 sub-factors  │ │ > 4 factors   │ │
│  └───────────────────┘ └───────────────────┘ └───────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key decisions:**
1. **Growth stage + weights shown in the section header** — preempts "why is Value weighted 40%?"
2. **Three equal cards** regardless of weight — visual parity, weight shown as label
3. **Percentile as hero number** — most honest representation of relative standing
4. **Expandable sub-factors** — click to reveal detail table

**Expanded sub-factor table:**

```
  Sub-Factor              Raw Value    Percentile    Detail
  ─────────────────────────────────────────────────────────
  Piotroski F-Score       7 / 9        85th         Strong
  Gross Profitability     0.43         78th         Above avg
  ROIC Stability          0.91         74th         Consistent
  Asset Turnover          0.82         65th         Average
  Operating Leverage      1.23         71st         Good
  Accrual Ratio           -0.03        80th         Clean
  Insider Cluster         2 buys       62nd         Mild
  Inst. Accumulation      +1.2%        58th         Neutral

  Methodology: Each sub-factor is ranked within the stock's
  GICS sector first (sector-neutral), then combined.
```

**Four columns per sub-factor:**
- Name
- Raw value (the actual number — "show the math")
- Percentile rank (how it compares)
- Plain-English detail word

**Psychology:** Raw value + percentile pairing is critical. The percentile alone feels like a black box ("how did you get 85th?"). Showing "7/9" alongside it makes the percentile verifiable. The sector-neutral methodology note preempts sector-bias objections.

---

### Section 4: Conviction Engine

Answers: "What kind of opportunity is this, and how should I size/time it?"

```
┌─────────────────────────────────────────────────────────────────┐
│  CONVICTION ENGINE                                              │
│                                                                 │
│  Opportunity Type: COMPOUNDER                                   │
│  This stock exhibits durable competitive advantages and         │
│  consistent reinvestment returns.                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │ Asymmetry    │  │ Max Position │  │ Timing            │    │
│  │   4.2x       │  │   5.0%       │  │ ADD ON PULLBACK   │    │
│  │ Upside is    │  │ of portfolio │  │ Wait for a 5-10%  │    │
│  │ 4.2x the    │  │              │  │ dip from current   │    │
│  │ downside     │  │              │  │ levels.            │    │
│  └──────────────┘  └──────────────┘  └───────────────────┘    │
│                                                                 │
│  COMPOUNDER TRACK (winning)                                     │
│    Moat Durability     82nd  [================----]             │
│    Compounding Power   76th  [===============-----]             │
│    Capital Allocation  71st  [==============------]             │
│    Growth Gap          68th  [=============-------]             │
│                                                                 │
│  MISPRICING TRACK                                               │
│    Asymmetry Ratio     4.2x                                     │
│    Catalyst Strength   45th  [==========-----------]            │
│    Quality Floor       72nd  [==============------]             │
│    Valuation Conv.     55th  [===========---------]             │
└─────────────────────────────────────────────────────────────────┘
```

**Key decisions:**
1. **Opportunity type badge with one-line explanation** — "COMPOUNDER" alone is jargon; the explanation makes it accessible
2. **Three action-oriented metric cards** — asymmetry ratio, max position, timing signal — with plain-English interpretations
3. **Both conviction tracks shown** — even the losing track, so users can see *why* one won
4. **Winning track visually differentiated** with label

**Opportunity type descriptions:**
- **Compounder:** Durable competitive advantages and consistent reinvestment returns
- **Mispricing:** Market is undervaluing this stock relative to its fundamentals
- **Both:** Exhibits both compounding qualities and current mispricing
- **Neither:** Does not clearly fit either opportunity pattern

**Psychology:** This section transitions from data to prescription. Showing both tracks — including the loser — signals intellectual honesty. The asymmetry ratio ("upside is 4.2x the downside") resonates instantly with quantitative investors.

---

### Section 5: Valuation & Price Targets

Answers: "What is this stock worth, and where are we relative to fair value?"

```
┌─────────────────────────────────────────────────────────────────┐
│  VALUATION                                                      │
│                                                                 │
│     $142          $165           $187          $214             │
│      Buy           ·              ·            Sell             │
│       |------------|--------------|-------------|              │
│                    |         ^                                  │
│              Intrinsic    Current                               │
│              Value        Price                                 │
│              $165         $187.42                               │
│                                                                 │
│  Price Upside: -11.9%     Margin of Safety: -13.6%             │
│  Warning: Currently trading ABOVE intrinsic value               │
│                                                                 │
│  Valuation Methods                                              │
│  Method              Implied Value    Weight   Status           │
│  ──────────────────────────────────────────────────            │
│  Reverse DCF         $158.20          35%      Computed        │
│  EV/FCF Median       $172.40          25%      Computed        │
│  Acquirer's Multiple $161.80          25%      Computed        │
│  Shareholder Yield   $170.50          15%      Computed        │
│  ──────────────────────────────────────────────────            │
│  Blended Intrinsic Value: $165.00                              │
│                                                                 │
│  > Full Valuation Audit (DCF scenarios, sensitivity analysis)  │
└─────────────────────────────────────────────────────────────────┘
```

**Key decisions:**
1. **Price ruler visualization** — horizontal number line from Buy to Sell with Intrinsic Value and Current Price marked. Converts four abstract numbers into a single spatial relationship.
2. **Negative upside shown honestly** — when overvalued, the warning is explicit. Strongest trust signal: "we'll tell you when our own picks are overvalued."
3. **Valuation methods table** — shows each method, implied value, weight, and computation status. Dismantles the black-box objection for price targets.
4. **"Full Valuation Audit" expandable** — links to detailed DCF scenarios and sensitivity tables for power users.

**Graceful degradation when intrinsic value unavailable:**

```
  Intrinsic value unavailable.
  Reason: Negative trailing earnings prevent reliable DCF computation.
  Score-based assessment is still available above.
```

Powered by the `price_target_invalid_reason` API field.

**Psychology:** The price ruler is a "worth the scroll" visualization — instant spatial understanding. Negative upside display is counterintuitive for a picks platform, but it's the strongest trust signal: "we're honest even when the numbers aren't flattering."

---

### Section 6: "What If It Had Passed?" (Failed Tickers Only)

Appears only on eliminated tickers, below the gauntlet. Collapsed by default.

**Collapsed:** "What if TSLA had passed all filters? See partial scores."

**Expanded:**

```
┌─────────────────────────────────────────────────────────────────┐
│  HYPOTHETICAL SCORES                                            │
│  These scores are informational only. TSLA did not survive      │
│  elimination and is NOT a scored recommendation.                │
│                                                                 │
│  Composite Score: 61.4    Conviction: NONE    Signal: N/A      │
│                                                                 │
│  QUALITY 30%: 54th  |  VALUE 25%: 42nd  |  MOMENTUM 35%: 78th │
│  (Sub-factors expandable, same layout as Section 3)            │
│                                                                 │
│  Even if it had passed filters, TSLA would rank in the 38th   │
│  percentile of the scored universe — below the threshold for   │
│  any conviction level (minimum: 65.0).                         │
└─────────────────────────────────────────────────────────────────┘
```

**Key decisions:**
1. **Prominent "HYPOTHETICAL" warning** — amber banner, unambiguous
2. **Same pillar card layout** as Section 3 for visual consistency
3. **Narrative conclusion** — states where it would have ranked and whether it would have achieved any conviction level

**Narrative adapts to the data:**
- Low hypothetical score: "would rank in the 38th percentile — below the threshold for any conviction level"
- High hypothetical score: "would rank in the 82nd percentile — however, the elimination filters exist to remove fundamental risk regardless of scoring potential"

**Psychology:** This section exists purely for trust. Users searching TSLA are testing the system. The tiered reveal satisfies their curiosity while the hypothetical warning prevents them from treating it as a recommendation.

---

## Interaction Flows

### Flow 1: User clicks a pick from dashboard
1. Dashboard pick card -> click -> `/asset/AAPL`
2. Hero loads with score, conviction, signal, sparkline
3. Full audit report below: Gauntlet -> Pillars -> Conviction -> Valuation
4. Pillar sub-factors collapsed by default

### Flow 2: User searches any ticker via global search
1. Search bar in top nav -> type "TSLA" -> select from autocomplete
2. Navigate to `/asset/TSLA`
3. API returns score data with filter failures
4. Hero shows "ELIMINATED" banner
5. Gauntlet dominates: failed filters expanded, passed filters compact
6. "What if?" section collapsed at bottom
7. No Conviction Engine or Valuation sections for eliminated tickers

### Flow 3: Ticker with insufficient data
1. Search -> ticker not in system
2. Hero: "No data available for XYZA. This ticker may not be in our coverage universe (minimum market cap $200M)."
3. Clean empty state with explanation

### Flow 4: Ticker that passes but scores low
1. Search -> `/asset/F` (Ford)
2. Full audit report shown (passes all filters)
3. Hero shows score 58.2, conviction NONE, signal WATCH
4. Identical layout to a top pick — the system doesn't editorialize

## Visual Hierarchy

| Priority | Element | Purpose |
|----------|---------|---------|
| 1 | Hero: Score + Signal | Immediate verdict |
| 2 | Elimination Gauntlet | Trust anchor |
| 3 | Scoring Pillars (collapsed) | Factor summary |
| 4 | Conviction Engine | Opportunity classification + action guidance |
| 5 | Valuation + Price Ruler | Fair value assessment |
| 6 | Sub-factor expansion | Deep forensic detail |
| 7 | "What if?" reveal | Failed-ticker hypothesis |

## Color Language

- **Green:** Pass / positive / above threshold
- **Red:** Fail / eliminated / below threshold
- **Amber/Yellow:** Warning / hypothetical / inconclusive
- **Neutral (gray/slate):** Informational, no judgment

## API Dependencies

All data comes from existing endpoints:

| Endpoint | Data |
|----------|------|
| `GET /api/v1/scores/{ticker}` | Full score response: filters, pillars, sub-factors, conviction, price targets |
| `GET /api/v1/scores/{ticker}/history` | Historical scores for sparkline (limit=30) |
| `GET /api/v1/scores/{ticker}/valuation-audit` | Detailed valuation breakdown for expanded audit |

Optional query params: `?include=price_history,signal_history`

## Data Model Mapping

The API `ScoreResponse` already provides all fields needed:

- **Hero:** `composite_raw_score`, `composite_percentile`, `conviction_level`, `signal`, `data_coverage`, `scored_at`, `data_freshness`, `growth_stage`
- **Gauntlet:** `filters_passed[]` — each with `name`, `passed`, `value`, `threshold`, `detail`, `verdict`
- **Pillars:** `quality`, `value`, `momentum` — each `FactorBreakdownResponse` with `sub_scores[]` containing `name`, `raw_value`, `percentile_rank`, `detail`, `weight`
- **Conviction:** `opportunity_type`, `winning_track`, `asymmetry_ratio`, `max_position_pct`, `timing_signal`, `capital_allocation`, `catalyst`
- **Valuation:** `margin_invest_value`, `buy_price`, `sell_price`, `actual_price`, `price_upside`, `margin_of_safety`, `valuation_methods`, `price_target_invalid_reason`
