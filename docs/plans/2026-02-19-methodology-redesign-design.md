# Methodology Page Redesign — Design Document

**Date:** 2026-02-19
**Status:** Approved
**Approach:** Education-First Funnel (Approach A)

## Goal

Rewrite and redesign the Methodology page so it contains real, helpful content and visuals that clearly communicate value — without revealing proprietary details (formulas, weights, thresholds).

The page must:
- Explain how Margin Invest creates value (clear, credible, specific)
- Describe the engine at a mid to semi-high level (name factors, don't reveal formulas)
- Explain the dual-track conviction system (Compounder vs Mispricing)
- Use tasteful charts/diagrams to make concepts intuitive
- Include conversion-oriented marketing copy that justifies paying for the product
- Stay consistent with the app's actual workflow and UI terms

## Audience

- **Primary:** Self-directed investors who want a systematic workflow and time savings
- **Secondary:** Advanced users who care about rigor, repeatability, and transparency

## Disclosure Level

- Name all sub-factors (ROIC-WACC Spread, Piotroski F-Score, etc.)
- Do NOT reveal formulas, exact weights, thresholds, or vendor-specific details
- Explain both conviction tracks (Compounder and Mispricing) at a high level

---

## Page Structure

| # | Section | Eyebrow | H2 | Purpose |
|---|---|---|---|---|
| 1 | Hero | How It Works | (H1 — see options below) | Value prop, outcomes, who it's for / not for |
| 2 | Pipeline Overview | The Pipeline | "From raw data to conviction — every day." | Visual diagram, mental model of end-to-end flow |
| 3 | Universe & Data | Universe Selection | "Every US-listed equity. No cherry-picking." | What's included/excluded, refresh cadence, freshness |
| 4 | Elimination Filters | Elimination Filters | "Bad candidates are removed before scoring begins." | 6 filters described, funnel visual |
| 5 | Scoring Engine | Multi-Factor Scoring | "20+ factors. Three pillars. Sector-neutral ranking." | Pillars, named factors, how ranking works |
| 6 | Dual-Track Conviction | Conviction System | "Two independent lenses. One conviction score." | Compounder vs Mispricing, conviction levels |
| 7 | What You Get | Product Outputs | "Structured outputs you can act on — not opinions to interpret." | Cards, breakdowns, price targets, sizing |
| 8 | How to Use the Output | Responsible Usage | "What to do — and not do — with these candidates." | Do/Don't lists, judgment-is-yours framing |
| 9 | Transparency & Limitations | Transparency | "What this is — and what it isn't." | Not advice, model limits, validation checklist |
| 10 | Why Margin Invest | Why Pay | "Replace hours of screening with a system that runs every day." | ROI framing, tier features, CTA |

---

## Section 1 — Hero

**Eyebrow:** How It Works

**H1 headline options (choose during implementation):**
1. "A scoring engine for every equity in your universe."
2. "Systematic conviction. No narratives."
3. "From 7,000+ stocks to the ones worth your attention."

**Subhead:**
"Margin Invest runs every US-listed equity through a deterministic pipeline of elimination filters, multi-factor scoring, and conviction ranking — daily. Same inputs, same outputs. No human judgment anywhere in the process."

**Outcome bullets (5):**
- Scores updated daily after market close
- Transparent factor breakdowns you can audit
- Quantified conviction levels, not subjective ratings
- Price targets with explicit margin of safety
- Position sizing tied to conviction strength

**Who it's for / not for (two-column layout):**

| Built for | Not built for |
|---|---|
| Self-directed investors who want a repeatable process | Traders looking for intraday signals |
| Portfolio managers who value transparency over tips | Anyone expecting guaranteed returns |
| Analysts who want to eliminate blind spots | Passive index investors |

**Visual:** None — clean typography, let the copy breathe.

---

## Section 2 — Pipeline Overview

**Eyebrow:** The Pipeline

**H2:** "From raw data to conviction — every day."

**Subhead:** "Each scoring cycle runs the same sequence. Every stage is deterministic: same data in, same scores out."

**Visual: Pipeline Diagram** — 6-stage horizontal flow (desktop), vertical stack (mobile):

| Stage | Label | Subtitle | Metric |
|---|---|---|---|
| 01 | Universe | Selection | ~7,000 US equities |
| 02 | Data | Ingestion | Daily after close |
| 03 | Filters | Elimination | 6 independent checks |
| 04 | Scoring | Multi-Factor | 20+ quantitative factors |
| 05 | Conviction | Dual-Track | Compounder & Mispricing |
| 06 | Output | Decisions | Cards, targets, sizing |

Arrows connect each stage. Each stage is a card with number in accent monospace, name in bold, subtitle, and metric in text-tertiary.

**Implementation:** Hand-built SVG + Tailwind CSS, similar to the existing pipeline component but with 6 stages instead of 7. Desktop: horizontal with SVG arrows. Mobile: vertical stack with downward arrows.

**Caption:** "The pipeline runs automatically after each market close. Scores typically refresh within 2 hours of the closing bell."

---

## Section 3 — Universe & Data

**Eyebrow:** Universe Selection

**H2:** "Every US-listed equity. No cherry-picking."

**Copy:** "The engine starts with the full universe of US-listed equities across all major exchanges — NYSE, NASDAQ, and NYSE American. Financials and Real Estate are excluded because their capital structures make standard profitability metrics unreliable. Everything else is in."

**Three detail cards (md:grid-cols-3):**

**Card 1 — "What's included"**
- ~7,000+ US-domiciled equities
- 9 sectors: Technology, Healthcare, Industrials, Energy, Consumer Cyclical, Consumer Defensive, Basic Materials, Utilities, Communication Services
- All market caps above liquidity minimums

**Card 2 — "What's excluded"**
- Financials (banks, insurance, asset managers — leverage-as-product breaks ROIC metrics)
- Real Estate (REITs use fundamentally different valuation frameworks)
- OTC / Pink Sheet listings
- Foreign ADRs

**Card 3 — "Data freshness"**
- Full scoring cycle runs daily after market close (4:30 PM ET)
- Scores refresh within ~2 hours of the closing bell
- Each score carries a freshness label: Fresh (< 18 hours), Stale (18h–3 days), or Expired (> 3 days)

---

## Section 4 — Elimination Filters

**Eyebrow:** Elimination Filters

**H2:** "Bad candidates are removed before scoring begins."

**Copy:** "Before any stock receives a score, it must pass six independent elimination filters. All six run regardless of earlier failures — you see the full diagnostic, not just the first thing that went wrong. Roughly 40% of the universe fails at least one filter."

**Six filter cards (md:grid-cols-2):**

| Filter | Description |
|---|---|
| **Liquidity** | Sufficient trading volume and market cap to build a real position |
| **Earnings Quality** | Beneish M-Score screens for signs of earnings manipulation |
| **Bankruptcy Risk** | Altman Z-Score identifies companies in financial distress |
| **Cash Flow** | Consistent free cash flow generation over multiple years |
| **Interest Coverage** | Ability to service debt obligations from operating earnings |
| **Balance Sheet Health** | Current ratio and quick ratio above sector-adjusted thresholds |

**Footer note (text-xs):** "Filter thresholds are sector-adjusted — a utility company and a tech company are held to different standards where appropriate."

**Visual: Filter Funnel** — Horizontal narrowing bar or simple funnel graphic:
- ~7,000 universe → ~4,200 pass all filters → scored
- Implementation: Hand-built SVG, three segments with labels and counts

---

## Section 5 — Scoring Engine

**Eyebrow:** Multi-Factor Scoring

**H2:** "20+ factors. Three pillars. Sector-neutral ranking."

**Intro copy:** "Every stock that passes elimination is scored across 20+ quantitative factors organized into three pillars. Each factor is ranked within its own sector first — a tech company's profitability is compared to other tech companies, not to utilities. This sector-neutral approach ensures scores reflect genuine outlier performance among true peers."

**Three pillar cards (md:grid-cols-3), each with accent border-top:**

### Quality
"Measures the durability and efficiency of a business — how well it converts capital into returns, and whether those returns are real."
- ROIC-WACC Spread
- ROIC Stability
- Incremental ROIC
- Gross Profitability
- Piotroski F-Score
- Accrual Ratio
- Moat Durability

### Value
"Measures what you're paying relative to what the business generates — across multiple valuation lenses to avoid single-metric traps."
- DCF Margin of Safety
- EV/FCF
- Acquirer's Multiple
- Owner Earnings Yield
- Shareholder Yield
- Reverse DCF Growth Gap
- Asset Floor

### Momentum
"Measures whether the market, insiders, and institutions are confirming what the fundamentals suggest."
- Price Momentum (12-1 month)
- Standardized Unexpected Earnings
- Insider Cluster Score
- Institutional Accumulation
- Sentiment Score
- Runway Score

**Below pillars — "How scoring works":**
"Factor scores are converted to percentile ranks within each sector, then combined into a pillar average. Pillar weights adjust based on the company's growth stage — a high-growth company is weighted differently than a mature cash cow. The final composite score is re-ranked across the entire universe to produce a single conviction percentile."

**Visual: Score Breakdown Bars** — Example stock's three pillar scores as horizontal percentile bars:

```
Example: ACME Corp (Technology)
Quality    ████████████████████░░░░░  78th percentile
Value      ████████████████░░░░░░░░░  64th percentile
Momentum   ██████████████████████░░░  88th percentile
──────────────────────────────────
Composite  ████████████████████░░░░░  79th percentile
```

**Implementation:** CSS percentile bars with Tailwind width classes and accent color fills. Static example data, not dynamic.

---

## Section 6 — Dual-Track Conviction

**Eyebrow:** Conviction System

**H2:** "Two independent lenses. One conviction score."

**Intro copy:** "Not every great investment looks the same. Some are durable compounders you want to hold for years. Others are deeply mispriced assets where the market hasn't caught up to the fundamentals. The engine runs both analyses in parallel — a stock can qualify through either track, or both."

**Two track cards (md:grid-cols-2):**

### Track A — Compounder
"Identifies businesses with durable competitive advantages and strong reinvestment engines. These are companies where incremental capital deployed earns high returns — the kind of business that compounds value over long holding periods."

What the engine looks for:
- Evidence of an economic moat (multiple structural signals)
- A reinvestment engine that converts retained earnings into growth
- Disciplined capital allocation
- A valuation that doesn't already price in perfection

### Track B — Mispricing
"Identifies stocks trading at a significant discount to intrinsic value with a catalyst to close the gap. These are situations where multiple valuation methods converge on a higher value than the market price, and smart money is starting to notice."

What the engine looks for:
- Multiple valuation methods agreeing the stock is cheap
- Downside protection (a floor on how much you can lose)
- A catalyst — insider buying, institutional accumulation, or earnings momentum
- A minimum quality floor (cheap for a reason doesn't qualify)

**Below both cards — orchestration note:**
"When a stock qualifies on both tracks simultaneously — a high-quality compounder that also happens to be mispriced — it receives the highest conviction level and the largest suggested position size."

**Conviction levels (small table or badge row):**

| Level | Meaning |
|---|---|
| **Exceptional** | Strongest factor alignment across the universe |
| **High** | Strong multi-factor case with clear margin of safety |
| **Watchlist** | Promising but missing one dimension |

**Visual: Example Candidate Journey Chart** — Line chart showing conviction score over ~6 months:

- X-axis: Jan through Jun (monthly labels)
- Y-axis: Score 0–100
- Single line rising from ~50 to ~90 over the period
- Horizontal bands at Watchlist / High / Exceptional thresholds
- Data points: Jan=52, Feb=61, Mar=70, Apr=78, May=85, Jun=91

**Caption:** "As a company's fundamentals improve and the market hasn't repriced, conviction rises. The engine tracks this progression automatically."

**Implementation:** Recharts `<LineChart>` with `<ReferenceLine>` for conviction thresholds. Static example data. Responsive via Recharts ResponsiveContainer.

---

## Section 7 — What You Get

**Eyebrow:** Product Outputs

**H2:** "Structured outputs you can act on — not opinions to interpret."

**Intro copy:** "Every scored candidate produces a set of concrete outputs designed to eliminate ambiguity. You see exactly why a stock scores the way it does, what price represents a good entry, and how much of your portfolio it warrants."

**Four output cards (md:grid-cols-2):**

| Card | Description |
|---|---|
| **Candidate Cards** | Each stock on your dashboard shows its conviction level, opportunity type (Compounder or Mispricing), signal (Buy / Hold / Sell), and pillar percentile bars — all at a glance. Click any card to open the full analysis. |
| **Factor Breakdown** | Drill into the exact Quality, Value, and Momentum percentile scores. See which factors are driving the conviction level and which are holding it back. Every score is auditable — no black boxes. |
| **Price Target Framework** | The engine synthesizes multiple valuation methods into a single Margin Invest Value, then applies a dynamic margin of safety to produce a buy price and a sell price. You always know where the current price sits relative to the engine's assessment. |
| **Position Sizing** | Suggested allocation percentages are tied directly to conviction strength and opportunity type. Higher conviction and stronger factor alignment earn a larger suggested position. The engine does the sizing math so you don't have to. |

**Visual: Margin of Safety Band Chart** — Horizontal price band with zones:

- Green zone: "Discount" ($120)
- Accent zone: "Buy Below" ($145)
- Neutral zone: "Fair Value" / Margin Invest Value ($175)
- Red zone: "Overvalued" ($210)
- Current price marker at $138

**Caption:** "When the current price falls below the buy price, the signal is Buy. Between buy and sell, it's Hold. Above the sell target, it's Sell. The margin of safety widens or tightens based on how much the valuation methods agree."

**Implementation:** CSS flex-based horizontal band chart (refine the existing `MarginOfSafetyChart` component).

---

## Section 8 — How to Use the Output

**Eyebrow:** Responsible Usage

**H2:** "What to do — and not do — with these candidates."

**Copy:** "Margin Invest surfaces candidates and quantifies conviction. It does not make decisions for you. Here's how to get the most value from the output."

**Do list (checkmarks):**
- Use candidates as a starting point for your own research
- Review the factor breakdown to understand *why* a stock scores well
- Compare the engine's price target to your own valuation work
- Use position sizing as a framework, then adjust for your risk tolerance
- Monitor conviction changes over time — a rising score often confirms an improving fundamental picture

**Don't list (x-marks):**
- Don't treat a high conviction score as a buy recommendation
- Don't skip your own due diligence because the engine did quantitative work
- Don't ignore the limitations section below
- Don't assume past scoring accuracy predicts future results

**Closing line:** "The engine replaces the tedious parts of investment analysis — data gathering, normalization, cross-factor comparison, and ranking. The judgment call on whether to act is always yours."

---

## Section 9 — Transparency & Limitations

**Eyebrow:** Transparency

**H2:** "What this is — and what it isn't."

**Three principle cards (md:grid-cols-3):**

| Card | Content |
|---|---|
| **Not financial advice** | Margin Invest is an analytical tool for informational and educational purposes. Conviction scores, price targets, and position sizing suggestions are model outputs — not recommendations to buy, sell, or hold any security. You make the decisions. |
| **Models have limits** | The engine relies on publicly available financial data. Data can be delayed, restated, or incomplete. Quantitative models cannot capture qualitative factors like management quality, regulatory changes, or geopolitical risk. Edge cases exist in every model. |
| **Structure, not prediction** | The engine identifies where quality, value, and momentum signals align. It does not predict future prices. A high conviction score means strong current factor alignment — not a guarantee that the stock will outperform. |

**Validation checklist:**

**H3:** "Before acting on any candidate, verify:"
- Does the thesis make sense to you independent of the score?
- Have you checked for recent news the model can't capture (M&A, litigation, regulatory)?
- Is the position size appropriate for your portfolio and risk tolerance?
- Do you have an exit plan — not just an entry plan?
- Are you comfortable holding through a drawdown if the fundamentals haven't changed?

---

## Section 10 — Why Margin Invest

**Eyebrow:** Why Pay

**H2:** "Replace hours of screening with a system that runs every day."

**ROI framing (two-column layout):**

| Without a system | With Margin Invest |
|---|---|
| Hours spent gathering data from multiple sources | Full universe scored daily — candidates surface automatically |
| Ad-hoc screening with different criteria each time | Same factors, same weights, same process every cycle |
| No consistent framework for comparing candidates | Transparent breakdown so you know exactly why |
| Position sizes based on gut feel | Position sizing calibrated to conviction strength |
| No systematic monitoring for changes | Score changes flag when something needs your attention |

**Pricing tiers (real product features):**

### Analyst (Free)
- 3 analyses per month
- Composite conviction score
- Top-level pillar breakdown
- 5-ticker watchlist

### Portfolio ($29/mo) — Most Popular
- Unlimited analysis
- Full factor breakdown (all 20+ sub-factors)
- 90-day score history
- 25-ticker watchlist
- Conviction alerts when scores change

### Institutional ($79/mo)
- Everything in Portfolio
- Unlimited history
- Correlation analysis
- Sector rotation tools
- API access

**Social proof placeholder:**
"Used by self-directed investors managing $50K–$5M portfolios."
*(Replace with real testimonials when available.)*

**CTA variants:**
1. **"Score your first stock free"** → `/onboarding` (recommended)
2. **"See your dashboard"** → `/dashboard`
3. **"Run any ticker through the engine"** → `/onboarding`

---

## Visual Package Summary

| # | Visual | Type | Section | Implementation |
|---|---|---|---|---|
| 1 | Pipeline Diagram | 6-stage flow with metrics | Pipeline Overview | Hand-built SVG + Tailwind CSS |
| 2 | Filter Funnel | Narrowing bar (7,000 → 4,200) | Elimination Filters | Hand-built SVG |
| 3 | Score Breakdown Bars | Horizontal percentile bars | Scoring Engine | CSS width + Tailwind |
| 4 | Candidate Journey Chart | Line chart, score over 6 months | Dual-Track Conviction | Recharts LineChart |
| 5 | Margin of Safety Band | Horizontal price zone bar | What You Get | CSS flex (refine existing) |

---

## Developer Implementation Notes

### File structure
Replace existing methodology components. New structure:
```
web/src/components/methodology/
  sections/
    hero-section.tsx
    pipeline-section.tsx
    universe-section.tsx
    filters-section.tsx
    scoring-section.tsx
    conviction-section.tsx
    outputs-section.tsx
    usage-section.tsx
    transparency-section.tsx
    cta-section.tsx
  visuals/
    pipeline-diagram.tsx
    filter-funnel.tsx
    score-breakdown-bars.tsx
    candidate-journey-chart.tsx
    margin-of-safety-band.tsx
  index.ts
```

### Dependencies
- Add `recharts` for the Candidate Journey Chart (Section 6 visual)
- All other visuals are hand-built SVG + Tailwind CSS

### Responsive considerations
- Pipeline diagram: horizontal on md+, vertical stack on mobile
- Filter funnel: horizontal on md+, vertical on mobile
- All grids: md:grid-cols-2 or md:grid-cols-3 → grid-cols-1 on mobile
- Margin of Safety Band: full-width on all breakpoints, labels stack on mobile
- Candidate Journey Chart: ResponsiveContainer from Recharts handles resize

### Animation
- Continue using framer-motion `whileInView` entrance animations
- Stagger child elements within grid sections (0.08s delay)
- Pipeline diagram stages animate in sequence (0.1s delay per stage)

### Design tokens
- Continue using existing dark-theme tokens: bg-bg-primary, bg-bg-elevated, text-text-primary/secondary/tertiary, border-border-primary/subtle, text-accent
- Pillar accent colors: Quality = accent, Value = bullish, Momentum = warning (match existing PercentileBar colors)

### Layout constraints
- Max width: 1280px
- Horizontal padding: 8vw
- Section padding: 96px top/bottom (64px on mobile)
- Consistent with existing methodology page layout
