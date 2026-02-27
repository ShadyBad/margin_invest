# Metric Interference Analysis: Stacked Filter Architecture Audit

**Date:** 2026-02-27
**Scope:** Full stack — elimination filters, scoring tracks, ML override, orchestration
**Approach:** Static correlation audit with selective Shapley decomposition (Approach A+C)
**Output:** Analytical framework + concrete architectural recommendations

---

## 1. Conceptual Model of Metric Interference

### Definition

Metric interference occurs when combining multiple selection criteria produces a worse outcome than a proper subset of those criteria. "Worse" means: lower risk-adjusted returns, excessive universe compression, false elimination of high-quality candidates, or amplified sensitivity to noise in any single input.

The Margin Invest stack has three interference surfaces:

1. **Filter-filter** (within the 6 elimination gates)
2. **Gate-gate** (within each track's 4 multiplicative gates)
3. **Filter-track** (cross-layer: hard elimination removing assets that would score well)

### Interference Taxonomy

**Redundant filters (high correlation):** Two gates that fail on substantially the same companies. The survivor set after applying both is nearly identical to applying either alone — the second gate adds implementation complexity and false-rejection risk without improving selectivity.

Candidates in the current stack:

- **Altman Z-Score <-> Interest Coverage <-> Current Ratio.** Altman's formula is `6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)`. The WC/TA term directly encodes the current ratio. The EBIT/TA term correlates with interest coverage (EBIT/Interest x Interest/TA). A company failing Altman will frequently also fail one or both of the other two. Three gates may be doing the work of one.
- **FCF Distress <-> Altman Z-Score.** Altman penalizes negative working capital and low EBIT, which correlate with FCF distress. Companies with persistent negative FCF tend to have deteriorating Altman scores.

**Conflicting filters (opposing signal direction):** Two gates where the conditions that improve performance on one degrade performance on the other, creating contradictory selection pressure.

Candidates:

- **Liquidity minimum (market cap >= $300M) <-> Track B mispricing detection.** Deep value mispricings concentrate in smaller, less-liquid names. The liquidity gate explicitly excludes the segment where mispricing signals are strongest. Deliberate design choice (investability), but structurally weakens Track B's opportunity set.
- **FCF Distress (positive FCF >= 3 of 5 years) <-> Track C Efficient Growth.** High-growth companies frequently burn cash in early expansion. The growth rescue clause (OCF > 0 + gross margin > 40%) partially addresses this, but companies in the 30-40% gross margin range with heavy investment cycles are eliminated before Track C can evaluate them.

**Noise-amplifying filters:** Gates sensitive to accounting volatility, restatement timing, or data-provider artifacts, where stacking amplifies spurious rejection probability.

Candidates:

- **Beneish M-Score.** The 8-component formula uses ratio-of-ratios (current/prior period). A single restated quarter, asset write-down, or one-time item can produce a spike in DSRI, AQI, or TATA that pushes M-Score above -1.78. Stacking Beneish with FCF Distress means a company hit by a one-time charge can fail both gates from a single noise event.
- **Interest Coverage with EBIT.** EBIT is accrual-based and subject to depreciation schedule changes, impairment charges, and restructuring costs. A company with strong cash generation but a non-cash write-down can have negative EBIT temporarily, triggering the v2 auto-fail.

**Capacity-reducing constraints:** Gates that compress the opportunity set beyond what is justified by their risk-reduction benefit.

Current architecture: ~8,000 -> ~1,200-1,500 after 6 filters (80-85% rejection rate). Then Track A qualifies ~5-8% of survivors, Track B ~3-6%, Track C ~2-4%. After orchestration and the 50-position cap, final portfolio is <50 names from 8,000 — a 99.4% rejection rate. Each additional filter narrows the funnel multiplicatively.

### How Stacking Reduces Signal-to-Noise Ratio

Each gate has a false rejection rate `e_i` (probability of eliminating a company that should pass). Under independence, the probability of surviving all N gates while being a "true positive" is:

```
P(survive | true positive) = PRODUCT(1 - e_i) for i=1..N
```

With 6 filters and e = 0.05 each, P(survive) = 0.74 — 26% of good candidates are falsely eliminated. Under correlation (shared noise exposure, e.g., a restatement affecting Beneish + FCF + Interest Coverage simultaneously), the effective false rejection rate is higher than the independent case because failures cluster.

The SNR degradation is:

```
SNR_stack = SNR_best_single x correction_factor
correction_factor = (true_positive_survival) / (false_positive_survival)
```

If correlated noise causes true positives to cluster-fail while false positives still fail independently, the correction factor drops below 1.0 — stacking hurts selectivity.

---

## 2. Ablation Study Design

### Experimental Structure

Four phases, each building on the previous. All experiments run through the existing backtest engine.

**Phase 1: Single-gate baselines**

Run the backtest engine 6 times for elimination filters and 12 times for track gates (4 per track x 3 tracks), each time with only one gate active and all others disabled. This establishes the marginal value of each gate in isolation.

For elimination filters:

- Run 0 (control): No filters -> score all -> backtest
- Run 1: Liquidity only -> score all survivors -> backtest
- Run 2: Beneish only -> score all survivors -> backtest
- Run 3: Altman only -> score all survivors -> backtest
- Run 4: FCF Distress only -> score all survivors -> backtest
- Run 5: Interest Coverage only -> score all survivors -> backtest
- Run 6: Current Ratio only -> score all survivors -> backtest

For track gates (within each track, e.g., Track A):

- Gate A1 only: Moat Durability >= 2
- Gate A2 only: Compounding Power > 0.04
- Gate A3 only: Capital Allocation > 0.5
- Gate A4 only: Reverse DCF gap > 0.0

**Phase 2: Pairwise combinations**

C(6,2) = 15 filter pairs. For each pair, run full pipeline with only those two filters active. Measure whether the pair outperforms the better single-gate baseline. A pair that underperforms its best constituent exhibits destructive interference.

Within tracks: C(4,2) = 6 pairs per track, 18 total.

**Phase 3: Incremental stacking**

Add filters one at a time in the current pipeline order (Liquidity -> Beneish -> Altman -> FCF -> Interest -> Current). Record marginal change in every evaluation metric at each addition. Then repeat in reverse order and in ranked order (best single-gate first). If results are order-dependent, the architecture exhibits path dependence.

Stack sequences to test:

1. Current order (as deployed)
2. Reverse order
3. Best-single-first (ranked by Phase 1 Sharpe)
4. Worst-single-first

**Phase 4: Shapley value decomposition**

For the top 5 interference candidates identified in Phases 1-3, compute exact Shapley values:

```
phi_i = SUM_{S in N\{i}} [|S|!(N-|S|-1)!/N!] x [v(S U {i}) - v(S)]
```

where `v(S)` is the backtest performance metric with gate set S active. For the 6 elimination filters, full Shapley requires 2^6 = 64 coalition evaluations — tractable. For the full 18-gate stack, restrict to the top interference candidates.

### Evaluation Metrics

| Metric | What it measures | Why it matters |
|--------|-----------------|----------------|
| CAGR | Compound annual return | Raw performance |
| Sharpe ratio | Risk-adjusted return | Primary comparison metric |
| Max drawdown | Worst peak-to-trough | Tail risk from over/under-filtering |
| Sortino ratio | Downside risk-adjusted return | Distinguishes upside from downside vol |
| Hit rate | % of positions with positive return | Precision of the selection system |
| Universe size | Survivors at each stage | Capacity/diversification constraint |
| Turnover | Annual portfolio churn | Stability of the selection signal |
| Sector concentration | Max sector weight | Whether filters create unintended sector bets |

Primary metric for ablation comparison: Sharpe ratio. Secondary: CAGR and max drawdown as boundary checks.

### Time Horizon and Cross-Validation

**Backtest period:** Full available history (240 monthly snapshots). Split into:

- **In-sample (IS):** First 60% of months (~144 months / 12 years)
- **Out-of-sample (OOS):** Last 40% of months (~96 months / 8 years)
- **Expanding window:** 5-fold time-series cross-validation using expanding windows (no future data leakage). Each fold trains on months 1..T and evaluates on T+1..T+k.

**Regime stratification:** Partition backtest months into regime buckets (bull, bear, sideways) using trailing 12-month S&P 500 return (>10% = bull, <-10% = bear, else sideways). Report all metrics stratified by regime.

### Controls for Overfitting and Data Snooping

1. **Pre-registration:** Define the 6 primary comparisons (each filter's marginal contribution) before running. All other comparisons are exploratory and flagged as such.
2. **Multiple testing correction:** Bonferroni correction for the 15 pairwise comparisons and 64 Shapley coalitions. Report both raw and adjusted p-values.
3. **Effect size thresholds:** A marginal contribution must exceed +/-0.05 Sharpe to be considered material.
4. **Bootstrap confidence intervals:** 10,000 bootstrap resamples of monthly returns for each comparison. Report 95% CI on the difference.
5. **OOS confirmation gate:** No recommendation to add/remove a filter unless the effect is directionally consistent in both IS and OOS periods.

---

## 3. Detection of Interference

### Five Detection Tests

Each test produces a binary signal (detected / not detected) plus a continuous severity measure. A gate is flagged for review if it triggers any two of the five tests.

**Test 1: Performance degradation relative to best single gate**

```
delta_degradation = Sharpe_full_stack - Sharpe_best_single
```

- If delta < 0 with 95% bootstrap CI excluding zero: interference detected
- Severity = |delta| / Sharpe_best_single

**Test 2: Negative marginal contribution**

From Phase 3 incremental stacking:

```
MC_i = Sharpe_{filters 1..i} - Sharpe_{filters 1..i-1}
```

- If MC_i < -0.02 with bootstrap CI excluding zero: negative marginal contribution detected
- Severity = |MC_i|
- Cross-check: Must be negative in at least 2 of the 4 stacking orders. If negative in only one order, the effect is order-dependent, not intrinsic.

**Test 3: Pairwise destructive interaction**

```
Interaction_ij = Sharpe_{i+j} - max(Sharpe_i, Sharpe_j)
```

- If Interaction_ij < -0.03 with bootstrap CI excluding zero: destructive interaction detected
- Severity = |Interaction_ij|

Build a 6x6 interaction matrix for filters and 4x4 within each track. Additionally compute conditional failure correlation:

```
rho_fail(i,j) = corr(fail_i, fail_j)
```

High positive correlation (rho > 0.6) with destructive interaction confirms redundancy. High negative correlation with destructive interaction confirms conflict.

**Test 4: Universe collapse analysis**

Track survival count at each filter stage and compute:

Incremental kill rate:
```
Kill_i = (N_{i-1} - N_i) / N_{i-1}
```

Unique kill rate:
```
UniqueKill_i = |{tickers: fail_i AND pass_all_others}| / N_0
```

- UniqueKill_i < 1%: the filter is almost entirely redundant.
- Kill_i > 30% AND killed companies have higher subsequent returns than survivors: the filter is capacity-destroying.

Sector collapse check: If any sector drops below 10 survivors after all filters, that sector's representation is effectively eliminated.

**Test 5: Volatility injection without return improvement**

```
Vol_with_i = std(monthly returns, filter i active)
Vol_without_i = std(monthly returns, filter i removed)
Return_with_i = mean(monthly returns, filter i active)
Return_without_i = mean(monthly returns, filter i removed)
```

- If Vol_with_i > Vol_without_i AND Return_with_i <= Return_without_i: noise amplification detected

### Statistical Testing Protocol

1. Bootstrap difference test (10,000 resamples, 3-month block bootstrap to preserve autocorrelation)
2. Report: point estimate, 95% CI, bootstrap p-value
3. Multiple testing: Bonferroni-adjusted alpha = 0.05/K
4. Practical significance gate: statistical significance alone insufficient; effect must exceed materiality thresholds

### Cross-Layer Interference Detection

For each elimination filter `f` and each track `T`:

```
CrossInterference_{f,T} = Sharpe_{all_filters + T} - Sharpe_{all_filters_except_f + T}
```

If removing filter `f` improves Track T's Sharpe, that filter interferes with that track's opportunity set. Primary candidates: Liquidity <-> Track B, FCF Distress <-> Track C.

---

## 4. Structural Analysis

### Dimensionality of the Filter Space

Input dependency map across the 6 elimination filters:

| Financial Input | Liquidity | Beneish | Altman | FCF | Int. Cov. | Curr. Ratio |
|----------------|:---------:|:-------:|:------:|:---:|:---------:|:-----------:|
| Market cap / shares | X | | | | | |
| Volume / price bars | X | | | | | |
| Revenue / COGS | | X | | | | |
| Receivables | | X | X | | | |
| Total assets | | X | X | | | |
| Current assets | | | X | | | X |
| Current liabilities | | | X | | | X |
| EBIT | | | X | | X | |
| Interest expense | | | | | X | |
| Retained earnings | | | X | | | |
| Equity / liabilities | | | X | | | |
| Operating cash flow | | | | X | | |
| CapEx | | | | X | | |
| Depreciation | | X | | | | |
| Gross margin | | X | | | | |
| SGA | | X | | | | |
| Accruals | | X | | | | |

Key observations:

- **Liquidity** is structurally independent — market data, not financial statements. No shared inputs with any other filter. Cleanest gate in the stack.
- **Altman Z-Score** touches 5 balance sheet / income statement items, 3 of which overlap with other filters. Highest-dimensional single filter; partially subsumes the information in 3 other gates.
- **Interest Coverage** and **Current Ratio** each probe a single ratio that is already a component of Altman. Lower-dimensional projections of information Altman already encodes.
- **Beneish** and **Altman** share receivables and total assets, but Beneish uses ratio-of-ratio form (period-over-period change) while Altman uses level values. Shared inputs diverge in construction, reducing effective correlation.
- **FCF Distress** is semi-independent — operating cash flow and CapEx are not direct inputs to any other filter.

Effective dimensionality estimate: PCA on the 6 filter pass/fail vectors would likely reveal 3-4 significant components: (1) market-data liquidity, (2) balance-sheet solvency (Altman/Current Ratio/Interest Coverage cluster), (3) cash generation (FCF), (4) earnings quality (Beneish). The architecture has 6 gates but approximately 4 independent information dimensions.

### Opportunity Set Compression

Multiplicative compression at three levels:

```
Level 1 (Elimination):  8,000 -> 1,200-1,500  (~82% rejection)
Level 2 (Track gates):  1,200 -> ~60-120 qualifiers  (~92% rejection of survivors)
Level 3 (Position cap):  60-120 -> 50 max  (~50% rejection of qualifiers)
```

Cumulative pass rate: ~0.6% of the starting universe enters the portfolio.

The solvency cluster (Altman + Interest Coverage + Current Ratio) may be applying 3 gates where 1 would suffice. If Altman alone eliminates 95% of the companies that any of the three eliminates, the other two contribute <5% incremental filtering at the cost of additional false rejection risk.

Track-level: Each track requires all 4 gates for HIGH/EXCEPTIONAL conviction. With multiplicative scoring, a single weak gate zeros out the track score. Track B is particularly vulnerable — the quality floor gate (ROIC >= 8%) eliminates deep-value turnarounds with asymmetric mispricing but temporarily depressed ROIC.

### Ordering Effects and Path Dependence

The elimination pipeline runs all 6 filters with no short-circuit, so filter ordering does not affect which companies survive. Strong design choice that eliminates path dependence at the elimination layer.

Path dependence exists at two other points:

1. **Track orchestration promotion rules.** Checks "all_three" before "both" before "compounder_growth" before "single." A company qualifying for Tracks A and C is promoted differently than Tracks B and C (no special promotion). The order of evaluation in promotion rules affects final conviction and position sizing.

2. **ML override sequencing.** ML override runs after track orchestration on the post-promotion conviction level, not per-track levels. If promotion miscategorizes a company, ML inherits the wrong baseline.

3. **V2 filter rescue clause interactions.** A company with improving FCF trend (rescued by FCF filter) but negative most-recent EBIT (auto-failed by Interest Coverage) is eliminated despite the improving trajectory the FCF rescue was designed to preserve.

### Cross-Layer Structural Interference

The boundary between hard gate (elimination) and soft gate (scoring track) is the most consequential structural decision. Currently:

- Hard gates are binary with no gradient. Z'' = 1.09 eliminated; Z'' = 1.11 passes. The 0.02 difference carries infinite weight.
- Track gates produce continuous multiplicative scores. Failing one track gate zeros that track but other tracks remain available.
- No information flows from elimination to scoring. A company barely passing Beneish (M-Score = -1.80) is scored identically to M-Score = -4.0. Near-miss information is discarded.

This creates a structural discontinuity: the elimination layer destroys gradient information that the scoring layer could use.

---

## 5. Decision Framework

### Four Actions, Five Decision Criteria

For each gate, ablation results map to one of four actions. First matching criterion determines the action.

**Action 1: Remove the gate**

- UniqueKill rate < 1%, AND
- Marginal Sharpe contribution negative or indistinguishable from zero in both IS and OOS, AND
- Shapley value in bottom quartile

**Action 2: Merge gates into a composite**

- Pairwise failure correlation rho > 0.6, AND
- Both gates have positive individual Sharpe contribution, AND
- The pair shows destructive interaction (Interaction_ij < -0.03)

Application: If Altman and Interest Coverage are redundant but each individually valuable, replace both with a single "solvency composite" — one continuous score, one threshold.

**Action 3: Convert from hard gate to scoring input**

- Positive marginal contribution to return but negative to Sharpe (adds return, adds more volatility), OR
- Regime-dependent performance, OR
- UniqueKill set contains companies with above-median subsequent returns

Primary candidate: FCF Distress -> Track C input. Growth companies with negative FCF but strong unit economics are killed before Track C can evaluate them. Converting FCF health to a continuous penalty within Track C allows weighing FCF weakness against growth strength.

Secondary candidate: Beneish M-Score -> Track A/B input. Rather than binary elimination at -1.78, M-Score enters as a continuous quality discount.

**Action 4: Retain as-is**

- Positive marginal Sharpe in both IS and OOS, AND
- Shapley value in top half, AND
- Low failure correlation with other gates (rho < 0.3), AND
- No regime dependence

Liquidity is the most likely retention candidate — structurally independent, enforces investability.

### Decision Matrix

| Signal | Action |
|--------|--------|
| Redundant + no marginal value | Remove |
| Redundant + individually valuable + destructive pair | Merge |
| Valuable signal + cliff-effect harm + kills good candidates | Convert to scoring input |
| Independent + stable + positive contribution | Retain |
| Regime-dependent value | Convert to scoring input with regime-aware weighting |
| Negative Shapley + negative marginal + negative pairwise | Remove (strongest case) |

### Simplicity Bias

When ablation evidence is ambiguous — marginal contribution near zero, CI spanning zero, inconsistent across IS/OOS — the default action is **remove**. The burden of proof is on each gate to justify its inclusion. This follows from:

1. Each additional gate increases complexity, maintenance burden, and false rejection risk.
2. More gates = more parameters = more overfitting opportunity. Fewer gates generalizes better.
3. Each gate requires explanation to stakeholders. Gates without demonstrable value erode trust.

Exception: gates with regulatory or fiduciary justification independent of backtest performance (e.g., liquidity for investability, Beneish for fraud screening). These are retained on structural grounds but documented as "structural constraints" distinct from "performance-enhancing filters."

### Cross-Layer Decision Rule

If removing elimination filter `f` improves Track T's Sharpe by more than 0.05 in OOS, and filter `f` has a natural continuous form, convert `f` from hard elimination to continuous Track input. The elimination layer should contain only investability constraints and catastrophic risk exclusion — not quality or performance filters that scoring tracks handle better as continuous signals.

---

## 6. Hidden Assumptions and Risks

### Survivorship Bias

The ticker universe is drawn from current index constituents. Companies delisted, acquired, or bankrupt before the backtest start date are absent. This removes the worst outcomes from the "no filter" baseline, making filters appear less valuable — the companies filters would have caught were already removed by history.

In the ablation study, the no-filter baseline benefits from this bias, deflating apparent filter contribution for catastrophic-risk gates (Altman, Beneish).

Mitigation: Include delisted/bankrupt tickers with terminal return = -100% if available. If not, document the bias and apply a qualitative premium to catastrophic-risk filters that backtest metrics cannot capture.

### Lookahead Bias

Current thresholds (Beneish <= -1.78, Altman >= 1.1, etc.) were calibrated on academic studies using historical data. Applying them to an overlapping backtest period inflates apparent performance.

V2 rescue clauses (growth rescue, quick ratio rescue) were designed after observing which companies were falsely eliminated — implicitly fit to the known universe. Test rescue clauses separately (with/without) to measure OOS value vs. overfitted patches.

The ablation study itself is the biggest lookahead risk. IS/OOS split and pre-registration are primary defenses. Hard rule: no filter removed based on IS results alone.

### Regime Dependence

The available backtest period contains limited regime diversity:

| Regime | Period | Characteristics |
|--------|--------|-----------------|
| Post-GFC recovery | 2010-2019 | Low rates, low defaults, rising markets |
| COVID crash + recovery | 2020-2021 | V-shaped, unprecedented monetary response |
| Rate hiking cycle | 2022-2024 | Rising rates, valuation compression |
| Normalization | 2025-2026 | Rate stabilization |

Missing regimes: sustained bear market (2000-2002), inflationary spiral, credit crisis with cascading defaults. Filters like Altman and Interest Coverage are designed for these missing regimes.

Mitigation:

1. Stress test simulation: synthetically shock financial inputs (EBIT -50%, interest expense +100%, current liabilities +30%) and measure how many current survivors would fail each filter under stress.
2. Asymmetric loss function: weight downside outcomes (drawdown, max loss) more heavily than upside when evaluating marginal contribution.

### Overfitting to Historical Structure

The system has ~40+ tunable parameters. With ~240 monthly snapshots and ~50 positions (~12,000 position-months), the observation-to-parameter ratio is 300:1 — adequate but not generous.

The ablation study produces ~100 performance comparisons. Probability of at least one spurious "significant" result at alpha = 0.05 is ~99.4%. Materiality thresholds and OOS confirmation are the primary defenses.

### False Confidence from Complexity

A 6-filter elimination pipeline followed by a 3-track conviction engine with ML override feels rigorous. The complexity itself generates confidence independent of whether each component adds value.

Manifestations:

- The solvency cluster creates an impression of thorough balance sheet analysis. If Altman alone captures 95% of the signal, the other two add complexity-confidence without proportional value.
- Track B's 4-gate structure requires simultaneous satisfaction. Joint probability may be so low that Track B rarely qualifies anyone — not selectivity but capacity destruction.
- V2 rescue clauses accumulate conditional branches, suggesting underlying thresholds may be miscalibrated rather than that rescues are the correct fix.

Mitigation: The ablation study directly measures whether complexity translates to performance. The simplicity bias in the decision framework (Section 5) is the structural defense.

### Data Quality Risks

Financial statement data may contain NaN values, restatements, and timing mismatches affecting filter outcomes non-uniformly. Some filters return INCONCLUSIVE on missing data, others use defaults, creating non-uniform data quality across the universe.

Mitigation: Log INCONCLUSIVE rate per filter per period. Exclude periods where INCONCLUSIVE rate exceeds 10%. Run sensitivity check with INCONCLUSIVE-as-pass vs. INCONCLUSIVE-as-fail.

---

## Appendix: Architecture Reference

### Current Elimination Filters (6 active, 1 dormant)

| # | Filter | Threshold | Key Input | Sector Adjustments |
|---|--------|-----------|-----------|-------------------|
| 1 | Liquidity | Market cap >= $300M, tiered dollar volume | Market data | Excludes Financials, Real Estate; Utilities $1B |
| 2 | Beneish M-Score | <= -1.78 | Income/Balance/CF (2 periods) | None |
| 3 | Altman Z-Score | >= 1.1 | Balance + Income | Exempt: Utilities |
| 4 | FCF Distress | Positive FCF >= 3 of 5 years (v2) | Cash flow (multi-period) | Cyclical: 2 of 5 |
| 5 | Interest Coverage | >= 1.5 default (v2: 3-yr median) | Income (multi-period) | Tech: 5.0, Utilities: 1.2 |
| 6 | Current Ratio | >= 0.8 default (v2: 3-yr median) | Balance (multi-period) | Utilities: 0.6 |
| 7 | Mediocrity Gate | ROIC > 8%, margins, FCF, revenue | History (multi-period) | Energy/Utilities adjusted |

### Scoring Tracks (3 tracks, 4 gates each)

**Track A (Compounder):** Moat Durability >= 2, Compounding Power > 0.04, Capital Allocation > 0.5, Reverse DCF gap > 0.0

**Track B (Mispricing):** Ensemble Valuation (converged + discount), Downside Protection (max loss < 50%), Catalyst Strength > 40th percentile, Quality Floor (ROIC >= 8%)

**Track C (Efficient Growth):** Growth Efficiency (Rule of 40 >= 30), Unit Economics (stable margins + leverage), Capital Efficiency (incremental ROIC > WACC), Growth Durability (deceleration >= -5pp, TAM >= 3x)

### Orchestration

Promotion: all_three > both > compounder_growth > single > neither
ML override: upgrade/downgrade conviction if model qualifies (IC >= 0.15)
Position cap: 50 maximum positions

### Pipeline Flow

```
Universe (~8,000)
    |
    v
6 Elimination Filters (all run, no short-circuit)
    |
    v
Survivors (~1,200-1,500)
    |
    v
Track A (Compounder) | Track B (Mispricing) | Track C (Efficient Growth)
    |                         |                          |
    v                         v                          v
Orchestration (promotion rules)
    |
    v
ML Override (optional)
    |
    v
Position Sizing + Cap (50 max)
    |
    v
Final Portfolio
```
