# Margin Invest Engine Validation Audit — Design Spec

**Date:** 2026-04-27
**Status:** Draft — awaiting user review before implementation planning
**Type:** Design specification (not implementation plan)
**Next step after approval:** invoke `superpowers:writing-plans` to produce the implementation plan

---

## 1. Goal

Answer the question, with regulator-grade evidence: **does Margin Invest's scoring engine actually beat passive SPY ownership on a risk-adjusted basis, net of frictions?** If not, the engine is expensive noise.

Deliverable: a single auditable markdown report backed by an immutable, content-hashed evidence pack stored in R2. The report is the answer; the R2 pack is the proof.

## 2. Why Now

The engine has run in production since the v4 ML pipeline shipped (2026-02-23 onward), accumulating ~9-day windows of legacy `scores` and 2-month windows of PIT data. The PIT pipeline (complete 2026-02-27) gives us 12.8M dividend-adjusted prices and 5,327 tickers back to 2015 — the load-bearing prerequisite that makes a walk-forward audit feasible without a 2-3 week yfinance backfill.

Two surface findings forced design changes:

1. **`v4_scores` shows zero conviction candidates locally** (3 rows, all `composite_score=0.0`, `conviction='none'`, dated 2026-03-22) because production V4 scoring runs on Railway, not localhost. Local DB state is not authoritative.
2. **`pit_daily_prices` shows 0 rows locally** for the same reason. Local is a development sandbox; the production data lives in Railway Postgres.

Both findings reshape the audit architecture (Section 4): the audit must run *where the data is*, not where the dev clone is.

## 3. Scope

### In Scope

- Walk-forward backtest of the production V4 scoring config, **2015-01-31 → audit run date**, monthly rebalance.
- Component attribution by **two methods** (tercile spread + rank-IC) for every component in the inventory (Section 9).
- Live-window forward-return measurement on the 1,002 legacy candidates from the `scores` table — **folded into the walk-forward report** as a "Live Forward Track Record (60-day, in-progress)" section, not a separate deliverable.
- v2 scoring-formula proposal derived from attribution findings — **proposal only**; no engine changes.
- R2 evidence pack with content hashes; markdown report cites hashes for reproducibility.

### Out of Scope

- Engine modifications. Any v2 implementation is a separate follow-up project.
- ML retraining. ML override behavior is audited as-is from `v4_scores.ml_override`.
- New factor research beyond the inventory.
- Conviction-tier threshold changes. We report calibration; we don't change thresholds.
- Production scheduling of audits. Ad-hoc `railway run` only — promotion to ARQ deferred until recurring use is proven.
- Admin UI / dashboard surface for audit runs. R2 bundle + markdown report is the surface.
- Non-SPY benchmarks (factor-replicating ETFs, sector ETFs). Future work.
- Regime-conditioned analysis (bull/bear/sideways). Flagged as v2 follow-up.

## 4. Architecture Decision

**Path B with R2 evidence packs**, single CLI command pattern, handles both phases.

### 4.1 Why Path B over alternatives

Three access modes were considered:

- **A) ARQ worker + admin endpoint.** Heaviest path. Requires migration (`audit_runs` table), admin endpoint plumbing, governance integration. Rejected because no recurring-use evidence yet — premature.
- **B) One-shot Railway CLI command.** Mirrors the existing `seed`, `score`, `edgar-backfill`, `price-backfill` precedent. Reuses `BacktestRun`/`BacktestResult` for Part B persistence. **Selected.**
- **C) SQL-only Part A.** Smallest blast radius, but cannot run `WalkForwardSimulator` in pure SQL — Part B impossible. Rejected.

### 4.2 Path B properties

- Audit code lives inside `api/` package: free ORM access, ships with every API deploy, audit always matches the engine version that produced production scores.
- Heavy compute (5M-row JSONB ⋈ price joins) runs server-side, not over a TCP proxy.
- Output is a content-hashed R2 bundle. Re-runs are *deterministic* and *idempotent*.
- Stage 2 (report rendering) runs locally from the R2 bundle. Report copy iterates without re-running compute.
- Trade-off accepted: no `governance_events` trail per run. Easy to add later if needed.

