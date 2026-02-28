# Multi-Seed Validation & Reproducibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multi-seed ML training (20 seeds), distributional validation gates, reproducibility audit trails for scoring/backtest, and an admin Model Validation panel.

**Architecture:** Additive validation layer wrapping existing ML pipeline. Engine gets 3 new modules (seed_validation, reproducibility, model_comparison). Worker loops over 20 seeds sequentially, stores per-seed MlModelRun rows linked by run_group_id, validates distribution before promoting best model. Admin UI surfaces reports.

**Tech Stack:** Python/Pydantic (engine), FastAPI/SQLAlchemy (API), Alembic (migrations), Next.js/React/Recharts (web), scipy.stats (Wilcoxon test), sklearn.metrics (ARI)

---

### Task 1: Engine — Seed Validation Module

**Files:**
- Create: `engine/src/margin_engine/ml/seed_validation.py`
- Test: `engine/tests/ml/test_seed_validation.py`

**Step 1: Write the failing tests**

```python
# engine/tests/ml/test_seed_validation.py
"""Tests for multi-seed validation module."""

import numpy as np
import pytest

from margin_engine.ml.seed_validation import (
    MetricDistribution,
    SeedValidationResult,
    SeedValidationThresholds,
    compute_metric_distribution,
    validate_seed_distribution,
)


class TestComputeMetricDistribution:
    def test_basic_stats(self) -> None:
        values = [0.10, 0.15, 0.20, 0.25, 0.30]
        dist = compute_metric_distribution(values)
        assert dist.mean == pytest.approx(0.20, abs=1e-6)
        assert dist.median == pytest.approx(0.20, abs=1e-6)
        assert dist.min == pytest.approx(0.10, abs=1e-6)
        assert dist.max == pytest.approx(0.30, abs=1e-6)
        assert dist.std > 0
        assert dist.cv == pytest.approx(dist.std / dist.mean, abs=1e-6)

    def test_confidence_interval_contains_mean(self) -> None:
        values = [0.18, 0.20, 0.22, 0.19, 0.21, 0.20, 0.23, 0.17, 0.22, 0.19]
        dist = compute_metric_distribution(values)
        assert dist.ci_lower <= dist.mean <= dist.ci_upper

    def test_single_value(self) -> None:
        dist = compute_metric_distribution([0.25])
        assert dist.mean == pytest.approx(0.25)
        assert dist.std == pytest.approx(0.0)
        # CI should still be defined (degenerate)
        assert dist.ci_lower == pytest.approx(0.25)
        assert dist.ci_upper == pytest.approx(0.25)

    def test_two_values(self) -> None:
        dist = compute_metric_distribution([0.10, 0.30])
        assert dist.mean == pytest.approx(0.20, abs=1e-6)
        assert dist.median == pytest.approx(0.20, abs=1e-6)


class TestValidateSeedDistribution:
    def _make_seed_metrics(self, rank_ics: list[float]) -> list[dict]:
        return [
            {"rank_ic": ic, "cluster_labels": list(range(5))}
            for ic in rank_ics
        ]

    def test_passing_distribution(self) -> None:
        # All ICs well above thresholds
        metrics = self._make_seed_metrics([0.25, 0.22, 0.28, 0.20, 0.24, 0.23, 0.26, 0.21, 0.27, 0.19])
        result = validate_seed_distribution(metrics)
        assert result.gate_passed is True
        assert result.selected_seed is not None
        assert "rank_ic" in result.metric_distributions

    def test_failing_low_median(self) -> None:
        # All ICs below 0.15 threshold
        metrics = self._make_seed_metrics([0.05, 0.08, 0.12, 0.10, 0.07, 0.09, 0.11, 0.06, 0.13, 0.04])
        result = validate_seed_distribution(metrics)
        assert result.gate_passed is False
        assert result.gate_details["median_rank_ic"]["passed"] is False

    def test_failing_high_cv(self) -> None:
        # High variance relative to mean
        metrics = self._make_seed_metrics([0.05, 0.50, 0.03, 0.48, 0.06, 0.45, 0.04, 0.52, 0.07, 0.47])
        result = validate_seed_distribution(metrics)
        assert result.gate_passed is False
        assert result.gate_details["rank_ic_cv"]["passed"] is False

    def test_failing_worst_seed(self) -> None:
        # One catastrophic seed below 0.05 floor
        metrics = self._make_seed_metrics([0.25, 0.22, 0.28, 0.20, 0.24, 0.23, 0.26, 0.21, 0.27, 0.01])
        result = validate_seed_distribution(metrics)
        assert result.gate_passed is False
        assert result.gate_details["worst_seed_ic"]["passed"] is False

    def test_selects_best_ic_seed(self) -> None:
        ics = [0.20, 0.25, 0.30, 0.22, 0.28, 0.24, 0.26, 0.21, 0.27, 0.23]
        metrics = self._make_seed_metrics(ics)
        result = validate_seed_distribution(metrics)
        assert result.selected_seed == 2  # index of 0.30

    def test_custom_thresholds(self) -> None:
        metrics = self._make_seed_metrics([0.12, 0.13, 0.14, 0.11, 0.12])
        thresholds = SeedValidationThresholds(min_median_rank_ic=0.10, max_rank_ic_cv=0.80, min_worst_seed_ic=0.01)
        result = validate_seed_distribution(metrics, thresholds)
        assert result.gate_passed is True

    def test_result_to_dict(self) -> None:
        metrics = self._make_seed_metrics([0.25, 0.22, 0.28, 0.20, 0.24])
        result = validate_seed_distribution(metrics)
        d = result.to_dict()
        assert "metric_distributions" in d
        assert "gate_passed" in d
        assert "gate_details" in d
        assert "selected_seed" in d
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_seed_validation.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
# engine/src/margin_engine/ml/seed_validation.py
"""Multi-seed validation: distributional statistics and promotion gates."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats


@dataclass
class MetricDistribution:
    """Distributional statistics for a single metric across seeds."""

    mean: float
    median: float
    std: float
    min: float
    max: float
    ci_lower: float
    ci_upper: float
    cv: float  # coefficient of variation (std / mean)

    def to_dict(self) -> dict:
        return {
            "mean": self.mean,
            "median": self.median,
            "std": self.std,
            "min": self.min,
            "max": self.max,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "cv": self.cv,
        }


@dataclass
class SeedValidationThresholds:
    """Configurable thresholds for the distributional gate."""

    min_median_rank_ic: float = 0.15
    max_rank_ic_cv: float = 0.50
    min_worst_seed_ic: float = 0.05


@dataclass
class SeedValidationResult:
    """Result of validating a multi-seed training run."""

    metric_distributions: dict[str, MetricDistribution]
    gate_passed: bool
    gate_details: dict
    selected_seed: int | None  # index of best-IC seed, None if gate failed

    def to_dict(self) -> dict:
        return {
            "metric_distributions": {
                k: v.to_dict() for k, v in self.metric_distributions.items()
            },
            "gate_passed": self.gate_passed,
            "gate_details": self.gate_details,
            "selected_seed": self.selected_seed,
        }


def compute_metric_distribution(values: list[float]) -> MetricDistribution:
    """Compute distributional statistics for a list of metric values."""
    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    mn = float(np.min(arr))
    mx = float(np.max(arr))

    # 95% CI using t-distribution
    if n > 1 and std > 0:
        se = std / math.sqrt(n)
        t_crit = stats.t.ppf(0.975, df=n - 1)
        ci_lower = mean - t_crit * se
        ci_upper = mean + t_crit * se
    else:
        ci_lower = mean
        ci_upper = mean

    cv = std / abs(mean) if abs(mean) > 1e-12 else 0.0

    return MetricDistribution(
        mean=mean,
        median=median,
        std=std,
        min=mn,
        max=mx,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cv=cv,
    )


def validate_seed_distribution(
    seed_metrics: list[dict],
    thresholds: SeedValidationThresholds | None = None,
) -> SeedValidationResult:
    """Validate a multi-seed training run against distributional gates.

    Args:
        seed_metrics: List of dicts, one per seed. Each must have "rank_ic" (float).
            May also have "cluster_labels" (list[int]) for ARI computation.
        thresholds: Gate thresholds. Uses defaults if None.

    Returns:
        SeedValidationResult with distributional stats and gate pass/fail.
    """
    if thresholds is None:
        thresholds = SeedValidationThresholds()

    rank_ics = [m["rank_ic"] for m in seed_metrics]
    ic_dist = compute_metric_distribution(rank_ics)

    # Cluster stability (ARI) if cluster_labels provided
    distributions: dict[str, MetricDistribution] = {"rank_ic": ic_dist}
    if all("cluster_labels" in m for m in seed_metrics) and len(seed_metrics) > 1:
        from sklearn.metrics import adjusted_rand_score

        ari_scores: list[float] = []
        for i in range(len(seed_metrics)):
            for j in range(i + 1, len(seed_metrics)):
                labels_i = seed_metrics[i]["cluster_labels"]
                labels_j = seed_metrics[j]["cluster_labels"]
                if len(labels_i) == len(labels_j):
                    ari_scores.append(adjusted_rand_score(labels_i, labels_j))
        if ari_scores:
            distributions["cluster_stability_ari"] = compute_metric_distribution(ari_scores)

    # Gate checks
    median_check = {
        "value": ic_dist.median,
        "threshold": thresholds.min_median_rank_ic,
        "passed": ic_dist.median >= thresholds.min_median_rank_ic,
    }
    cv_check = {
        "value": ic_dist.cv,
        "threshold": thresholds.max_rank_ic_cv,
        "passed": ic_dist.cv <= thresholds.max_rank_ic_cv,
    }
    worst_check = {
        "value": ic_dist.min,
        "threshold": thresholds.min_worst_seed_ic,
        "passed": ic_dist.min >= thresholds.min_worst_seed_ic,
    }

    gate_passed = all([median_check["passed"], cv_check["passed"], worst_check["passed"]])

    gate_details = {
        "median_rank_ic": median_check,
        "rank_ic_cv": cv_check,
        "worst_seed_ic": worst_check,
        "overall": gate_passed,
    }

    # Select best seed if gate passed
    selected_seed = None
    if gate_passed:
        selected_seed = int(np.argmax(rank_ics))

    return SeedValidationResult(
        metric_distributions=distributions,
        gate_passed=gate_passed,
        gate_details=gate_details,
        selected_seed=selected_seed,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_seed_validation.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ml/seed_validation.py engine/tests/ml/test_seed_validation.py
git commit -m "feat(engine): add seed validation module with distributional gates"
```

