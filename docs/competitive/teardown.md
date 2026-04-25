# Competitive Teardown: Margin Invest vs. 6 Competitors

> **Limitations Note:** This teardown is based on publicly available information (pricing pages, free tiers, documentation). Several competitors (Stockopedia, Finviz Elite) gate features behind login/paywall. Coverage is partial but sufficient for positioning decisions.

---

## Feature Matrix

| Feature | Stockopedia | Finviz Elite | GuruFocus | Koyfin | Simply Wall St | TIKR |
|---|---|---|---|---|---|---|
| **Multi-factor scoring / stock ranking** | Present (StockRank: Quality, Value, Momentum composite; 20+ year backtest) | Partial (signal-based, no unified composite score) | Present (GF Score, GF Value Line, proprietary valuation ranks) | Absent (data terminal, no scoring) | Present (Snowflake 5-factor visual score) | Absent (data only, no scoring) |
| **Screening / filtering** | Present (200+ metrics) | Present (real-time screener, 70+ filters, visual maps) | Present (deep fundamental screener, All-in-One Screener) | Present (advanced screener with 100+ metrics) | Partial (basic screener, limited filter depth) | Present (screener with financial statement filters) |
| **13F / institutional holdings tracking** | Absent | Partial (insider trading data, no 13F depth) | Present (Guru portfolios: Buffett, Ackman, etc.; quarter-over-quarter tracking) | Partial (ownership data visible but not a primary workflow) | Absent | Present (institutional holdings pages per stock) |
| **Risk factor analysis (10-K text analysis)** | Absent | Absent | Absent | Absent | Absent | Absent |
| **Backtesting** | Present (StockRank backtests published, user-accessible strategy backtests) | Absent | Present (All-in-One Screener backtesting) | Absent | Absent | Absent |
| **API access** | Absent (no public API) | Absent (no public API) | Present (GuruFocus API, paid add-on) | Absent (no public API) | Absent (no public API) | Absent (no public API) |
| **Alerts / watchlists** | Present (portfolio tracking, email alerts) | Present (real-time alerts on Elite plan) | Present (watchlists, email alerts on value changes) | Present (watchlists, dashboards, alerts) | Present (watchlists, email notifications) | Present (watchlists, alerts) |
| **Portfolio tools / position sizing** | Present (portfolio tracker, allocation view) | Absent | Present (portfolio tracking, no sizing logic) | Present (portfolio analytics, allocation) | Present (portfolio tracker, diversification view) | Present (portfolio tracker) |
| **Deterministic/reproducible scoring** | Absent (scores update with market data; no reproducibility guarantee) | N/A (no scoring system) | Absent (models updated continuously) | N/A (no scoring system) | Absent (Snowflake updates dynamically) | N/A (no scoring system) |
| **Governance / audit trail** | Absent | Absent | Absent | Absent | Absent | Absent |
| **Tamper-evident track record** | Absent | Absent | Absent | Absent | Absent | Absent |

---

## Pricing

| Competitor | Free Tier | Paid Plans | Notes |
|---|---|---|---|
| **Stockopedia** | No (14-day free trial) | ~$40/mo (single market), ~$55/mo (multi-market) [verify] | UK-based, prices in GBP; annual discounts available |
| **Finviz Elite** | Yes (delayed data, limited features) | $39.50/mo (Elite, real-time) or $299.50/yr [verify] | Free tier is ad-supported; Elite removes ads, adds real-time |
| **GuruFocus** | Yes (limited data, 5-year financials) | Premium $34.92/mo, Premium Plus ~$41.58/mo (annual pricing) [verify] | API add-on costs extra; Premium Plus unlocks backtesting, 30-year data |
| **Koyfin** | Yes (limited dashboards) | Plus $35/mo, Pro $59/mo, Pro+ $99/mo [verify] | Free tier covers basic charting; Pro+ for full data depth |
| **Simply Wall St** | Yes (limited analyses) | ~$10/mo (annual) or ~$20/mo (monthly) [verify] | Cheapest paid option in the set; individual investor focus |
| **TIKR** | Yes (limited tickers) | Plus $15.83/mo, Pro $24.99/mo (annual pricing) [verify] | Positioned as "the free Bloomberg terminal"; good value |

**Margin Invest pricing for reference:** Scout (free), Analyst ($19/mo), Portfolio ($49/mo).

---

## Hardest-to-Replicate Feature Per Competitor

### Stockopedia: StockRank with 20+ Years of Backtested Track Record