## 5. Module Layout

New files marked `+`, modified `M`:

```
api/src/margin_api/audit/                    +
  __init__.py                                +
  cli.py             # `audit-engine` subcommand impl     +
  forward_returns.py # Part A: legacy-candidate alpha     +
  walk_forward.py    # Part B: WalkForwardSimulator wrap  +
  attribution.py     # tercile spread + rank-IC + power   +
  bundler.py         # CSV emit + manifest + R2 + hash    +
  schema.py          # Pydantic output models             +

api/src/margin_api/cli.py                    M  # register `audit-engine` subcommand
scripts/audit/finalize_report.py             +  # Stage 2 local report renderer
docs/templates/audit-report.md.j2            +  # Jinja markdown template
docs/reports/margin-invest-validation-2026-04-27.md  +  # final deliverable
```

Tests:

```
api/tests/audit/test_attribution.py          +  # synthetic data: monotonic / noisy / U-shaped
api/tests/audit/test_forward_returns.py      +  # synthetic small DB
api/tests/audit/test_walk_forward.py         +  # WalkForwardSimulator wrapper
api/tests/audit/test_bundler.py              +  # CSV/manifest/hash determinism
api/tests/audit/test_end_to_end.py           +  # synthetic 10-candidate / 100-day DB → bundle
scripts/audit/test_finalize_report.py        +  # golden-file template render
```

## 6. Two-Stage Dataflow

### Stage 1 — Server-side (Railway)

```bash
railway run python -m margin_api.cli audit-engine \
  --report-date 2026-04-27 \
  --r2-prefix audits/2026-04-27/ \
  --part both
```

Stage 1 responsibilities:

1. Connect to Railway Postgres via existing API session/DB plumbing.
2. **Phase 0 verification** — query PIT coverage; abort with explicit error if `MIN(date) > 2015-01-31` or SPY coverage gaps exceed 1% of trading days.
3. **Part A** — read `scores` table (legacy 1,002 candidates), compute forward returns vs SPY for windows {30, 60, 63} days where the window has closed by `--report-date`.
4. **Part B** — instantiate `WalkForwardSimulator` with replication parameters (Section 10), run from 2015-01-31 to `--report-date`, write `BacktestRun` + `BacktestResult` rows.
5. **Attribution** — compute tercile spread and rank-IC for every component in the inventory across each closed window.
6. **Bundle** — emit 6 CSVs + `manifest.json` with sha256s, upload to R2 under `--r2-prefix`, print signed URL + content hash to stdout.

### Stage 2 — Local

```bash
python scripts/audit/finalize_report.py --r2-prefix audits/2026-04-27/
```

Stage 2 responsibilities:

1. Download bundle from R2 using signed URLs in `manifest.json`.
2. Validate every file's sha256 against the manifest. Abort on mismatch.
3. Render `docs/templates/audit-report.md.j2` with the bundle's data.
4. Write `docs/reports/margin-invest-validation-{report-date}.md`.
5. Print the manifest content hash so it can be cited in the report's reproducibility footer.

### Why split the stages

Report copy iterates faster than backtest data. Re-rendering markdown from a cached R2 bundle is free; re-running Stage 1 takes minutes-to-hours. The split also enforces the regulator-grade property: **audit data is immutable, report is mutable**.

## 7. Data Contracts

### 7.1 Manifest

`audits/{YYYY-MM-DD}/manifest.json`:

```json
{
  "audit_version": "1.0",
  "audit_run_id": "<uuid>",
  "report_date": "2026-04-27",
  "engine_git_sha": "<sha of HEAD when Stage 1 ran>",
  "engine_config_sha": "<sha256 of v3_scoring_config + v4_pipeline imports>",
  "data_provenance": {
    "scores_count": <int>,
    "v4_scores_count": <int>,
    "pit_prices_min_date": "2015-01-02",
    "pit_prices_max_date": "<MAX(date)>",
    "pit_distinct_tickers": <int>,
    "spy_coverage_days": <int>
  },
  "files": {
    "candidates_part_a.csv": "sha256:<hex>",
    "walk_forward_snapshots.csv": "sha256:<hex>",
    "component_attribution.csv": "sha256:<hex>",
    "conviction_calibration.csv": "sha256:<hex>",
    "performance_metrics.csv": "sha256:<hex>",
    "v2_proposal_inputs.csv": "sha256:<hex>"
  },
  "stats": {
    "part_a": {"candidate_count": <int>, "windows_closed": [30, 60, 63]},
    "part_b": {
      "start": "2015-01-31",
      "end": "<report-date>",
      "cohort_count": <int>,
      "rebalance": "monthly",
      "max_positions": 50,
      "selection": "exceptional+high"
    }
  }
}
```

### 7.2 CSV schemas

**`candidates_part_a.csv`** (1 row per legacy candidate)

| Column | Type | Notes |
|---|---|---|
| `ticker` | str | |
| `scored_at` | date | from `scores.scored_at` |
| `conviction_level` | str | `exceptional` / `high` / `medium` |
| `composite_percentile` | float | 0-100 |
| `opportunity_type` | str | from `scores.opportunity_type` |
| `asymmetry_ratio` | float | from `scores.asymmetry_ratio` |
| `candidate_return_30d` | float \| null | dividend-adjusted total return |
| `candidate_return_60d` | float \| null | |
| `candidate_return_63d` | float \| null | actual elapsed window |
| `spy_return_30d` | float \| null | |
| `spy_return_60d` | float \| null | |
| `spy_return_63d` | float \| null | |
| `alpha_30d` | float \| null | candidate − spy |
| `alpha_60d` | float \| null | |
| `alpha_63d` | float \| null | |
| `hit_30d` | bool \| null | alpha > 0 |
| `hit_60d` | bool \| null | |
| `hit_63d` | bool \| null | |
| `data_status` | str | `ok` / `data_unavailable` / `partial` |

Null returns when PIT prices are missing. `data_unavailable` rows are counted in methodology, never silently dropped.

**`walk_forward_snapshots.csv`** (1 row per monthly cohort)

| Column | Type | Notes |
|---|---|---|
| `cohort_date` | date | |
| `cohort_size` | int | post-elimination, post-cap |
| `portfolio_return` | float | net of frictions |
| `benchmark_return` | float | SPY total return same period |
| `excess_return` | float | portfolio − benchmark |
| `turnover` | float | from `WalkForwardSimulator` |
| `gross_return` | float | pre-frictions |
| `cost_drag_bps` | float | gross − net, basis points |

**`component_attribution.csv`** (1 row per component × method × window)

| Column | Type | Notes |
|---|---|---|
| `component` | str | from inventory (Section 9) |
| `method` | str | `tercile` or `rank_ic` |
| `window` | str | `30d` / `60d` / `63d` / `walk_forward` |
| `n_top` | int | tercile size; null for rank-IC |
| `n_bottom` | int | tercile size; null for rank-IC |
| `top_tercile_alpha` | float \| null | mean alpha of top tercile |
| `bottom_tercile_alpha` | float \| null | mean alpha of bottom tercile |
| `spread` | float \| null | top − bottom |
| `rank_ic` | float \| null | Spearman correlation of component score vs forward alpha |
| `ci_lo` | float | 95% bootstrap CI lower bound |
| `ci_hi` | float | 95% bootstrap CI upper bound |
| `p_value_raw` | float | uncorrected |
| `p_value_holm` | float | Holm-Bonferroni-corrected across components |
| `verdict` | str | `keep` / `demote` / `cut` / `underpowered` |

**`conviction_calibration.csv`** (1 row per tier)

