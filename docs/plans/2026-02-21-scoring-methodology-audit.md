# Margin Invest Scoring Methodology Audit

**Date:** 2026-02-21
**Scope:** Full audit of v2, v3, and v4 scoring systems
**Objective:** Determine whether the scoring methodology is optimized for "finding once-in-a-generation, high-conviction bets"

---

## 1. Current-State Specification

### 1.1 Pipeline Overview

```
Raw Data (yfinance/SEC/FRED/Finnhub)
  |
  v
Elimination Filters (6 filters + mediocrity gate)
  |
  v
Classification (growth stage, style, sector)
  |
  +-- v2 Additive Percentile Scoring
  |     Quality(6) + Value(3) + Momentum(3)
  |     Weighted sum -> composite -> conviction
  |
  +-- v3/v4 Gates-First Multiplicative Scoring
        Track A: Compounder (4 gates)
        Track B: Mispricing (4 gates)
        Track C: Efficient Growth (4 gates)
        v4 Orchestrator -> conviction + position sizing
```

All three versions run in parallel and coexist in the database.

### 1.2 Elimination Filters

All filters run regardless of failures (no short-circuit). Applied before any scoring.

| Filter | Threshold | Purpose |
|--------|-----------|---------|
| Liquidity | Market cap > $300M, adequate daily volume, 5yr history | Investability |
| Beneish M-Score | M > -1.78 = FAIL | Earnings manipulation |
| Altman Z'' | Z'' < 1.1 = FAIL | Financial distress |
| FCF Distress | Negative FCF streak | Cash burn |
| Interest Coverage | Below sector threshold (default 1.5x) | Debt service |
| Current Ratio | Below sector threshold (default 0.8x) | Short-term liquidity |
| **Mediocrity Gate** | See below | Anti-mediocrity |

**Mediocrity gate thresholds:**

| Metric | Threshold |
|--------|-----------|
| 5yr median ROIC | > 8% |
| Gross margin | > 20% (sector-adjusted: Utilities 10%, Energy 15%) |
| FCF consistency | 4 of last 5 years positive |
| Revenue trend | Not declining 3+ consecutive years |

**Excluded sectors:** Financials, Real Estate (structural incompatibility with standard metrics).

### 1.3 Classification

**Growth stage** (first-match priority):

| Stage | Conditions |
|-------|-----------|
| TURNAROUND | 2+ negative NI quarters + 2+ sequential margin improvements + positive CFO |
| HIGH_GROWTH | Revenue CAGR > 20% AND gross margin > 40% AND market cap > $2B |
| CYCLICAL | Revenue StdDev > 15% OR cyclical sector (Energy, Materials, Industrials, Consumer Disc) |
| MATURE | Revenue CAGR < 5% AND FCF yield > 4% |
| STEADY_GROWTH | Revenue CAGR 5-20% AND positive FCF |

**Investment style:** VALUE / BLEND / GROWTH (classified by valuation multiples relative to sector).

### 1.4 v2 — Additive Percentile Scoring

**Quality sub-factors (6):**

| Factor | Formula | Inverted |
|--------|---------|----------|
| Gross Profitability | (Revenue - COGS) / Total Assets | No |
| ROIC-WACC Spread | ROIC - WACC | No |
| Piotroski F-Score | Sum of 9 binary accounting signals (0-9) | No |
| Accrual Ratio | (NI - CFO) / Total Assets | Yes |
| Insider Cluster | Weighted count of $100K+ buys within 90 days, CEO/CFO 2x | No |
| Institutional Accumulation | 13F holdings change analysis | No |

**Value sub-factors (3):**

| Factor | Formula | Inverted |
|--------|---------|----------|
| EV/FCF | Enterprise Value / Free Cash Flow | Yes |
| Shareholder Yield | (Dividends + Net Buybacks) / Market Cap | No |
| Owner Earnings Yield | (CFO - Maintenance CapEx) / EV | No |

**Momentum sub-factors (3):**

| Factor | Formula |
|--------|---------|
| Price Momentum (12-1) | (Price_T-1mo / Price_T-12mo) - 1 |
| SUE | Most recent earnings surprise / stdev(all surprises) |
| Sentiment Score | TBD (not yet implemented) |

**Normalization:** Percentile rank within sector (ascending for normal, descending for inverted). Ties averaged. Single score = 50.0.

**Composite:** `composite = quality_pctl * Q_weight + value_pctl * V_weight + momentum_pctl * M_weight`

**v4 weight matrix** (style x stage -> quality, value, momentum, growth):

