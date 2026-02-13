# Margin Invest v1 — Design Document

**Date**: 2026-02-12
**Version**: 1.0
**Status**: Approved

## Vision

Margin Invest finds once-in-a-generation, high-conviction investment bets. It eliminates human bias entirely — no vibes, no narratives, no feelings. The system is deterministic: same inputs produce the same outputs, every time. It evaluates every US-listed equity through a ruthless multi-stage funnel of elimination filters, quantitative scoring, qualitative analysis, and backtesting validation. Only the top ~10-30 stocks at any given time surface as recommendations.

## Decisions

| Decision | Choice |
|----------|--------|
| Architecture | Monorepo with decoupled engine (engine / api / web) |
| Frontend | Next.js 15 (React, App Router) |
| Backend | Python FastAPI (async) |
| Database | PostgreSQL + TimescaleDB |
| Task Queue | ARQ (async Redis queue) |
| Hosting | Vercel (frontend) + Railway (backend, DB, Redis) |
| Auth | OAuth via Google, Microsoft, Facebook, GitHub (NextAuth.js v5) |
| Package Manager | uv (Python), npm (Node) |
| Design | Dark, bold, confident — deep navy/charcoal + gold/amber accents |
| Asset Scope (v1) | US equities only (financials and REITs excluded) |
| CLI | Shared engine enables CLI as bonus; web-app is primary |

---

## 1. Project Structure

```
margin_invest/
├── engine/                     # Pure Python analysis library
│   ├── pyproject.toml          # Standalone package: "margin-engine"
│   ├── src/margin_engine/
│   │   ├── ingestion/          # Data fetching from APIs
│   │   │   ├── providers/      # One module per API (yahoo, polygon, fred, etc.)
│   │   │   ├── registry.py     # Provider registry + fallback chains
│   │   │   ├── rate_limiter.py # Per-provider rate limiting
│   │   │   ├── normalizer.py   # Normalize to common schema
│   │   │   └── scheduler.py    # Ingestion job orchestration
│   │   ├── scoring/            # Analysis & scoring methods
│   │   │   ├── filters/        # Stage 1: elimination filters
│   │   │   ├── quantitative/   # Stage 2: quality, value, momentum factors
│   │   │   ├── qualitative/    # AI-powered moat, sentiment analysis
│   │   │   ├── composite.py    # Combines factor scores into conviction score
│   │   │   ├── classifier.py   # Sector/growth-stage classification
│   │   │   └── normalizer.py   # Cycle normalization, sector adjustment
│   │   ├── backtesting/        # Historical performance validation
│   │   ├── models/             # Pydantic data models
│   │   └── secrets.py          # API key management interface
│   └── tests/                  # Full test suite
│
├── api/                        # FastAPI service
│   ├── pyproject.toml          # Depends on margin-engine
│   ├── src/margin_api/
│   │   ├── routes/             # API endpoints
│   │   ├── auth/               # OAuth JWT handling
│   │   ├── ws/                 # WebSocket for live updates
│   │   ├── tasks/              # Background job management (ARQ)
│   │   └── db/                 # SQLAlchemy models, Alembic migrations
│   └── tests/
│
├── web/                        # Next.js frontend
│   ├── package.json
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   ├── components/         # React components
│   │   ├── lib/                # API client, utilities
│   │   └── styles/             # Tailwind + custom theme
│   └── tests/                  # Vitest + Playwright
│
├── docker-compose.yml          # Local dev: Postgres/TimescaleDB, Redis
├── pyproject.toml              # Workspace root (uv workspaces)
└── CLAUDE.md
```

Key structural decisions:
- **uv workspaces** manage the Python monorepo
- **engine** has zero web dependencies — pure data science
- **api** depends on engine as a local path dependency
- **Secrets**: python-keyring for local dev, environment variables for production

---

## 2. Visual Design

### Color System