| Column | Type | Notes |
|---|---|---|
| `tier` | str | `exceptional` / `high` / `medium` |
| `n` | int | candidates in tier |
| `mean_alpha_60d` | float \| null | |
| `sharpe` | float \| null | annualized |
| `sortino` | float \| null | |
| `max_drawdown` | float \| null | |
| `anova_p` | float | one-way ANOVA across tiers |
| `monotonic` | bool | `exceptional ≥ high ≥ medium` on `mean_alpha` |

**`performance_metrics.csv`** (key=value rows)

| `metric` | Type |
|---|---|
| `cagr` | float |
| `excess_cagr` | float |
| `sharpe` | float |
| `sortino` | float |
| `max_drawdown` | float |
| `win_rate` | float |
| `info_ratio` | float |
| `gross_cagr` | float |
| `net_cagr` | float |
| `cost_drag_bps` | float |
| `t_statistic` | float |
| `p_value` | float |

All from `PerformanceCalculator`. The `excess_cagr` field is the canonical "engine vs SPY" verdict number — quoted verbatim in the report's executive summary.

**`v2_proposal_inputs.csv`** (1 row per component)

| Column | Type | Notes |
|---|---|---|
| `component` | str | |
| `current_weight` | float | from `v3_scoring_config` |
| `attribution_spread` | float | from walk-forward attribution |
| `marginal_alpha_loss_when_zeroed` | float | re-run simulator with this component zeroed |
| `proposed_action` | str | `keep` / `demote` / `cut` |
| `proposed_new_weight` | float | normalized over keepers |

Marginal-loss column requires re-running `WalkForwardSimulator` once per component (28 runs). This is the most expensive part of Stage 1 and is **gated behind a `--with-marginal-attribution` flag**, defaulting to off. First-pass audit produces spread-only attribution; second pass (after spec review confirms the cost is acceptable) adds marginal loss.

### 7.3 Report sections (rendered by Stage 2)

The report template enforces these sections in order:

1. **Executive Summary** — five bullets, all populated with non-asterisked numbers OR explicitly asterisked with "in-progress / underpowered" labels. The `excess_cagr` value appears verbatim here.
2. **Methodology + Replication Deviations from Production** — full disclosure of every replication choice (Section 10) and any deviation.
3. **Component Inventory** — the table from Section 9.
4. **Performance Metrics + Risk-Adjusted Verdict** — full `PerformanceCalculator` output table.
5. **Component Attribution** — sorted descending by walk-forward spread, both methods side-by-side, disagreement-flagged rows highlighted.
6. **Conviction Calibration** — tier table + ANOVA.
7. **Live Forward Track Record (60-day, in-progress)** — the legacy-candidate signal, with statistical-power disclaimer.
8. **Kill List + v2 Scoring Formula Proposal** — derived from attribution + marginal-loss runs.
9. **Statistical Power Disclaimer** — explicit section listing windows, n, multiple-comparisons correction, and what is NOT validated by this audit.
10. **Reproducibility Footer** — engine git sha, engine config sha, manifest content hash, R2 bundle URL, command line.

## 8. Statistical Methodology

### 8.1 Forward returns

Always computed from `pit_daily_prices.adj_close` (dividend-adjusted). Never `close`. Total return = `adj_close[t+window] / adj_close[t] - 1`. SPY return computed identically. Alpha = candidate return − SPY return over the same calendar window.

### 8.2 Tercile-spread attribution

For each component:
- Sort candidates by component sub-score.
- Top tercile = top 33%; bottom tercile = bottom 33%.
- Spread = `mean_alpha(top) − mean_alpha(bottom)`.
- Bootstrap 95% CI with 1000 resamples.

Robust to outliers; blind to U-shape and saturating monotonic. Reported alongside rank-IC for cross-check.

### 8.3 Rank-IC attribution

For each component:
- Spearman correlation between component sub-score and forward alpha.
- Bootstrap 95% CI with 1000 resamples.

Sensitive to monotonicity; assumes near-linear relationship. **Disagreement with tercile spread is itself a finding** — flagged in the report as "predictive by rank-IC but not by tercile spread → likely U-shaped or non-monotonic-saturating → demote, don't cut."

### 8.4 Multiple-comparisons correction