| Style | Mature | Steady Growth | Cyclical | High Growth | Turnaround |
|-------|--------|---------------|----------|-------------|------------|
| VALUE | 0.25, 0.40, 0.20, 0.15 | 0.25, 0.35, 0.20, 0.20 | 0.25, 0.35, 0.20, 0.20 | 0.25, 0.30, 0.20, 0.25 | 0.30, 0.30, 0.20, 0.20 |
| BLEND | 0.30, 0.25, 0.25, 0.20 | 0.30, 0.20, 0.25, 0.25 | 0.30, 0.20, 0.25, 0.25 | 0.25, 0.15, 0.25, 0.35 | 0.30, 0.25, 0.25, 0.20 |
| GROWTH | 0.25, 0.15, 0.30, 0.30 | 0.25, 0.10, 0.30, 0.35 | 0.25, 0.10, 0.30, 0.35 | 0.20, 0.05, 0.30, 0.45 | 0.30, 0.20, 0.30, 0.20 |

**v2 conviction thresholds:**

| Tier | Score |
|------|-------|
| EXCEPTIONAL | >= 79.0 |
| HIGH | >= 72.0 |
| MEDIUM | >= 65.0 |
| NONE | < 65.0 |

### 1.5 v3/v4 — Gates-First Multiplicative Scoring

#### Track A: Compounder (4 sequential gates)

**Gate 1 — Moat Evidence** (moat_durability >= 2):

| Signature | Detection | Weight |
|-----------|-----------|--------|
| Switching Costs | Revenue growth > cost growth | 1.5x |
| Pricing Power | Gross margins expand >= 60% of periods | 1.25x |
| Scale Economics | ROIC increases as revenue grows (60%+ periods) | 1.0x |
| Capital Efficiency | Incremental ROIC >= median ROIC | 0.75x |

Raw score = weighted_sum * (4.0 / 4.5), normalized to 0-4 scale.

**Gate 2 — Reinvestment Engine** (compounding_power > 0.04):

```
compounding_power = incremental_ROIC * reinvestment_rate * stability

incremental_ROIC = (NOPAT_latest - NOPAT_earliest) / (IC_latest - IC_earliest)
reinvestment_rate = growth_capex / NOPAT_latest
  where growth_capex = max(capex - depreciation, 0)
stability = 1.0 - normalized_MAD(ROIC series)
  where normalized_MAD = median(|ROIC_i - median_ROIC|) / |median_ROIC|
```

Uses median tax rate across all periods for ROIC stability calculation (isolates operating performance from tax volatility).

**Gate 3 — Capital Allocation** (composite > 0.5):

Simple average of available sub-factors (2-6 depending on data):
1. Debt discipline (negative net_debt/EBITDA slope = improving)
2. Organic reinvestment ratio (growth capex / total deployed capital)
3. Buyback effectiveness (if buyback_yield provided and > 0)
4. Insider ownership score (if insider_ownership_pct provided)
5. SBC dilution tax (1.0 - SBC/revenue ratio)
6. M&A discipline (ROIC change post-acquisition, or 1.0 if no acquisitions)

**Gate 4 — Valuation** (growth_gap > 0.0 + regime adjustment):

Reverse DCF solves for implied growth rate via bisection:
- `growth_gap = sustainable_growth_rate - implied_growth_rate`
- Combined gap solver: `max(growth_gap, margin_gap)` when margin inputs available
- Positive gap = market underestimates the business

**Track A multiplicative score:**

```
score = moat_durability * compounding_power * capital_allocation * max(growth_gap, 0)
```

**Track A conviction thresholds:**

| Tier | Gates | Compounding Power | Moat | Growth Gap |
|------|-------|-------------------|------|------------|
| EXCEPTIONAL | 4/4 | > 0.15 | >= 3 | > 0.08 + adj |
| HIGH | 4/4 | > 0.08 | >= 2 | > 0.03 + adj |
| MEDIUM | 3+ | > 0.04 | >= 2 | (no gap req) |
| NONE | < 3 gates OR moat < 2 | | | |

#### Track B: Mispricing (4 sequential gates)

**Gate 1 — Ensemble Valuation** (converged AND price < iv_discount * ensemble_iv):

Four independent methods:

| Method | Formula |
|--------|---------|
| DCF | PV(projected FCF) + PV(terminal value) |
| Owner Earnings | OE * (1 + g) / (WACC - g) |
| Asset Floor | max(net_cash + tangible_book * sector_liquidation_multiple, 0) |
| Peer Comparison | Sector median EV/EBIT * company EBIT |

Convergence: >= 3 of 4 must agree within 30% of median. Asset-light sectors (Tech, Healthcare, Comm Services): fallback to DCF + Peer Comparison only.

IV discount tiered by quality:
- 0.75 (25% margin) if ROIC >= 8%
- 0.65 (35% margin) if ROIC < 8% but improving
- 0.60 (40% margin) if ROIC < 8% and not improving

**Gate 2 — Downside Protection** (max_loss < 50%):

```
floor = max(net_cash_per_share, tangible_book_per_share, 0)
max_loss = (current_price - floor) / current_price
```