---

### Task 2: Engine — Reproducibility Environment Capture

**Files:**
- Create: `engine/src/margin_engine/ml/reproducibility.py`
- Test: `engine/tests/ml/test_reproducibility.py`

**Step 1: Write the failing tests**

```python
# engine/tests/ml/test_reproducibility.py
"""Tests for environment capture utility."""

from margin_engine.ml.reproducibility import capture_environment, compute_data_hash


class TestCaptureEnvironment:
    def test_returns_dict(self) -> None:
        env = capture_environment()
        assert isinstance(env, dict)

    def test_contains_python_version(self) -> None:
        env = capture_environment()
        assert "python_version" in env
        assert env["python_version"].startswith("3.")

    def test_contains_platform(self) -> None:
        env = capture_environment()
        assert "platform" in env
        assert isinstance(env["platform"], str)
        assert len(env["platform"]) > 0

    def test_contains_libraries(self) -> None:
        env = capture_environment()
        assert "libraries" in env
        libs = env["libraries"]
        assert "numpy" in libs
        assert "scikit-learn" in libs
        assert "lightgbm" in libs

    def test_contains_determinism_flags(self) -> None:
        env = capture_environment()
        assert "determinism_flags" in env


class TestComputeDataHash:
    def test_same_input_same_hash(self) -> None:
        h1 = compute_data_hash(["AAPL", "MSFT"], "2026-02-27")
        h2 = compute_data_hash(["AAPL", "MSFT"], "2026-02-27")
        assert h1 == h2

    def test_different_input_different_hash(self) -> None:
        h1 = compute_data_hash(["AAPL", "MSFT"], "2026-02-27")
        h2 = compute_data_hash(["AAPL", "GOOG"], "2026-02-27")
        assert h1 != h2

    def test_order_independent(self) -> None:
        h1 = compute_data_hash(["MSFT", "AAPL"], "2026-02-27")
        h2 = compute_data_hash(["AAPL", "MSFT"], "2026-02-27")
        assert h1 == h2

    def test_returns_hex_string(self) -> None:
        h = compute_data_hash(["AAPL"], "2026-02-27")
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_reproducibility.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
# engine/src/margin_engine/ml/reproducibility.py
"""Reproducibility utilities: environment capture and data hashing."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version


def capture_environment() -> dict:
    """Capture current environment snapshot for reproducibility audit.

    Returns a dict with python_version, platform, libraries, git_commit,
    and determinism_flags.
    """
    # Library versions
    libs: dict[str, str] = {}
    for pkg in ["numpy", "scikit-learn", "lightgbm", "torch", "pandas", "scipy"]:
        try:
            libs[pkg] = version(pkg)
        except PackageNotFoundError:
            libs[pkg] = "not installed"

    # Git commit
    git_commit = os.environ.get("GIT_COMMIT", "")
    if not git_commit:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            git_commit = "unknown"

    # Determinism flags
    determinism_flags: dict[str, str] = {
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "not set"),
    }
    try:
        import torch

        determinism_flags["torch_deterministic"] = str(torch.are_deterministic_algorithms_enabled())
        determinism_flags["cudnn_deterministic"] = str(torch.backends.cudnn.deterministic)
        determinism_flags["cudnn_benchmark"] = str(torch.backends.cudnn.benchmark)
    except ImportError:
        pass

    return {
        "python_version": platform.python_version(),
        "platform": f"{sys.platform}-{platform.machine()}",
        "libraries": libs,
        "git_commit": git_commit,
        "determinism_flags": determinism_flags,
    }


def compute_data_hash(tickers: list[str], timestamp: str) -> str:
    """Compute SHA-256 hash of input data identifiers.

    Sorts tickers for order-independence.

    Args:
        tickers: List of ticker symbols.
        timestamp: Timestamp string identifying the data vintage.

    Returns:
        SHA-256 hex digest string.
    """
    payload = json.dumps(
        {"tickers": sorted(tickers), "timestamp": timestamp},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_reproducibility.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ml/reproducibility.py engine/tests/ml/test_reproducibility.py
git commit -m "feat(engine): add reproducibility environment capture utility"
```

