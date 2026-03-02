# Scoring Factors Audit & Remediation Design

**Date:** 2026-03-02
**Status:** Approved
**Scope:** Full audit of Scoring Factors methodology page — UI fixes, institutional accuracy audit, gap analysis, and remediation roadmap

---

## 1. Objective

Conduct a comprehensive audit of the Margin Invest Scoring Factors / Methodology page covering:

1. UI and formatting defects
2. Methodology accuracy against academic literature, commercial quant platforms, and institutional expectations
3. Claims-vs-reality gap analysis
4. Prioritized remediation roadmap

This builds on and expands the existing 2026-02-21 scoring audit, adding frontend accuracy assessment and institutional benchmarking.

---

## 2. UI Defects Identified

### 2.1 Color Collision: Quality and Value Bars Identical

**Root cause:** `--color-accent` (#0E4F3A) and `--color-bullish` (#0E4F3A) are the same hex value in `globals.css`.

**Affected components:**
- `score-breakdown-bars.tsx` — Quality (`bg-accent`) and Value (`bg-bullish`) render as identical green bars
- `scoring-section.tsx` — Quality (`border-t-accent`) and Value (`border-t-bullish`) pillar card borders are identical
- Composite bar also uses `bg-accent` — 3 green bars + 1 gold bar total

**Fix:** Introduce a distinct `--color-value` token (blue/teal) for the Value pillar:
- Quality → `--color-accent` (green #0E4F3A) — durability/stability
- Value → `--color-value` (blue, e.g. #2563EB or teal #0D6E6E) — valuation/measurement
- Momentum → `--color-warning` (gold #B8860B) — signals/confirmation
- Composite → neutral or blended indicator

Update all references in `scoring-section.tsx`, `score-breakdown-bars.tsx`, and any other components using `bullish` for the Value pillar context.

### 2.2 Filter Funnel Browser Compatibility

**Issue:** `filter-funnel.tsx:65` uses `color-mix(in srgb, ...)` which has inconsistent browser support.
**Fix:** Replace with a pre-computed rgba value or CSS custom property.

### 2.3 Section Formatting Audit

All 12 methodology sections should be audited for consistent:
- Section container padding (currently `8vw` horizontal, `96px` vertical)
- Typography hierarchy (stage label → heading → body → detail)
- Card styling (border, border-radius, background, padding)
- Motion patterns (fade-up animations, stagger delays)
- Dark mode rendering

---

## 3. Methodology Page vs Engine: Structural Mismatch

### 3.1 What the Page Describes

A linear pillar-scoring model:
```
Factors → Pillar Percentiles → Growth-Stage Weights → Composite Score → Conviction
```

- 20 factors across 3 pillars (Quality/Value/Momentum)
- Factor scores ranked within GICS sector
- Pillar weights adjust by growth stage
- Final composite re-ranked across universe
- Conviction levels: EXCEPTIONAL, HIGH, WATCHLIST, NONE

### 3.2 What the Engine Actually Does

A multi-track gate cascade (v4):
```
Factors → Gate Checks (per track) → Multiplicative Score → Conviction Thresholds
                                   → Track Orchestration → Final Conviction + Opportunity Type
```

- 3 independent tracks: Compounder (A), Mispricing (B), Efficient Growth (C)
- Each track has 4 gates with absolute thresholds (not percentile-based)
- Scoring is multiplicative within each track (zero in any gate = zero score)
- Track orchestration promotes the strongest qualifying track(s)
- Conviction levels: EXCEPTIONAL, HIGH, MEDIUM, NONE
- Track C only runs for GROWTH-style assets

### 3.3 Specific Discrepancies

| # | Page Claim | Engine Reality | Action |
|---|-----------|---------------|--------|
| 1 | "20 factors. Three pillars." | 20 factors computed, but feed into gates across 3 tracks, not weighted pillar averages | Rewrite to describe gate cascade |
| 2 | No mention of Track C | Engine has 3 tracks | Add Track C description |
| 3 | "Factor scores ranked within each sector" | Some factors ranked by sector; gate thresholds are absolute | Clarify which steps use ranking vs absolute thresholds |
| 4 | "Pillar weights adjust based on growth stage" | Growth stage determines Track C eligibility, not pillar weights | Correct description |
| 5 | "Re-ranked across entire universe" | Conviction assigned by absolute gate thresholds | Remove or correct |
| 6 | Conviction: "WATCHLIST" | Engine uses "MEDIUM" | Fix terminology |
| 7 | "Every US-listed equity. No cherry-picking." | Universe is current-only (no delisted) | Add survivorship disclosure |
| 8 | "Scores updated daily" | Depends on pipeline operations | Add operational caveat |

### 3.4 Remediation Approach

Rewrite the methodology page to accurately describe the 3-track gate cascade system. This is a content-only change — no engine modifications required.

---

## 4. Institutional Accuracy Audit: Factor-by-Factor

### 4.1 Confidence Ratings

**HIGH confidence (7 factors)** — exact matches to seminal academic papers:

| Factor | Academic Source | Notes |
|--------|---------------|-------|
| Gross Profitability | Novy-Marx (2013) | Exact formula match |
| Piotroski F-Score | Piotroski (2000) | All 9 signals correct |
| Accrual Ratio | Sloan (1996) | Cash-flow approach, standard |
| EV/FCF | O'Shaughnessy; institutional standard | Standard EV definition |
| Acquirer's Multiple | Carlisle (2017) | EV/EBIT, exact match |
| Shareholder Yield | Faber (2013) | Dividends + buybacks |
| Price Momentum (12-1) | Jegadeesh & Titman (1993) | Correct 1-month exclusion |

**MEDIUM confidence (7 factors)** — reasonable but with caveats:

| Factor | Key Issue |
|--------|-----------|
| ROIC-WACC Spread | Uses end-of-period IC (not average); static sector WACC |
| ROIC Stability | CV fragile near zero; no academic precedent for exact formula |
| Incremental ROIC | Uses only first/last period; regression approach more robust |
| DCF Margin of Safety | Terminal value dominance; externally supplied growth rate |
| Owner Earnings Yield | 1.1x depreciation proxy crude; collinear with EV/FCF |
| Reverse DCF Growth Gap | Depends on externally supplied sustainable growth rate |
| Asset Floor | Near-zero for tech; static liquidation multiples |

**Additional MEDIUM factors:**
| Factor | Key Issue |
|--------|-----------|
| SUE | Minimum 2 quarters too lenient; no PEAD time decay |
| Insider Cluster | Fixed $100K threshold; no accuracy tracking |
| Institutional Accumulation | 45-day lag; no fund quality or position-size weighting |

**LOW confidence (3 factors)** — significant methodology gaps:

| Factor | Key Issue |
|--------|-----------|
| Moat Durability | "Switching cost" proxy actually measures operating leverage; no empirical weight basis; backward-looking only |
| Sentiment Score | LLM-dependent; no established benchmark; arbitrary contrarian bonus |
| Runway Score | TAM data unreliable; penetration ratio oversimplified; sub-industry revenue often unavailable |

### 4.2 Elimination Filters (All HIGH confidence)

| Filter | Implementation | Notes |
|--------|---------------|-------|
| Beneish M-Score | Exact Beneish (1999) | All 8 coefficients match original paper |
| Altman Z-Score | Altman Z'' (1993) | Correct non-manufacturing variant |
| FCF Distress | Multi-year with sector adjustment | v2 adds cyclical relaxation |
| Interest Coverage | EBIT/Interest with sector thresholds | v2 adds trend guard |
| Current Ratio | CA/CL with quick ratio rescue | Pragmatic low threshold |
| Liquidity | Market cap + dollar volume | Sector-adjusted thresholds |
| Mediocrity Gate | ROIC + margin + FCF + revenue | Composite quality screen |

### 4.3 Cross-Cutting Systemic Issues

**Issue 1: Static Sector WACC (200-400bps systematic error)**
- Current: Static sector average from Damodaran table
- Standard: Company-specific WACC using beta, capital structure, risk-free rate
- Impact: Affects ROIC-WACC spread, DCF MoS, Reverse DCF, Owner Earnings — 4+ factors

**Issue 2: End-of-Period Invested Capital (ROIC bias)**
- Current: `IC = Total Equity + Total Debt - Cash` (point-in-time)
- Standard: Average of beginning and ending IC (Bloomberg, FactSet, S&P)
- Impact: Overstates ROIC for growing companies, understates for shrinking

**Issue 3: Factor Collinearity**
- EV/FCF ↔ Owner Earnings Yield: r ~0.7-0.8
- Accrual Ratio ↔ F-Score signal #4: same underlying concept
- Gross Profitability ↔ ROIC-WACC Spread: r ~0.6-0.7
- Effective independent factor count: ~14, not 20

**Issue 4: No Cyclical Normalization**
- EV/FCF, Acquirer's Multiple, Owner Earnings use trailing 12-month data
- Cyclical businesses at peak/trough get systematically mispriced
- Standard: 7-year median normalization (design doc mentions this but not implemented for valuation multiples)

**Issue 5: yfinance Data Restatement**
- yfinance provides restated (as-reported-now) financial data, not as-originally-reported
- This introduces look-ahead bias in historical analysis
- Impact: Backtesting results would be invalid; current scoring is affected when data gets restated

---

## 5. Remediation Roadmap

### Tier 1 — Critical (content/UI, no engine changes)

| # | Item | Category | Effort | Risk |
|---|------|----------|--------|------|
| 1.1 | Fix pillar color differentiation (Green/Blue/Gold) | UI | Small | None |
| 1.2 | Rewrite methodology page to match engine (3-track gate cascade) | Content | Large | None |
| 1.3 | Change "20 factors" to "17 factors" — remove LOW-confidence factors from claims | Content | Small | None |
| 1.4 | Fix "WATCHLIST" → "MEDIUM" | Content | Small | None |
| 1.5 | Add Track C (Efficient Growth) description | Content | Medium | None |
| 1.6 | Correct "pillar weights adjust by growth stage" | Content | Small | None |
| 1.7 | Correct "re-ranked across universe" claim | Content | Small | None |
| 1.8 | Add survivorship bias disclosure | Content | Small | None |

### Tier 2 — High Priority (engine improvements, approval required per change)

| # | Item | Category | Effort | Risk |
|---|------|----------|--------|------|
| 2.1 | Implement average Invested Capital for ROIC calculations | Engine | Medium | Low |
| 2.2 | Add volatility normalization to Price Momentum (MSCI-style) | Engine | Small | Low |
| 2.3 | Increase SUE minimum to 4 quarters | Engine | Small | Low |
| 2.4 | Fix Moat Durability switching cost label/proxy | Engine | Small | Low |
| 2.5 | Add position-size weighting to institutional accumulation | Engine | Medium | Low |
| 2.6 | Address factor collinearity (analysis + potential deduplication) | Engine | Large | Medium |

### Tier 3 — Medium Priority (significant engine improvements)

| # | Item | Category | Effort | Risk |
|---|------|----------|--------|------|
| 3.1 | Company-specific WACC (beta-based computation) | Engine | Large | Medium |
| 3.2 | Cyclical normalization for valuation multiples | Engine | Medium | Low |
| 3.3 | Add PEAD time decay to SUE | Engine | Small | Low |

### Tier 4 — Long-term (infrastructure & validation)

| # | Item | Category | Effort | Risk |
|---|------|----------|--------|------|
| 4.1 | Run validated walk-forward backtest with PIT data | Engine/Infra | Very Large | Low |
| 4.2 | Calibrate thresholds to empirical outcomes | Engine | Large | Medium |
| 4.3 | Switch from yfinance to PIT data source | Infra | Very Large | High |
| 4.4 | Add delisted stocks to universe | Infra | Large | Medium |

---

## 6. Execution Strategy

### Phase 1: Immediate (1-2 sessions)
- Execute all Tier 1 items
- Zero risk — content and UI only
- Produces: Fixed methodology page, corrected claims, proper color palette

### Phase 2: Short-term (3-5 sessions)
- Execute Tier 2 items with individual approval per change
- Each change is isolated and testable
- Produces: Improved factor methodology, higher signal-to-noise ratio

### Phase 3: Medium-term (multiple weeks)
- Execute Tier 3 items
- Company-specific WACC is the single highest-leverage improvement
- Produces: Significantly more accurate valuation calculations

### Phase 4: Long-term (ongoing)
- Execute Tier 4 items
- Data source migration and backtesting infrastructure
- Produces: Empirically validated system with point-in-time data

### Risk Assessment
- **Tier 1:** Zero risk (content only)
- **Tier 2:** Low risk (isolated, testable engine changes)
- **Tier 3:** Medium risk (WACC change affects all downstream calculations)
- **Tier 4:** High complexity (multi-month data infrastructure effort)

---

## 7. Factor Confidence Detail Table

| # | Factor | Confidence | Academic Source | Primary Risk |
|---|--------|-----------|----------------|-------------|
| 1 | ROIC-WACC Spread | MEDIUM | Stern Stewart / McKinsey EVA | No avg IC; static sector WACC |
| 2 | ROIC Stability | MEDIUM | Asness et al. (2014) quality concepts | CV fragile near zero |
| 3 | Incremental ROIC | MEDIUM | McKinsey / Greenwald | Only first/last period |
| 4 | Gross Profitability | HIGH | Novy-Marx (2013) | — |
| 5 | Piotroski F-Score | HIGH | Piotroski (2000) | Designed for deep value |
| 6 | Accrual Ratio | HIGH | Sloan (1996) | Collinear with F-Score #4 |
| 7 | Moat Durability | LOW | No academic analog | Invalid switching cost proxy |
| 8 | DCF Margin of Safety | MEDIUM | Damodaran; Klarman | Terminal value dominance |
| 9 | EV/FCF | HIGH | Institutional standard | No cyclical normalization |
| 10 | Acquirer's Multiple | HIGH | Carlisle (2017) | No EBIT normalization |
| 11 | Owner Earnings Yield | MEDIUM | Buffett (1986) | 1.1x depreciation crude; collinear |
| 12 | Shareholder Yield | HIGH | Faber (2013) | Missing debt paydown component |
| 13 | Reverse DCF Growth Gap | MEDIUM | Mauboussin (2001) | Depends on supplied growth rate |
| 14 | Asset Floor | MEDIUM | Graham (1934) | Near-zero for tech |
| 15 | Price Momentum (12-1) | HIGH | Jegadeesh & Titman (1993) | No risk adjustment |
| 16 | SUE | HIGH | Latane & Jones (1977) | 2-quarter minimum too lenient |
| 17 | Insider Cluster | MEDIUM | Lakonishok & Lee (2001) | Fixed threshold; no accuracy tracking |
| 18 | Inst. Accumulation | LOW-MEDIUM | Griffin & Xu (2009) | 45-day lag; no quality weighting |
| 19 | Sentiment Score | LOW | Tetlock (2007) concepts | LLM-dependent; no benchmark |
| 20 | Runway Score | LOW | No academic analog | TAM data unreliable |

---

## 8. Decision Log

- **Pillar colors:** Green (Quality) / Blue (Value) / Gold (Momentum) — user approved
- **Page-engine mismatch:** Rewrite page to match actual engine — user approved
- **LOW-confidence factors:** Remove from claimed factor count (20 → 17) — user approved
- **Engine changes:** Proposed with individual approval required per change — user approved
- **Prior audit:** Incorporated and expanded from 2026-02-21 risk register
- **Benchmark standard:** Academic + commercial + institutional (all three)
