# v3 Conviction Engine — Design Document

**Date**: 2026-02-16
**Version**: 3.0
**Status**: Approved
**Supersedes**: v1 composite scorer (`composite.py`), partially supersedes v2 dual-track

---

## Problem Statement

The current scoring engine (v1 composite + v2 dual-track overlay) has five structural flaws that prevent it from surfacing generational, high-conviction investment opportunities:

1. **Percentile averaging compresses the right tail.** Additive weighted averages smooth away extreme outliers. A once-in-a-decade compounder with one moderate sub-factor scores "good, not great."
2. **Single-point DCF is unreliable.** Small changes in growth rate or discount rate produce wildly different intrinsic values. The margin of safety calculation is garbage-in, garbage-out.
3. **No moat detection.** The system measures ROIC but cannot distinguish durable advantage (network effects, switching costs) from temporary advantage (hot product cycle). This is the difference between a generational compounder and a value trap.
4. **Conviction thresholds are universe-relative.** The system always surfaces ~5 Exceptional and ~50 High stocks regardless of whether any deserve capital. Zero is a valid number of recommendations.
5. **Momentum is overweighted as conviction.** Momentum is a 6-12 month phenomenon. Conviction investing operates on 5-10 year horizons. The v1 composite weights momentum at 35% — equal to quality.

---

## Design Philosophy: Gates First, Ranks Second

The v3 engine asks two sequential questions:

1. **"Does this business qualify?"** Absolute gates determine whether a stock enters a conviction track. If it doesn't meet the minimum bar for either Compounder or Mispricing, it is invisible. No percentile rank overrides a gate failure. No "best of bad" recommendations.

2. **"How compelling is it among qualifiers?"** Only stocks that pass gates get scored. Scoring uses multiplicative factors (not additive averages) so that a fatal weakness in any dimension produces a low score, not a moderate one. Ranks break ties among qualifiers only.

### Key Behavioral Change

The system can output zero recommendations. In an expensive market with no qualifying compounders or mispricings, the correct output is "nothing to do."

### Conviction Levels (Absolute, Not Relative)

| Level | Meaning | How Determined |
|-------|---------|----------------|
| Exceptional | Deploy 15-20% of capital | Passes ALL gates + top multiplicative score + ensemble valuation convergence |
| High | Deploy 5-10% of capital | Passes ALL gates + strong multiplicative score |
| Watchlist | Monitor, not actionable | Passes most gates, one or two marginal |
| None | Invisible | Fails gates |

---

## Track A: Compounder Pipeline

Sequential gate cascade with multiplicative scoring. Each stage is pass/fail with a score. You must pass to proceed. The final conviction score is the product of normalized stage scores.

### Stage 1: Moat Evidence Gate (new)

Detects moat durability from financial statement patterns. No narrative, no vibes.

| Moat Type | Financial Pattern | Measurement |
|-----------|------------------|-------------|
| Scale Economics | ROIC increases as revenue grows | Slope of ROIC vs. revenue over 5 years (positive slope = scale advantage) |
| Pricing Power | Gross margins expand during inflation | Gross margin delta in years when industry input costs rose >5% |
| Switching Costs | Revenue retention stays high | Revenue growth exceeds new customer acquisition spending (approximation) |
| Capital Efficiency | New capital as productive as existing | Incremental ROIC >= trailing ROIC (existing `incremental_roic.py`) |

**Scoring:** Each detected moat signature = 1 point. Moat durability score = count (0-4).
**Gate:** `moat_durability >= 2`. Stocks with 0-1 moat signatures are excluded from Track A regardless of ROIC.

### Stage 2: Reinvestment Engine Gate (modified scoring math)

**Gate thresholds (unchanged):** ROIC > 15%, ROIC CV < 0.30, Reinvestment Rate > 30%.

**Score (changed to multiplicative):**

```
compounding_power = incremental_ROIC * reinvestment_rate * (1 - roic_cv)
```