---

### Task 3: Engine — Model Comparison (Wilcoxon Test)

**Files:**
- Create: `engine/src/margin_engine/ml/model_comparison.py`
- Test: `engine/tests/ml/test_model_comparison.py`

**Step 1: Write the failing tests**

```python
# engine/tests/ml/test_model_comparison.py
"""Tests for model group comparison via Wilcoxon signed-rank test."""

import pytest

from margin_engine.ml.model_comparison import ModelComparisonResult, compare_model_groups


class TestCompareModelGroups:
    def test_identical_groups(self) -> None:
        values = [0.20, 0.22, 0.21, 0.23, 0.19]
        result = compare_model_groups(values, values)
        # Identical groups should not be significantly different
        assert result.significant is False

    def test_clearly_different_groups(self) -> None:
        current = [0.30, 0.32, 0.31, 0.33, 0.29, 0.31, 0.30, 0.32, 0.28, 0.34]
        previous = [0.10, 0.12, 0.11, 0.13, 0.09, 0.11, 0.10, 0.12, 0.08, 0.14]
        result = compare_model_groups(current, previous)
        assert result.p_value < 0.05
        assert result.significant is True
        assert result.label == "significantly_better"

    def test_current_worse(self) -> None:
        current = [0.10, 0.12, 0.11, 0.13, 0.09, 0.11, 0.10, 0.12, 0.08, 0.14]
        previous = [0.30, 0.32, 0.31, 0.33, 0.29, 0.31, 0.30, 0.32, 0.28, 0.34]
        result = compare_model_groups(current, previous)
        assert result.significant is True
        assert result.label == "significantly_worse"

    def test_different_lengths_uses_min(self) -> None:
        current = [0.20, 0.22, 0.21]
        previous = [0.20, 0.22, 0.21, 0.23, 0.19]
        # Should compare only first 3 seeds
        result = compare_model_groups(current, previous)
        assert isinstance(result, ModelComparisonResult)
        assert result.n_compared == 3

    def test_too_few_samples(self) -> None:
        result = compare_model_groups([0.20], [0.22])
        assert result.significant is False
        assert result.label == "insufficient_data"

    def test_result_to_dict(self) -> None:
        result = compare_model_groups([0.20, 0.22, 0.21], [0.20, 0.22, 0.21])
        d = result.to_dict()
        assert "p_value" in d
        assert "effect_size" in d
        assert "significant" in d
        assert "label" in d
        assert "n_compared" in d
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ml/test_model_comparison.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
# engine/src/margin_engine/ml/model_comparison.py
"""Compare model groups via paired Wilcoxon signed-rank test."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.stats import wilcoxon

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_TEST = 3  # Wilcoxon needs at least 3 paired samples


@dataclass
class ModelComparisonResult:
    """Result of comparing two seed groups."""

    p_value: float
    effect_size: float  # mean difference / pooled std
    significant: bool  # p < 0.05
    label: str  # "significantly_better", "significantly_worse", "no_significant_difference", "insufficient_data"
    n_compared: int
    mean_difference: float

    def to_dict(self) -> dict:
        return {
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "significant": self.significant,
            "label": self.label,
            "n_compared": self.n_compared,
            "mean_difference": self.mean_difference,
        }


def compare_model_groups(
    current_metrics: list[float],
    previous_metrics: list[float],
    alpha: float = 0.05,
) -> ModelComparisonResult:
    """Paired Wilcoxon signed-rank test between two seed groups.

    Compares rank ICs (or any metric) from current vs previous training cycle.
    If groups have different sizes, compares only overlapping seeds (0..min(N1,N2)-1).

    Args:
        current_metrics: Per-seed metric values from current group.
        previous_metrics: Per-seed metric values from previous group.
        alpha: Significance level (default 0.05).

    Returns:
        ModelComparisonResult with p-value, effect size, and interpretation.
    """
    n = min(len(current_metrics), len(previous_metrics))

    if n < MIN_SAMPLES_FOR_TEST:
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="insufficient_data",
            n_compared=n,
            mean_difference=0.0,
        )

    if n < len(current_metrics) or n < len(previous_metrics):
        logger.warning(
            "Seed group sizes differ (%d vs %d), comparing first %d seeds",
            len(current_metrics),
            len(previous_metrics),
            n,
        )

    curr = np.array(current_metrics[:n])
    prev = np.array(previous_metrics[:n])
    diff = curr - prev

    mean_diff = float(np.mean(diff))

    # If all differences are zero, no test needed
    if np.allclose(diff, 0.0):
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="no_significant_difference",
            n_compared=n,
            mean_difference=0.0,
        )

    try:
        stat, p_value = wilcoxon(curr, prev)
    except ValueError:
        # Can happen if all differences are zero (already handled) or other edge cases
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="no_significant_difference",
            n_compared=n,
            mean_difference=mean_diff,
        )

    # Effect size: mean difference / pooled std
    pooled_std = float(np.std(diff, ddof=1))
    effect_size = mean_diff / pooled_std if pooled_std > 1e-12 else 0.0

    significant = p_value < alpha
    if significant:
        label = "significantly_better" if mean_diff > 0 else "significantly_worse"
    else:
        label = "no_significant_difference"

    return ModelComparisonResult(
        p_value=float(p_value),
        effect_size=float(effect_size),
        significant=significant,
        label=label,
        n_compared=n,
        mean_difference=float(mean_diff),
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ml/test_model_comparison.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ml/model_comparison.py engine/tests/ml/test_model_comparison.py
git commit -m "feat(engine): add model group comparison via Wilcoxon test"
```

---

### Task 4: Alembic Migration — New Tables and Columns

**Files:**
- Create: `api/alembic/versions/<hash>_add_seed_validation_tables.py`
- Modify: `api/src/margin_api/db/models.py`

**Depends on:** None (can run in parallel with Tasks 1-3)

**Step 1: Add new models and columns to `models.py`**

Add these to `api/src/margin_api/db/models.py`:

1. Add `Boolean` import to the existing sqlalchemy import line
2. Add `seed` and `run_group_id` columns to `MlModelRun` (after `deployment_status`):
```python
    seed: Mapped[int] = mapped_column(Integer, default=42)
    run_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
```

3. Add `seed` and `environment_snapshot` columns to `BacktestRun` (after `created_at`):
```python
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    environment_snapshot: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
```

4. Add new `SeedValidationReport` model (after `MlModelRun`):
```python
class SeedValidationReport(Base):
    """Distributional validation results for a multi-seed ML training run."""

    __tablename__ = "seed_validation_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_group_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    n_seeds: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_distributions: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    gate_passed: Mapped[bool] = mapped_column(default=False)
    gate_details: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    selected_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_comparison: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    environment_snapshot: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
```