| Token | Hex | Usage |
|-------|-----|-------|
| Primary Background | `#0A0F1C` | Main dark background |
| Secondary Background | `#141B2D` | Cards, elevated surfaces |
| Accent Gold | `#D4A843` | Conviction scores, CTAs, highlights |
| Accent Gold Hover | `#E8C468` | Interactive gold states |
| Success/Bullish | `#2D8B5E` | Positive price changes, passing filters |
| Danger/Bearish | `#C74B50` | Negative changes, failing filters, sell signals |
| Text Primary | `#E8E4DD` | Body text (warm off-white) |
| Text Secondary | `#8B95A8` | Labels, metadata |
| Borders | `#1E2740` | Dividers, card borders |

### Typography

- Headlines: Bold sans-serif (Inter or Geist) — large, confident
- Body: Clean sans-serif (Inter)
- Data/Numbers: Monospace (Geist Mono or JetBrains Mono)

### Design Language

- Ventriloc's single-column narrative flow for landing page
- Vizcom's dark sophistication with grain texture overlay
- Ciridae's typographic precision and whitespace
- Scroll-triggered reveal animations (Framer Motion)
- Dark mode only for v1
- Desktop-first, fully responsive to mobile

---

## 3. Pages

| Page | Route | Purpose |
|------|-------|---------|
| Landing | `/` | Narrative scroll: hero, how it works, performance, CTA |
| Login | `/login` | OAuth provider buttons |
| Dashboard | `/dashboard` | Grid of high-conviction picks + watchlist |
| Asset Detail | Inline on dashboard | Expandable full analysis (click card to expand) |
| Backtesting | `/backtesting` | System performance vs S&P 500, metrics, charts |
| Settings | `/settings` | Account, API keys, notification preferences |

---

## 4. Scoring Engine — Complete Specification

### Philosophy

Quality companies, bought cheap, with momentum confirmation. Deterministic. No human judgment at any step.

### STAGE 1: Elimination Filters (Binary Pass/Fail)

Any single fail = eliminated from scoring.

#### Filter 1: Beneish M-Score (Earnings Manipulation)

Formula: `M = -4.84 + 0.920(DSRI) + 0.528(GMI) + 0.404(AQI) + 0.892(SGI) + 0.115(DEPI) - 0.172(SGAI) + 4.679(TATA) - 0.327(LVGI)`

| Variable | Formula | Detects |
|----------|---------|---------|
| DSRI | (Receivables_t/Revenue_t) / (Receivables_t-1/Revenue_t-1) | Revenue inflation |
| GMI | Gross_Margin_t-1 / Gross_Margin_t | Margin deterioration |
| AQI | [1-(PP&E_t+CA_t)/TA_t] / [1-(PP&E_t-1+CA_t-1)/TA_t-1] | Capitalizing expenses |
| SGI | Revenue_t / Revenue_t-1 | High-growth manipulation risk |
| DEPI | DepRate_t-1 / DepRate_t | Slowed depreciation |
| SGAI | (SGA_t/Revenue_t) / (SGA_t-1/Revenue_t-1) | Cost deterioration |
| TATA | (Income_Continuing_Ops - CFO) / Total_Assets | Accrual vs cash gap |
| LVGI | [(CL_t+LTD_t)/TA_t] / [(CL_t-1+LTD_t-1)/TA_t-1] | Increasing leverage |

**Threshold**: M > -1.78 = FAIL.

#### Filter 2: Financial Distress (Composite)

All four must pass:
1. Altman Z'' (non-manufacturing): `Z'' = 6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)`. Z'' < 1.1 = FAIL. (Not applied to utilities.)
2. Negative FCF for 3+ consecutive quarters = FAIL.
3. Interest Coverage (EBIT/Interest Expense) < threshold = FAIL. (Sector-adjusted: Tech >3.0, Default >1.5, Utilities >1.2.)
4. Current Ratio < threshold = FAIL. (Sector-adjusted: Tech >0.8, Default >0.8, Utilities >0.6. Note: Tech threshold calibrated from >1.0 to >0.8 to avoid excluding fundamentally strong mega-caps with aggressive buyback programs.)

#### Filter 3: Minimum Liquidity & Coverage

- Market cap < $300M = FAIL (utilities: $1B, energy: $500M)
- Average daily dollar volume < $1M = FAIL
- Less than 5 years of financial history = FAIL
- Financial sector (banks, insurance, REITs) = EXCLUDED in v1