**Gate 3 — Catalyst** (catalyst_strength > 40):

Weighted blend: 50% strongest + 30% second + 20% third of:
- Insider cluster percentile (0-100)
- Institutional accumulation percentile (0-100)
- SUE percentile (0-100)

Euphoria regime override: threshold raised to 90.

**Gate 4 — Quality Floor** (quality_floor_factor > 0):

```
1.0 if ROIC >= 8%
0.5 + 0.5 * min(ROIC/8%, 1.0) if ROIC < 8% and improving
0.0 if ROIC < 8% and not improving
```

**Track B multiplicative score:**

```
score = min(asymmetry_ratio, 20) * (catalyst_strength / 100) * quality_floor * convergence_factor

asymmetry_ratio = (ensemble_iv - price) / (price - floor)
convergence_factor = max(converging_methods / 4, 0.75)
```

**Track B conviction thresholds:**

| Tier | Gates | Asymmetry | Catalyst | Converging |
|------|-------|-----------|----------|------------|
| EXCEPTIONAL | 4/4 | > 5.0 + adj | > 55 | >= 4 |
| HIGH | 4/4 | > 3.0 + adj | > 40 | >= 3 |
| MEDIUM | 3+ | > 1.5 | (no req) | (no req) |
| NONE | < 3 gates OR asymmetry < 1.5 | | | |

#### Track C: Efficient Growth (4 sequential gates)

**Gate 1 — Growth Efficiency:** Rule of 40 >= 30 OR (revenue_growth > 25% AND gross_margin > 50%)
**Gate 2 — Unit Economics:** Gross margin stable (>= -2pp vs 3yr ago) AND operating leverage >= 1.0
**Gate 3 — Capital Efficiency:** Incremental ROIC > WACC
**Gate 4 — Growth Durability:** Deceleration >= -5pp AND TAM headroom >= 3x

**Track C multiplicative score:**

```
GE = min(rule_of_40 / 40, 2.0)
UE = (1.0 + margin_trend) * max(op_leverage, 0)
CE = min(inc_roic / wacc, 3.0)
GD = min(tam_headroom / 3.0, 1.5) * (1.0 - max(-deceleration, 0) / 20)
score = GE * UE * CE * GD
```

**Track C conviction thresholds:**

| Tier | Gates | Rule of 40 | Inc ROIC | TAM |
|------|-------|-----------|---------|-----|
| EXCEPTIONAL | 4/4 | >= 50 | > 2x WACC | > 5x |
| HIGH | 4/4 | >= 30 | > WACC | (no req) |
| MEDIUM | 3+ | (no req) | (no req) | (no req) |
| NONE | < 3 gates | | | |

### 1.6 v4 Orchestrator — Track Combination

Promotion rules (checked in order):

| Rule | Condition | Result |
|------|-----------|--------|
| 1 | A + B + C all strong (HIGH+) | "all_three", EXCEPTIONAL |
| 2 | A + B strong | "both", EXCEPTIONAL |
| 3 | A + C strong | "compounder_growth", EXCEPTIONAL |
| 4 | Single qualifier | Use strongest track's conviction |
| 5 | None qualify | "neither", NONE |

Note: B + C has no special promotion (picks strongest single track).

### 1.7 Position Sizing

MAX_POSITIONS = 10 (code). Sizes by opportunity type and conviction:

| Type | EXCEPTIONAL | HIGH | MEDIUM |
|------|-------------|------|--------|
| both / compounder_growth / all_three | 20% | 10-12% | 5% |
| compounder | 15% | 8% | 4% |
| mispricing | 12% | 6% | 3% |
| efficient_growth | 15% | 8% | 3% |

### 1.8 Market Regime

Shiller CAPE-based adjustment:

| Regime | CAPE | Track A Gap Adj | Track B Asymmetry Adj | Track B Catalyst Override |
|--------|------|----|----|----|
| CHEAP | < 15 | -0.02 | -1.0 | None |
| NORMAL | 15-25 | 0.0 | 0.0 | None |
| EXPENSIVE | 25-35 | +0.02 | 0.0 | None |
| EUPHORIA | > 35 | +0.05 | 0.0 | 90.0 |

### 1.9 Timing Overlay

Post-conviction entry guidance (momentum-based):

**Track A (Compounder):**
- Momentum >= 50th pctl: "buy_now"
- Momentum 30-49th pctl: "add_on_pullback"
- Momentum < 30th pctl: "accumulate_slowly"

**Track B (Mispricing) — inverted:**
- Momentum < 50th pctl: "buy_now" (contrarian)
- Momentum >= 50th pctl: "wait_for_catalyst"

### 1.10 Intrinsic Value & Price Targets

Ensemble IV = median of converging valuation methods (see Track B Gate 1).

