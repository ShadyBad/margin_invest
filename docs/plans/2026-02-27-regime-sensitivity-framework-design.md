# Regime Sensitivity Framework — Design Document

**Date:** 2026-02-27
**Status:** Approved
**Approach:** Regime-Stratified Ablation Extension (Approach A)
**Deliverable:** Full implementation design — analytical framework + implementable spec extending existing engine infrastructure

---

## Overview

This document defines a framework for characterizing each deterministic elimination filter within its operational market context, with focus on regime sensitivity and stability. The framework extends the existing ablation study pipeline with a multi-dimensional regime classifier and a post-hoc gate characterization module.

**Architecture decision:** Layered approach — regime-conditioned metrics computed natively during replay (cheap, inline), with a separate characterization module for deep statistical analysis (bootstrap CIs, stability tests, failure mode detection) on the regime-segmented results.

**Safeguard posture:** Analytical framework only. The characterization module documents trade-offs between circuit-breakers, dynamic thresholds, and no-action. Empirical results drive the eventual mechanism choice.

---

## 1. Conceptual Framework: Context-Sensitive Logic

### Definition

A deterministic rule is context-sensitive when its **empirical rejection accuracy** — the proportion of eliminations that correctly remove future underperformers — varies as a function of market state, despite the threshold being fixed. The threshold is constant; the economic significance of the threshold is not.

### Three Sources of Context Sensitivity

**Structural regime sensitivity (true economic change).** The economic relationship between a filter's inputs and future outcomes changes across regimes. Example: the FCF Distress filter requires positive FCF in 3 of 5 years. During secular credit expansion, this gate is permissive — most firms generate positive FCF. During credit contraction, the gate becomes highly selective but may also eliminate firms with temporarily impaired cash flows that recover. The filter's discriminative power shifts because the economic mechanism (access to capital, spending patterns) has changed.

**Statistical instability (parameter drift).** The distribution of filter inputs shifts, changing the effective selectivity of a fixed threshold even without structural change. The Current Ratio filter at 0.8 eliminates ~X% of the universe in normal conditions. During a liquidity crunch, the distribution compresses toward 1.0 as firms hoard cash, making the 0.8 threshold nearly non-binding. Conversely, the Interest Coverage threshold of 1.5 becomes hyper-selective when EBIT margins compress in recession. The thresholds haven't changed; the population distribution has.