**Holm-Bonferroni** across all components subject to attribution (the composite-contributing subset; components 27-28 are audited separately and excluded from the family-wise correction). At a typical family size of ~24-26, expected ~1.2-1.3 false positives at uncorrected α=0.05 — enough to fabricate a "kill list" item. The correction line in `attribution.py` is mandatory; absence of it is a correctness bug.

### 8.5 Statistical-power gate

Each component-attribution row needs **n ≥ 30 per tercile** to publish a verdict. Below threshold:
- `verdict = "underpowered"` — never `keep`/`demote`/`cut`.
- This protects against falsely cutting a component because its spread estimate has huge uncertainty.

The "underpowered" verdict also fires when bootstrap CI crosses zero — i.e., the spread is statistically indistinguishable from zero even with adequate n.

### 8.6 Conviction-tier monotonicity

Tested with **one-way ANOVA** across tier alphas, not visual inspection. Reported alongside the monotonicity boolean (`exceptional_alpha ≥ high_alpha ≥ medium_alpha`). If ANOVA p > 0.05 the tiers are statistically indistinguishable — a finding regardless of point-estimate ordering.

### 8.7 Determinism

Stage 1 uses `seed=42` for any sampling (bootstrap CI, tercile-tie breakers, etc.). Re-running Stage 1 on identical input data produces byte-identical CSV outputs and identical manifest content hash. **This determinism gate is a merge-blocker test.** Non-determinism in an audit is a correctness bug, not a flake.

## 9. Component Inventory

The 28 components contributing to `V4ResultWithML`. Every row gets an attribution entry in `component_attribution.csv`. Source of truth is `v4_pipeline.score_universe_v4`; the audit's first server-side step (`audit/cli.py`) walks the pipeline and emits this table for cross-check against this spec.

| # | Component | Where | What it measures | Wiring |
|---|---|---|---|---|
| 1 | Mediocrity gate | `filters/mediocrity_gate.py` | trajectory-aware ROIC/GM/FCF/stage screen | filter (binary, with conditional override) |
| 2 | Altman Z | `filters/altman.py` | bankruptcy risk | filter |
| 3 | Beneish M | `filters/beneish.py` | earnings manipulation risk | filter |
| 4 | Current ratio | `filters/current_ratio.py` | short-term liquidity | filter |
| 5 | FCF distress | `filters/fcf_distress.py` | sustained negative FCF | filter |
| 6 | Interest coverage | `filters/interest_coverage.py` | EBIT / interest expense | filter |
| 7 | Liquidity (volume/mkt-cap) | `filters/liquidity.py` | tradeability | filter |
| 8 | Conviction gates (ROIC) | `conviction_gates.py` | ROIC-conditional reinvestment tier | gate |
| 9-17 | Track A factor inputs | `quantitative/*.py` (compounder factors) | per-factor sub-scores | composite input |
| 18 | Track A composite | `v3_cascade.run_track_a_cascade` | compounder cascade | track score (geometric mean) |
| 19 | Track B composite | `v3_cascade.run_track_b_cascade` | mispricing cascade | track score |
| 20 | Track C composite | `v3_track_c_cascade.run_track_c_cascade` | efficient-growth cascade (GROWTH style only) | track score (style-gated) |
| 21 | Anti-consensus modifier | `score_modifiers.anti_consensus_modifier` | short interest + analyst divergence + EPS revisions | post-composite multiplicative |
| 22 | Liquidity modifier | `score_modifiers.liquidity_modifier` | mkt cap + ADV + divergence | post-composite multiplicative |
| 23 | Insider signal modifier | `score_modifiers.insider_signal_modifier` | cluster + total buy + first-buy + drawdown | post-composite multiplicative |
| 24 | Inflection modifier | `score_modifiers.inflection_modifier` | inflection score on history | post-composite multiplicative |
| 25 | TAM modifier | `score_modifiers.tam_modifier` | TAM expansion velocity vs industry | post-composite multiplicative |
| 26 | ML override | `ml/ensemble_override.apply_ml_override` | ML alpha + VAE confidence | conditional bump/demote |
| 27 | Risk Factor Diff | `services/risk_diffing/` | 10-K Item 1A semantic delta | overlay only — **not in composite per memory; audited separately** |
| 28 | Kelly sizing | `kelly_position_sizing.py` | f* = (bp − q) / b | position sizing — **not a composite input; audited as portfolio-construction step** |