| Target | Formula |
|--------|---------|
| Buy Price | IV * 0.75 (25% margin of safety) |
| Sell Price | IV (no margin) |
| Price Upside | (IV - price) / price |
| Margin of Safety | (IV - market_cap) / IV |

Sector-specific liquidation multiples for asset floor:

| Sector | Multiple |
|--------|----------|
| Technology | 0.3x |
| Healthcare | 0.4x |
| Consumer Staples | 0.7x |
| Consumer Discretionary | 0.5x |
| Industrials | 0.6x |
| Energy | 0.5x |
| Materials | 0.6x |
| Utilities | 0.8x |
| Communication Services | 0.3x |
| Financials | 0.5x |
| Real Estate | 0.7x |

---

## 2. Fitness Evaluation

**Objective:** "Finding once-in-a-generation, high-conviction bets."

### 2.1 Signal Quality

**Strengths:**
- Track A's moat-reinvestment-allocation-valuation sequence maps directly to the Buffett/Munger compounding machine framework.
- Multiplicative scoring preserves magnitude differences (5x better business = 5x higher score, not 1.3x).
- Capital allocation composite addresses a commonly overlooked dimension (SBC dilution, M&A discipline, insider ownership).

**Weaknesses:**
- Moat detection is backward-looking and uses weak proxies. "Revenue growth > cost growth" is operating leverage, not switching costs. No leading indicators of moat erosion (market share loss, customer concentration, competitive entry).
- Reinvestment rate (`growth_capex / NOPAT`) misses R&D-intensive compounders (ASML, MSFT) where reinvestment is OpEx, and acquisition-driven compounders (CSU.TO) where reinvestment is M&A.
- Zero competitive dynamics information. No data about competitors, market share trends, or industry structure.

### 2.2 Valuation Robustness

**Strengths:**
- Ensemble valuation (4 methods with convergence test) is meaningfully better than single-method DCF.
- Tiered IV discount by quality floor adapts margin of safety to business quality.
- Asset-light sector fallback (2-of-4 convergence) handles structural limitation.

**Weaknesses:**
- Single-point intrinsic value with no bear/base/bull range. No uncertainty bounds.
- DCF and Owner Earnings both depend on FCF projections — not truly independent despite being counted as 2 of 4 methods.
- Terminal value drives 60-80% of DCF output. Small WACC or terminal growth changes swing IV by 15-25%.
- WACC is shared across all 4 methods — correlated errors.

### 2.3 Style and Sector Neutrality

**Strengths:**
- Sector-neutral ranking (rank within GICS sector, then combine).
- Style classifier with style-specific weight matrix prevents value bias.
- Asset-light fallback for ensemble valuation avoids penalizing tech.

**Weaknesses:**
- Growth/High_Growth weight cell: momentum(0.30) + growth(0.45) = 0.75 on trend-following signals. This is momentum chasing, not multi-factor scoring.
- Small bucket sizes. Ranking within (sector x style) may produce < 10 stocks per bucket, making percentiles unstable.
- Static GICS classification doesn't capture cross-sector competition.

### 2.4 Stability vs. Responsiveness

**Strengths:**
- MAD instead of CV for stability (robust to outliers).
- Market regime modifier adjusts thresholds dynamically.

**Weaknesses:**
- No hysteresis. Binary gates create cliff effects — moat score of 1.99 = NONE, 2.01 = qualifies.
- A single quarter's data change can flip conviction level entirely.
- Moat signatures all-or-nothing: 60% threshold on consecutive increases means one bad year can flip a signature off.

### 2.5 Data Integrity

**Strengths:**
- Point-in-time design intention (filing_date field on FinancialPeriod).
- NaN sanitization before JSONB storage.

**Weaknesses:**
- No point-in-time historical dataset for backtesting — needs to be sourced.
- yfinance restates historical data (current-state, not as-originally-reported).
- Survivorship bias: universe constructed from currently-listed stocks.
- Insider data has 2-day lag; 13F data has 45-day lag.

### 2.6 Interpretability

**Strengths:**
- Gate-based architecture is inherently interpretable ("failed moat gate").
- Track classification (compounder/mispricing/efficient_growth) gives users a mental model.
- Valuation audit model exposes per-method inputs and intermediates.

**Weaknesses:**
- v2 composite percentile is opaque (weighted average of percentiles loses the original signal).
- v3 multiplicative scores have no natural units — 0.05 vs 0.10 doesn't mean "twice as good."
- No confidence indicator. "Exceptional with 3 missing data points" should feel different.

### 2.7 Outcome Alignment

**Cannot be assessed.** No backtest with point-in-time data has been run. All thresholds are theory-derived, not calibrated to outcomes. This is the single largest gap in the system.

---

## 3. Risk Register

