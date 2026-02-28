"""Tests for seed validation module."""

from __future__ import annotations

import math

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
        values = [0.20, 0.25, 0.30, 0.35, 0.40]
        dist = compute_metric_distribution(values)
        assert dist.mean == pytest.approx(0.30)
        assert dist.median == pytest.approx(0.30)
        assert dist.min == pytest.approx(0.20)
        assert dist.max == pytest.approx(0.40)
        # std with ddof=1
        expected_std = float(np.std(values, ddof=1))
        assert dist.std == pytest.approx(expected_std)
        # CI should contain the mean
        assert dist.ci_lower <= dist.mean
        assert dist.ci_upper >= dist.mean
        # CV = std / mean
        assert dist.cv == pytest.approx(expected_std / 0.30)

    def test_single_value(self) -> None:
        dist = compute_metric_distribution([0.25])
        assert dist.mean == pytest.approx(0.25)
        assert dist.median == pytest.approx(0.25)
        assert dist.std == pytest.approx(0.0)
        assert dist.min == pytest.approx(0.25)
        assert dist.max == pytest.approx(0.25)
        # CI collapses to the mean for n=1
        assert dist.ci_lower == pytest.approx(0.25)
        assert dist.ci_upper == pytest.approx(0.25)
        # CV = 0 / 0.25 = 0
        assert dist.cv == pytest.approx(0.0)

    def test_two_values(self) -> None:
        values = [0.10, 0.30]
        dist = compute_metric_distribution(values)
        assert dist.mean == pytest.approx(0.20)
        assert dist.median == pytest.approx(0.20)
        expected_std = float(np.std(values, ddof=1))
        assert dist.std == pytest.approx(expected_std)
        # With n=2, t-distribution CI is very wide but should still contain mean
        assert dist.ci_lower <= dist.mean
        assert dist.ci_upper >= dist.mean

    def test_ci_width_decreases_with_more_samples(self) -> None:
        """More samples should yield a tighter confidence interval."""
        rng = np.random.default_rng(42)
        small = rng.normal(0.25, 0.05, size=5).tolist()
        large = rng.normal(0.25, 0.05, size=50).tolist()
        dist_small = compute_metric_distribution(small)
        dist_large = compute_metric_distribution(large)
        width_small = dist_small.ci_upper - dist_small.ci_lower
        width_large = dist_large.ci_upper - dist_large.ci_lower
        assert width_large < width_small


class TestMetricDistributionToDict:
    def test_to_dict_keys(self) -> None:
        dist = compute_metric_distribution([0.20, 0.30, 0.40])
        d = dist.to_dict()
        expected_keys = {"mean", "median", "std", "min", "max", "ci_lower", "ci_upper", "cv"}
        assert set(d.keys()) == expected_keys

    def test_to_dict_values_are_float(self) -> None:
        dist = compute_metric_distribution([0.20, 0.30, 0.40])
        d = dist.to_dict()
        for key, value in d.items():
            assert isinstance(value, float), f"{key} is {type(value)}, expected float"


class TestSeedValidationThresholds:
    def test_defaults(self) -> None:
        t = SeedValidationThresholds()
        assert t.min_median_rank_ic == pytest.approx(0.15)
        assert t.max_rank_ic_cv == pytest.approx(0.50)
        assert t.min_worst_seed_ic == pytest.approx(0.05)


