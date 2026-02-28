# Multi-Seed Validation & Reproducibility Framework

**Date:** 2026-02-27
**Status:** Approved
**Scope:** Full (ML pipeline + backtesting groundwork + scoring audit)

## Problem

All ML training uses a single hardcoded seed (42). This means:
- No way to distinguish genuine signal from a lucky initialization
- No distributional evidence that model performance is robust
- Single-run point estimates provide false confidence
- No reproducibility audit trail for scoring or backtesting

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Full (ML + backtest + scoring) | Lay complete groundwork now |
| Seed count | 20 per training cycle | Good balance of rigor and training time |
| Model selection | Best-qualified with distributional gate | Deploy strongest model, but only if distribution proves signal is real |
| Execution | Sequential in single worker | Simpler than parallel fan-out; weekly cron can absorb 20x training time |
| Visibility | Admin UI + API only | Operators see validation reports; end users don't |
| Approach | Validation Layer (additive) | Wraps existing pipeline without restructuring |

## Architecture

### Database Schema

#### Modified: `ml_model_runs`

New columns:
- `seed: Integer, default=42` — which random seed produced this model
- `run_group_id: UUID, nullable=True` — links all seeds from the same training cycle

#### New table: `seed_validation_reports`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `run_group_id` | UUID, unique | Links to the group of MlModelRun rows |
| `created_at` | DateTime(tz) | When validation ran |
| `n_seeds` | Integer | Number of seeds in the group |
| `metric_distributions` | JSONB | Per-metric stats (mean, median, std, min, max, CI, CV) |
| `gate_passed` | Boolean | Whether the distribution met promotion thresholds |
| `gate_details` | JSONB | Per-check pass/fail with values and thresholds |
| `selected_seed` | Integer, nullable | Which seed's model was promoted (null if gate failed) |
| `previous_comparison` | JSONB, nullable | Wilcoxon test results vs. previous group |
| `environment_snapshot` | JSONB | Python version, library versions, commit hash, hardware |

`metric_distributions` structure:
```json
{
  "rank_ic": {
    "mean": 0.22, "median": 0.21, "std": 0.04,
    "min": 0.14, "max": 0.29,
    "ci_lower": 0.18, "ci_upper": 0.26, "cv": 0.18
  },
  "cluster_stability_ari": { ... },
  "per_cluster_accuracy": { ... }
}
```

`gate_details` structure:
```json
{
  "median_rank_ic": {"value": 0.21, "threshold": 0.15, "passed": true},
  "rank_ic_cv": {"value": 0.18, "threshold": 0.50, "passed": true},
  "worst_seed_ic": {"value": 0.14, "threshold": 0.05, "passed": true},
  "overall": true
}
```

#### New table: `reproducibility_audits`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `pipeline_stage` | String | e.g. "full_score_v4", "train_ml_models", "backtest" |
| `run_at` | DateTime(tz) | When the pipeline ran |
| `config_hash` | String | SHA-256 of pipeline configuration |
| `environment_snapshot` | JSONB | Library versions, commit hash, hardware |
| `input_data_hash` | String, nullable | SHA-256 of input data |

#### Modified: `backtest_runs`

New columns:
- `seed: Integer, nullable=True` — for future use when real PIT backtests are wired
- `environment_snapshot: JSONB, nullable=True` — for future reproducibility tracking

### ML Pipeline Changes

#### Engine Layer

No changes to function signatures — `cluster_stocks`, `train_cluster_models`, and `train_factor_vae` already accept `seed` parameters. The hardcoding is in the worker layer.

#### New: `engine/src/margin_engine/ml/seed_validation.py`

```python
def validate_seed_distribution(
    seed_metrics: list[dict],  # one dict per seed with rank_ic, cluster_labels, etc.
    thresholds: SeedValidationThresholds | None = None,
) -> SeedValidationResult:
    """Compute distributional statistics and gate checks across seed runs."""
```