Rows 9-17 collapse to "Track A factor inputs" in this table for compactness; the actual `component_attribution.csv` enumerates each factor file individually. The Stage 1 cross-check enumerates them by walking `factors/registry.py` and `quantitative/`.

Components 27 and 28 are audited separately:
- **27 (Risk Factor Diff)** — overlay metric, not in composite. Attribution row reports correlation between `risk_factor_analyses.delta_score` and forward alpha, not a kill-list verdict.
- **28 (Kelly sizing)** — portfolio-construction step. Audited by comparing walk-forward results with Kelly-sized weights vs equal-weight, reported as "Kelly contribution to alpha" in the report.

## 10. Replication Choices (Production → Audit)

The walk-forward simulator approximates production. Every deviation is documented here and in the report's methodology section.

| Choice | Audit | Production | Rationale |
|---|---|---|---|
| Rebalance frequency | Monthly | Continuous (every score change re-allocates) | Standard backtest discipline; documented deviation |
| Position cap | 50 | Variable (Kelly-bounded) | Practical end-user portfolio constraint |
| Conviction selection | `exceptional` + `high` | Same (these are the "buy" signals) | Match |
| Position sizing | Kelly-derived from `kelly_position_sizing.py` | Same | Match |
| Friction model | `PerformanceCalculator` defaults | Same model, may differ in bps assumptions | Verify defaults match production at Phase 1 implementation time |
| Universe construction | `pit_universe_memberships` (survivorship-bias-safe) | Live universe | PIT is the audit gold standard |
| Data sources | `pit_financial_snapshots` + `pit_daily_prices` | Same PIT tables | Match |
| ML override | Applied if `v4_scores.ml_override` non-null at cohort date | Same | Match |
| Score regeneration | **Audit re-runs V4 scoring at each cohort date with current engine code (not reads precomputed `v4_scores`)** | Production wrote scores at time T with engine V_T | Audit measures "engine as it exists at audit run date" using PIT inputs at cohort date — NOT "what production actually shipped." Critical methodology disclosure: this audit validates the *current* engine, not a historical replay. |

The report's methodology section reproduces this table verbatim with the `excess_cagr` framed as "achievable under these replication assumptions, NOT a guarantee that production attains the same number." The score-regeneration row gets its own paragraph in methodology — this is the most consequential replication choice and the one most likely to be misread.

## 11. Implementation Phases

### Phase 0 — Data Verification (no code changes, ~10 min)

```bash
railway run psql $DATABASE_URL -c "
  SELECT MIN(date), MAX(date), COUNT(*), COUNT(DISTINCT ticker)
  FROM pit_daily_prices;
  SELECT MIN(date), MAX(date), COUNT(*) FROM pit_daily_prices WHERE ticker='SPY';
  SELECT COUNT(*) FROM scores WHERE conviction_level IN ('exceptional','high','medium');
  SELECT COUNT(*) FROM v4_scores;
  SELECT COUNT(*) FROM pit_universe_memberships;
"
```

**Pass conditions:**
- `pit_daily_prices` MIN ≤ 2015-01-31, MAX ≥ `report-date − 7d`, COUNT > 10M, distinct tickers > 4000.
- SPY coverage continuous from 2015 to within 7 days of report date.
- `scores` legacy candidate count ≈ 1002.
- `pit_universe_memberships` non-empty (required for survivorship-bias-safe Part B).

**Fail handling:**
- If PIT coverage is shallower than 2015: invoke existing `price-backfill --start-date 2015-01-01` CLI before proceeding.
- If `pit_universe_memberships` empty: invoke `edgar-backfill --start-year 2015`.

