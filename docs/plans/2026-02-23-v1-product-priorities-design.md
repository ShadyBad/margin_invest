# V1 Product Priorities — Strategic Design Document

**Date:** 2026-02-23
**Status:** Approved
**Author:** Claude (strategic analysis session)

## Purpose

This document evaluates four critical product priorities for Margin Invest V1, provides strategic recommendations for each, and defines a unified positioning approach. It builds on the existing behavioral positioning analysis and asset detail UI design.

## Context

The asset detail page (forensic report) is complete with 9 implemented components. The behavioral positioning plan has 5 of 10 tasks complete (empty state, overvaluation explanation, hero copy, filter citations, sub-factor formulas are shipped). The backtesting engine is designed but not built. Data freshness indicators exist in the hero header metadata ribbon and ingestion banner.

---

## Priority A: The "Glass Box" (Explainability Is Everything)

### Strategic Assessment: Category-defining. 90% built.

The asset detail page already functions as an interactive forensic report. The elimination gauntlet shows every filter with value vs. threshold, formulas, academic citations (Beneish 1999, Altman 1968, etc.), and "WHY THIS MATTERS" blocks. Scoring pillars expand to show raw values alongside percentile ranks with inline formula toggles. The valuation section honestly displays negative upside. Hypothetical scores handle eliminated tickers.

No competitor offers this level of transparency. Zacks shows rank without work. Simply Wall St visualizes without depth. Portfolio123 makes the user build it. Margin Invest shows the work *and* does the work.

### Gaps to Close

1. **Fundamental data dating on filter cards.** Current metadata ribbon shows "Scored: 2h ago" but individual filter cards don't show which filing period their data comes from. Add "Based on Q3 2025 10-Q filed Oct 28, 2025" to each filter card.

2. **Elimination rate context on passing tickers.** Passing ticker pages show the gauntlet as "6 of 6 passed" but don't contextualize the difficulty. Add "X% of the universe was eliminated before scoring."

3. **Dead-end on eliminated ticker pages.** User searches TSLA, sees ELIMINATED, reads hypothetical scores, and has no path forward. Add a CTA: "N stocks in [same sector] survived the gauntlet."

4. **Gauntlet Replay: recent eliminations timeline.** Show recently eliminated stocks that previously passed — the URGENT SELL equivalent. "In the last 90 days, N stocks that previously passed all filters were eliminated." This proves the system catches deterioration in real time.

### Psychological Impact

| Archetype | Impact | Mechanism |
|-----------|--------|-----------|
| Burned but Serious | Very High | "WHY THIS MATTERS" on failed filters recreates the moment they wish they'd had. Every filter card is a post-mortem they never got. |
| DIY Quant | Very High | Inline formula toggle + academic citations enable the verification ritual. |
| Rationalist | High | Deterministic structure (same value, same threshold, same outcome) satisfies structural bias prevention need. |

### Execution Risks

- **Data staleness.** If fundamental data is weeks old and a user catches it, the forensic report becomes evidence against you. Mitigated by adding filing period attribution.
- **Formula density overwhelms non-quant users.** Mitigated by progressive disclosure (collapsed by default, "WHY THIS MATTERS" leads, formula one click deeper).
- **"Why Not?" dead end.** Mitigated by sector survivor CTA.

---

## Priority B: "Zero Results" Scenario (Market Regimes)

### Strategic Assessment: Genuinely differentiating. Partially built.

The empty dashboard state shows "The system is working. It found nothing worth your capital right now." This frames absence as discipline. But in an actual zero-results scenario during a market bubble, this single sentence needs to carry much more weight.

### Gaps to Close

1. **Enrich the empty state with quantitative context.** Three layers: (a) headline, (b) elimination/scoring stats ("X% failed elimination, none scored above 90th percentile"), (c) historical parallel when available.

2. **Market Regime indicator on dashboard header.** Not a prediction — a measurement. Based on elimination rate and scoring distribution. Categories: Normal, Concentrated, Overheated. A single label that contextualizes whatever the dashboard shows.

3. **Low-results state (2-3 picks).** Distinct from zero results. When only a few stocks pass, the dashboard should contextualize scarcity: "Only N stocks survived all filters and scored above the 90th percentile. The full universe: X stocks scored."

4. **"Discipline Dividend" retrospective.** After a correction following a low/zero-results period, automatically surface: "During [date range], the system recommended staying in cash. The S&P 500 subsequently declined X%." This converts subscribers into evangelists. Requires no prediction — only backward-looking measurement.

### Psychological Impact

| Archetype | Impact | Mechanism |
|-----------|--------|-----------|
| Burned but Serious | Very High | "If I'd had this in 2021, it would have told me to stay in cash." The empty dashboard becomes the product's defining memory. |
| DIY Quant | High | Seeing the system quantify market regimes ("98% failed Margin of Safety") converts abstract knowledge into confirmation. |
| Rationalist | Very High | The system refusing to recommend is the purest expression of zero discretion. |

### Execution Risks

- **Churn risk.** A user paying monthly who sees zero picks for 2-3 months questions value. Mitigated by providing ongoing analytical value (market regime data, elimination stats, historical parallels) even when picks are absent.
- **"Cash is a position" reads as dismissive without data.** Mitigated by surfacing elimination rate and scoring distribution stats.
- **Pipeline must run every cycle regardless of output.** Elimination rate and scoring distribution are valuable even when zero stocks qualify. Must store these as "market health" metrics.

---

## Priority C: Backtest Validation (Onboarding Proof)

### Strategic Assessment: Highest-leverage item. Cannot ship yet.