Computes:
- Mean, median, std, min, max, 95% CI (t-distribution), CV for rank_ic
- Cluster stability via Adjusted Rand Index (ARI) between all pairs of seed clusterings
- Gate evaluation against thresholds

```python
@dataclass
class SeedValidationThresholds:
    min_median_rank_ic: float = 0.15
    max_rank_ic_cv: float = 0.50
    min_worst_seed_ic: float = 0.05

@dataclass
class SeedValidationResult:
    metric_distributions: dict[str, MetricDistribution]
    gate_passed: bool
    gate_details: dict
    selected_seed: int | None  # best-IC seed if gate passed
```

#### New: `engine/src/margin_engine/ml/reproducibility.py`

```python
def capture_environment() -> dict:
    """Capture current environment for reproducibility audit."""
```

Returns:
- `python_version`: e.g. "3.13.5"
- `platform`: e.g. "darwin-arm64"
- `libraries`: dict of package → version for numpy, scikit-learn, lightgbm, torch, pandas
- `git_commit`: full SHA from `git rev-parse HEAD` or `GIT_COMMIT` env var
- `determinism_flags`: PYTHONHASHSEED, torch determinism settings

#### New: `engine/src/margin_engine/ml/model_comparison.py`

```python
def compare_model_groups(
    current_metrics: list[float],   # rank_ic per seed, current group
    previous_metrics: list[float],  # rank_ic per seed, previous group
) -> ModelComparisonResult:
    """Paired Wilcoxon signed-rank test between two seed groups."""
```

Returns p-value, effect size (rank-biserial correlation), and a significance label.

Note: If groups have different seed counts, compare only overlapping seeds (0..min(N1,N2)-1). Log a warning if counts differ.

#### Worker Layer — `train_ml_models` Changes

Current:
```
train_ml_models() → cluster(seed=42) → train(seed=42) → vae(seed=42) → store 1 MlModelRun
```

New:
```
train_ml_models() →
  run_group_id = uuid4()
  seed_metrics = []

  for seed in range(N_SEEDS):  # N_SEEDS = 20
    clusters = cluster_stocks(features, tickers, seed=seed)
    models = train_cluster_models(features, fwd_returns, clusters, seed=seed)
    vae = train_factor_vae(features, fwd_returns, config, seed=seed)  # if enabled

    Store MlModelRun(seed=seed, run_group_id=run_group_id, ...)
    Collect seed_metrics entry (rank_ic, cluster_labels, accuracy)

  validation = validate_seed_distribution(seed_metrics)
  comparison = compare_to_previous_group(run_group_id)  # if previous exists

  Store SeedValidationReport(
    run_group_id, validation, comparison, capture_environment()
  )

  if validation.gate_passed:
    best_model = MlModelRun where seed == validation.selected_seed
    best_model.deployment_status = 'candidate'
    Create GovernanceEvent("ml_model_staged", ...)
    Chain to promote_ml_model
  else:
    Create GovernanceEvent("seed_validation_failed", ...)
    Log warning — no model promoted this cycle

  Store ReproducibilityAudit("train_ml_models", ...)
```

### Scoring Reproducibility Audit

After `full_score_v4` completes, insert a `ReproducibilityAudit` row:
- `pipeline_stage = "full_score_v4"`
- `config_hash` = SHA-256 of scoring parameters (elimination thresholds, factor weights)
- `environment_snapshot` = capture_environment()
- `input_data_hash` = SHA-256 of sorted ticker list + max(financial_data.updated_at)

One row per scoring run. No behavioral changes to scoring.

### Backtesting Groundwork

Schema-only changes (no behavioral changes):
- `ReplayConfigRequest` gains `seed: Optional[int] = None`
- `BacktestRun` model gains `seed` and `environment_snapshot` columns
- `compute_config_hash()` includes seed in hash computation
- When real PIT data is wired, backtest runs will automatically record seeds