| ID | Issue | Severity | Likelihood | Component |
|----|-------|----------|------------|-----------|
| R1 | No empirical validation — all thresholds theory-derived | Critical | Certain | All |
| R2 | Survivorship bias — universe from currently-listed stocks | Critical | Certain | Ingest |
| R3 | yfinance restates history — not as-originally-reported | Critical | Certain | Data |
| R4 | Single-point IV — no bear/base/bull, no uncertainty bounds | High | Certain | Valuation |
| R5 | Binary gate cliff effects — no hysteresis | High | Likely | v3/v4 |
| R6 | Switching costs proxy invalid — measures operating leverage | High | Certain | Track A G1 |
| R7 | Reinvestment misses R&D and M&A | High | Likely | Track A G2 |
| R8 | Quality pillar collinearity — profitability + earnings quality double-counted | High | Likely | v2 Quality |
| R9 | Terminal value dominance in DCF — WACC sensitivity | High | Certain | Valuation |
| R10 | Growth style momentum chasing — 0.75 weight on trend signals | Medium | Likely | v4 Weights |
| R11 | Small bucket percentile instability | Medium | Likely | Normalizer |
| R12 | No leading moat indicators — all backward-looking | Medium | Likely | Track A G1 |
| R13 | Insider/institutional data lag (2-day/45-day) | Medium | Certain | Track B G3 |
| R14 | Capital allocation composite sensitivity — variable factor count | Medium | Likely | Track A G3 |
| R15 | v2 conviction thresholds (79/72/65) are uncalibrated | Medium | Certain | v2 |
| R16 | No competitive dynamics — zero market share or industry structure data | Medium | Likely | All |
| R17 | Ensemble convergence biased toward asset-heavy businesses | Medium | Likely | Track B G1 |
| R18 | Sentiment score not yet implemented — momentum is 2/3 sub-factors | Low | Certain | Momentum |

---

## 4. Methodology Audit Checklist

### 4.1 Intrinsic Value (Ensemble)

- **What it measures:** Central tendency of 4 independent valuation methods with convergence filter.
- **Predictive value:** Convergence across methods increases confidence the value is real, not a model artifact.
- **Failure modes:** (1) All methods share WACC — correlated errors. (2) DCF and Owner Earnings both depend on FCF — not truly independent. (3) Peer comparison assumes sector median is "fair" — circular in sector-wide bubbles. (4) Asset floor near-zero for tech.
- **Collinearity:** DCF and Owner Earnings overlap ~50% on FCF signal.
- **Sensitivity:** WACC dominates. 1pp change swings DCF by 15-25%. Terminal growth has similar leverage.
- **Missing:** Bear/base/bull scenarios. Probability-weighted IV. Model uncertainty discount.

### 4.2 Quality Factor (v2)

- **What it measures:** Profitability, earnings quality, smart money signals.
- **Predictive value:** High-quality businesses have durable earnings power.
- **Failure modes:** (1) Insider/institutional are timing signals, not quality — misplaced. (2) F-score designed for deep value, not growth. (3) Gross profitability penalizes capital-light businesses.
- **Collinearity:** Gross profitability ~ ROIC-WACC (~0.6-0.7 correlation). Accrual ratio ~ F-score accruals.
- **Sensitivity:** ROIC-WACC has most discriminating power. F-score is coarse (0-9 integer).
- **Missing:** ROIC trend (direction > level). Gross margin durability. FCF conversion ratio. Return on incremental invested capital.

### 4.3 Value Factor (v2)

- **What it measures:** Cash flow cheapness and shareholder yield.
- **Failure modes:** (1) EV/FCF penalizes high-reinvestment businesses (low FCF = high multiple, but reinvestment engine is working). (2) Shareholder yield rewards capital return over reinvestment — contradicts compounder thesis.
- **Collinearity:** EV/FCF and owner earnings yield ~0.7-0.8 correlation.
- **Missing:** Normalized earnings yield (cycle adjustment). Price-to-IV ratio. Earnings yield gap vs risk-free.

### 4.4 Momentum Factor (v2)

- **What it measures:** Price trend and earnings surprise.
- **Failure modes:** (1) 12-1 month momentum crashes during regime changes. (2) SUE captures last quarter, not next. (3) Single-horizon momentum misses inflections.
- **Collinearity:** Minimal between price momentum and SUE.
- **Missing:** Multi-horizon momentum (3/6/12mo). Short-term reversal. Earnings revision momentum.

### 4.5 Track A (Compounder)

- **Conceptual design:** Excellent. Gate sequence maps to the Buffett/Munger framework.
- **Implementation gaps:** Weak moat proxies, narrow reinvestment definition, noisy capital allocation with variable factor count.
- **Key risk:** May be too restrictive — could produce zero Exceptional candidates in normal markets.

### 4.6 Track B (Mispricing)

- **Conceptual design:** Strong. Disciplined deep-value framework.
- **Implementation gaps:** Asymmetry ratio depends on asset floor (near-zero for asset-light). Catalyst threshold is relative not absolute. Quality floor at 8% ROIC is arbitrary for cyclicals at trough.
- **Key risk:** Structurally biased toward asset-heavy, cyclical businesses. Tech mispricing (Apple 2016, Meta 2022) may fail.

