# Self-Healing Data Layer Design

## Status

Approved design. Pending implementation plan.

## Motivation

The Margin Invest pipeline ingests financial data from external providers (yfinance, FMP, SEC EDGAR) and scores it through a deterministic elimination + factor-scoring pipeline. Data quality failures — stale values, parse errors, provider outages, silent format changes — propagate directly into scores. The system currently has Level 0 defenses (NaN sanitization, provider circuit breakers, ticker quarantine) but no statistical detection or correction of anomalous data points between ingest and scoring.

This design introduces a validation and correction layer that detects data quality degradation and applies deterministic corrections before feature engineering, trading slightly increased latency for improved reliability.

**Driving context**: Both active data quality issues (yfinance NaN spikes, stale carry-forward) and proactive architecture for scaling to more tickers and adding PIT data providers.

## 1. Conceptual Model: Healing vs. Distortion

"Self-healing" obscures a fundamental epistemological problem. The system cannot distinguish between data that is *wrong* (measurement failure) and data that is *surprising* (genuine economic change). These are operationally identical at observation time.

### Three Categories of Deviation

| Category | Signal Type | Correct Action | Risk of Auto-Correction |
|---|---|---|---|
| Measurement failure | Provider error, stale data, parse failure | Correct or substitute | Low |
| Regime shift | Structural change in fundamentals | Preserve and flag | **High** |
| Tail event | Extreme but real observation within existing regime | Preserve | Moderate |

### Design Principle

The correction layer is **asymmetrically conservative**: aggressive on clear measurement failures (impossible values, stale data, provider errors), reluctant on statistical outliers. The burden of proof for "this observation is wrong" is high, because the cost of smoothing a real regime shift exceeds the cost of scoring one noisy data point.

Financial data is heavy-tailed by nature. A correction layer that assumes Gaussian normalcy will systematically destroy the observations that matter most for risk management.

## 2. Pipeline Placement

The layer sits **post-storage, pre-feature-engineering** — between raw `FinancialData` (JSONB in DB) and normalized `FinancialPeriod` objects consumed by the engine. It intercepts after `normalize_income_statement()` / `normalize_balance_sheet()` / `normalize_cash_flow()` and before `build_financial_period()`.

Rationale:
- Raw data is never modified (auditability by default)
- Normalization has already resolved field-name inconsistencies
- Detection operates on typed Pydantic models, not raw JSON
- Every downstream consumer (filters, factors, backtesting) gets corrected data without per-consumer logic

## 3. Detection Layer

Three tiers, ordered from cheapest/most certain to most expensive/most ambiguous.

### Tier 1: Deterministic Impossibility Checks

Zero false positives. Logical constraints no valid financial statement can violate:

- Revenue < 0 for non-financial companies
- `shares_outstanding == 0` or `None`
- `total_assets < total_liabilities + total_equity` beyond rounding tolerance
- Current period identical to prior period across all fields (stale carry-forward)
- Price data with zero volume on a trading day
- Timestamps outside expected range (future dates, pre-IPO dates)

Severity: `IMPOSSIBLE`. Unambiguous measurement failures.

### Tier 2: Univariate Robust Outlier Detection

Per-field MAD (Median Absolute Deviation) against rolling per-sector distributions. MAD preferred over FAST-MCD because:

- FAST-MCD requires n > p (more observations than dimensions) — with 50-200 tickers per sector and 30+ fields, the multivariate case is poorly conditioned
- MAD has a 50% breakdown point
- Computationally trivial (no iterative optimization)
- Financial fields lack the tight joint distributions that MCD would exploit

Detection rule: Flag when `|x - median| / MAD > k`

| Field Class | k Threshold | Rationale |
|---|---|---|
| Margins (gross, net, FCF) | 6.0 | Bounded, true outliers rare |
| Growth rates (revenue, earnings) | 8.0 | Heavy-tailed, regime shifts common |
| Leverage ratios (D/E, coverage) | 7.0 | Sector-dependent, legitimate extremes |
| Price returns | 10.0 | Very heavy-tailed, almost never correct to clip |

Severity: `OUTLIER`. Eligible for correction but not certain.

### Tier 3: Cross-Sectional Consistency Checks

Compare a ticker's current-period values against sector peers AND its own trailing 8-quarter history. Flag when:

- Value deviates from ticker's own trailing median by >3× its own historical MAD **AND** sector peer median hasn't moved comparably
- Revenue/earnings growth exceeds anything in ticker's history by >2× **AND** no corroborating earnings data (SUE)
- A ratio is >5× sector median when it was <2× last quarter