Example: 40% incremental ROIC, 60% reinvestment, 0.15 CV = `0.40 * 0.60 * 0.85 = 0.204`.
Compare: 15% incremental ROIC, 35% reinvestment, 0.28 CV = `0.15 * 0.35 * 0.72 = 0.038`.
The first is 5.4x better. Under percentile averaging they'd be ~1.3x apart.

### Stage 3: Capital Allocation Quality

**Existing sub-factors (keep):**
- Buyback effectiveness (avg buyback price vs avg stock price)
- Debt discipline (5yr Net Debt/EBITDA slope)
- Organic reinvestment ratio (growth capex / total capital deployed)
- Insider ownership (skin in the game)

**New sub-factors:**
- **SBC Dilution Tax**: Share-based compensation as % of revenue. >5% of revenue = heavy penalty. High SBC destroys owner earnings even when GAAP earnings look strong.
- **M&A Discipline**: Does ROIC decline in the 2 years following large acquisitions (>10% of market cap)? Acquisitive companies that destroy value are penalized.

### Stage 4: Valuation Reasonableness — Reverse DCF (new)

For compounders, the right question is not "what is this worth?" but "what is the market assuming?"

```
implied_growth_rate = reverse_dcf(current_price, current_fcf, wacc, terminal_growth)
sustainable_growth_rate = incremental_ROIC * reinvestment_rate
growth_gap = sustainable_growth_rate - implied_growth_rate
```

**Gate:** `growth_gap > 0` (market prices in less growth than the business sustains).
**Score:** `growth_gap` magnitude. Larger gaps = more compelling.

Replaces the current "not above 2x intrinsic value" gate, which is too loose.

### Track A Final Score

```
track_a_score = moat_durability * compounding_power * capital_allocation * valuation_gap
```

Fully multiplicative. A zero in any dimension kills the score.

### Track A Conviction Thresholds

| Level | Requirements |
|-------|-------------|
| Exceptional | All 4 gates pass + compounding_power > 0.15 + moat_durability >= 3 + growth_gap > 0.08 |
| High | All 4 gates pass + compounding_power > 0.08 + moat_durability >= 2 + growth_gap > 0.03 |
| Watchlist | 3 of 4 gates pass + compounding_power > 0.04 + moat_durability >= 2 |

---

## Track B: Mispricing Pipeline

Different thesis than Track A. Buying a dollar for forty cents and waiting for the market to close the gap. Three simultaneous requirements: the discount is real, the downside is protected, something will unlock the value.

### Stage 1: Ensemble Valuation Gate (redesigned)

Single-point DCF replaced by convergence across four independent valuation methods.

| Method | Formula | What It Captures |
|--------|---------|-----------------|
| DCF (existing) | 10yr projected FCF, WACC discount, terminal value | Going-concern value of cash flows |
| Owner Earnings Capitalization (new) | Owner Earnings / WACC | Steady-state earning power, no growth assumption |
| Asset-Based Floor (new) | Net Cash + (Tangible Book * sector liquidation multiple) | Liquidation/breakup value |
| EV/EBIT Peer Comparison (modified) | Median sector EV/EBIT applied to company's EBIT | What an acquirer would pay |

**Convergence test:**

```
values = [dcf_iv, owner_earnings_iv, asset_floor, peer_comparison_iv]
median_iv = median(values)
methods_within_30pct = count of methods where abs(method - median_iv) / median_iv < 0.30
```

**Gate:** `methods_within_30pct >= 3`. At least 3 of 4 methods must agree within 30% of the median.

**Ensemble intrinsic value:** Median of converging methods (not mean, not minimum).

**Discount depth gate:** `current_price < 0.60 * ensemble_IV`.

#### Sector Liquidation Multiples (for asset-based floor)

| Sector | Tangible Book Multiple |
|--------|----------------------|
| Technology | 0.3x |
| Healthcare | 0.4x |
| Consumer Staples | 0.7x |
| Industrials | 0.6x |
| Energy | 0.5x |
| Materials | 0.6x |
| Utilities | 0.8x |
| Communication Services | 0.3x |
| Consumer Discretionary | 0.5x |