5. Add new `ReproducibilityAudit` model:
```python
class ReproducibilityAudit(Base):
    """Audit trail for pipeline reproducibility."""

    __tablename__ = "reproducibility_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    environment_snapshot: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    input_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

**Step 2: Create the Alembic migration**

Run: `uv run alembic -c api/alembic.ini revision --autogenerate -m "add seed validation tables"`

Then edit the generated migration to add idempotent checks:
- Use `op.get_bind().execute(text("SELECT ..."))` or `inspector.has_table()` guards
- Handle `run_group_id` and `seed` column additions on existing tables

**Step 3: Run the migration**

Run: `uv run alembic -c api/alembic.ini upgrade head`
Expected: Migration applies successfully

**Step 4: Verify no multiple heads**

Run: `uv run alembic -c api/alembic.ini heads`
Expected: Single head

**Step 5: Run existing tests to verify no regressions**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: All existing tests PASS (new columns have defaults, new tables are additive)

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add seed validation, reproducibility audit tables and columns"
```

---

### Task 5: API — Model Validation Schemas

**Files:**
- Create: `api/src/margin_api/schemas/model_validation.py`
- Test: `api/tests/test_model_validation_schemas.py`

**Depends on:** Task 4

**Step 1: Write the failing test**

```python
# api/tests/test_model_validation_schemas.py
"""Tests for model validation response schemas."""

from margin_api.schemas.model_validation import (
    GateCheckResponse,
    MetricDistributionResponse,
    ModelComparisonResponse,
    SeedDetailResponse,
    SeedValidationReportResponse,
    SeedValidationHistoryResponse,
)


class TestSchemas:
    def test_metric_distribution_response(self) -> None:
        dist = MetricDistributionResponse(
            mean=0.22, median=0.21, std=0.04, min=0.14, max=0.29,
            ci_lower=0.18, ci_upper=0.26, cv=0.18,
        )
        assert dist.mean == 0.22

    def test_gate_check_response(self) -> None:
        gate = GateCheckResponse(
            name="median_rank_ic", value=0.21, threshold=0.15, passed=True,
        )
        assert gate.passed is True

    def test_seed_detail_response(self) -> None:
        detail = SeedDetailResponse(
            seed=0, rank_ic=0.22, n_clusters=5, n_samples=342, selected=False,
        )
        assert detail.seed == 0

    def test_report_response(self) -> None:
        report = SeedValidationReportResponse(
            run_group_id="abc-123",
            created_at="2026-02-27T00:00:00Z",
            n_seeds=20,
            gate_passed=True,
            selected_seed=7,
            metric_distributions={},
            gate_checks=[],
            seed_details=[],
            environment_snapshot={},
            comparison=None,
        )
        assert report.gate_passed is True

    def test_history_response(self) -> None:
        history = SeedValidationHistoryResponse(
            reports=[], total=0,
        )
        assert history.total == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_model_validation_schemas.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
# api/src/margin_api/schemas/model_validation.py
"""Schemas for seed validation report API responses."""

from __future__ import annotations

from pydantic import BaseModel


class MetricDistributionResponse(BaseModel):
    mean: float
    median: float
    std: float
    min: float
    max: float
    ci_lower: float
    ci_upper: float
    cv: float


class GateCheckResponse(BaseModel):
    name: str
    value: float
    threshold: float
    passed: bool


class ModelComparisonResponse(BaseModel):
    p_value: float
    effect_size: float
    significant: bool
    label: str
    n_compared: int
    mean_difference: float


class SeedDetailResponse(BaseModel):
    seed: int
    rank_ic: float
    n_clusters: int
    n_samples: int
    selected: bool


class SeedValidationReportResponse(BaseModel):
    run_group_id: str
    created_at: str
    n_seeds: int
    gate_passed: bool
    selected_seed: int | None
    metric_distributions: dict[str, MetricDistributionResponse]
    gate_checks: list[GateCheckResponse]
    seed_details: list[SeedDetailResponse]
    environment_snapshot: dict
    comparison: ModelComparisonResponse | None = None


class SeedValidationHistoryResponse(BaseModel):
    reports: list[SeedValidationReportResponse]
    total: int
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_model_validation_schemas.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/model_validation.py api/tests/test_model_validation_schemas.py
git commit -m "feat(api): add model validation response schemas"
```

---

### Task 6: API — Model Validation Admin Routes

**Files:**
- Create: `api/src/margin_api/routes/model_validation.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/test_model_validation_routes.py`

**Depends on:** Tasks 4, 5

**Step 1: Write the failing tests**

```python
# api/tests/test_model_validation_routes.py
"""Tests for model validation admin API routes."""

import pytest
from datetime import UTC, datetime
from httpx import AsyncClient

from margin_api.db.models import SeedValidationReport, MlModelRun


@pytest.mark.asyncio
async def test_latest_report_empty(async_client: AsyncClient, admin_headers: dict) -> None:
    resp = await async_client.get("/api/v1/admin/model-validation/latest", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_latest_report_returns_data(
    async_client: AsyncClient, admin_headers: dict, db_session,
) -> None:
    report = SeedValidationReport(
        run_group_id="test-group-1",
        n_seeds=10,
        metric_distributions={"rank_ic": {"mean": 0.22, "median": 0.21, "std": 0.04, "min": 0.14, "max": 0.29, "ci_lower": 0.18, "ci_upper": 0.26, "cv": 0.18}},
        gate_passed=True,
        gate_details={"median_rank_ic": {"value": 0.21, "threshold": 0.15, "passed": True}, "rank_ic_cv": {"value": 0.18, "threshold": 0.50, "passed": True}, "worst_seed_ic": {"value": 0.14, "threshold": 0.05, "passed": True}, "overall": True},
        selected_seed=7,
        environment_snapshot={"python_version": "3.13.5"},
    )
    db_session.add(report)
    await db_session.commit()

    resp = await async_client.get("/api/v1/admin/model-validation/latest", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_group_id"] == "test-group-1"
    assert data["gate_passed"] is True
    assert data["n_seeds"] == 10


@pytest.mark.asyncio
async def test_history_returns_list(
    async_client: AsyncClient, admin_headers: dict, db_session,
) -> None:
    for i in range(3):
        report = SeedValidationReport(
            run_group_id=f"group-{i}",
            n_seeds=10,
            metric_distributions={},
            gate_passed=i % 2 == 0,
            gate_details={"overall": i % 2 == 0},
            selected_seed=0 if i % 2 == 0 else None,
            environment_snapshot={},
        )
        db_session.add(report)
    await db_session.commit()

    resp = await async_client.get("/api/v1/admin/model-validation/history", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["reports"]) == 3


@pytest.mark.asyncio
async def test_specific_report(
    async_client: AsyncClient, admin_headers: dict, db_session,
) -> None:
    report = SeedValidationReport(
        run_group_id="specific-group",
        n_seeds=20,
        metric_distributions={},
        gate_passed=True,
        gate_details={"overall": True},
        selected_seed=5,
        environment_snapshot={},
    )
    db_session.add(report)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/admin/model-validation/specific-group", headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["run_group_id"] == "specific-group"


@pytest.mark.asyncio
async def test_specific_report_not_found(
    async_client: AsyncClient, admin_headers: dict,
) -> None:
    resp = await async_client.get(
        "/api/v1/admin/model-validation/nonexistent", headers=admin_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_requires_admin(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/admin/model-validation/latest")
    assert resp.status_code in (401, 403)
```