### STAGE 2: Quantitative Scoring (Percentile Rank 0-100)

Three factor dimensions. Each sub-component percentile-ranked against all surviving stocks. Sector-neutral scoring applied within GICS sectors first.

#### Factor 1: QUALITY (Weight: 35%)

Equal-weighted sub-components:

**a) Gross Profitability (Novy-Marx)**
- `(Revenue - COGS) / Total Assets`
- Gross profit is harder to manipulate than net income.

**b) ROIC — WACC Spread (Mauboussin)**
- ROIC = `NOPAT / Invested Capital`
- NOPAT = `EBIT * (1 - Effective Tax Rate)`
- Invested Capital = `Total Equity + Total Debt - Excess Cash`
- WACC via CAPM: `Risk-Free Rate + Beta * Equity Risk Premium`
- Score the spread (ROIC - WACC), not raw ROIC.

Sector-specific ROIC expectations:

| Sector | Typical WACC | Moat-Level ROIC (sustained 5yr) |
|--------|-------------|--------------------------------|
| Technology | 9-12% | >30% |
| Healthcare | 8-11% | >25% |
| Consumer Staples | 7-9% | >20% |
| Consumer Discretionary | 8-11% | >22% |
| Industrials | 8-10% | >18% |
| Energy | 9-12% | >20% |
| Utilities | 5-7% | >10% |
| Materials | 8-10% | >17% |
| Communication Services | 8-10% | >20% |

**c) Earnings Quality — Sloan Accrual Ratio**
- `(Net Income - CFO) / Total Assets`
- Lower accruals = higher quality. Inverted percentile rank.

**d) Piotroski F-Score (0-9)**

| # | Signal | Score 1 if |
|---|--------|-----------|
| 1 | ROA | Net Income / Total Assets > 0 |
| 2 | Operating Cash Flow | CFO > 0 |
| 3 | ROA Change | ROA_t > ROA_t-1 |
| 4 | Accruals | CFO > Net Income |
| 5 | Leverage Change | LT Debt/TA decreased YoY |
| 6 | Liquidity | Current Ratio increased YoY |
| 7 | Dilution | Shares outstanding_t <= shares_t-1 |
| 8 | Gross Margin Change | Gross Margin improved YoY |
| 9 | Asset Turnover Change | Revenue/Assets improved YoY |

#### Factor 2: VALUE (Weight: 30%)

**a) EV/FCF (Enterprise Value / Free Cash Flow)**
- EV = Market Cap + Total Debt - Cash
- FCF = CFO - CapEx
- Lower = cheaper. Inverted percentile rank. Negative FCF stocks excluded from this sub-rank.

**b) Shareholder Yield (Mebane Faber)**
- `(Dividends Paid + Net Buybacks) / Market Cap`
- Net Buybacks from shares outstanding change or cash flow statement repurchase line.
- Higher = better.

**c) DCF Margin of Safety (Klarman/Buffett)**
- Two-stage model: 10-year projected FCF growth + terminal value at GDP growth (2-3%).
- Discount rate: WACC (CAPM). Risk-free rate from FRED 10-year Treasury.
- Growth rate: min(analyst consensus, 5-year historical FCF CAGR, sustainable growth rate).
- Margin of Safety = `(Intrinsic Value - Price) / Intrinsic Value`
- Higher margin = more undervalued.

**d) Acquirer's Multiple (Tobias Carlisle)**
- `Enterprise Value / EBIT`
- Lower = cheaper. Inverted percentile rank.

#### Factor 3: MOMENTUM + CATALYST (Weight: 35%)

**a) Price Momentum (12-1 month)**
- `(Price_current / Price_12mo_ago) - 1`, excluding most recent month.
- Per Jegadeesh & Titman: last month shows mean reversion.

**b) Earnings Momentum — SUE**
- `(Actual EPS - Expected EPS) / StdDev of past surprises`
- Last 4 quarters. Consistent positive surprises = high score.

**c) Insider Cluster Buying**
- 3+ distinct insiders buying within 90 days = cluster buy.
- Purchases > $100K or > 10% of compensation. CEO/CFO weighted 2x vs directors.
- Selling ignored (asymmetric signal).
- Data: SEC EDGAR Form 4, Finnhub.