### Stage 2: Downside Protection Gate (quantified)

Replace OR-logic checkbox with a concrete maximum loss calculation.

```
downside_floor = max(net_cash_per_share, tangible_book_per_share * sector_liquidation_multiple, 0)
max_loss_pct = (current_price - downside_floor) / current_price
```

**Gate:** `max_loss_pct < 0.50`. Maximum downside capped at 50% even in worst case.

### Stage 3: Catalyst Gate (strengthened)

Three catalyst types, each scored 0-100 (existing implementations):
- Insider cluster buying (`insider_cluster.py`)
- Institutional accumulation (`institutional_accumulation.py`)
- Contrarian signal (`contrarian_signal.py`)

**Score:**

```
catalyst_strength = max(insider_score, institutional_score, contrarian_score)
```

**Gate:** `catalyst_strength > 60th percentile` (among all stocks with any catalyst activity). A weak catalyst doesn't count. The catalyst must be meaningful.

### Stage 4: Quality Floor (tightened)

**Gate:** ROIC > 8% OR improving trajectory.

**v3 change:** If ROIC < 8% but improving, require **3+ consecutive quarters** of margin improvement. Single-quarter blips do not qualify.

### Track B Final Score

```
track_b_score = asymmetry_ratio * catalyst_strength * quality_floor_factor * valuation_convergence
```

Where:
- `asymmetry_ratio`: Raw upside/downside, capped at 20.0
- `catalyst_strength`: Normalized to 0-1 range
- `quality_floor_factor`: 1.0 if ROIC > 8%, scaled 0.5-1.0 if improving but below
- `valuation_convergence`: converging_methods / 4 (0.75-1.0 range)

### Track B Conviction Thresholds

| Level | Requirements |
|-------|-------------|
| Exceptional | All 4 gates pass + asymmetry_ratio > 5.0 + catalyst_strength > 80th pctl + 4/4 methods converge |
| High | All 4 gates pass + asymmetry_ratio > 3.0 + catalyst_strength > 60th pctl + 3/4 methods converge |
| Watchlist | 3 of 4 gates pass + asymmetry_ratio > 1.5 |

---

## Track Combination

### Independent Track Results

Each track produces an independent result. No unified score. No "pick the winner."

```
track_a_result: QUALIFIES(level, score) | DOES_NOT_QUALIFY
track_b_result: QUALIFIES(level, score) | DOES_NOT_QUALIFY
```

### Opportunity Type (from existing `opportunity_classifier.py`, behavior unchanged)

| Classification | Meaning |
|---------------|---------|
| COMPOUNDER | Qualifies on Track A only |
| MISPRICING | Qualifies on Track B only |
| BOTH | Qualifies on both tracks |
| NEITHER | Qualifies on neither (invisible) |

### "Both" Classification

If a stock reaches High or Exceptional on both tracks simultaneously, it automatically becomes **Exceptional** with max position sizing. This is the rarest signal — a durable compounder that the market has also deeply mispriced. Expect this 1-2 times per year at most.

---

## Position Sizing

### Track-Specific Sizing

| Track | Exceptional | High | Watchlist |
|-------|-----------|------|-----------|
| Track A (Compounder) | 15% | 8% | 0% |
| Track B (Mispricing) | 12% | 6% | 0% |
| Both (Exceptional + Exceptional) | 20% | N/A | N/A |

### Design Rationale

- **Watchlist = 0%.** Watchlist stocks are monitoring targets, not positions. Allocating 3-6% to uncertain ideas is how concentrated portfolios become closet index funds.
- **Compounders > Mispricings.** Compounders have longer duration and less binary risk. A mispricing that doesn't re-rate stays cheap for years. A compounder that keeps compounding forces eventual recognition.
- **"Both" gets 20%.** This is the concentrated bet the system exists to find.

### Portfolio Cap

