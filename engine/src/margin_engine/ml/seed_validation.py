"""Seed validation: statistical gates for multi-seed ML training."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy import stats
from sklearn.metrics import adjusted_rand_score


@dataclass
class MetricDistribution:
    """Descriptive statistics for a metric across seeds."""

    mean: float
    median: float
    std: float
    min: float
    max: float
    ci_lower: float
    ci_upper: float
    cv: float

    def to_dict(self) -> dict[str, float]:
        return {
            "mean": float(self.mean),
            "median": float(self.median),
            "std": float(self.std),
            "min": float(self.min),
            "max": float(self.max),
            "ci_lower": float(self.ci_lower),
            "ci_upper": float(self.ci_upper),
            "cv": float(self.cv),
        }


@dataclass
class SeedValidationThresholds:
    """Gate thresholds for seed validation."""

    min_median_rank_ic: float = 0.15
    max_rank_ic_cv: float = 0.50
    min_worst_seed_ic: float = 0.05


@dataclass
class SeedValidationResult:
    """Result of validating a distribution of seed metrics."""

    metric_distributions: dict[str, MetricDistribution]
    gate_passed: bool
    gate_details: dict
    selected_seed: int | None

    def to_dict(self) -> dict:
        return {
            "metric_distributions": {k: v.to_dict() for k, v in self.metric_distributions.items()},
            "gate_passed": self.gate_passed,
            "gate_details": self.gate_details,
            "selected_seed": self.selected_seed,
        }


def compute_metric_distribution(values: list[float]) -> MetricDistribution:
    """Compute descriptive statistics for a list of metric values.

    Uses t-distribution for 95% confidence interval. For n=1, std is 0
    and the CI collapses to the single value.

    Args:
        values: List of metric values across seeds.

    Returns:
        MetricDistribution with all summary statistics.
    """
    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    if n == 1:
        return MetricDistribution(
            mean=mean,
            median=median,
            std=0.0,
            min=min_val,
            max=max_val,
            ci_lower=mean,
            ci_upper=mean,
            cv=0.0,
        )

    std = float(np.std(arr, ddof=1))
    se = std / np.sqrt(n)
    t_crit = stats.t.ppf(0.975, df=n - 1)
    ci_lower = mean - t_crit * se
    ci_upper = mean + t_crit * se
    cv = std / mean if mean != 0.0 else 0.0

    return MetricDistribution(
        mean=mean,
        median=median,
        std=std,
        min=min_val,
        max=max_val,
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        cv=float(cv),
    )


def validate_seed_distribution(
    seed_metrics: list[dict],
    thresholds: SeedValidationThresholds | None = None,
) -> SeedValidationResult:
    """Validate that multi-seed training results are stable and sufficient.

    Extracts rank_ic from each seed's metrics dict, computes distribution
    statistics, and runs gate checks against thresholds. If cluster_labels
    are present in all dicts, computes pairwise Adjusted Rand Index.

    Args:
        seed_metrics: List of dicts, each containing at least "rank_ic".
            Optionally "cluster_labels" (list[int]) for ARI computation.
        thresholds: Gate thresholds. Defaults to SeedValidationThresholds().

    Returns:
        SeedValidationResult with distributions, gate outcome, and selected seed.
    """
    if thresholds is None:
        thresholds = SeedValidationThresholds()

    # Extract rank_ic values
    rank_ics = [m["rank_ic"] for m in seed_metrics]
    distributions: dict[str, MetricDistribution] = {}

    ic_dist = compute_metric_distribution(rank_ics)
    distributions["rank_ic"] = ic_dist

    # Compute pairwise ARI if cluster_labels present in all dicts
    if all("cluster_labels" in m for m in seed_metrics):
        labels_list = [m["cluster_labels"] for m in seed_metrics]
        ari_values: list[float] = []
        for i, j in combinations(range(len(labels_list)), 2):
            ari = adjusted_rand_score(labels_list[i], labels_list[j])
            ari_values.append(float(ari))
        if ari_values:
            distributions["cluster_ari"] = compute_metric_distribution(ari_values)

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
    min_ic_check = {
        "value": ic_dist.min,
        "threshold": thresholds.min_worst_seed_ic,
        "passed": ic_dist.min >= thresholds.min_worst_seed_ic,
    }

    all_passed = median_check["passed"] and cv_check["passed"] and min_ic_check["passed"]

    gate_details = {
        "median_rank_ic": median_check,
        "rank_ic_cv": cv_check,
        "min_rank_ic": min_ic_check,
        "overall": {"passed": all_passed},
    }

    selected_seed: int | None = None
    if all_passed:
        selected_seed = int(np.argmax(rank_ics))

    return SeedValidationResult(
        metric_distributions=distributions,
        gate_passed=all_passed,
        gate_details=gate_details,
        selected_seed=selected_seed,
    )