The backtesting engine is designed (walk-forward from Jan 2015, point-in-time data, fixed weights, transaction costs, anti-bias measures) but not implemented. The landing page proof section has a placeholder ribbon ("Walk-forward backtest since 2015") with disclaimer but no actual numbers. The backtesting page UI exists as shells waiting for data.

### Decision: Ship V1 without backtest numbers. Start paper trading from day one.

**Rationale:**
- The Glass Box features are 90% built and genuinely category-defining
- A rushed backtest with bad methodology would destroy trust faster than no backtest
- Walk-forward backtesting with point-in-time data is months of engineering
- Factor strategies post-2020 have mixed results — the numbers might not be flattering
- The paper trading log creates forward-looking proof that compounds over time and cannot be overfit

### V1 Approach

1. **Publish backtest methodology now, results later.** Put anti-bias measures on the methodology page as commitments: point-in-time data, fixed weights, survivorship handling, transaction costs. When results arrive, they're pre-credible.

2. **Start live paper portfolio on launch day.** Every BUY/SELL signal recorded with timestamp. After 6 months, you have live out-of-sample performance. Publish as running log, updated daily.

3. **Remove placeholder backtest numbers from proof section.** Replace with methodology description and "live tracking since [launch date]" framing. Never show numbers that don't exist.

4. **Build the full backtesting engine post-launch** as the highest-priority V1.1 feature.

### Psychological Impact

| Archetype | Impact | What V1 delivers without backtest |
|-----------|--------|----------------------------------|
| Burned but Serious | Reduced conversion without a number. Mitigated by Glass Box strength. | The forensic report + "search any ticker" + honest overvaluation display create trust through transparency rather than historical proof. |
| DIY Quant | Will note the absence. Mitigated by methodology publication + paper tracking. | They respect the intellectual honesty of not claiming results you haven't produced. |
| Rationalist | Accepts the logic that a system with no backtest is honest about its limitations. | The determinism claim is independently verifiable (search any ticker, check the math). |

---

## Priority D: Smart Pricing of Data (Reliability as Product)

### Strategic Assessment: Important hygiene factor. Not differentiating alone.

Data freshness indicators already exist: hero header metadata ribbon ("Data coverage: 94% / Scored: 2h ago / Price: Live"), ingestion banner with pipeline progress, dashboard last-updated timestamp.

### Gaps to Close

1. **Abstract away provider names.** Show "Fundamentals: Q3 2025 10-Q (filed Oct 28)" not "Source: yfinance." The filing date matters, not the pipe.

2. **Color-code freshness.** Green = <1 hour. Yellow = <24 hours. Amber = >24 hours. No red — if data is too stale, suppress it.

3. **"Audit Trail" toggle for power users.** Off by default. Shows exact data source and timestamp for every number: "EBIT: $129.3B (10-K filed Jan 26, 2026)." This level of provenance doesn't exist in retail finance.

4. **Data coverage breakdown on methodology page.** One paragraph: "Our data infrastructure uses N providers with automatic failover. Every data point is cross-validated against SEC filings."

### Psychological Impact

| Archetype | Impact | Mechanism |
|-----------|--------|-----------|
| Burned but Serious | Low-Medium | They notice staleness only when it contradicts experience. Proactive freshness prevents that moment. |
| DIY Quant | Medium | "SEC Q3 10-Q filed Oct 28" signals professional-grade operations. Prevents de-conversion. |
| Rationalist | Low | Data freshness is a hygiene factor. They expect it to be right. |

### Execution Risks

- **Overpromising freshness.** If showing "5 minutes ago" but yfinance has 15-minute delay, that's a verifiable lie. Must accurately reflect actual data latency.
- **Exposing fallback chain.** Users shouldn't see provider names. They should see data quality characteristics (filing date, coverage %).

---

## Implementation Scope for V1

### What to build (ordered by impact)

**From Priority A (Glass Box):**
1. Filing period attribution on filter cards — show which SEC filing the data comes from
2. Elimination rate context on passing ticker hero — "X% of the universe was eliminated"
3. Sector survivor CTA on eliminated tickers — "N stocks in [sector] survived"
4. Gauntlet Replay timeline — recently eliminated stocks that previously passed (complex, may defer)

**From Priority B (Zero Results):**
5. Enrich empty dashboard with elimination/scoring stats
6. Market Regime indicator label on dashboard header
7. Low-results contextual messaging (2-3 picks)

**From Priority C (Backtest):**
8. Remove placeholder backtest numbers, replace with methodology + "live tracking" framing
9. Paper portfolio tracking infrastructure (record every signal with timestamp)

**From Priority D (Data Reliability):**
10. Filing period attribution on filter cards (shared with item 1)
11. Freshness color-coding on metadata ribbon
12. Audit Trail toggle on asset detail (power user, off by default)

### What to defer to V1.1

- Full walk-forward backtesting engine
- "Discipline Dividend" retrospective (requires historical zero-results periods)
- Gauntlet Replay timeline (requires historical elimination tracking not yet stored)
- Methodology page enrichment with "why not the alternative" reasoning per section

---

## V1 Positioning Statement

> "Every number shown. Every formula cited. Every elimination explained. The system has no opinion — only math, applied ruthlessly."

### Unification

- **Glass Box** → "Every number shown. Every formula cited."
- **Zero Results** → "applied ruthlessly" (even when ruthless means recommending nothing)
- **Backtest Proof** → "Every elimination explained" (the audit trail is the proof until backtest exists)
- **Data Reliability** → implied by "every number shown" (you can only show numbers you trust)

### Archetype Resonance

| Archetype | What They Hear |
|-----------|---------------|
| Burned but Serious | "You'll see everything. No hidden surprises." |
| DIY Quant | "Every formula cited. You can verify it." |
| Rationalist | "No opinion. Only math." |