StockRank combines Quality, Value, and Momentum into a single composite score, backtested across global markets since ~2000. The difficulty is not the formula (factor composites are well-documented in academic literature) but the 20+ years of validated historical performance data. Margin Invest would need to either (a) run its scoring engine against point-in-time data going back two decades, or (b) wait 20 years. Option (a) requires clean survivorship-bias-free data for every market Stockopedia covers, which is expensive and time-consuming to assemble but not impossible given the existing PIT pipeline. The real moat is credibility: Stockopedia can say "this worked for 20 years" with published evidence. Margin Invest cannot yet.

### Finviz Elite: Real-Time Screener with Market Visualizations

Finviz's heat maps, bubble charts, and real-time scanning are immediate-gratification tools that serve day traders and active screeners. Replicating the visualization layer is an engineering task (substantial but bounded). The harder part is real-time market data: Finviz has direct exchange data feeds, and licensing real-time data from NYSE/Nasdaq costs $5,000-50,000+/year depending on redistribution terms and subscriber count. Margin Invest's architecture (batch-oriented daily scoring) is fundamentally different from a real-time scanning tool, so this would be a product direction change, not just a feature add.

### GuruFocus: Depth of Valuation Models

GuruFocus offers DCF (multiple variants), GF Value Line (their proprietary "fair value" estimate), Peter Lynch value, Ben Graham Number, Earnings Power Value, and several more. Each model draws on 30 years of historical financial data. Building one DCF model is straightforward. Building eight valuation models with 30 years of clean input data, plus the editorial/research layer that explains methodology, is a multi-quarter effort. The data licensing (30-year fundamentals, international coverage) represents the primary cost barrier; S&P Capital IQ or Refinitiv data feeds run $50,000-200,000+/year at institutional scale.

### Koyfin: Institutional-Grade Data Terminal Coverage

Koyfin covers equities, fixed income, macro economics, ETFs, and mutual funds across global markets with Bloomberg-like dashboards. The breadth is the moat: tens of thousands of data points across asset classes, sourced from multiple data vendors (likely including S&P, LSEG, and others). Margin Invest covers US equities only. Expanding to fixed income or global macro would require new data vendor contracts, new data models, and new domain expertise. This is a years-long, capital-intensive effort that fundamentally changes the product scope.

### Simply Wall St: Snowflake Infographics

The Snowflake is a five-axis radar chart (Value, Future, Past, Health, Dividend) that makes complex financial analysis instantly legible to retail investors. The visualization itself is simple to build. The difficulty is the design system and brand identity it represents: Simply Wall St has built their entire product experience around visual, non-technical storytelling. Every data point connects to a narrative explanation written for non-experts. Replicating this would require Margin Invest to maintain two UX paradigms simultaneously: the technical, deterministic scoring interface for sophisticated users, and a simplified visual layer for retail. The engineering cost is moderate, but the editorial and UX design cost is high, and it risks diluting the product positioning.

### TIKR: 10-Year Financials with International Coverage (30,000+ Stocks)

TIKR provides standardized 10-year financial statements for equities across 30+ countries. The data depth per stock (quarterly and annual income statement, balance sheet, cash flow, per-share metrics) combined with international breadth creates a coverage moat. The raw data likely comes from S&P Global Market Intelligence or a similar provider. Margin Invest's EDGAR pipeline covers US-listed SEC filers. Extending to international markets means parsing non-XBRL filings, handling different accounting standards (IFRS vs. GAAP), and licensing data from providers that aggregate international filings. Cost and complexity scale roughly linearly with number of markets covered.

---

## Honest Wedge Assessment

Margin Invest does three things that none of the six competitors do, and it does them in combination. First, its scoring is deterministic: the same inputs produce the same outputs, with no opaque model updates or silent recalibrations. Stockopedia, GuruFocus, and Simply Wall St all offer scoring, but none guarantee reproducibility or publish the conditions under which a score was computed. Second, Margin Invest runs a governance pipeline (staged, approved, published) with human oversight checkpoints, circuit breakers, and audit logs before any score reaches users. No competitor has anything resembling this; they publish scores as soon as they are computed. Third, Margin Invest archives daily picks with a SHA-256 hash chain, creating a tamper-evident historical record that cannot be retroactively edited. No competitor offers a cryptographically verifiable track record.

The open question is whether buyers care. The target buyer who values provable, unmanipulable scoring with an auditable pipeline is likely an institutional allocator, a compliance-sensitive RIA, or a sophisticated individual investor who has been burned by opaque quant products. This is a narrower market than the retail screener audience served by Simply Wall St or TIKR. The risk factor diffing (AI-based 10-K text analysis) is a genuine capability gap that no competitor fills, but it is currently a standalone overlay, not integrated into scoring, which limits its practical value until the eval harness validates precision. The elimination-first methodology (filters before scoring) is a design choice that improves signal quality but is not visible to users as a feature. The wedge is real but narrow: it matters most to buyers who have specific reasons to distrust black-box scoring systems.