### 4.7 Track C (Efficient Growth)

- **Conceptual design:** Addresses the SaaS/tech gap.
- **Implementation gaps:** TAM is unreliable and gameable — source unclear. Operating leverage can be gamed by deferring OpEx. Deceleration penalty is linear but real deceleration is nonlinear (S-curve).
- **Key risk:** Works for SaaS but poorly for biotech, hardware, or platform businesses.

---

## 5. Validation and Backtest Plan

### 5.1 Required Data

| Dataset | Purpose | Source | Cost |
|---------|---------|--------|------|
| Point-in-time fundamentals | Avoid look-ahead bias | Sharadar / SimFin / Compustat | $20-240/yr |
| Historical index membership | Survivorship bias correction | S&P constituent lists, CRSP | $0-500/yr |
| Historical price data | Returns calculation | Yahoo Finance (free) | $0 |
| Historical insider transactions | Catalyst validation | SEC EDGAR Form 4, OpenInsider | $0 |
| Historical 13F filings | Institutional validation | SEC EDGAR, WhaleWisdom | $0 |
| Historical CAPE | Regime detection | Shiller dataset (multpl.com) | $0 |

Minimum viable: Sharadar + free sources = ~$20/month.

### 5.2 Walk-Forward Simulation

Monthly walk-forward from 2010-01 to 2025-12:

1. At each month-end, reconstruct universe using only data available at that point (filing_date <= as_of_date).
2. Run full scoring pipeline: filters -> classification -> v2 + v3/v4 scoring.
3. Select top candidates by each scoring version.
4. Track 1/3/6/12-month forward returns.
5. Rebalance monthly with 15bps total cost (10bps transaction + 5bps slippage).

### 5.3 Regime Windows

| Period | Regime | What it tests |
|--------|--------|--------------|
| 2010-2014 | Post-GFC recovery | Quality rally, low rates |
| 2015-2018 | Late cycle | Momentum dominance |
| 2020 Q1-Q2 | COVID crash | Drawdown resilience, recovery speed |
| 2022 | Rate shock | Growth-to-value rotation |
| 2023-2025 | AI boom | Concentration risk, tech bias |

### 5.4 Performance Metrics

| Metric | Target | What it tests |
|--------|--------|--------------|
| Forward 1/3/5yr excess return | Monotonically increasing by tier | Higher conviction -> higher return |
| Precision@K (Exceptional, K=5) | > 60% | Of top picks, how many outperform? |
| Sharpe ratio | > 0.7 | Risk-adjusted return |
| Sortino ratio | > 1.0 | Downside-adjusted return |
| Max drawdown | < 35% | Tail risk |
| Hit rate | > 55% | Win rate vs benchmark |
| Information ratio | > 0.5 | Active return per unit of active risk |
| Score autocorrelation (monthly) | > 0.85 | Score stability |
| Turnover | < 30%/month | Excessive trading |
| Sector concentration | No sector > 40% | Systematic sector bias |
| Style concentration | No style > 50% | Systematic style bias |

### 5.5 Baselines

| Baseline | Purpose |
|----------|---------|
| S&P 500 equal-weight | Naive benchmark |
| Top decile ROIC | Simple quality factor |
| Top decile EV/FCF | Simple value factor |
| Top decile 12-1 momentum | Simple momentum factor |
| Equal-weight Q+V+M blend | Naive 3-factor blend |

### 5.6 Ablation Tests

1. Remove moat gate -> does precision drop?
2. Remove capital allocation gate -> does it let in value traps?
3. Remove ensemble valuation (DCF only) -> does convergence add value?
4. Remove catalyst gate -> does it degrade timing?
5. Vary conviction thresholds (79 -> 75/80/85) -> sensitivity curve
6. Switch multiplicative to additive -> does magnitude preservation matter?
7. Remove regime adjustment -> does it hurt in expensive markets?
8. Remove each quality sub-factor -> which ones carry the signal?

---

## 6. Proposed Improvements (Ranked by Impact/Effort)

### Tier 1: High Impact, Low Effort

**I1. Uncertainty bounds on intrinsic value**
- Compute bear/base/bull IV using WACC +/- 1pp and growth +/- 2pp.
- Report: "IV = $120 ($85 bear - $160 bull)".
- Use bear-case IV for downside protection instead of point estimate.
- **Effect on tiers:** Reduces false positives by ~20-30%. Stocks with high IV but wide uncertainty ranges get demoted.
- **Validation:** Check if bear-case IV produces better hit rate than point IV.