The AND clauses are regime-shift protection: if the whole sector is moving, the observation is likely real.

Severity: `SUSPICIOUS`. Requires strongest correction justification.

### Explicitly Excluded Detection Methods

- **Multivariate anomaly detection (FAST-MCD, robust covariance)**: Sample sizes too small relative to dimensionality. Near-singular covariance matrices require regularization with unauditable hyperparameters.
- **Learned detection models (autoencoders, isolation forests)**: Black-box anomaly scores are unacceptable in a system claiming deterministic transparency. Every flag must be explainable.
- **Time-series structural break detection (CUSUM, Bai-Perron)**: Quarterly, non-stationary, variable-lag financial data requires substantial adaptation. Tier 3 achieves rough break detection without the machinery.

## 4. Correction Mechanisms

### Correction Hierarchy

Applied in strict priority order. Each level attempted only if the previous is inapplicable.

**Level 1: Secondary Source Substitution**

Fetch the same field from the next provider in the fallback chain. Accept if:
- Secondary source returns non-null
- Secondary value is not itself flagged by Tier 1/2
- Secondary value within 20% of primary OR primary was flagged `IMPOSSIBLE`

Risk: Source hierarchy introduces latent bias if providers systematically disagree. Mitigated by logging substitution source/magnitude and periodic audits for provider dominance in corrections.

**Level 2: Carry-Forward with Decay**

Use ticker's most recent valid observation with confidence decay:

```
corrected_value = last_valid_value
correction_confidence = max(0.3, 1.0 - (quarters_stale * 0.15))
```

Below 30% confidence (>4 quarters stale), mark `UNAVAILABLE` rather than correct. Risk: pro-cyclical (optimistic during deterioration, pessimistic during improvement). Acceptable for gap-filling but dangerous as dominant correction mode.

**Level 3: Cross-Sectional Imputation**

Replace with sector median. Most aggressive correction.

**Excluded fields** (never L3-imputed — ticker excluded from scoring instead):
- `revenue`, `net_income`, `operating_cash_flow`, `free_cash_flow`
- `total_assets`, `total_liabilities`, `total_equity`, `total_debt`
- `shares_outstanding`, `market_cap`
- `price_history`

These represent the company's identity. Sector-median substitution produces a score for a hypothetical average company.

### Winsorization: Rejected at Data Layer

Winsorization is inappropriate as a data correction mechanism. Clamping raw financial fields to the 95th percentile prevents elimination filters from detecting extreme leverage, distress, or manipulation. Percentile ranking already compresses factor ranges. If winsorization is ever needed, it belongs inside individual factor computations, not the data layer.

### Correction Confidence Propagation

Every correction produces a `CorrectionRecord`:

```
field: str
original_value: float | None
corrected_value: float
correction_method: L1_SUBSTITUTE | L2_CARRY_FORWARD | L3_SECTOR_MEDIAN
correction_confidence: float (0.0 - 1.0)
source: str | None
detection_tier: IMPOSSIBLE | OUTLIER | SUSPICIOUS
detection_detail: str
```

Scoring functions can optionally discount factors computed from corrected inputs by `(1 - correction_confidence)`.

### Correction Amplification

If revenue is corrected and prior-period revenue was also corrected (differently), derived `revenue_growth` may be distorted more than either individual correction. The system computes and logs `derived_correction_impact`: percentage difference between derived values from corrected vs. original inputs.

## 5. Feedback & Reflexivity Risks

### Failure Mode 1: Masking Upstream Degradation

If a provider begins returning systematically degraded data, the correction layer will "fix" it, and data quality metrics remain stable while inputs become fictional.

Mitigation: Track correction rates per provider per field. Alert when any provider's correction rate exceeds rolling baseline by >2σ.

### Failure Mode 2: Illusion of Stability

Never report corrected data as "valid." Monitoring must distinguish three states: `VALID`, `CORRECTED`, `EXCLUDED`. Headline metric is always the raw validity rate.

### Failure Mode 3: Historical Distribution Reinforcement

Corrections narrow observed distributions → MAD shrinks → thresholds tighten → more corrections → distributions narrow further. Positive feedback loop.

Mitigation: **Detection thresholds computed from raw (uncorrected) data only.** Rolling sector distributions used for Tier 2/3 must never include corrected values. Non-negotiable.

### Failure Mode 4: Pro-Cyclical Smoothing During Crises

During market crises, many metrics move simultaneously to historical extremes. The correction layer would refuse to see the crisis until rolling distributions absorb it.