**d) Institutional Accumulation (Smart Money)**
- Track 13F filings from curated top-fund list: Berkshire Hathaway, Baupost, Appaloosa, Greenlight, Pershing Square, Scion, Pabrai Funds, Himalaya Capital, TCI Fund, Lone Pine.
- New positions > additions. Weight by fund track record.
- Account for 45-day filing lag.

**e) Sentiment & Event Analysis (AI-Powered)**
- LLM analysis of news (30 days), earnings call transcripts, analyst reports.
- Structured prompt, temperature = 0. Fixed numerical scale (-5 to +5).
- Contrarian bonus: extremely negative sentiment + strong fundamentals = buy signal.
- Weight: earnings calls > analyst reports > news.

### Composite Score

`Composite = (Quality Rank * 0.35) + (Value Rank * 0.30) + (Momentum Rank * 0.35)`

Percentile rank 0-100. Sector-neutral: rank within GICS sector first, then combine.

### STAGE 3: Backtesting Validation Gate

Stocks in top 5% get profile-backtested. Historical stocks with similar factor profiles must show:

| Metric | Threshold |
|--------|-----------|
| Excess Return (annualized) | > 3% vs S&P 500 over 5 years |
| Sharpe Ratio | > 0.7 |
| Max Drawdown | < 35% |
| Win Rate | > 55% of similar profiles beat S&P |
| Information Ratio | > 0.5 |

### STAGE 4: Final Classification

| Percentile | Label | Expected Count |
|-----------|-------|---------------|
| Top 1% (99-100) | Exceptional Conviction | 5-10 stocks |
| Top 5% (95-98) | High Conviction | 15-25 stocks |
| Top 10% (90-94) | Watchlist | 30-50 stocks |
| Below 90 | Not shown | Everything else |

### Buy/Hold/Sell Signals (Deterministic)

| Condition | Signal |
|-----------|--------|
| Enters top 5% | BUY |
| Remains in top 5% | HOLD |
| Score declining, still top 10% | WATCH |
| Drops below 85th percentile | SELL |
| Fails elimination filter after previously passing | URGENT SELL |

No price targets. The system evaluates when the thesis is intact or broken.

---

## 5. Asset Classification System

### Axis 1: GICS Sector

Automatic from data provider. 11 sectors. Financials and REITs excluded in v1.

### Axis 2: Growth Stage (Algorithmic)

| Stage | Rule |
|-------|------|
| High Growth | Revenue CAGR (3yr) > 20% AND Gross Margin > 40% AND Market Cap > $2B |
| Steady Growth | Revenue CAGR (3yr) 5-20% AND Positive FCF |
| Mature/Cash Cow | Revenue CAGR (3yr) < 5% AND FCF Yield > 4% |
| Cyclical | Revenue StdDev (5yr) > 15% OR cyclical sector |
| Turnaround | Negative NI 2 of 4 quarters BUT sequential margin improvement 2+ quarters AND positive CFO most recent quarter |

### Growth Stage Scoring Weight Adjustments

| Stage | Quality | Value | Momentum |
|-------|---------|-------|----------|
| High Growth | 40% | 25% | 35% |
| Steady Growth | 35% | 30% | 35% |
| Mature/Cash Cow | 30% | 40% | 30% |
| Cyclical | 35% | 30% | 35% |
| Turnaround | 35% | 30% | 35% (must score top 3% not top 5%) |

### Cycle Normalization (Cyclical Assets)

For cyclical companies, all value ratios use **median** earnings/FCF/revenue over trailing 7 years (full economic cycle), not trailing twelve months.

### Structural Trend Analysis (Data-Driven, Not Vibes)

Measured from public data only. Modifies DCF growth rate assumptions (bounded, +/-2% max):

| Signal | Source | Measurement |
|--------|--------|-------------|
| Industry Revenue Growth | SEC EDGAR aggregate | 3-year CAGR of sub-industry total revenue |
| R&D Investment Intensity | Financial statements | Company R&D/Revenue vs industry median |
| Capital Inflows | 13F aggregate | Net new institutional money into sub-industry |
| Regulatory Impact | AI analysis of Federal Register | Structured prompt, temp=0, -5 to +5 |
| Margin Trends | Financial statements | Industry median gross margin 5-year trend |