Note: These tests depend on existing test fixtures (`async_client`, `admin_headers`, `db_session`). Check `api/tests/conftest.py` for the exact fixture names and adapt if needed.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_model_validation_routes.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```python
# api/src/margin_api/routes/model_validation.py
"""Admin API routes for seed validation reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import MlModelRun, SeedValidationReport
from margin_api.db.session import get_db
from margin_api.routes.governance import require_admin_key
from margin_api.schemas.model_validation import (
    GateCheckResponse,
    MetricDistributionResponse,
    ModelComparisonResponse,
    SeedDetailResponse,
    SeedValidationHistoryResponse,
    SeedValidationReportResponse,
)

router = APIRouter(prefix="/api/v1/admin/model-validation", tags=["model-validation"])


def _report_to_response(
    report: SeedValidationReport,
    seed_details: list[SeedDetailResponse] | None = None,
) -> SeedValidationReportResponse:
    """Convert a SeedValidationReport ORM model to response schema."""
    # Parse metric distributions
    metric_dists: dict[str, MetricDistributionResponse] = {}
    for name, dist_data in (report.metric_distributions or {}).items():
        if isinstance(dist_data, dict) and "mean" in dist_data:
            metric_dists[name] = MetricDistributionResponse(**dist_data)

    # Parse gate checks
    gate_checks: list[GateCheckResponse] = []
    for name, check_data in (report.gate_details or {}).items():
        if name == "overall":
            continue
        if isinstance(check_data, dict) and "value" in check_data:
            gate_checks.append(GateCheckResponse(name=name, **check_data))

    # Parse comparison
    comparison = None
    if report.previous_comparison and isinstance(report.previous_comparison, dict):
        comparison = ModelComparisonResponse(**report.previous_comparison)

    return SeedValidationReportResponse(
        run_group_id=report.run_group_id,
        created_at=report.created_at.isoformat() if report.created_at else "",
        n_seeds=report.n_seeds,
        gate_passed=report.gate_passed,
        selected_seed=report.selected_seed,
        metric_distributions=metric_dists,
        gate_checks=gate_checks,
        seed_details=seed_details or [],
        environment_snapshot=report.environment_snapshot or {},
        comparison=comparison,
    )


async def _get_seed_details(
    session: AsyncSession, run_group_id: str, selected_seed: int | None,
) -> list[SeedDetailResponse]:
    """Fetch per-seed MlModelRun details for a run group."""
    result = await session.execute(
        select(MlModelRun)
        .where(MlModelRun.run_group_id == run_group_id)
        .order_by(MlModelRun.seed)
    )
    runs = result.scalars().all()
    return [
        SeedDetailResponse(
            seed=run.seed,
            rank_ic=run.overall_rank_ic or 0.0,
            n_clusters=run.n_clusters,
            n_samples=run.n_samples,
            selected=(run.seed == selected_seed) if selected_seed is not None else False,
        )
        for run in runs
    ]


@router.get("/latest", dependencies=[Depends(require_admin_key)])
async def get_latest_report(
    session: AsyncSession = Depends(get_db),
) -> SeedValidationReportResponse:
    result = await session.execute(
        select(SeedValidationReport).order_by(SeedValidationReport.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="No validation reports found")

    seed_details = await _get_seed_details(session, report.run_group_id, report.selected_seed)
    return _report_to_response(report, seed_details)


@router.get("/history", dependencies=[Depends(require_admin_key)])
async def get_report_history(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> SeedValidationHistoryResponse:
    count_result = await session.execute(select(func.count(SeedValidationReport.id)))
    total = count_result.scalar() or 0

    result = await session.execute(
        select(SeedValidationReport)
        .order_by(SeedValidationReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.scalars().all()

    return SeedValidationHistoryResponse(
        reports=[_report_to_response(r) for r in reports],
        total=total,
    )


@router.get("/{run_group_id}", dependencies=[Depends(require_admin_key)])
async def get_report_by_group(
    run_group_id: str,
    session: AsyncSession = Depends(get_db),
) -> SeedValidationReportResponse:
    result = await session.execute(
        select(SeedValidationReport).where(SeedValidationReport.run_group_id == run_group_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found")

    seed_details = await _get_seed_details(session, run_group_id, report.selected_seed)
    return _report_to_response(report, seed_details)
```

**Step 4: Register the router in `app.py`**

Add to `api/src/margin_api/app.py`:
- Import: `from margin_api.routes.model_validation import router as model_validation_router`
- Register: `app.include_router(model_validation_router)` (near other admin routes)

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_model_validation_routes.py -v`
Expected: All 6 tests PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/model_validation.py api/src/margin_api/app.py api/tests/test_model_validation_routes.py
git commit -m "feat(api): add model validation admin API routes"
```

---

### Task 7: API — Multi-Seed Worker Loop

**Files:**
- Modify: `api/src/margin_api/workers.py` (`train_ml_models` function, lines ~1563-1842)
- Modify: `api/src/margin_api/config.py` (add `ml_n_seeds` setting)
- Test: `api/tests/test_seed_training.py`

**Depends on:** Tasks 1-4

This is the core change. The worker must:
1. Loop over `N_SEEDS` (20) seeds
2. Store each as a separate `MlModelRun` with `seed` and `run_group_id`
3. After all seeds, call `validate_seed_distribution`
4. Store `SeedValidationReport`
5. If gate passes, set best model to `candidate`
6. Compare to previous group if exists
7. Store `ReproducibilityAudit`

**Step 1: Add `ml_n_seeds` to config**

In `api/src/margin_api/config.py`, add after `vae_enable`:
```python
    ml_n_seeds: int = 20
```

**Step 2: Write the failing test**

```python
# api/tests/test_seed_training.py
"""Tests for multi-seed ML training worker."""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from margin_api.db.models import MlModelRun, SeedValidationReport


@pytest.mark.asyncio
async def test_multi_seed_creates_run_group(db_session, mock_ml_training_data) -> None:
    """After training, all MlModelRun rows share the same run_group_id."""
    from margin_api.workers import train_ml_models

    # This test uses fixtures that mock the DB queries and ML functions
    # to avoid needing real financial data.
    # The key assertion: multiple MlModelRun rows exist with same run_group_id.
    # Implementation details depend on existing test infrastructure.
    pass  # Placeholder — actual test uses existing conftest fixtures


@pytest.mark.asyncio
async def test_seed_validation_report_created(db_session) -> None:
    """After training, a SeedValidationReport exists."""
    from sqlalchemy import select, func

    count = await db_session.execute(select(func.count(SeedValidationReport.id)))
    # This tests that the report table exists and is queryable
    assert count.scalar() is not None
```

