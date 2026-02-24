# Backtesting Engine Design

## Strategic Purpose

The backtesting engine exists to answer one question: "Would this system have protected me in 2008?"

It is not a sandbox. It is not a research lab. It is a **proof machine** -- it replays the exact elimination and scoring pipeline against 20 years of point-in-time data so users can verify every decision the system would have made, in every market regime, with full transparency into which factors were available and which weren't.

For free users, it surfaces a single compelling headline: the model's cumulative performance through the worst drawdown in modern history. For paid users, it opens the full audit trail -- every rebalance, every elimination, every regime transition -- with constrained knobs to stress-test assumptions without curve-fitting.

A shadow portfolio runs in parallel from day one, building genuine out-of-sample track record that no amount of historical simulation can replicate. Over time, the live track record replaces the backtest as the primary trust signal.

**Positioning:** The backtest is the glass box turned sideways through time. Competitors show backtested equity curves with no audit trail. Margin shows every decision at every point, including when the model had incomplete data and what it did about it.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary audience | Retention/upgrade tool | Free users see static scores; paying users stress-test them historically |
| Customization | Constrained knobs | Few parameters within guardrails; enough for research, not enough to overfit |
| Historical depth | 15-20 years | Captures GFC (2008) -- the credibility litmus test for this audience |
| Compute model | Hybrid | Pre-computed default loads instantly; on-demand for knob adjustments |
| Monetization | Fully paywalled with teaser | Three numbers free, everything else paid |
| Data source | yfinance + supplement | Sharadar/Nasdaq Data Link for point-in-time fundamentals and delisted companies |

## Architecture Blueprint

### Core Components

#### 1. Point-in-Time Data Store

A separate data layer storing historical snapshots of fundamentals, pricing, and corporate actions as they were known at each date. Distinct from the live data pipeline.

- Indexed by `(ticker, as_of_date)` -- every query asks "what did we know about AAPL on March 1, 2009?"
- Includes delisted companies with their full history up to delisting
- Stores restated vs. originally-reported financials separately (the engine uses originally-reported only)
- Built from Sharadar/Nasdaq Data Link for fundamentals + a survivorship-bias-free pricing source

#### 2. Replay Orchestrator

The central engine. For each rebalance date in the simulation window:

1. Loads the point-in-time snapshot of the investable universe
2. Runs the elimination filter cascade (same code path as live)
3. Runs the scoring pipeline on survivors (same code path as live)
4. Selects positions based on conviction threshold
5. Records every decision with full audit metadata
6. Rolls forward to the next rebalance date, tracking portfolio performance

Critical: this calls the actual `margin_engine` elimination and scoring functions. No simplified proxy. The engine package has zero web dependencies, so it plugs directly into the replay loop.

#### 3. Factor Availability Registry

A metadata layer declaring, for each factor, the date range where reliable data exists:

- `revenue_growth`: available from 2005 (SEC EDGAR XBRL)
- `ml_cluster_score`: available from 2026 (when the ML pipeline started)
- `insider_activity`: available from 2010 (spotty before that)

When the replay engine hits a period where a factor is unavailable, it scores with the reduced factor set and records exactly which factors were missing. This is surfaced in the UI, not hidden.

#### 4. Portfolio Tracker

Handles position sizing, rebalancing mechanics, and performance attribution:

- Equal-weight or conviction-weighted (user knob)
- Configurable rebalance frequency: monthly, quarterly, semi-annual (user knob)
- Transaction cost model: configurable basis points per trade (default: 20bps)
- Slippage model: volume-based square-root market impact estimate
- Cash drag: uninvested cash earns risk-free rate
- Tracks: total return, drawdowns, Sharpe, Sortino, Calmar, max drawdown, recovery time

#### 5. Shadow Portfolio Service

A lightweight daily job that:

- Runs today's live model output through the same portfolio tracker
- Records paper positions and marks-to-market daily
- Stores results in a dedicated table with immutable timestamps
- Cannot be edited or backfilled -- provably forward-looking

#### 6. Results Cache

- Pre-computed default backtest (model with default settings) stored as materialized results -- loads instantly
- On-demand runs (knob adjustments) computed server-side via ARQ worker queue, cached by parameter hash
- Cache invalidation: only when the underlying model version changes

### Data Flow