**Hard maximum: 10 positions.** If more than 10 stocks qualify at High+, rank by multiplicative score within each track and surface only the top 10. Concentration, not diversification.

---

## Market Regime Modifier (new)

Absolute conviction thresholds adjust based on market valuation regime. Not prediction — detection of current conditions.

| Regime | CAPE Range | Track A Adjustment | Track B Adjustment |
|--------|-----------|-------------------|-------------------|
| Cheap | < 15 | Relax growth_gap threshold by 2% | Relax asymmetry threshold by 1.0 |
| Normal | 15-25 | No adjustment | No adjustment |
| Expensive | 25-35 | Tighten growth_gap by 2% | No adjustment |
| Euphoria | > 35 | Tighten growth_gap by 5% | Tighten catalyst_strength to 90th pctl |

**Rationale:** In expensive markets, demand a larger growth gap before calling a compounder a buy. In cheap markets, more opportunities exist and the bar can relax. Track B is less affected because genuine mispricings appear in any market — but in euphoria, cheap stocks are often cheap for a reason, so require stronger catalysts.

**Data source:** Shiller CAPE from FRED (already in the data pipeline).

---

## Timing Overlay (modified)

Momentum is entry timing, not conviction. Lives exclusively in the timing overlay.

### Track A Timing

```
momentum >= 50  -> "buy_now"            (trend confirms quality)
momentum 30-49  -> "add_on_pullback"    (good business, wait for better price)
momentum < 30   -> "accumulate_slowly"  (great business in pain — DCA over 2-3 months)
```

### Track B Timing

```
momentum < 50   -> "buy_now"            (contrarian confirmation)
momentum >= 50  -> "wait_for_catalyst"  (not yet in pain, catalyst hasn't fired)
```

### New Signal: `accumulate_slowly`

For Track A compounders in sharp decline (momentum < 30th percentile). A great business down 30%+ with intact moats is the best buying opportunity — but DCA over 2-3 months rather than going all-in at once.

---

## Components Removed

| Component | File | Reason |
|-----------|------|--------|
| v1 composite scorer | `composite.py` | Additive percentile averaging is the core problem. Superseded by dual-track. |
| Momentum as conviction pillar | `composite.py` weights | Momentum is timing, not conviction. Lives only in timing overlay. |
| Universe-relative thresholds | `ScoringConfig` (99.95, 99.3, 98.0) | Replaced by absolute thresholds. No guaranteed recommendation count. |
| `min()` growth rate selection | `dcf_mos.py` | Each growth estimate used independently in ensemble. No artificial floor. |
| Global re-ranking | `normalizer.rerank_composites()` | No global re-ranking. Each track scores against absolute bars. |
| Shareholder yield in Track A | `shareholder_yield.py` usage | Buybacks/dividends are capital allocation, not value. Already in cap alloc pillar. Keep in Track B. |
| Price momentum in composite | v1 composite 35% weight | Moved to timing overlay. |

---

## Components Added

| Component | Track | File (proposed) | Purpose |
|-----------|-------|-----------------|---------|
| Moat durability classifier | A | `scoring/quantitative/moat_durability.py` | Detect 4 moat signatures from financial patterns |
| Reverse DCF | A | `scoring/quantitative/reverse_dcf.py` | Compute implied vs sustainable growth gap |
| Ensemble valuation | B | `scoring/quantitative/ensemble_valuation.py` | 4-method convergence test for reliable IV |
| Owner earnings capitalization IV | B | Extend `owner_earnings.py` | New valuation method: Owner Earnings / WACC |
| Asset-based floor IV | B | `scoring/quantitative/asset_floor.py` | Liquidation/breakup valuation method |
| Market regime modifier | Both | `scoring/market_regime.py` | CAPE-based threshold adjustment |
| SBC dilution tax | A | Extend `capital_allocation.py` | Penalize high stock-based compensation |
| M&A discipline score | A | Extend `capital_allocation.py` | Detect value-destroying acquisitions |
| Sustained ROIC improvement | B | Extend `roic_stability.py` | 3+ consecutive quarters, not single-quarter blip |
| Portfolio concentration cap | Both | `scoring/portfolio.py` | Max 10 positions |
| `accumulate_slowly` timing | A | Extend `timing_overlay.py` | DCA into compounders in sharp decline |