NOT considered: media narratives, social media hype, analyst price targets, any non-quantifiable signal.

---

## 6. Data Ingestion

### Provider Strategy

**Free tier ($0/mo — fully functional):**

| Role | Provider |
|------|----------|
| Fundamentals | yfinance → SEC EDGAR XBRL |
| Price history | yfinance |
| Insider transactions | Finnhub (60 req/min) + SEC EDGAR Form 4 |
| Institutional holdings | Finnhub + SEC EDGAR 13F |
| Macro data | FRED (120 req/min) |
| News | Finnhub |
| Earnings estimates | Finnhub |

**Production tier ($43/mo):**
- Add FMP Starter ($14/mo) — pre-computed ratios, DCF endpoint
- Add Polygon Starter ($29/mo) — superior price data

### Dynamic Provider Fallback

Provider registry is key-aware. Checks available API keys and builds fallback chain at runtime:

```
Fundamentals:  FMP → yfinance → SEC EDGAR XBRL
Price:         Polygon → yfinance
Insider:       SEC EDGAR Form 4 → Finnhub
Institutional: SEC EDGAR 13F → Finnhub
Macro:         FRED (no fallback needed)
News:          Finnhub → FMP
```

User-provided keys get highest priority (user's own rate limits). System keys next. Free providers always available.

AI provider fallback: Claude → GPT → Gemini. Temperature = 0 for all. Without an AI key, qualitative scoring is omitted and conviction score is calculated from quantitative factors only.

If >30% of scoring sub-components can't be calculated due to missing data, the stock is excluded from recommendations.

### Ingestion Schedule

| Data | Frequency |
|------|-----------|
| Price (daily OHLCV) | Daily at 4:30 PM ET |
| Fundamentals | Quarterly (on SEC filing) |
| Insider transactions | Daily |
| Institutional (13F) | Quarterly |
| Macro indicators | On release per FRED calendar |
| News | Every 30 min during market hours |
| Earnings estimates | Weekly |
| AI analysis | Event-triggered (new data arrival) |

### Storage (PostgreSQL + TimescaleDB)

**Relational tables**: assets, users, scores, recommendations, api_keys (encrypted)

**TimescaleDB hypertables**: prices, financials (point-in-time, never overwritten), scores_history, insider_transactions, institutional_holdings

Point-in-time storage: financial data stored with filing date. Never updated retroactively. Critical for backtest validity.

---

## 7. Authentication & Security

### OAuth (NextAuth.js v5)

| Provider | Scopes |
|----------|--------|
| Google | openid, email, profile |
| Microsoft | openid, email, profile |
| Facebook | email, public_profile |
| GitHub | read:user, user:email |

Flow: NextAuth.js handles OAuth → JWT issued (httpOnly secure cookie) → FastAPI validates JWT via shared secret → stateless backend.

### API Key Storage

- Encrypted at rest via Fernet symmetric encryption (Python cryptography library)
- Master encryption key from environment variable (never in code or DB)
- Keys decrypted only in-memory for API calls, never logged
- Local dev: python-keyring or .env (gitignored)
- Production: Railway environment variables

---

## 8. Real-Time Event System

### Event Types

| Event | Source | Frequency |
|-------|--------|-----------|
| Earnings release | Finnhub calendar | Daily check |
| SEC filing | EDGAR RSS | Every 15 min |
| Insider transaction | EDGAR RSS + Finnhub | Every 30 min |
| Price alert (>2σ move) | Price data | Every 5 min market hours |
| Analyst rating change | Finnhub | Every 2 hours |
| Macro event | FRED calendar | On release |
| Material news | Finnhub → AI classification | Every 30 min |
| Score change (>5 pts) | Internal | After every re-score |

### Event Pipeline

1. Event detected → relevance filter (only recommended + watchlisted assets)
2. AI impact classification (temp=0): MAJOR / MODERATE / MINOR
3. Re-score trigger: MAJOR = immediate, MODERATE = 1 hour, MINOR = next batch
4. Score delta check: >5 points = notify user via WebSocket + notification feed
5. Recommendation update: asset moves between lists based on new score

### Notification Controls

- Max 1 notification per asset per hour (unless MAJOR)
- MINOR events batched into daily digest
- User-configurable: which event types generate notifications

---

## 9. Backtesting Engine

### System Backtest (Walk-Forward)

Monthly walk-forward simulation from Jan 2015 to present. At each month, use ONLY data available at that time. Run full scoring pipeline. Select top 5%. Track forward returns. Rebalance monthly.

### Anti-Bias Measures

| Bias | Prevention |
|------|-----------|
| Look-ahead | Point-in-time database |
| Survivorship | Include delisted stocks (v1 limitation: incomplete delisted price data) |
| Selection | Test on ALL qualifying US equities |
| Overfitting | Fixed factor weights (35/30/35), not optimized on backtest |
| Transaction costs | 10 bps per trade + 5 bps slippage |

### Pass Thresholds

| Metric | Threshold |
|--------|-----------|
| CAGR excess vs S&P 500 | > 3% annualized |
| Sharpe Ratio | > 0.7 |
| Sortino Ratio | > 1.0 |
| Max Drawdown | < 35% |
| Win Rate | > 55% |
| Information Ratio | > 0.5 |

### Automated Schedule

- Monthly: append new month, compare to prior run
- Quarterly: full re-run from inception, performance report
- On methodology change: new must beat old on ≥3 of 5 core metrics before deploy

---

## 10. Testing Strategy

### Iron Rule

No scoring formula ships without a test verifying it against a hand-calculated expected value.

### Coverage Requirements

| Package | Minimum Coverage |
|---------|-----------------|
| engine/ | 95% |
| api/ | 90% |
| web/ | 80% |

### Test Categories

**engine/**: Golden-value tests (hand-calculated from real 10-K data), parameterized sector/growth-stage tests, composite scoring determinism tests, provider fallback tests, snapshot tests for API normalization.

**api/**: Auth flow tests (mock OAuth), endpoint tests (FastAPI TestClient), background job tests, WebSocket lifecycle tests, DB tests against real PostgreSQL (Docker).

**web/**: Component tests (Vitest + React Testing Library), page tests (MSW mocking), E2E (Playwright: login → dashboard → expand asset → verify data).

### CI Pipeline

```
Every PR:  lint → type check → unit tests → integration tests → coverage gate
Nightly:   live provider tests → full pipeline test → backtest validation
```

### Test Data

- Golden dataset: ~20 real companies with hand-verified scoring (from actual SEC filings)
- Synthetic dataset: 100 stocks with designed edge cases (deterministic from seed)
- Snapshot fixtures: recorded real provider responses

---

## 11. Deterministic Guarantees

| Component | Mechanism |
|-----------|-----------|
| Quantitative metrics | Pure math on financial data |
| DCF growth rate | Algorithmic: min(consensus, CAGR, sustainable), trend-adjusted |
| WACC | CAPM formula, FRED inputs, calculated beta |
| Sector classification | GICS code from data provider |
| Growth stage | Quantitative thresholds only |
| Cycle normalization | Median over fixed window |
| AI analysis | Temperature = 0, structured output schema, cached and versioned |
| Composite score | Weighted sum of percentile ranks |
| Recommendations | Fixed threshold: top 5% = recommend |

### Anti-Bias Safeguards

- No recency bias: factor weights are fixed
- No sector bias: sector-neutral scoring
- No popularity bias: market cap does not affect score
- No narrative bias: AI uses structured prompts with fixed numerical scales
- No survivorship bias: delisted stocks in backtest universe
- No look-ahead bias: point-in-time data only
- No regime prediction: adapts to current conditions, does not forecast

---

## 12. Responsive Design

| Breakpoint | Layout |
|-----------|--------|
| Desktop (>=1200px) | 3-column card grid, full nav |
| Tablet (768-1199px) | 2-column grid, hamburger nav |
| Mobile (<768px) | Single-column stacked, bottom tab nav, slide-up detail sheets |