```
Historical Data Sources
        |
        v
Point-in-Time Data Store --> Factor Availability Registry
        |                              |
        v                              v
Replay Orchestrator (calls margin_engine directly)
        |
        v
Portfolio Tracker (position sizing, costs, attribution)
        |
        +--> Results Cache (pre-computed default)
        +--> ARQ Queue (on-demand knob runs)
                    |
                    v
              Results Cache (keyed by param hash)
                    |
                    v
              API Endpoints --> Web Frontend
```

### Integration with Existing Stack

- **Engine:** Replay orchestrator imports `margin_engine` functions directly. No duplication.
- **API:** New `/backtest/` endpoint group. Pre-computed results served from cache. On-demand runs enqueued via existing ARQ worker infrastructure.
- **DB:** New tables: `backtest_snapshots`, `backtest_results`, `shadow_portfolio_positions`, `factor_availability`. All in the existing PostgreSQL instance.
- **Web:** New pro-tier page. Teaser component on the free asset detail page.

## Bias-Prevention Framework

### Survivorship Bias

**Problem:** Testing only against companies that exist today inflates results -- you never "bought" Lehman Brothers or Enron.

**Solution:**
- The point-in-time universe includes every company that was publicly traded at each snapshot date, including those later delisted, acquired, or bankrupt
- Delisted stocks handled explicitly: acquisition = cash at acquisition price, bankruptcy = total loss, voluntary delisting = last traded price
- The UI shows a "universe size" indicator at each rebalance date

### Look-Ahead Bias

**Problem:** Using data that wasn't available at the time of the decision.

**Solution:**
- All fundamental data indexed by filing date (when SEC received it), not period end date
- Configurable reporting lag buffer (default: 45 days after quarter end)
- Price data uses close prices with a 1-day execution delay
- Factor availability registry enforces hard date boundaries per data source

### Overfitting / Curve-Fitting Protection

**Constrained Knobs with Guardrails:**
- Users can adjust: rebalance frequency (monthly/quarterly/semi-annual), conviction threshold (top 10/20/30 percentile), sector exclusions (max 2 sectors), weighting scheme (equal/conviction-weighted)
- Users cannot adjust: factor weights, factor selection, elimination filter thresholds, scoring formula
- Total parameter space: fewer than 50 possible combinations
- Every result screen shows: "N parameter combinations tested" as disclosure

**Walk-Forward Validation:**
- Default backtest uses rolling walk-forward analysis, not a single in-sample fit
- Train on years 1-5, test on year 6, roll forward, repeat
- Reported return is the composite of out-of-sample periods only
- Displayed explicitly: "All returns shown are out-of-sample"

### Regime Change Handling

- Performance segmented by market regime: bull (>20% from trough), bear (>20% from peak), sideways (neither), crisis (VIX > 30 sustained)
- Regime classification uses NBER recession dates + S&P 500 drawdown thresholds
- UI leads with regime-segmented performance, not blended
- Regime transitions marked on the equity curve

### Transaction Costs & Slippage

- Default cost model: 20bps round-trip
- Slippage: square-root market impact based on position size vs. average daily volume
- Default view always includes costs (toggle to exclude for comparison)
- High-turnover configurations trigger a warning with cost impact

### Honesty Disclosures

Every backtest result screen includes a persistent footer:

> **What this backtest does not account for:** taxes, margin costs, liquidity constraints for portfolios over $X, regulatory changes, factor crowding effects, and the behavioral difficulty of following a systematic strategy through a 40% drawdown.

## UX Layout

### Teaser (Free Users -- Asset Detail Page)

A single component below the scoring section:

- **Headline number:** "Model back-tested cumulative return since 2006: +387%"
- **Benchmark comparison:** "S&P 500 over same period: +214%"
- **Worst drawdown teaser:** "Max drawdown during 2008 financial crisis: -31% vs. S&P 500 -56%"
- **CTA:** "See every decision the model made -> Upgrade to Pro"

Three numbers and a button. No chart, no detail, no knobs.

### Full Backtest Page (Paid Users)

Organized top-to-bottom in order of what builds trust fastest:

**1. Regime Performance Cards** -- Four cards (Bull, Bear, Sideways, Crisis), each showing model return vs. benchmark, month count, and max drawdown within regime. First thing users see.