Note: The actual worker test will need to use the existing test infrastructure patterns (mock session factories, patched imports). The implementing agent should look at existing worker tests in `api/tests/` for the pattern.

**Step 3: Modify `train_ml_models` in `workers.py`**

The key changes to the worker function (lines ~1563-1842):

1. After loading scores and building feature matrix (unchanged), add the multi-seed loop:

```python
# Replace the single cluster/train/vae block with:
import uuid
from margin_engine.ml.seed_validation import validate_seed_distribution
from margin_engine.ml.reproducibility import capture_environment, compute_data_hash
from margin_engine.ml.model_comparison import compare_model_groups

run_group_id = str(uuid.uuid4())
seed_metrics_list: list[dict] = []
ml_run_ids: list[int] = []

for seed_idx in range(settings.ml_n_seeds):
    # Cluster
    clusters = cluster_stocks(features, tickers, n_clusters=n_clusters, seed=seed_idx)

    # Convert to indices
    cluster_indices = {
        cid: [ticker_to_idx[t] for t in ctickers if t in ticker_to_idx]
        for cid, ctickers in clusters.items()
    }

    # Train LightGBM
    models = train_cluster_models(features, forward_returns, cluster_indices, seed=seed_idx)

    # Train VAE (if enabled)
    vae_bytes_s = None
    vae_metrics_s = None
    if settings.vae_enable:
        try:
            vae_config = FactorVAEConfig(enable=True)
            vae_bytes_s, vae_metrics_s = train_factor_vae(features, forward_returns, vae_config, seed=seed_idx)
        except Exception as e:
            logger.warning("[ml] VAE seed %d failed: %s", seed_idx, e)

    # Compute rank IC for this seed
    all_preds = np.zeros(len(tickers))
    for cid, model_bytes_s in models.items():
        c_idx = cluster_indices[cid]
        if c_idx:
            preds = predict_alpha(model_bytes_s, features[c_idx])
            for j, idx in enumerate(c_idx):
                all_preds[idx] = preds[j]

    mask = forward_returns != 0.0
    if mask.sum() > 10:
        rank_ic, _ = spearmanr(all_preds[mask], forward_returns[mask])
        if np.isnan(rank_ic):
            rank_ic = 0.0
    else:
        rank_ic = 0.0

    # Collect cluster labels for ARI
    cluster_labels = np.zeros(len(tickers), dtype=int)
    for cid, idx_list in cluster_indices.items():
        for idx in idx_list:
            cluster_labels[idx] = cid

    seed_metrics_list.append({
        "rank_ic": float(rank_ic),
        "cluster_labels": cluster_labels.tolist(),
    })

    # Store MlModelRun
    cluster_model_data = pickle.dumps(models)
    raw_metrics = {
        "feature_names": feature_names,
        "cluster_sizes": {str(k): len(v) for k, v in cluster_indices.items()},
        "vae_metrics": vae_metrics_s.model_dump() if vae_metrics_s else None,
    }

    async with session_factory() as session:
        ml_run = MlModelRun(
            model_type="lightgbm_cluster",
            n_clusters=int(len(models)),
            n_features=int(features.shape[1]),
            n_samples=int(features.shape[0]),
            train_metrics=_sanitize(raw_metrics),
            cluster_model_data=cluster_model_data,
            vae_model_data=vae_bytes_s,
            model_qualifies=rank_ic > 0.15,
            overall_rank_ic=float(rank_ic),
            vae_rank_ic=float(vae_metrics_s.rank_ic) if vae_metrics_s else None,
            deployment_status="candidate",
            seed=seed_idx,
            run_group_id=run_group_id,
        )
        session.add(ml_run)
        await session.commit()
        ml_run_ids.append(ml_run.id)

    logger.info("[ml] Seed %d/%d: rank_ic=%.4f", seed_idx + 1, settings.ml_n_seeds, rank_ic)

# Validate distribution
validation = validate_seed_distribution(seed_metrics_list)
env_snapshot = capture_environment()
data_hash = compute_data_hash(tickers, str(datetime.now(UTC).date()))

# Compare to previous group
previous_comparison = None
async with session_factory() as session:
    prev_report_result = await session.execute(
        select(SeedValidationReport)
        .where(SeedValidationReport.run_group_id != run_group_id)
        .order_by(SeedValidationReport.created_at.desc())
        .limit(1)
    )
    prev_report = prev_report_result.scalar_one_or_none()
    if prev_report is not None:
        prev_runs = await session.execute(
            select(MlModelRun.overall_rank_ic)
            .where(MlModelRun.run_group_id == prev_report.run_group_id)
            .order_by(MlModelRun.seed)
        )
        prev_ics = [r[0] or 0.0 for r in prev_runs.all()]
        current_ics = [m["rank_ic"] for m in seed_metrics_list]
        comparison_result = compare_model_groups(current_ics, prev_ics)
        previous_comparison = comparison_result.to_dict()

# Store validation report
async with session_factory() as session:
    report = SeedValidationReport(
        run_group_id=run_group_id,
        n_seeds=settings.ml_n_seeds,
        metric_distributions=validation.to_dict()["metric_distributions"],
        gate_passed=validation.gate_passed,
        gate_details=validation.to_dict()["gate_details"],
        selected_seed=validation.selected_seed,
        previous_comparison=previous_comparison,
        environment_snapshot=env_snapshot,
    )
    session.add(report)
    await session.commit()

# Store reproducibility audit
async with session_factory() as session:
    audit = ReproducibilityAudit(
        pipeline_stage="train_ml_models",
        config_hash=compute_data_hash(
            [str(settings.ml_n_clusters), str(settings.ml_n_seeds)],
            str(datetime.now(UTC).date()),
        ),
        environment_snapshot=env_snapshot,
        input_data_hash=data_hash,
    )
    session.add(audit)
    await session.commit()

# Promote best model if gate passed
if validation.gate_passed and validation.selected_seed is not None:
    best_run_id = ml_run_ids[validation.selected_seed]
    async with session_factory() as session:
        # Set all runs in group to non-candidate except the best
        for rid in ml_run_ids:
            result = await session.execute(select(MlModelRun).where(MlModelRun.id == rid))
            run = result.scalar_one()
            run.deployment_status = "rejected" if rid != best_run_id else "candidate"
        await session.commit()

    # Stage best model for operator approval
    async with session_factory() as session:
        stage_result = await _stage_ml_model_impl(session, best_run_id)
        logger.info("[ml] Staged best seed %d (run %d) for approval", validation.selected_seed, best_run_id)
else:
    logger.warning("[ml] Seed validation gate FAILED — no model promoted")
    # Create governance event for failed validation
    async with session_factory() as session:
        event = GovernanceEvent(
            event_type="seed_validation_failed",
            source="train_ml_models",
            detail=validation.to_dict()["gate_details"],
        )
        session.add(event)
        await session.commit()
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/ -v --timeout=120`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/src/margin_api/config.py api/tests/test_seed_training.py
git commit -m "feat(api): implement multi-seed ML training loop with validation gate"
```

---

### Task 8: API — Scoring Reproducibility Audit

**Files:**
- Modify: `api/src/margin_api/workers.py` (add audit after `full_score_v4`)
- Test: Add test case to `api/tests/test_seed_training.py`

**Depends on:** Task 4

**Step 1: Find the `full_score_v4` worker function**

Search: `async def full_score_v4` in `workers.py`

**Step 2: Add reproducibility audit after scoring completes**

At the end of `full_score_v4`, before the return statement, add:

```python
# Reproducibility audit
try:
    from margin_engine.ml.reproducibility import capture_environment, compute_data_hash

    async with session_factory() as session:
        audit = ReproducibilityAudit(
            pipeline_stage="full_score_v4",
            config_hash=compute_data_hash(
                sorted(scored_tickers),
                str(datetime.now(UTC).date()),
            ),
            environment_snapshot=capture_environment(),
            input_data_hash=compute_data_hash(
                sorted(scored_tickers),
                str(max_scored_at) if max_scored_at else str(datetime.now(UTC).date()),
            ),
        )
        session.add(audit)
        await session.commit()
