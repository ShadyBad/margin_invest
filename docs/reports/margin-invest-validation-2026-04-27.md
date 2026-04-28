# Margin Invest Engine Validation Audit — 2026-04-27

**Audit run:** fc33ea0a-5f55-448c-820d-6f65b4607e40
**Engine git sha:** `116bfc28a49cd15c2d80b734c9eb3efb8f523f71`
**Engine config sha:** `5b384b15c7232721c17490710ce19a61e6c748c8b10f0da7cb36865f1b3a8d69`
**Manifest content hash:** `fe376c43b2bc76b5e2ae57c0a45d84b224699727cff874dacae9071385e7c9b7`
**R2 bundle:** `(local bundle, R2 not provisioned in production)`

---

## 1. Executive Summary

- **Excess CAGR vs SPY (net of frictions):** **0.00%**
- **Sharpe ratio (net):** 0.00
- **Maximum drawdown:** 0.0%
- **Cohorts evaluated:** 135 (rebalance: monthly)
- **Verdict:** (populated by Stage 1; use excess_cagr to write a one-line verdict)

## 2. Methodology + Replication Deviations from Production

This audit runs the V4 scoring engine *as it exists at audit run date* against
PIT financial snapshots and PIT prices, NOT a replay of historical production
score outputs. See **§10 (Replication Choices)** in the design spec for the
full deviation table; the most consequential deviations are reproduced here:

| Choice | Audit | Production | Why |
|---|---|---|---|
| Score regeneration | Re-run V4 with current code at each cohort date | Production used engine V_T at time T | Critical: this audit measures the *current* engine. |
| Rebalance frequency | Monthly | Continuous | Standard backtest discipline. |
| Position cap | 50 | Variable (Kelly-bounded) | End-user portfolio constraint. |
| Selection | exceptional+high | Same | Match. |

## 3. Component Inventory

(See spec §9 for the canonical inventory table.)

## 4. Performance Metrics + Risk-Adjusted Verdict

| Metric | Value |
|---|---|


## 5. Component Attribution

Sorted descending by walk-forward tercile spread. Both methods reported
side-by-side; rows where they disagree are flagged.

| Component | Method | Window | n_top | n_bottom | Spread | Rank-IC | CI lo | CI hi | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|


## 6. Conviction Calibration

| Tier | n | Mean alpha (60d) | Sharpe | Sortino | Max DD | ANOVA p | Monotonic? |
|---|---|---|---|---|---|---|---|


## 7. Live Forward Track Record (60-day, in-progress)

> **Statistical power note:** The 60-day window is too short to claim
> validation. These numbers are *operational* (did the live engine ship
> something?) not *scientific* (does the engine work?). For the latter, see
> §4 walk-forward results.

Mean candidate alpha vs SPY across closed windows:

- 30-day: 0.0293 (2141 candidates)
- 60-day: 0.0103 (565 candidates)

## 8. Kill List + v2 Scoring Formula Proposal

### Kill List



### v2 Reweight Proposal

| Component | Current weight | Spread | Action | Proposed weight |
|---|---|---|---|---|


## 9. Statistical Power Disclaimer

### Coverage of the V4 scoring engine

This audit reconstructs production V4 inputs from PIT tables. Some inputs are
NOT PIT-reconstructable and are neutral-defaulted at every cohort date. The
audit therefore measures the **PIT-reconstructable subset** of V4, not the
complete production engine. Readers must weigh findings accordingly.

**PIT-sourced fields (audit measures these accurately):**
ticker, history, latest_period, profile, current_price (adj_close),
current_fcf_per_share, sustainable_growth_rate, dcf_iv,
profile.market_cap, profile.avg_daily_volume.

**Neutral-defaulted (audit does NOT measure these — production may behave differently):**
short_interest_percentile, analyst_divergence, eps_revision_strength,
momentum_percentile, beta, accumulation_percentile, sue_percentile,
all insider cluster fields (cluster, total_buy, first_buy, drawdown),
`shiller_cape` (constant 30.0 stub), buyback_yield, insider_ownership_pct,
sbc_pct, recent_acquisition_count, fundamental_trajectory, high_52w,
**all Track C growth fields** (revenue_growth_rate, fcf_margin,
gross_margin_current/3yr_ago, opex_growth_rate, incremental_roic,
revenue_deceleration, tam_headroom).

**Implication for findings:**
- **Track A (compounder cascade):** measured robustly — most inputs are PIT-sourced.
- **Track B (mispricing cascade):** measured partially — DCF-related inputs PIT-sourced; momentum/beta/short-interest defaulted.
- **Track C (efficient-growth cascade):** **effectively not measured by this audit.** All growth-trajectory inputs are zeroed. Track C's contribution to `excess_cagr` here represents the engine's behavior when Track C is null, not when production-style Track C inputs are populated.

A v2 proposal that downweights Track C based on this audit alone would be
unsafe — the audit cannot distinguish "Track C carries no signal" from
"Track C signal is unmeasurable in this audit." A separate, non-PIT
audit (or a richer PIT pipeline that captures growth-trajectory inputs)
is required to make that judgment defensibly.

### Statistical-method disclaimers

- Each component-attribution row required `n ≥ 30` per tercile to publish a
  verdict. Below threshold: verdict = `underpowered`.
- Bootstrap 95% CI computed with 1000 resamples (deterministic seed=42).
- Holm-Bonferroni multiple-comparisons correction applied across the
  composite-contributing component family (24 components).
- Rank-IC reported alongside tercile spread for cross-method check.
  Disagreement → verdict = `demote`, not `cut`.
- This audit does NOT validate: regime-conditioned performance, non-SPY
  benchmarks, conviction-tier threshold accuracy, post-audit engine changes.

## 10. Reproducibility Footer

- **Engine git sha:** `116bfc28a49cd15c2d80b734c9eb3efb8f523f71`
- **Engine config sha:** `5b384b15c7232721c17490710ce19a61e6c748c8b10f0da7cb36865f1b3a8d69`
- **Manifest content hash:** `fe376c43b2bc76b5e2ae57c0a45d84b224699727cff874dacae9071385e7c9b7`
- **R2 bundle:** `(local bundle, R2 not provisioned in production)`
- **Command line:** `railway run python -m margin_api.cli audit-engine --report-date 2026-04-27 --r2-prefix audits/2026-04-27/`

To re-verify any number in this report, fetch the bundle from R2, validate
each CSV's sha256 against `manifest.json`, and recompute. Bundle is
content-addressable; identical inputs produce identical hashes.