class TestValidateSeedDistribution:
    def _make_seed_metrics(
        self, rank_ics: list[float], cluster_labels: list[list[int]] | None = None
    ) -> list[dict]:
        metrics = []
        for i, ic in enumerate(rank_ics):
            d: dict = {"rank_ic": ic, "seed": i}
            if cluster_labels is not None:
                d["cluster_labels"] = cluster_labels[i]
            metrics.append(d)
        return metrics

    def test_passing_distribution(self) -> None:
        """All ICs well above thresholds — gate should pass."""
        ics = [0.25, 0.28, 0.30, 0.27, 0.26]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert result.gate_passed is True
        assert result.selected_seed is not None
        assert "rank_ic" in result.metric_distributions
        assert result.gate_details["overall"]["passed"] is True

    def test_failing_low_median(self) -> None:
        """All ICs below 0.15 — median check should fail."""
        ics = [0.10, 0.11, 0.12, 0.09, 0.13]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert result.gate_passed is False
        assert result.selected_seed is None
        assert result.gate_details["median_rank_ic"]["passed"] is False

    def test_failing_high_cv(self) -> None:
        """Wildly varying ICs — CV check should fail."""
        ics = [0.50, 0.05, 0.45, 0.06, 0.48]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert result.gate_passed is False
        assert result.selected_seed is None
        assert result.gate_details["rank_ic_cv"]["passed"] is False

    def test_failing_worst_seed(self) -> None:
        """One IC below 0.05 floor — worst seed check should fail."""
        ics = [0.20, 0.22, 0.18, 0.04, 0.21]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert result.gate_passed is False
        assert result.selected_seed is None
        assert result.gate_details["min_rank_ic"]["passed"] is False

    def test_selects_best_ic_seed(self) -> None:
        """Should select the seed with the highest rank_ic."""
        ics = [0.20, 0.30, 0.25, 0.28, 0.22]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert result.gate_passed is True
        # Index 1 has the highest IC (0.30)
        assert result.selected_seed == 1

    def test_custom_thresholds(self) -> None:
        """Custom thresholds should override defaults."""
        ics = [0.10, 0.11, 0.12, 0.09, 0.13]
        # With lower thresholds, this should pass
        thresholds = SeedValidationThresholds(
            min_median_rank_ic=0.08,
            max_rank_ic_cv=0.60,
            min_worst_seed_ic=0.05,
        )
        result = validate_seed_distribution(self._make_seed_metrics(ics), thresholds=thresholds)
        assert result.gate_passed is True
        assert result.selected_seed is not None

    def test_gate_details_structure(self) -> None:
        """Gate details should have per-check dicts with value/threshold/passed."""
        ics = [0.25, 0.28, 0.30, 0.27, 0.26]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        for check_name in ["median_rank_ic", "rank_ic_cv", "min_rank_ic"]:
            detail = result.gate_details[check_name]
            assert "value" in detail
            assert "threshold" in detail
            assert "passed" in detail
        assert "overall" in result.gate_details
        assert "passed" in result.gate_details["overall"]

    def test_with_cluster_labels_computes_ari(self) -> None:
        """When cluster_labels present, should compute ARI distribution."""
        ics = [0.25, 0.28, 0.30, 0.27, 0.26]
        # 10 items, 3 seeds with same-ish cluster assignments
        labels = [
            [0, 0, 1, 1, 2, 2, 0, 1, 2, 0],
            [0, 0, 1, 1, 2, 2, 0, 1, 2, 0],
            [1, 1, 0, 0, 2, 2, 1, 0, 2, 1],
            [0, 0, 1, 1, 2, 2, 0, 1, 2, 0],
            [0, 0, 1, 1, 2, 2, 0, 1, 2, 0],
        ]
        result = validate_seed_distribution(self._make_seed_metrics(ics, cluster_labels=labels))
        assert "cluster_ari" in result.metric_distributions
        ari_dist = result.metric_distributions["cluster_ari"]
        # ARI is between -0.5 and 1.0; identical labelings yield 1.0
        assert ari_dist.min >= -0.5
        assert ari_dist.max <= 1.0

    def test_without_cluster_labels_no_ari(self) -> None:
        """Without cluster_labels, no ARI distribution should be computed."""
        ics = [0.25, 0.28, 0.30]
        result = validate_seed_distribution(self._make_seed_metrics(ics))
        assert "cluster_ari" not in result.metric_distributions


class TestSeedValidationResultToDict:
    def test_to_dict_serializable(self) -> None:
        """to_dict() output should be JSON-serializable (all native types)."""
        import json

        ics = [0.25, 0.28, 0.30, 0.27, 0.26]
        result = validate_seed_distribution(
            [{"rank_ic": ic, "seed": i} for i, ic in enumerate(ics)]
        )
        d = result.to_dict()
        # Should not raise
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_to_dict_keys(self) -> None:
        ics = [0.25, 0.28, 0.30]
        result = validate_seed_distribution(
            [{"rank_ic": ic, "seed": i} for i, ic in enumerate(ics)]
        )
        d = result.to_dict()
        assert "metric_distributions" in d
        assert "gate_passed" in d
        assert "gate_details" in d
        assert "selected_seed" in d

    def test_to_dict_distributions_are_dicts(self) -> None:
        ics = [0.25, 0.28, 0.30]
        result = validate_seed_distribution(
            [{"rank_ic": ic, "seed": i} for i, ic in enumerate(ics)]
        )
        d = result.to_dict()
        for key, dist_dict in d["metric_distributions"].items():
            assert isinstance(dist_dict, dict), f"{key} distribution is not a dict"
            assert "mean" in dist_dict