Both fail paths use existing CLI commands — no new code. They are gated behind explicit user approval per command, since they are user-visible long-running operations.

### Phase 1 — Stage 1 Implementation (TDD)

Order:

1. `audit/schema.py` — Pydantic models for manifest + CSV row types. Tests assert schema stability.
2. `audit/forward_returns.py` — Part A logic. Tests use synthetic small DB.
3. `audit/attribution.py` — both methods + Holm-Bonferroni + power gate. Tests use synthetic monotonic / noisy / U-shaped data; verify the disagreement-flag fires on U-shape.
4. `audit/walk_forward.py` — wrapper around `WalkForwardSimulator`. Tests assert cohort row structure.
5. `audit/bundler.py` — CSV emit + manifest + R2 upload + hash verification. Tests assert determinism (re-emit → byte-identical hashes) and hash-mismatch detection.
6. `audit/cli.py` + `cli.py` registration — CLI subcommand. End-to-end test on synthetic 10-candidate / 100-day DB.

Coverage target ≥ 90% for the audit module (matches api/ standard).

### Phase 2 — Stage 2 Implementation

1. `docs/templates/audit-report.md.j2` — Jinja template enforcing the 10 report sections.
2. `scripts/audit/finalize_report.py` — download R2 bundle, validate hashes, render template, write markdown.
3. Golden-file test for Stage 2 with a fixed bundle fixture.

### Phase 3 — First Live Run

1. Phase 0 verification (live, against Railway).
2. `railway run python -m margin_api.cli audit-engine --report-date 2026-04-27 --r2-prefix audits/2026-04-27/ --part both` (without `--with-marginal-attribution`).
3. Local Stage 2: render report.
4. Review numbers; commit report.
5. If methodology-acceptable: re-run with `--with-marginal-attribution` for v2 proposal numbers; re-render report.

### Phase 4 — v2 Scoring Formula Proposal (Section in Report, Not Engine Change)

Within the report's Kill List section:

- **Cut**: components with `verdict=cut` AND marginal-alpha-loss < 2% (zeroing them barely moves excess CAGR).
- **Demote**: components with `verdict=demote` (positive but weak; methodology disagreement; or U-shaped) → move to overlay/diagnostic only.
- **Keep**: components with `verdict=keep`.
- **Reweight**: propose new geometric-mean weights proportional to per-component spread, normalized over keepers.
- **Net result**: 2-3 page proposal section with before/after weights and a **projected** alpha lift derived from the attribution-by-spread numbers (not validated; v2 implementation would need its own walk-forward audit).

## 12. Verification / Definition of Done

A green audit run satisfies all of:

1. **Phase 0 query** returns pass-conditions stated in §11. Queryable evidence in stdout transcript.
2. **R2 bundle uploaded.** `manifest.json` validates against `audit/schema.py` Pydantic model. All 6 CSVs have hash-matching content.
3. **Markdown report committed** to `docs/reports/`. All 10 required sections present. `excess_cagr` value in executive summary matches `performance_metrics.csv` byte-for-byte.
4. **Component attribution complete.** Every inventory component has at least one row in `component_attribution.csv`. Verdicts conform to power gate (n < 30 → `underpowered`).
5. **`BacktestRun` row written** by Stage 1 with non-null `total_return`, `sharpe_ratio`, `excess_cagr`.
6. **Determinism property holds.** Re-running Stage 1 on the same DB snapshot produces byte-identical manifest content hash. Test asserts this on every CI run.
7. **Reproducibility footer cites:** engine git sha, engine config sha, manifest content hash, R2 URL. Reader can fetch the bundle and recompute every reported number.

End-to-end the user can verify by reading the executive summary's five bullets and immediately answering "does the engine beat SPY net of frictions?" without ambiguity. If a verdict bullet says "Engine adds X bps over SPY net of costs" and the underlying CSVs don't support that number, the audit fails its own integrity check.

## 13. Risks & Open Questions

### 13.1 Risks