**Data artifact effects.** Filters consume financial statement data with inherent reporting lags (60-90 days post quarter-end). During stress, reporting distortions amplify: impairment charges spike (affecting EBIT, hence Altman and ICR), goodwill writedowns inflate total assets (affecting Altman's WC/TA), and one-time restructuring charges contaminate Beneish's accrual components. Multi-period medians provide partial protection, but 3-year medians still include distorted periods. The Liquidity filter's volume-based metrics degrade during liquidity crises precisely when they matter most.

### System-Level Implication

The no-short-circuit design (all 6 filters always execute) means regime sensitivity compounds across the full pipeline. If 3 of 6 filters become simultaneously hyper-selective in a stress regime, universe compression could spike from 80-85% to 95%+, collapsing the investable universe to the point where portfolio construction becomes meaningless. The ablation framework's unconditional Shapley values mask this regime-conditional interaction.

---

## 2. Regime Definition & Detection

### Multi-Dimensional Regime Vector

At each rebalance date, the regime is a 4-tuple computed from observable market data:

```
RegimeState = (volatility: LOW|NORMAL|ELEVATED|CRISIS,
               trend: BULL|SIDEWAYS|BEAR|DRAWDOWN,
               valuation: CHEAP|NORMAL|EXPENSIVE|EUPHORIA,
               credit: LOOSE|NORMAL|TIGHT|STRESS)
```

Total theoretical state space: 4 × 4 × 4 × 4 = 256 combinations. In practice, many are near-impossible. The characterization module collapses the space to empirically observed regimes.

### Axis Definitions

**Axis 1 — Volatility State** (realized, not implied)
- `LOW`: 20-day realized vol of S&P 500 < 10th percentile of expanding window
- `NORMAL`: 10th–75th percentile
- `ELEVATED`: 75th–95th percentile
- `CRISIS`: > 95th percentile

Realized vol rather than VIX because: (a) VIX history is limited pre-1990, constraining backtest depth; (b) VIX embeds a risk premium that contaminates regime classification with market positioning; (c) realized vol is directly computable from price data already stored.

**Axis 2 — Trend State** (extends existing classifier)
- `BULL`: Trailing 12m S&P 500 return > +10%
- `SIDEWAYS`: -10% to +10%
- `BEAR`: < -10%
- `DRAWDOWN`: Current level > 20% below trailing 12m high

DRAWDOWN is distinct from BEAR — captures acute selloffs within secular trends. This is the regime where filters are most stressed: acute dislocations where financial statement data lags market reality by a full quarter.

**Axis 3 — Valuation State** (existing CAPE classifier, unchanged)
- `CHEAP`: CAPE < 15
- `NORMAL`: 15–25
- `EXPENSIVE`: 25–35
- `EUPHORIA`: > 35

**Axis 4 — Credit/Liquidity State**
- `LOOSE`: IG credit spread < 25th percentile of expanding 10-year window
- `NORMAL`: 25th–75th percentile
- `TIGHT`: 75th–90th percentile
- `STRESS`: > 90th percentile

Directly conditions solvency-oriented filters (Altman, ICR, Current Ratio). Without this axis, cannot distinguish "firm is genuinely distressed" from "firm's ratios are temporarily impaired by macro credit conditions."

**Data sources:** S&P 500 daily prices (axes 1, 2), Shiller CAPE (axis 3), ICE BofA US Corporate Index OAS or Moody's BAA-AAA spread (axis 4). All publicly available.

### Classification Method

**Primary: Observable threshold-based classification.** Each axis uses fixed percentile thresholds relative to an expanding window. No latent state estimation, no model risk, no lookahead.

**Lookback calibration:** Percentile thresholds use expanding windows (all data from backtest start to current date). Prevents the "calm before the storm" problem where a rolling window spanning only low-vol years sets absurdly low crisis thresholds.

**Transition handling:** Regime transitions lagged by 5 trading days (must persist for a full week). Prevents single-day spikes from triggering reclassification, matching monthly rebalance cadence.

### Confidence Metrics

Each regime classification carries a distance-from-boundary measure:

```
confidence = |observed_value - nearest_threshold| / threshold_range
```

Values near 0.0 = close to boundary (low confidence). Values near 1.0 = deep within regime (high confidence). The characterization module can weight gate performance statistics by classification confidence.

### Out-of-Validated-Conditions Detection

A regime state is "outside validated conditions" when:

1. **Novel combination:** The 4-tuple has fewer than 6 monthly observations in backtest history
2. **Extreme percentile:** Any axis exceeds 99th percentile of expanding-window distribution
3. **Rapid transition:** Two or more axes change state within the same month

These are flags, not triggers — consistent with the analytical safeguard posture.

---

## 3. Gate-Level Characterization

### Characterization Protocol

For each of the 6 elimination filters, the characterization module produces a **Gate Regime Profile** — a structured report documenting behavior across the regime state space.

### Metrics Per Gate Per Regime

**Performance metrics:**
- **Elimination rate:** % of universe eliminated in regime R vs unconditional rate
- **True positive rate (TPR):** % of eliminated stocks that would have underperformed benchmark over subsequent holding period
- **False positive rate (FPR):** % of eliminated stocks that would have outperformed
- **Unique kill rate:** % of eliminations exclusive to this gate in regime R
- **Hit rate delta:** Change in portfolio hit rate when gate enabled vs disabled, within regime R

**Stability metrics:**
- **Threshold utilization:** Distribution of gate input metric relative to threshold in regime R (population density near boundary)
- **Selectivity variance:** Std dev of elimination rate across months within regime R
- **Regime transition shock:** Elimination rate change from month T-1 (old regime) to month T (new regime) at boundaries

**Interaction metrics (from ablation pipeline):**
- **Regime-conditional Shapley value:** φ_i(R) — marginal contribution of gate i to portfolio Sharpe, computed only over months in regime R
- **Regime-conditional pairwise interaction:** Interaction effect for each gate pair within regime R

### Per-Gate Expected Regime Sensitivity

**Liquidity Filter — HIGH sensitivity**
- Primary risk axis: Credit/liquidity state
- During STRESS credit, dollar volume thresholds become hyper-selective. Position-sizing constraint (5 days to fill $500K) becomes nearly impossible for mid-caps. Divergence ratio (90d/20d ≤ 3.0) may invert — panic volume spikes make the ratio permissive on stocks becoming illiquid.
- Characteristic failure: Eliminates temporarily illiquid but fundamentally sound stocks; passes stocks with artificially inflated volume from forced selling.

**Beneish M-Score — MODERATE sensitivity**
- Primary risk axis: Volatility state (proxy for earnings quality distortion)
- Accrual components (TATA, AQI, DSRI) contaminated by one-time charges during stress. Impairment writedowns inflate total accruals. GMI mechanically deteriorates during demand shocks. The -1.78 threshold generates false positives during broad earnings distress.
- Characteristic failure: Flags entire sectors as "manipulators" during recessions due to fraud-like mechanical financial statement patterns.

**Altman Z'' — HIGH sensitivity**
- Primary risk axes: Credit state AND volatility state
- WC/TA (weight 6.56×) compresses during liquidity hoarding, pushing Z'' up (false safety). EBIT/TA (weight 6.72×) collapses during earnings recessions, pushing Z'' down. Net effect depends on component dominance — unstable, direction-ambiguous. Equity/TL swings wildly during mark-to-market regimes.
- Characteristic failure: Oscillating pass/fail across consecutive rebalances during extended stress, generating churn. The 1.1 threshold sits in high population density for cyclicals during downturns.

**FCF Distress — LOW-MODERATE sensitivity**
- Primary risk axis: Trend state (prolonged bears erode 5-year history)
- 5-year lookback with 3-of-5 positive years is the most regime-robust design in the filter stack. Becomes excessively restrictive 2-3 years into prolonged downturns. Cyclical relaxation (2 of 5) is partial mitigation calibrated on historical cycle durations.
- Characteristic failure: Misses early recovery opportunities — positive-trend rescue requires 2+ consecutive improving years.

**Interest Coverage — HIGH sensitivity**
- Primary risk axes: Credit state AND valuation state (via rate regime)
- ICR mechanically coupled to credit environment. Rising rates increase interest expense while compressing EBIT via demand destruction. Sector-adjusted thresholds assume stable relative leverage patterns, which break during credit regime shifts.
- Characteristic failure: Anti-selects for recent capital deployment (growth investment), which is regime-dependent in implications.

**Current Ratio — MODERATE sensitivity**
- Primary risk axis: Credit state
- During STRESS credit, firms hoard cash (CR improves, filter becomes less selective). During LOOSE credit, aggressive working capital optimization lowers CR. The 0.8 threshold was calibrated for mega-cap tech (Apple at 0.87).
- Characteristic failure: Near-inert during the regime where short-term liquidity matters most. Only binds during calm markets when least needed.

### Summary Statistics Per Gate

**Performance degradation ratio:**
```
PDR_i(R) = Sharpe_portfolio_with_i(R) / Sharpe_portfolio_with_i(unconditional) - 1
```

**Variance inflation factor:**
```
VIF_i(R) = Var(monthly_returns | gate_i, regime_R) / Var(monthly_returns | gate_i, all_regimes)
```

**False signal ratio shift:**
```
FSR_i(R) = FPR_i(R) / FPR_i(unconditional)
```

These three numbers across all regime states produce the gate's **regime sensitivity surface**.

---

## 4. Failure Modes Under Regime Change

### Mode 1: Threshold Brittleness

Fixed thresholds applied to continuous distributions. Population density around thresholds is regime-dependent. In normal regimes, distributions are well-separated from thresholds. During stress, distributions compress toward thresholds, making small input perturbations cause mass reclassification.

**Quantification:** Threshold density ratio — proportion of universe within ±10% of threshold in regime R vs unconditional. Ratio > 2.0 = high brittleness.

**Exposure:** Altman Z'' and ICR most brittle (continuous thresholds on compressed distributions). FCF least brittle (binary threshold with multi-year vote).

### Mode 2: Signal Inversion

A filter that correctly eliminates future underperformers in one regime systematically eliminates future outperformers in another. TPR drops below 50%.

**Primary inversion risks:**
- Liquidity filter during post-crisis recovery (eliminates highest-recovery small/mid-caps)
- Beneish during broad restatement waves (flags most transparent firms taking timely writedowns)

**Quantification:** TPR per gate per regime. Flag TPR < 0.50 (inversion) or TPR < 0.55 (near-inversion) with bootstrap CIs.

### Mode 3: Synchronized Gating — Universe Collapse

Altman, ICR, and Current Ratio share balance sheet inputs. During credit stress, shared input correlation spikes (~0.3-0.5 → 0.8+), causing multiple filters to become hyper-selective simultaneously.

**Worst case (CRISIS vol + BEAR + STRESS credit):** Surviving universe compresses to 200-400 names. Sector-neutral ranking breaks with <10 survivors per sector. Portfolio concentration into few surviving sectors.

**Quantification thresholds:**
- Universe collapse: < 500 survivors
- Sector collapse: any GICS sector with < 10 survivors
- Concentration breach: top 3 sectors > 70% of survivors

### Mode 4: Over-Pruning During Crises

Filters correctly identify fundamental deterioration but cannot distinguish cyclical from structural distress. Stocks eliminated at crisis troughs recover most aggressively — the filter was right about current distress but wrong about permanence.

**Quantification:** Recovery opportunity cost — average 12m forward return of stocks eliminated in CRISIS/BEAR vs NORMAL/BULL regimes.

### Mode 5: Latent Exposure Manifestation

Regime sensitivities that only appear under conditions absent from backtest history: sustained inflation (>5% CPI for 3+ years), negative rates, developed-market sovereign crisis. Invisible in any post-1990 backtest.

**Quantification:** Synthetic perturbation stress tests — apply ±2σ shocks to each input dimension independently and measure elimination rate sensitivity.

### Mode 6: Pro-Cyclical Amplification

Solvency filters permissive in bull/loose-credit → portfolio loads on cyclical, leveraged firms → filters snap tight in downturn → forced elimination at trough valuations → realized losses from regime-driven churn.

**Quantification:**
- Regime transition turnover ratio (>3.0 = filter-driven churn)
- Pro-cyclicality coefficient: correlation between survivor count and subsequent 12m returns (positive = pro-cyclical, negative = counter-cyclical)

---

## 5. Fallback & Safeguard Logic

### Analytical Framework (No Prescribed Mechanism)

Three classes of fallback, each with distinct failure profiles:

### Option A: Circuit-Breaker Logic

When regime detector classifies "outside validated conditions," one or more filters are suspended. System reverts to a reduced, broadly-validated filter set.

**For:** Clean, auditable boundary. Preserves determinism within each mode. Prevents synchronized gating.
**Against:** Binary cliff effects at threshold. Regime detection error directly propagates (false alarm disables correctly-functioning filters). Cannot empirically validate a mechanism that fires during events with 3-5 historical examples. Creates new optimization/overfitting surface.

### Option B: Dynamic Threshold Adjustment

Filter thresholds widen/tighten continuously as a function of regime state (e.g., Altman threshold shifts from 1.1 to 0.8 during STRESS credit).

**For:** Smooth, no cliff effects. Directly addresses threshold brittleness. Calibratable from characterization data.
**Against:** Destroys core determinism guarantee. Introduces continuous mapping to specify and validate. Optimal adjustment direction isn't obvious for all filters. Cross-filter interaction effects under simultaneous dynamic adjustment are combinatorially complex.

### Option C: No Regime-Conditional Modification

Filters remain fixed. Regime characterization used for monitoring and ex-post analysis only.

**For:** Preserves full deterministic integrity. Zero compounding of regime detection errors. Consistent with "no human judgment in pipeline" principle.
**Against:** Accepts all six failure modes as known, unmitigated risks. No automated response during conditions where system is most likely to fail.

### The Compounding Risk

All options share a meta-risk: regime detection error compounding rule instability. The compounding is asymmetric — Option C is the only approach where regime detection errors are costless to the decision engine.

### Decision Framework

Rather than prescribing an option, the characterization module should produce:

1. **Cost of inaction:** Total portfolio drag from regime-sensitive filter behavior across all historical regimes (the "damage budget" any safeguard must improve upon)
2. **Cost of regime detection error:** False alarm and missed detection rates × portfolio impact under Options A and B
3. **Decision criterion:** If cost of inaction exceeds cost of detection error by ≥ 2× in-sample (margin for OOS degradation), regime-conditional modification is warranted. Otherwise, Option C is rational.

---

## 6. System-Level Implications

### Path Dependence

Characterizing gates by regime introduces path dependence into system evolution. Each modification in response to characterization data creates a new system whose regime behavior differs from the one characterized. The characterization is valid for the system as-measured, not the system as-modified.

**Mitigation:** Treat each characterization run as a snapshot. Document exact filter configuration, thresholds, and system version. Re-characterize from scratch after modifications.

### Multi-Gate Interaction Under Regime

Three interaction mechanisms, all regime-dependent:

**Shared input correlation.** Altman, ICR, Current Ratio consume overlapping balance sheet data. Normal-regime cross-correlation (~0.3-0.5) spikes to 0.8+ during credit stress. Filters stop providing independent information and triple-count the same risk. Regime-conditional Shapley values quantify this: if φ_Altman(STRESS) + φ_ICR(STRESS) + φ_CR(STRESS) ≈ φ_Altman(STRESS) alone, the three filters are functionally one gate during stress.

**Sequential selection effects.** Multi-period lookbacks (3yr for ICR/CR, 5yr for FCF) create staggered response timing. Altman responds immediately, ICR lags 1-2 quarters, FCF lags years. During regime transitions, filters activate sequentially over 1-3 years, creating prolonged accelerating elimination rather than a single shock.

**Cross-gate false positive amplification.** In compressed stress-regime universes, each false positive represents a larger fraction of the investable opportunity set. Correlated-input false positives (same cyclical misclassification triggers multiple gates) amplify beyond independence assumptions.

### Regime Detection Latency

Three latency sources create misclassification risk:

**Financial statement lag (60-90 days).** During fast regime transitions (March 2020: NORMAL to CRISIS in 3 weeks), regime classifier correctly identifies CRISIS from prices, but filter inputs still reflect pre-crisis financials. Regime flag says "stress" while inputs say "normal."

**Credit spread overshooting.** Spreads reflect market pricing that may overshoot during panic. Regime classifier flags STRESS credit while actual default rates remain normal.

**Persistence filter (5 trading days) + monthly rebalance.** Potential 6-week gap between regime onset and portfolio response.

**Net effect:** Characterization accurately describes equilibrium behavior within stable regimes. Poorly describes behavior during regime transitions — precisely when failure modes are most acute. The module should flag transition months separately with transition-specific metrics.

### Feedback Loops

**Universe composition feedback.** Stress-regime filtering eliminating most stocks in a sector → within-sector ranking on truncated sample → sector-neutral construction overweights distressed sector survivors.

**Rebalance timing feedback.** Regime-conditional high turnover at transitions → transaction costs and tax realization when liquidity is lowest and spreads widest. Backtest overstates realizable returns.

**Survivorship feedback.** S&P 500 used for trend classification reflects index reconstitution survivorship, potentially making BEAR thresholds harder to trigger than the actual experience of the filter universe.

---

## 7. Hidden Assumptions & Validation Risks

### Regime Labeling Subjectivity

- The ±10% BULL/BEAR thresholds are conventional but arbitrary. ±8% or ±15% would produce different conclusions.
- Percentile-based thresholds are self-referential: ~5% of history is always CRISIS by construction.
- 48 regime boundaries create classification ambiguity near each one.

**Validation:** Sensitivity analysis with thresholds shifted ±20%. If gate sensitivity rankings are stable, labeling is robust. If not, conclusions are artifacts of the definition.

### Lookahead Bias

**Expanding-window percentiles.** Early backtest years have poorly estimated thresholds from small reference distributions. **Mitigation:** Require minimum 60-month expanding window; first 5 years classified UNKNOWN.

**NBER recession dating.** Announced retroactively 6-12 months post-facto. **Mitigation:** Use NBER only for ex-post validation, not real-time classification. The 4-axis observable vector is the sole real-time classifier.

**Regime-conditional TPR computation.** Regime at elimination time may differ from regime during forward holding period. **Mitigation:** Report TPR at multiple horizons (1m, 3m, 6m, 12m) tagged by regime at evaluation time, not just elimination time.

### Overfitting to Historical Crises

Backtest window (2006-2026) contains 2-3 major stress episodes (GFC, COVID, 2022 rate-hiking). Each structurally distinct. Effective sample size for stress-regime statistics is ~2-3 independent episodes, not number of months. Monthly bootstrap CIs overstate precision due to serial correlation within crises.

**Validation:** Crisis leave-one-out test — re-run characterization excluding each major crisis. If conclusions change when any single crisis is removed, they describe specific events, not general regime-dependent behavior.

### Survivorship Bias

- **Investable universe:** Must include stocks that subsequently delisted, were acquired, or went bankrupt at each historical rebalance date
- **Filter thresholds:** Altman and Beneish calibration samples reflect detected-only positive classes (detected bankruptcies, detected fraud)
- **Regime data:** S&P 500 reconstitution removes worst performers, biasing trend classification

**Validation:** Use point-in-time universe composition. Report separately the count of filter-eliminated firms that delisted within 12 months (true positive rate on severe outcomes).

### Regime Instability in Unknown Environments

The 4-axis taxonomy assumes volatility, trend, valuation, and credit are sufficient. Environments that would violate this:

- **Structural inflation (>5% CPI sustained):** Distorts every filter simultaneously via nominal effects, but no axis captures the mechanism
- **Regulatory regime change (e.g., accounting standard shifts):** Level shifts in filter inputs with no market-level signal
- **Market microstructure shift (passive flow dominance):** Alters informational content of volume-based metrics

**Validation:** Regime completeness test — compute residual variance in gate performance after conditioning on the 4-axis vector. Substantial residual confirms an omitted dimension exists.

---

## Implementation Scope

### Layer 1: Regime Classifier (engine extension)

New module `engine/src/margin_engine/regime/` with:
- `MultiDimensionalRegimeClassifier` producing `RegimeState` 4-tuples
- Expanding-window percentile computation for volatility and credit axes
- Confidence metrics and out-of-validated-conditions detection
- Integration with `ReplayOrchestrator` to tag each rebalance with regime state

### Layer 2: Regime-Conditioned Ablation Metrics (ablation extension)

Extend `ReplayResult` and ablation runner to:
- Segment all performance metrics by regime state
- Compute per-regime Shapley values
- Track universe/sector survivor counts per regime
- Record threshold utilization distributions per regime

### Layer 3: Gate Characterization Module (new post-hoc analysis)

New module `engine/src/margin_engine/regime/characterization.py` with:
- Gate Regime Profile generation (PDR, VIF, FSR per gate per regime)
- Failure mode detection (threshold brittleness, signal inversion, universe collapse, pro-cyclicality)
- Bootstrap confidence intervals with serial correlation adjustment
- Crisis leave-one-out robustness tests
- Regime completeness test (residual variance)
- Safeguard cost-benefit analysis framework

### Layer 4: CLI & Reporting

Extend CLI with:
- `regime-characterize` command running full pipeline
- Structured JSON/CSV output for regime sensitivity surfaces
- Summary report with gate rankings and failure mode flags