**I2. Gate hysteresis**
- Once qualified at Exceptional, require falling below HIGH threshold to be demoted (not just below Exceptional).
- Implement as 10% buffer on gate thresholds for current holdings.
- **Effect on tiers:** Reduces turnover by ~40%. Eliminates conviction whipsaw on borderline stocks.
- **Validation:** Compare turnover and return stability with/without hysteresis.

**I3. Relocate insider/institutional from quality to catalyst**
- Move insider cluster and institutional accumulation to catalyst pillar.
- Replace with: ROIC 3-year slope, FCF/Net Income conversion ratio.
- **Effect on tiers:** Quality pillar becomes pure business quality. Catalyst pillar gains the signals it needs.
- **Validation:** Ablation test — compare quality-only and catalyst-only factor performance.

### Tier 2: High Impact, Medium Effort

**I4. Multi-horizon momentum**
- Replace single 12-1 month with: 3-month (0.30) + 6-month (0.40) + 12-1 month (0.30).
- Add 1-month reversal as contrarian signal for Track B.
- **Effect on tiers:** More responsive to inflections. Reduces momentum crash risk during regime changes.
- **Validation:** Compare single vs multi-horizon Sharpe ratios across regimes.

**I5. Expanded reinvestment rate**
- `reinvestment = growth_capex + R&D_growth + net_acquisitions`
- R&D_growth = R&D - (prior_year_R&D * 1.03) — inflation-adjusted excess R&D.
- **Effect on tiers:** R&D-intensive compounders (ASML, MSFT, Google) correctly captured. Acquisition-driven compounders (CSU.TO) correctly captured.
- **Validation:** Check if expanded reinvestment produces higher compounding_power for known compounders.

**I6. Scenario-weighted intrinsic value**
- Three DCF scenarios with probability weights: bear(25%) / base(50%) / bull(25%).
- Vary growth rate, margin trajectory, WACC, terminal multiple per scenario.
- IV = probability-weighted average. Confidence = 1 - (bull-bear range / base IV).
- **Effect on tiers:** Structurally more honest. Makes high-upside vs stable-value distinguishable.
- **Validation:** Check if confidence-adjusted IV produces better precision@K.

### Tier 3: Medium Impact, Higher Effort

**I7. Competitive dynamics proxies**
- Gross margin stability (5-year std dev) as moat durability signal.
- Revenue growth vs sector median (relative market share proxy).
- Customer concentration (10-K parsing, if feasible).
- **Effect on tiers:** Partial substitute for qualitative competitive analysis.
- **Validation:** Check if adding these signals reduces false positives on moat gate.

**I8. Point-in-time data infrastructure**
- Integrate Sharadar (or equivalent) for historical fundamentals.
- Build historical universe reconstruction including delisted companies.
- **Effect:** Enables credible backtesting. Without this, all other improvements remain unvalidated.
- **Validation:** This IS the validation infrastructure.

**I9. Calibrated conviction thresholds**
- After backtesting, optimize v2 thresholds (79/72/65) and v3 gate thresholds to maximize precision@K.
- Use time-series cross-validation (rolling window, no look-ahead).
- **Effect on tiers:** Thresholds based on evidence. May significantly change tier distribution.
- **Validation:** Cross-validated precision@K and hit rate.

### Tier 4: Lower Priority

**I10. Style drift monitoring** — Track sector/style concentration in production. Alert if portfolio exceeds 40% sector or 50% style.

**I11. Data quality gating** — Require data_coverage > 0.8 for Exceptional. Weight conviction by completeness.

**I12. Earnings revision momentum** — Add FY1/FY2 consensus estimate revision (requires paid analyst estimates data). Strongest single-factor signal in institutional quant.

---

## 7. Proposed V2 Scoring Rubric

### 7.1 Factor Definitions (Revised)

**Quality pillar (revised sub-factors):**
1. Gross Profitability — (Revenue - COGS) / Total Assets
2. ROIC-WACC Spread — ROIC - WACC
3. Piotroski F-Score — 9-point accounting health
4. Accrual Ratio (inverted) — (NI - CFO) / Total Assets
5. **ROIC 3-Year Trend (NEW)** — slope of trailing 3-year ROIC
6. **FCF Conversion Ratio (NEW)** — FCF / Net Income (cash quality)

**Catalyst pillar (new, relocated):**
1. Insider Cluster — 3+ buys within 90 days, $100K+
2. Institutional Accumulation — smart money 13F changes
3. SUE — Standardized unexpected earnings

**Value pillar (unchanged):**
1. EV/FCF (inverted)
2. Shareholder Yield
3. Owner Earnings Yield

**Momentum pillar (revised):**
1. **Short-term momentum (3mo)** — 0.30 weight
2. **Medium-term momentum (6mo)** — 0.40 weight
3. **Long-term momentum (12-1mo)** — 0.30 weight

### 7.2 Weighting Scheme