Mitigation: **Sector breadth circuit breaker.** When >15% of tickers in a sector are simultaneously flagged on overlapping fields, suspend corrections for the entire sector. `sector_breadth_suspension_threshold = 0.15`.

### Failure Mode 5: Delayed Regime Change Detection

Structural shifts are smoothed in their early stages because early signals look like outliers.

Mitigation: Breadth circuit breaker + `regime_shift_suspicion` metric (tickers with Tier 3 flags persisting 2+ consecutive periods).

## 6. Auditability & Reproducibility

### Determinism Contract

Given the same raw inputs AND the same correction configuration version, produce the same corrected outputs and therefore the same scores.

### Correction Event Logging

Every correction produces a `CorrectionEvent` record:

```
correction_id: UUID
asset_id: int
period_end: date
field_path: str
detection_tier: IMPOSSIBLE | OUTLIER | SUSPICIOUS
detection_detail: str
original_value: float | None
corrected_value: float
correction_method: L1 | L2 | L3
correction_source: str
correction_confidence: float
correction_config_version: str
sector_distribution_snapshot: {median, mad, n_observations, period}
created_at: datetime(tz=True)
scoring_run_id: UUID | None
```

### Raw Data Preservation

Raw `FinancialData` table is never modified. Corrections stored as an **overlay table** keyed by `(asset_id, period_end, field_path)`. Scoring reads the corrected view; audit accesses the original.

### Deterministic Replay Requirements

1. **Correction config versioning**: Every threshold/rule change is a new semver version, recorded on every `CorrectionEvent`
2. **Distribution snapshots**: Per-sector, per-field rolling stats (median, MAD, n) snapshotted at each scoring run, immutable
3. **Replay mode**: Correction layer accepts optional `as_of_date` + `config_version`, uses historical distributions and rules

For backtesting: pre-compute correction overlays rather than re-running detection at every historical timestep.

### Correction Configuration

Versioned config artifact stored in database:

```yaml
correction_config:
  version: "1.0.0"
  detection:
    tier1_checks: [negative_revenue, zero_shares, identity_violation, stale_duplicate, ...]
    tier2_mad_thresholds:
      margins: 6.0
      growth_rates: 8.0
      leverage_ratios: 7.0
      price_returns: 10.0
    tier3_self_history_multiplier: 3.0
    tier3_sector_corroboration_required: true
  correction:
    excluded_fields: [revenue, net_income, operating_cash_flow, free_cash_flow,
                      total_assets, total_liabilities, total_equity, total_debt,
                      shares_outstanding, market_cap, price_history]
    carry_forward_max_quarters: 4
    carry_forward_decay_rate: 0.15
    cross_sectional_min_confidence: 0.3
    substitution_tolerance: 0.20
  circuit_breakers:
    sector_breadth_threshold: 0.15
    consecutive_flag_regime_shift: 2
    variance_compression_floor: 0.85
```

## 7. System-Level Trade-offs

### Latency

| Operation | Cost | Notes |
|---|---|---|
| Tier 1 checks | <1ms | Field-level bounds |
| Tier 2 MAD | 5-10ms | Lookup + deviation per field |
| Tier 3 cross-sectional | 20-50ms | Sector peers + trailing history |
| Correction application | 1-5ms | L1 may add provider fetch |
| Audit logging | 2-5ms | Async, non-blocking |

Per-ticker: ~30-70ms (normal path), ~200ms (L1 substitution). Universe-wide: ~5-12 seconds per 50-ticker batch. Negligible relative to rate-limited ingest.

Backtesting: pre-computed correction overlays, not inline re-detection.

### Complexity

Current data path: ingest → sanitize → normalize → score (4 stages). With correction layer: ingest → sanitize → normalize → detect → correct → audit-log → score (7 stages). Nearly doubles conceptual surface area. Net positive only with rigorous testing: golden-value tests per detection tier and correction level, property-based tests for distributions, integration tests for end-to-end determinism.

### Over-Correction Guard

Diagnostic: `std(corrected) / std(raw)` per field per sector. If ratio < 0.85 consistently, the correction layer is removing real variance. Log `VARIANCE_COMPRESSION` warning and review thresholds.

### Human-in-the-Loop Escape Valves

Auto-correction yields to flagging-only in narrow edge cases:
- Tier 3 flags on load-bearing excluded fields where only L3 is available → exclude ticker from scoring
- Sector breadth suspension events → flag for review
- Persistent Tier 3 flags (3+ consecutive periods) → flag for investigation