**2. Equity Curve with Regime Bands** -- Full 20-year curve, model vs. benchmark. Background bands color-coded by regime. Drawdowns shown as filled red areas below the curve (deliberate -- don't hide the pain). Interactive hover for exact values.

**3. Factor Availability Timeline** -- Horizontal bar chart showing which factors were active at each point. Clickable to see exactly which factors were missing per period and how the model scored with the reduced set.

**4. Rebalance Audit Log** -- Scrollable table: date, universe size, eliminated count, survivor count, top 10 positions with conviction scores, notable entries/exits. The glass box turned sideways.

**5. Knobs Panel** -- Right sidebar or collapsible. Rebalance frequency dropdown, conviction threshold slider, sector exclusions (max 2), weighting toggle, transaction cost toggle. "Run Backtest" button with progress indicator. Banner notes parameter changes from default.

**6. Statistical Summary** -- Sharpe, Sortino, Calmar, annualized return/volatility, max drawdown with recovery time, win rate, turnover, 95% confidence interval (bootstrap). "All returns shown are out-of-sample" disclosure.

**7. Shadow Portfolio Section** -- Clearly separated. Live paper portfolio since start date, same metrics, "cannot be backdated or edited" badge. Grows in credibility over time.

### Design Language

- Dark background, `terminal-card` containers
- `--color-bullish` / `--color-bearish` for returns
- Geist Mono for numerical data
- Inter Tight for labels
- Instrument Serif for headline teaser number
- No gratuitous animation

## Monetization Strategy

### Tier Structure

**Free tier:** Teaser only -- three numbers on the asset detail page. No chart, no drill-in, no knobs.

**Pro tier:** Full backtest page, constrained knobs, on-demand re-runs, regime analysis, audit log, stats, shadow portfolio, CSV export.

### Pricing Position

The backtest is the anchor feature that justifies Pro pricing, bundled with other Pro-tier features as part of a single subscription. Not sold separately -- bundling removes the "do I need this?" decision.

### Conversion Funnel

Free user views asset detail -> sees teaser numbers -> clicks "See every decision" -> hits paywall -> Pro signup. The teaser number reflects the model's actual performance for the ticker/universe being viewed.

### Cost Management

The bounded parameter space (< 50 combinations) keeps compute predictable. Pre-compute popular combinations off-peak. On-demand runs are CPU-bound but cacheable. High cache hit rate expected since most users try the same 5-10 configurations.

## Execution Risks

### 1. Point-in-Time Data Quality

If historical fundamentals contain restated figures rather than originally-reported, the entire backtest is silently dishonest. Sharadar has known gaps before ~2010.

*Mitigation:* Data validation layer cross-referencing filing dates against SEC EDGAR timestamps. Unverifiable data points marked and excluded from the default backtest. Data quality percentage surfaced per period in the UI.

### 2. Factor Degradation Undermines the Narrative

The model uses 12 factors but only 7 may be available in 2006. If the model performs poorly with 7 but well with 12, the backtest tells a misleading story.

*Mitigation:* Show two equity curves: "full model (from first date all factors available)" and "degraded model (full history)." Let users see the difference explicitly. "The model got better as more data became available" is a compelling and honest narrative.

### 3. Users Misinterpret Results Despite Guardrails

Some users will screenshot the best-looking curve and treat it as a guarantee.

*Mitigation:* Every shareable/exportable view automatically includes honesty disclosure and methodology note. Regime cards force confrontation with drawdowns before cumulative returns. Shadow portfolio reminds users: simulated past performance and live track record are different things.

## Bold Differentiator: The Failure Audit

Every backtesting platform shows when the model won. **Margin shows when it lost -- and why.**

A dedicated "Failure Audit" section surfaces:

- The 10 worst rebalance periods, ranked by relative underperformance vs. benchmark
- For each: what the model held, what it missed, which factors drove the bad selections
- A regime tag explaining the macro context ("Q4 2018: Fed tightening cycle, momentum factor crashed industry-wide")
- Whether the model would have recovered if the user held through vs. panic-sold

No competitor does this. They bury losses in blended returns. Margin dissects them.

**Why this works:** The burned-but-serious investor has been lied to by smooth equity curves. The DIY quant knows every model has failure modes and wants to understand them. The rationalist respects a system that does a postmortem on its own mistakes. The failure audit transforms the backtest from "look how good we are" into "here's exactly how this breaks, and here's why we think it's still worth using." That's the trust inflection point that turns a skeptic into a subscriber.