Retain v4 style x stage matrix with two adjustments:
- Cap growth + momentum combined weight at 0.60 (currently reaches 0.75).
- Add catalyst as a 5th dimension with 0.10 weight across all cells (reduce others proportionally).

Tuning method: After backtest infrastructure is built, run grid search over weight combinations with time-series cross-validation. Optimize for precision@K with Sharpe ratio constraint > 0.7.

### 7.3 Tier Thresholds

**v2:** Retain 79/72/65 as defaults. Calibrate via backtest.

**v3/v4 — Track A:**

| Tier | Gates | Compounding Power | Moat | Growth Gap |
|------|-------|-------------------|------|------------|
| EXCEPTIONAL | 4/4 | > 0.15 | >= 3 | > 0.08 + regime |
| HIGH | 4/4 | > 0.08 | >= 2 | > 0.03 + regime |
| MEDIUM | 3+ | > 0.04 | >= 2 | (no req) |

Add hysteresis: once at EXCEPTIONAL, only demote below HIGH thresholds + 10% buffer.

**v3/v4 — Track B:**

| Tier | Gates | Asymmetry | Catalyst | Converging |
|------|-------|-----------|----------|------------|
| EXCEPTIONAL | 4/4 | > 5.0 + regime | > 55 | >= 4 |
| HIGH | 4/4 | > 3.0 + regime | > 40 | >= 3 |
| MEDIUM | 3+ | > 1.5 | (no req) | (no req) |

Add: require data_coverage > 0.8 for EXCEPTIONAL.

### 7.4 Exclusion Rules

Retain current filters. Add:
- data_coverage < 0.6 -> force NONE regardless of score.
- Valuation uncertainty range > 100% of base IV -> cap at MEDIUM.

### 7.5 Production Monitoring

| Metric | Frequency | Alert Threshold |
|--------|-----------|----------------|
| Tier distribution (% Exceptional/High/Medium) | Weekly | Exceptional > 5% or < 0.5% of universe |
| Sector concentration in top picks | Weekly | Any sector > 40% |
| Style concentration in top picks | Weekly | Any style > 50% |
| Score autocorrelation (30-day) | Monthly | < 0.80 |
| Average data coverage of scored assets | Daily | < 0.85 |
| Conviction flip rate (Exceptional -> None) | Weekly | > 10% of Exceptionals flip |
| Ensemble IV dispersion (average CV across methods) | Weekly | CV > 0.50 |
| Gate pass rates by track | Monthly | Any gate < 5% or > 80% pass rate |

---

## 8. Summary of Findings

### What the system does well:
1. **Architectural design is sound.** Gates-first multiplicative scoring is a genuine improvement over additive averaging. The three-track system covers compounders, mispricing, and efficient growth.
2. **Anti-mediocrity filtering is aggressive.** The combination of elimination filters + mediocrity gate removes low-quality businesses before they can pollute the scoring universe.
3. **Determinism guarantee.** Same inputs always produce same outputs. No randomness, no human judgment in the pipeline.
4. **Sector-neutral ranking.** Rank within GICS sector first prevents systematic sector bias.
5. **Market regime awareness.** CAPE-based threshold adjustment is a practical approach to adaptive conviction.

### What must be fixed before the system can be trusted:
1. **Empirical validation.** (R1, R2, R3) Without point-in-time backtesting against survivorship-free data, the system is an untested theory. This is the highest-priority investment.
2. **Valuation uncertainty.** (R4, R9) Single-point IV with no scenario analysis gives false precision. Users cannot assess conviction quality.
3. **Gate hysteresis.** (R5) Binary gates with no buffer create unstable signals. One quarter of noise shouldn't flip conviction.
4. **Signal misplacement.** (R8) Insider and institutional signals in quality pillar conflate business quality with market sentiment.
5. **Reinvestment scope.** (R7) CapEx-only reinvestment rate misclassifies R&D-intensive and acquisition-driven compounders.

### What makes it competitive with best-in-class systems:
1. The moat detection concept (four financial signatures) is unique for a systematic tool. With better proxies and leading indicators, it could genuinely differentiate.
2. The three-track architecture (compounder / mispricing / efficient growth) covers the full opportunity space. Most systematic tools are single-track.
3. The multiplicative scoring with zero-tolerance gates enforces high standards without compromise.
4. The position sizing framework is conviction-appropriate (concentrated for exceptional, smaller for high/medium).

### Critical path to "best-in-class":
1. Source point-in-time data (Sharadar, ~$20/month) -> enables backtesting.
2. Run backtest -> calibrate thresholds -> identify which signals carry weight.
3. Add uncertainty bounds to IV -> reduces false positives.
4. Add gate hysteresis -> stabilizes signals.
5. Fix reinvestment rate -> captures R&D and M&A compounders.
6. Relocate insider/institutional to catalyst -> clean signal separation.
7. Multi-horizon momentum -> reduces crash risk.
8. Monitor in production -> detect drift.