### Admin UI — Model Validation Panel

#### New page: `/admin/model-validation`

**Summary header:**
- Run group timestamp, seed count, gate status badge (pass/fail)
- Selected seed and its rank IC (if gate passed)
- Environment info (Python version, key libraries, commit SHA)

**Distribution table:**
| Metric | Mean | Median | Std | Min | Max | 95% CI | CV | Gate |
|--------|------|--------|-----|-----|-----|--------|----|----|

**Box plot:**
- Rank IC distribution across seeds (Recharts)
- Horizontal threshold line at 0.15
- Highlighted dot for selected seed

**Per-seed detail table (expandable):**
| Seed | Rank IC | Clusters | Samples | Status |
|------|---------|----------|---------|--------|

**Historical comparison section:**
- Wilcoxon test result vs. previous run group
- p-value, effect size, significance label

**History list:**
- All past run groups with gate status, date, selected seed
- Click to view any historical report

#### API Endpoints

```
GET  /admin/model-validation/latest     → latest SeedValidationReport
GET  /admin/model-validation/{group_id} → specific report by run_group_id
GET  /admin/model-validation/history    → paginated list of all reports
```

All admin-gated (existing admin auth).

### Gate Thresholds

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| Median rank IC | > 0.15 | Existing qualification threshold, applied to median not single-run |
| Rank IC CV | < 0.50 | If std > half the mean, signal is unstable |
| Worst-seed IC | > 0.05 | No seed should be essentially random |

These are hardcoded initially. A future `GovernanceConfig` endpoint could make them configurable.

### Reproducibility Checklist (embedded in system)

The `SeedValidationReport.gate_details` JSONB serves as a machine-readable checklist. The admin UI renders it as a human-readable checklist:

- [ ] 20 seeds executed (predetermined, sequential 0-19)
- [ ] Full distribution reported (mean, median, std, min, max, 95% CI, CV)
- [ ] Median rank IC > 0.15
- [ ] Rank IC CV < 0.50
- [ ] Worst-seed rank IC > 0.05
- [ ] Cluster stability ARI computed across seed pairs
- [ ] Paired comparison to previous model group (if exists)
- [ ] Environment snapshot captured (Python, libraries, git commit)
- [ ] Input data hash recorded
- [ ] Selected model is best-IC within a passing distribution

## Files to Create or Modify

### Engine (new files)
- `engine/src/margin_engine/ml/seed_validation.py` — distributional stats + gate logic
- `engine/src/margin_engine/ml/reproducibility.py` — environment capture
- `engine/src/margin_engine/ml/model_comparison.py` — Wilcoxon test
- `engine/tests/ml/test_seed_validation.py`
- `engine/tests/ml/test_reproducibility.py`
- `engine/tests/ml/test_model_comparison.py`

### API (modified files)
- `api/src/margin_api/db/models.py` — new tables + modified columns
- `api/src/margin_api/workers.py` — multi-seed loop in train_ml_models
- `api/src/margin_api/schemas/backtest.py` — add seed to ReplayConfigRequest
- `api/src/margin_api/services/backtest.py` — include seed in config hash

### API (new files)
- `api/src/margin_api/routes/model_validation.py` — admin API endpoints
- `api/src/margin_api/schemas/model_validation.py` — response schemas
- Alembic migration for new tables and columns
- `api/tests/test_model_validation.py`
- `api/tests/test_seed_training.py`

### Web (new files)
- `web/src/app/admin/model-validation/page.tsx` — admin panel
- `web/src/components/admin/SeedDistributionTable.tsx`
- `web/src/components/admin/SeedBoxPlot.tsx`
- `web/src/components/admin/SeedDetailTable.tsx`
- `web/src/components/admin/ValidationChecklist.tsx`
- `web/src/lib/api/model-validation.ts` — API client
- `web/src/__tests__/admin/model-validation.test.tsx`