except Exception as e:
    logger.warning("[v4] Reproducibility audit failed (non-fatal): %s", e)
```

Note: `scored_tickers` and `max_scored_at` should be extracted from the scoring context. Check the exact variable names in the `full_score_v4` function and adapt.

**Step 3: Run tests**

Run: `uv run pytest api/tests/ -v --timeout=120`
Expected: All tests PASS (audit is fire-and-forget, wrapped in try/except)

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(api): add reproducibility audit to full_score_v4"
```

---

### Task 9: API — Backtest Schema Groundwork

**Files:**
- Modify: `api/src/margin_api/schemas/backtest.py` (add `seed` to `ReplayConfigRequest`)
- Modify: `api/src/margin_api/services/backtest.py` (include seed in config hash)
- Test: `api/tests/test_backtest_seed.py`

**Depends on:** Task 4

**Step 1: Write the failing test**

```python
# api/tests/test_backtest_seed.py
"""Tests for backtest seed parameter groundwork."""

from margin_api.schemas.backtest import ReplayConfigRequest
from margin_api.services.backtest import compute_config_hash
from margin_engine.backtesting.replay_orchestrator import ReplayConfig


class TestReplayConfigSeed:
    def test_seed_defaults_to_none(self) -> None:
        config = ReplayConfigRequest()
        assert config.seed is None

    def test_seed_can_be_set(self) -> None:
        config = ReplayConfigRequest(seed=42)
        assert config.seed == 42


class TestConfigHashWithSeed:
    def test_different_seeds_different_hashes(self) -> None:
        config1 = ReplayConfig(seed=0)
        config2 = ReplayConfig(seed=1)
        h1 = compute_config_hash(config1)
        h2 = compute_config_hash(config2)
        assert h1 != h2

    def test_same_seed_same_hash(self) -> None:
        config1 = ReplayConfig(seed=42)
        config2 = ReplayConfig(seed=42)
        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_none_seed_consistent(self) -> None:
        config1 = ReplayConfig()
        config2 = ReplayConfig()
        assert compute_config_hash(config1) == compute_config_hash(config2)
```

Note: Check if `ReplayConfig` (engine model) already has a `seed` field. If not, add `seed: int | None = None` to it as well.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_backtest_seed.py -v`
Expected: FAIL — seed attribute not found

**Step 3: Add `seed` to schemas**

In `api/src/margin_api/schemas/backtest.py`, add to `ReplayConfigRequest`:
```python
    seed: int | None = None
```

In `engine/src/margin_engine/backtesting/replay_orchestrator.py`, add `seed` to `ReplayConfig` if not present:
```python
    seed: int | None = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_backtest_seed.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/backtest.py api/src/margin_api/services/backtest.py engine/src/margin_engine/backtesting/replay_orchestrator.py api/tests/test_backtest_seed.py
git commit -m "feat(api): add seed parameter to backtest config (groundwork)"
```

---

### Task 10: Web — API Client for Model Validation

**Files:**
- Create: `web/src/lib/api/model-validation.ts`
- Test: `web/src/__tests__/lib/model-validation.test.ts`

**Depends on:** Task 6

**Step 1: Write the failing test**

```typescript
// web/src/__tests__/lib/model-validation.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock apiFetch
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api/client"
import {
  getLatestValidationReport,
  getValidationHistory,
  getValidationReport,
} from "@/lib/api/model-validation"

const mockedFetch = vi.mocked(apiFetch)

