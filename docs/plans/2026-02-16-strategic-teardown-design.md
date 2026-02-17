# Margin Invest Strategic Teardown

**Date:** 2026-02-16
**Status:** Approved

## Overview

Full strategic evaluation of Margin Invest covering product experience, category positioning, conversion strategy, pricing, and long-term authority building. Goal: transform from "another stock screener" into "conviction infrastructure for serious investors."

## Overall Grade: B-

The engine is genuinely differentiated. The scoring methodology is rigorous, deterministic, and philosophically coherent. But the product wrapping — how it's presented, sold, and experienced — hasn't caught up to the engine's ambition.

---

## Part 1: Product Experience

### What Works
- Deterministic 6-factor scoring engine (quality, value, momentum, growth, sentiment, stability)
- Elimination-before-scoring pipeline (fail-fast architecture)
- Sector-neutral normalization (rank within GICS sector first)
- Growth stage factor weight adjustments
- Clean monorepo architecture (engine/api/web)

### What Doesn't
- Architecture IS the product story, but it's invisible to users
- No activation loop in first 60 seconds
- Dashboard shows scores but doesn't teach the framework
- No "aha moment" designed into the experience

---

## Part 2: Category & Positioning

### New Category: Conviction Infrastructure

Margin Invest is not a screener, not a robo-advisor, not a research terminal. It's **conviction infrastructure** — systematic scoring that tells you whether a position deserves your capital.

### Positioning Statement

> Margin Invest is conviction infrastructure for investors who want to hold with structure instead of hope. A deterministic scoring engine evaluates every stock across 6 quantitative factors — quality, value, momentum, growth, sentiment, and stability — producing a single conviction score that tells you whether a position deserves your capital.

### Target User

Serious retail investor managing $100K-$2M. Self-directed but wants systematic rigor. Tired of reacting emotionally. Values process over predictions.

---

## Part 3: Conversion & Desire

### Homepage Reorder
1. Hero: Define the category immediately ("Conviction scoring for serious investors")
2. Engine pipeline visualization: Show a real ticker flowing through 4 stages (data → filter → score → rank)
3. Friction section (constellation narrative): "Most investors react. Few operate with structure."
4. Proof section: Backtests, performance transparency
5. Pricing: Clear tiers with activation hooks
6. CTA: "Score your first position free"

### Proof Strategy
- Publish quarterly backtests (High Conviction vs. S&P 500)
- Be transparent about underperformance periods
- Credibility compounds; cherry-picking destroys it

### Activation Loop
- Free tier must demonstrate value in <60 seconds
- Show composite score + conviction level immediately
- Create urgency: "You've scored 3 tickers. Your portfolio has 12 more."

---

## Part 4: Pricing & Monetization

### Strategy: Penetration Pricing with Premium Positioning

Price competitively to build a user base. Raise prices only after the product has earned the right.

### Competitive Context
- Simply Wall St: ~$10-20/mo
- Koyfin: ~$35-65/mo
- Seeking Alpha Premium: ~$20/mo
- Morningstar Premium: ~$35/mo

### Tiers

| | Scout (Free) | Operator ($29/mo annual, $39/mo monthly) | Allocator ($79/mo annual, $99/mo monthly) |
|---|---|---|---|
| Ticker analysis | 3/month | Unlimited | Unlimited |
| Composite score + conviction | Yes | Yes | Yes |
| Factor breakdown | Top-level only | Full detail | Full detail |
| Historical scores | None | 90 days | Unlimited |
| Watchlist | 5 tickers | 25 tickers | Unlimited |
| Portfolio-level analysis | No | No | Yes |
| Conviction change alerts | No | Email | Email + push |
| API access | No | No | Yes |
| Sector rotation signals | No | No | Yes |

### Conversion Hooks
- **Free → Operator:** "You've used all 3 lookups this month. Your portfolio has 12 more holdings."
- **Operator → Allocator:** "3 of your watchlist tickers had conviction changes. See portfolio impact."

### Growth Pricing Path
- Months 0-6: These prices, focus on adoption
- Month 6-12: Evaluate usage data, adjust if warranted
- Year 2+: Introduce team/advisor tier ($149-199/mo) after product-market fit

---

## Part 5: Long-Term Authority Strategy

### Year 1: Establish the Framework
- **Conviction Dispatch** — monthly analysis of 3-5 tickers through the engine's lens (not stock picks, framework application)
- Quarterly backtests with honest performance transparency
- SEO: own "conviction scoring" (nobody else is using it)

### Year 2: Build the Community
- Forum/Discord for Operators (framework discussions, not stock tips)
- Guest analysis from credible finance voices
- Conference presence (QuantCon, etc.)

### Year 3-5: Platform Gravity
- API ecosystem (RIA integrations, compliance audit trails)
- Research partnerships (behavioral finance academics)
- Data moat (3+ years of historical conviction scores = unique dataset)

### Authority Metrics

| Metric | Year 1 Target | Year 3 Target |
|---|---|---|
| "Conviction scoring" Google rank | Top 5 | #1 |
| Monthly Dispatch subscribers | 500 | 5,000 |
| Backtest reports published | 4 | 12+ |
| External mentions/citations | 10 | 100+ |
| API integrations | 0 | 20+ |

---

## 5 Biggest Weaknesses

1. **Category confusion** — reads as "another stock screener" despite being fundamentally different
2. **Empty proof** — zero social proof, no backtests, no public track record
3. **Homepage buries the lead** — engine pipeline and 6-factor breakdown below the fold
4. **No activation loop** — free tier doesn't create urgency to upgrade
5. **Invisible differentiation** — determinism, elimination pipeline, sector-neutral approach are hidden

## 5 Highest-Leverage Changes

1. **Rewrite hero to define the category** — "Conviction scoring for serious investors. A deterministic engine that scores every stock across 6 factors — so you hold with structure, not hope."
2. **Build and publish one backtest** — High Conviction vs. Low Conviction positions over 2 years
3. **Redesign free tier as a hook** — 3 tickers/month with full composite score visibility
4. **Make engine pipeline visible** — 4-stage pipeline as first-class homepage visual with real ticker flowing through it
5. **Launch Conviction Dispatch** — monthly framework-application content, builds authority + SEO

## 12-Month Authority-Building Roadmap

| Month | Action | Goal |
|---|---|---|
| 1 | Publish first backtest (2-year lookback) | Proof of concept |
| 2 | Launch Conviction Dispatch #1 | Content engine starts |
| 3 | SEO landing pages for "conviction scoring" | Own the category term |
| 4 | Publish second backtest (sector-specific) | Deepen credibility |
| 5 | Guest post on finance blog/Substack | External validation |
| 6 | Launch revised pricing tiers | Conversion optimization |
| 7 | Quarterly performance transparency report | Trust compounding |
| 8 | Dispatch reaches 200+ subscribers | Distribution growing |
| 9 | First API beta for RIA integration | Platform expansion signal |
| 10 | Third backtest + year-end review | Annual credibility anchor |
| 11 | Conference talk submission (QuantCon/similar) | Category authority |
| 12 | "State of Conviction" annual report | Signature content piece |