---

## Components Modified

| Component | File | Change |
|-----------|------|--------|
| `dual_track.py` | Orchestrator | Remove "pick the winner" — both tracks produce independent results |
| `conviction_gates.py` | Gates | Gates become primary conviction mechanism, not cap |
| `position_sizing.py` | Sizing | Track-specific sizing, watchlist = 0%, portfolio cap = 10 |
| `opportunity_classifier.py` | Classifier | "Both" at High+ on both tracks = automatic Exceptional |
| `composite_compounder.py` | Track A | Multiplicative scoring replaces weighted average |
| `composite_mispricing.py` | Track B | Multiplicative scoring, ensemble valuation input |
| `timing_overlay.py` | Timing | Add `accumulate_slowly` signal, 3-tier Track A timing |
| `models/scoring.py` | Models | Add moat_durability, growth_gap, ensemble_iv, regime fields |
| `mediocrity_gate.py` | Filter | Tighten: separate thresholds for Track A (ROIC > 15%) vs Track B (ROIC > 8%) |

---

## Scoring Math Comparison

### v1 (Current Default)

```
composite = quality_avg_pctl * 0.35 + value_avg_pctl * 0.30 + momentum_avg_pctl * 0.35
conviction = percentile_rank(composite) vs universe thresholds
```

### v2 (Current Dual-Track Overlay)

```
track_a = quality_avg_pctl * 0.50 + value_avg_pctl * 0.30 + cap_alloc_avg_pctl * 0.20
track_b = value_avg_pctl * 0.45 + quality_floor_avg_pctl * 0.25 + catalyst_avg_pctl * 0.30
winner = max(track_a, track_b)
conviction = percentile_rank(winner) vs universe thresholds, capped if gates fail
```

### v3 (This Design)

```
track_a = moat_durability * compounding_power * capital_allocation * growth_gap
track_b = asymmetry_ratio * catalyst_strength * quality_floor_factor * valuation_convergence
conviction = absolute thresholds per track (no universe ranking)
output = independent results per track, "both" = exceptional
```

---

## Determinism Guarantees (Maintained)

| Component | Mechanism |
|-----------|-----------|
| Moat durability | Pure math on 5yr financial patterns |
| Reverse DCF | Algebraic solver given price, FCF, WACC |
| Ensemble valuation | 4 independent formulas, median of convergent |
| Market regime | Shiller CAPE from FRED, fixed tier thresholds |
| Multiplicative scores | Product of deterministic sub-scores |
| Conviction thresholds | Fixed absolute values, regime-adjusted |
| Position sizing | Fixed table lookup |
| Timing overlay | Momentum percentile vs fixed thresholds |

Same inputs produce same outputs. No randomness. No human judgment.

---

## Testing Strategy

### New Test Categories

- **Moat signature golden tests**: Hand-verify moat patterns against known compounders (Costco, ASML, Visa) and known non-moat businesses.
- **Multiplicative scoring tests**: Verify that a zero in any factor produces a zero composite. Verify that magnitude differences are preserved (5x gap stays 5x, not compressed to 1.3x).
- **Ensemble valuation convergence tests**: Test with 4 agreeing methods, 3 agreeing, 2 agreeing (should fail gate), and all divergent.
- **Reverse DCF solver tests**: Hand-calculate implied growth rates for known price/FCF/WACC combinations.
- **Zero-output test**: Verify the system returns empty recommendations when no stock passes gates.
- **Regime adjustment tests**: Verify thresholds tighten/relax correctly at each CAPE tier.
- **"Both" classification tests**: Verify automatic Exceptional promotion when both tracks qualify at High+.

### Coverage Target

Engine scoring module: >= 95% (unchanged).