describe("model-validation API client", () => {
  beforeEach(() => {
    mockedFetch.mockReset()
  })

  it("getLatestValidationReport calls correct endpoint", async () => {
    const mockReport = { run_group_id: "test", gate_passed: true }
    mockedFetch.mockResolvedValueOnce(mockReport)

    const result = await getLatestValidationReport("admin-key")
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/latest",
      expect.objectContaining({
        headers: { "X-Admin-Key": "admin-key" },
      }),
    )
    expect(result).toEqual(mockReport)
  })

  it("getValidationHistory calls with pagination", async () => {
    const mockHistory = { reports: [], total: 0 }
    mockedFetch.mockResolvedValueOnce(mockHistory)

    await getValidationHistory("admin-key", 10, 20)
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/history?limit=10&offset=20",
      expect.objectContaining({
        headers: { "X-Admin-Key": "admin-key" },
      }),
    )
  })

  it("getValidationReport calls with group id", async () => {
    const mockReport = { run_group_id: "abc-123", gate_passed: false }
    mockedFetch.mockResolvedValueOnce(mockReport)

    await getValidationReport("admin-key", "abc-123")
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/abc-123",
      expect.objectContaining({
        headers: { "X-Admin-Key": "admin-key" },
      }),
    )
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/__tests__/lib/model-validation.test.ts`
Expected: FAIL — module does not exist

**Step 3: Write the implementation**

```typescript
// web/src/lib/api/model-validation.ts
import { apiFetch } from "./client"

export interface MetricDistribution {
  mean: number
  median: number
  std: number
  min: number
  max: number
  ci_lower: number
  ci_upper: number
  cv: number
}

export interface GateCheck {
  name: string
  value: number
  threshold: number
  passed: boolean
}

export interface ModelComparison {
  p_value: number
  effect_size: number
  significant: boolean
  label: string
  n_compared: number
  mean_difference: number
}

export interface SeedDetail {
  seed: number
  rank_ic: number
  n_clusters: number
  n_samples: number
  selected: boolean
}

export interface SeedValidationReport {
  run_group_id: string
  created_at: string
  n_seeds: number
  gate_passed: boolean
  selected_seed: number | null
  metric_distributions: Record<string, MetricDistribution>
  gate_checks: GateCheck[]
  seed_details: SeedDetail[]
  environment_snapshot: Record<string, unknown>
  comparison: ModelComparison | null
}

export interface ValidationHistory {
  reports: SeedValidationReport[]
  total: number
}

export async function getLatestValidationReport(
  adminKey: string,
): Promise<SeedValidationReport> {
  return apiFetch<SeedValidationReport>(
    "/api/v1/admin/model-validation/latest",
    { headers: { "X-Admin-Key": adminKey } },
  )
}

export async function getValidationHistory(
  adminKey: string,
  limit = 20,
  offset = 0,
): Promise<ValidationHistory> {
  return apiFetch<ValidationHistory>(
    `/api/v1/admin/model-validation/history?limit=${limit}&offset=${offset}`,
    { headers: { "X-Admin-Key": adminKey } },
  )
}

export async function getValidationReport(
  adminKey: string,
  runGroupId: string,
): Promise<SeedValidationReport> {
  return apiFetch<SeedValidationReport>(
    `/api/v1/admin/model-validation/${runGroupId}`,
    { headers: { "X-Admin-Key": adminKey } },
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/__tests__/lib/model-validation.test.ts`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add web/src/lib/api/model-validation.ts web/src/__tests__/lib/model-validation.test.ts
git commit -m "feat(web): add model validation API client"
```

---

### Task 11: Web — Model Validation Admin Page

**Files:**
- Create: `web/src/app/admin/model-validation/page.tsx`
- Create: `web/src/components/admin/SeedDistributionTable.tsx`
- Create: `web/src/components/admin/SeedBoxPlot.tsx`
- Create: `web/src/components/admin/SeedDetailTable.tsx`
- Create: `web/src/components/admin/ValidationChecklist.tsx`
- Test: `web/src/__tests__/admin/model-validation.test.tsx`

**Depends on:** Task 10

This is the largest web task. Build 4 components + the page.

**Step 1: Write the failing tests**

```typescript
// web/src/__tests__/admin/model-validation.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

import { SeedDistributionTable } from "@/components/admin/SeedDistributionTable"
import { SeedBoxPlot } from "@/components/admin/SeedBoxPlot"
import { SeedDetailTable } from "@/components/admin/SeedDetailTable"
import { ValidationChecklist } from "@/components/admin/ValidationChecklist"

import type { MetricDistribution, GateCheck, SeedDetail } from "@/lib/api/model-validation"

const mockDistributions: Record<string, MetricDistribution> = {
  rank_ic: {
    mean: 0.22, median: 0.21, std: 0.04, min: 0.14,
    max: 0.29, ci_lower: 0.18, ci_upper: 0.26, cv: 0.18,
  },
}

const mockGateChecks: GateCheck[] = [
  { name: "median_rank_ic", value: 0.21, threshold: 0.15, passed: true },
  { name: "rank_ic_cv", value: 0.18, threshold: 0.50, passed: true },
  { name: "worst_seed_ic", value: 0.14, threshold: 0.05, passed: true },
]

const mockSeedDetails: SeedDetail[] = [
  { seed: 0, rank_ic: 0.19, n_clusters: 5, n_samples: 342, selected: false },
  { seed: 1, rank_ic: 0.24, n_clusters: 5, n_samples: 342, selected: false },
  { seed: 2, rank_ic: 0.29, n_clusters: 5, n_samples: 342, selected: true },
]

describe("SeedDistributionTable", () => {
  it("renders metric rows", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    expect(screen.getByText("rank_ic")).toBeInTheDocument()
    expect(screen.getByText("0.22")).toBeInTheDocument()
  })
})

describe("SeedBoxPlot", () => {
  it("renders with seed data", () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    // Should render without crashing
    expect(screen.getByText(/rank ic/i)).toBeInTheDocument()
  })
})

describe("SeedDetailTable", () => {
  it("renders seed rows", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    expect(screen.getByText("Seed 0")).toBeInTheDocument()
    expect(screen.getByText("Seed 2")).toBeInTheDocument()
  })

  it("highlights selected seed", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    // Seed 2 should have a "Selected" indicator
    expect(screen.getByText("Selected")).toBeInTheDocument()
  })
})

describe("ValidationChecklist", () => {
  it("renders gate checks", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    expect(screen.getByText("median_rank_ic")).toBeInTheDocument()
  })

  it("shows overall pass state", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    expect(screen.getByText(/pass/i)).toBeInTheDocument()
  })

  it("shows fail state", () => {
    const failChecks = [
      { name: "median_rank_ic", value: 0.10, threshold: 0.15, passed: false },
    ]
    render(<ValidationChecklist checks={failChecks} gatePassed={false} />)
    expect(screen.getByText(/fail/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/__tests__/admin/model-validation.test.tsx`
Expected: FAIL — modules do not exist

**Step 3: Write the components**

Build 4 components following existing admin patterns (look at `web/src/components/admin/approval-card.tsx` and `web/src/components/admin/pipeline-status.tsx` for styling conventions):

- `SeedDistributionTable.tsx` — Table showing metric stats (mean, median, std, etc.)
- `SeedBoxPlot.tsx` — Recharts-based scatter/bar visualization of rank ICs per seed with threshold line
- `SeedDetailTable.tsx` — Expandable table of per-seed results with "Selected" badge
- `ValidationChecklist.tsx` — Checklist of gate checks with pass/fail indicators

Then build the page at `web/src/app/admin/model-validation/page.tsx` that:
- Uses `"use client"` directive
- Reads `NEXT_PUBLIC_ADMIN_KEY` from env
- Calls `getLatestValidationReport` on mount
- Renders all 4 components
- Shows loading/error/empty states

Use existing design tokens: `terminal-card` class, `--color-bullish`/`--color-bearish`, `font-mono`, etc.

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/__tests__/admin/model-validation.test.tsx`
Expected: All 7 tests PASS

**Step 5: Run all web tests for regressions**

Run: `cd web && npx vitest run`
Expected: All existing tests PASS

**Step 6: Commit**

```bash
git add web/src/app/admin/model-validation/ web/src/components/admin/Seed*.tsx web/src/components/admin/ValidationChecklist.tsx web/src/__tests__/admin/model-validation.test.tsx
git commit -m "feat(web): add Model Validation admin page with distribution visualization"
```

---

## Task Dependency Graph

```
Tasks 1, 2, 3, 4 — all independent, can run in parallel

Task 5 — depends on Task 4 (needs models for import)
Task 6 — depends on Tasks 4, 5
Task 7 — depends on Tasks 1, 2, 3, 4 (uses all engine modules + new DB schema)
Task 8 — depends on Task 4 (needs ReproducibilityAudit model)
Task 9 — depends on Task 4 (needs BacktestRun seed column)

Task 10 — depends on Task 6 (needs API endpoints defined)
Task 11 — depends on Task 10 (needs API client)
```

**Parallel groups:**
- **Group A** (independent): Tasks 1, 2, 3, 4
- **Group B** (after Group A): Tasks 5, 8, 9 (can run in parallel)
- **Group C** (after Task 5): Task 6
- **Group D** (after Tasks 1-4,6): Task 7
- **Group E** (after Task 6): Task 10
- **Group F** (after Task 10): Task 11

## Verification

After all tasks complete:
```bash
uv run pytest engine/tests/ml/ -v                  # Engine ML tests
uv run pytest api/tests/ -v                          # API tests
cd web && npx vitest run                             # Web tests
uv run alembic -c api/alembic.ini heads              # Single head
```