### ML Training

ML model training consumes **raw data, not corrected data**. Models should learn the actual distribution of financial data. Corrected data would train on an artificially clean distribution never encountered in live inference.

## 8. Hidden Assumptions & Statistical Pitfalls

### Lookahead Bias in Historical Distributions

Distribution snapshots may include data that wasn't available at the nominal date (reporting lag, restatements). Live scoring is unaffected. Backtesting replay must use stored PIT distribution snapshots, not retroactively recomputed ones. Early backtest periods before the correction layer existed pass raw data through uncorrected.

### Survivorship Bias in Secondary Sources

Secondary providers may lack data for delisted/merged/bankrupt companies. Corrections succeed more often for healthy companies than distressed ones. Track correction success rate by ticker health status; disclose in backtest methodology.

### Drift Misclassification

With 8-quarter rolling windows, a 2-3 quarter trend looks like a step change. Tier 3 may flag legitimate gradual deterioration.

Mitigation: **Trend-awareness adjustment.** If last 3 observations show monotonic movement, detection threshold widens by 50% (`k * 1.5`). Consistent directional moves are more likely drift than noise.

### Heavy-Tail Underestimation

For Student-t distributed data (~4 df), a 6-MAD deviation is ~10× more probable than Gaussian assumptions imply. Actual false positive rates may exceed theoretical expectations.

Mitigation: Run detection in observation-only mode for 2-3 quarterly cycles. Measure empirical flag rates. Loosen thresholds if any field exceeds 2% flag rate.

### Adversarial Data

A compromised provider could inject values within MAD thresholds but systematically biased. Cross-provider reconciliation is the primary defense. For load-bearing fields where providers disagree by >20%, flag for review. SEC EDGAR XBRL is least manipulable (regulatory filings with legal liability) and should serve as ground truth when available.

### Correction-Induced Correlation

L3 sector-median imputation mechanically increases correlation between corrected tickers and sector peers. Multiple tickers receiving the same median value creates artificial co-movement.

Mitigation: Exclude L3-corrected values from correlation computations. Correlation service should consume raw or L1/L2-corrected data only.

## 9. Migration Path

### Existing Level 0 Mechanisms (unchanged)

- **NaN sanitization**: Stays at ingest (parse-level concern)
- **Provider circuit breakers**: Stay (network failure gating)
- **Ticker quarantine**: Stays (ticker-level ingest health)

### Migration

- **consistency_flags**: Subsume into Tier 1 detection with structured output. Deprecate ad-hoc dict entries over time.

### Validation Phase (Recommended)

Before promoting to the primary scoring path, run the correction layer as a **shadow pipeline** (Approach C from design exploration): score on both raw and corrected data, measure divergence rates and magnitudes. Promote to primary path once correction behavior is characterized across 2-3 full quarterly cycles.

## 10. Architecture Diagram

```
Raw Data (FinancialData table, never modified)
  │
  ▼
┌─────────────────────────────────────────────┐
│         SELF-HEALING DATA LAYER             │
│                                             │
│  ┌─────────────┐                            │
│  │  Detection   │                           │
│  │  Tier 1: Impossible values               │
│  │  Tier 2: MAD outliers (per-field/sector) │
│  │  Tier 3: Cross-sectional + history       │
│  └──────┬──────┘                            │
│         │ flags                             │
│  ┌──────▼──────┐    ┌───────────────────┐   │
│  │  Correction  │───▶│  Audit Log        │  │
│  │  L1: Substitute   │  (CorrectionEvent │  │
│  │  L2: Carry-fwd    │   per mutation)   │  │
│  │  L3: Sector med   │                   │  │
│  └──────┬──────┘    └───────────────────┘   │
│         │                                   │
│  ┌──────▼──────┐                            │
│  │  Circuit     │                           │
│  │  Breakers    │                           │
│  │  • Breadth suspension (>15% sector)      │
│  │  • Trend-aware threshold widening        │
│  │  • Variance compression guard (<0.85)    │
│  └──────┬──────┘                            │
└─────────┼───────────────────────────────────┘
          │ corrected FinancialPeriod
          ▼
  Existing Pipeline (filters → factors → percentile rank → V4 score)
```

## Irreducible Risks Accepted

- Will sometimes smooth away legitimate tail events
- Gradual deterioration will be partially delayed through correction
- Correction-induced correlation may distort covariance when L3 used
- Data quality metrics will appear healthier than reality

These are structural properties of any automatic correction system, mitigated but not eliminated by the design.