- **PIT coverage gaps before 2018.** EDGAR backfill quality may be lower for 2015-2017 (less standardized XBRL). If walk-forward error rates spike pre-2018, report flags those years separately and proposes `start_date=2018-01-31` as a "high-confidence" sub-window.
- **Score-regeneration interpretation risk.** Per Section 10, Part B regenerates scores at each cohort date using current V4 code. The audit therefore answers "does the current engine beat SPY?" not "did the engine that shipped scores in production beat SPY?" Readers may conflate these. Mitigation: methodology section calls this out in its own paragraph; reproducibility footer pins `engine_git_sha`.
- **Engine git sha drift.** If the engine is modified between Phase 1 and Phase 3, the audit's attribution numbers reflect the post-modification engine. Mitigation: Phase 3 first live run pins `engine_git_sha` in the manifest; any subsequent v2 proposal compares manifests by sha pair.
- **R2 cost.** Each bundle is ~50-200 MB (CSVs are wide). At Railway's R2 pricing this is negligible per run; no concern below ~1000 audit runs.
- **`PerformanceCalculator` friction defaults may not match production.** Phase 1 step 0 includes a verification step: read defaults, document them in methodology, flag any divergence from production assumption.

### 13.2 Open Questions (acceptable to defer to implementation)

- Exact column name in `scores.score_detail` JSONB for each component sub-score. Verified by Phase 1 step 1 (schema introspection); spec assumes the JSONB has `{"factor_breakdown": {<component>: <percentile>}}` shape per memory.
- Whether `BacktestRun` accepts a `purpose='audit'` discriminator field or needs a new column. Verified at Phase 1 step 4; if needed, add column via migration with idempotent check (per Alembic-pitfalls memory).
- Whether existing `archiver/r2.py` exposes a public-enough API for the bundler. Spec assumes yes based on the modified-locally `archiver/snapshot.py` and `archiver/worker.py` files; if not, bundler ships its own thin wrapper.

## 14. References

- `engine/src/margin_engine/scoring/v4_pipeline.py` — production V4 orchestration; source of truth for component inventory.
- `engine/src/margin_engine/scoring/v3_cascade.py`, `v3_track_c_cascade.py`, `v3_composite.py` — track cascades.
- `engine/src/margin_engine/scoring/score_modifiers.py` — modifier inventory.
- `engine/src/margin_engine/scoring/conviction_gates.py`, `filters/*.py` — gate + filter inventory.
- `engine/src/margin_engine/factors/registry.py`, `scoring/quantitative/*.py` — factor enumeration.
- `engine/src/margin_engine/backtesting/simulator.py` — `WalkForwardSimulator.run()`. **Reused unchanged.**
- `engine/src/margin_engine/backtesting/metrics.py` — `PerformanceCalculator`. **Reused unchanged.**
- `engine/src/margin_engine/backtesting/rank_ic.py` — Spearman rank correlation. **Reused unchanged.**
- `engine/src/margin_engine/backtesting/pit_provider.py` — PIT data provider used by simulator.
- `api/src/margin_api/db/models.py` — `PITDailyPrice`, `BacktestRun`, `BacktestResult`, `Score`, `V4Score`, `PITUniverseMembership` ORMs.
- `api/src/margin_api/services/backtest.py` — existing backtest service wrapper; pattern reference, not modified.
- `api/src/margin_api/archiver/` — R2 client + signed URL handling for the bundler.
- `api/src/margin_api/cli.py` — existing CLI; `audit-engine` subcommand registered here.

## 15. Approval Gates

This spec is approved when:

- [ ] User has reviewed Section 3 (scope) — confirmed audit boundaries.
- [ ] User has reviewed Section 7.2 (CSV schemas) — confirmed columns are sufficient.
- [ ] User has reviewed Section 9 (component inventory) — confirmed coverage.
- [ ] User has reviewed Section 10 (replication choices) — confirmed deviations from production are acceptable.
- [ ] User has reviewed Section 13.1 (risks) — accepted or flagged for spec revision.

After approval: invoke `superpowers:writing-plans` to produce the implementation plan.
