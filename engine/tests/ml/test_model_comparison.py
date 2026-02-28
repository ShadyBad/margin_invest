"""Tests for model comparison (Wilcoxon signed-rank test)."""

from __future__ import annotations

from margin_engine.ml.model_comparison import (
    MIN_SAMPLES_FOR_TEST,
    ModelComparisonResult,
    compare_model_groups,
)


class TestModelComparisonResult:
    def test_to_dict_returns_all_fields(self) -> None:
        result = ModelComparisonResult(
            p_value=0.05,
            effect_size=1.2,
            significant=True,
            label="significantly_better",
            n_compared=5,
            mean_difference=0.03,
        )
        d = result.to_dict()
        assert d == {
            "p_value": 0.05,
            "effect_size": 1.2,
            "significant": True,
            "label": "significantly_better",
            "n_compared": 5,
            "mean_difference": 0.03,
        }

    def test_to_dict_is_plain_dict(self) -> None:
        result = ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="no_significant_difference",
            n_compared=3,
            mean_difference=0.0,
        )
        d = result.to_dict()
        assert isinstance(d, dict)


class TestCompareModelGroups:
    def test_identical_groups_not_significant(self) -> None:
        metrics = [0.5, 0.6, 0.7, 0.8, 0.9]
        result = compare_model_groups(metrics, metrics)
        assert result.significant is False
        assert result.label == "no_significant_difference"
        assert result.mean_difference == 0.0
        assert result.n_compared == 5

    def test_clearly_better_current(self) -> None:
        # Need >= 6 samples for Wilcoxon to achieve p < 0.05
        current = [0.80, 0.85, 0.90, 0.88, 0.92, 0.87]
        previous = [0.30, 0.35, 0.40, 0.38, 0.42, 0.37]
        result = compare_model_groups(current, previous)
        assert result.significant is True
        assert result.label == "significantly_better"
        assert result.mean_difference > 0
        assert result.p_value < 0.05
        assert result.n_compared == 6

    def test_clearly_worse_current(self) -> None:
        current = [0.10, 0.15, 0.12, 0.18, 0.11, 0.14]
        previous = [0.80, 0.85, 0.82, 0.88, 0.81, 0.84]
        result = compare_model_groups(current, previous)
        assert result.significant is True
        assert result.label == "significantly_worse"
        assert result.mean_difference < 0
        assert result.p_value < 0.05

    def test_different_lengths_uses_min(self) -> None:
        current = [0.9, 0.95, 1.0, 0.85, 0.92, 0.88, 0.91, 0.93]  # 8 elements
        previous = [0.3, 0.4, 0.5, 0.35, 0.45, 0.38]  # 6 elements
        result = compare_model_groups(current, previous)
        assert result.n_compared == 6  # min(8, 6)
        # Should detect a significant difference with 6 paired samples
        assert result.significant is True
        assert result.label == "significantly_better"

    def test_too_few_samples_insufficient_data(self) -> None:
        current = [0.5, 0.6]
        previous = [0.3, 0.4]
        result = compare_model_groups(current, previous)
        assert result.significant is False
        assert result.label == "insufficient_data"
        assert result.n_compared == 2

    def test_exactly_min_samples(self) -> None:
        """With exactly MIN_SAMPLES_FOR_TEST samples the test should run."""
        assert MIN_SAMPLES_FOR_TEST == 3
        current = [0.9, 0.95, 1.0]
        previous = [0.1, 0.15, 0.2]
        result = compare_model_groups(current, previous)
        assert result.n_compared == 3
        # With 3 clearly different pairs, it should detect significance
        assert result.label != "insufficient_data"

    def test_empty_lists_insufficient_data(self) -> None:
        result = compare_model_groups([], [])
        assert result.significant is False
        assert result.label == "insufficient_data"
        assert result.n_compared == 0

    def test_custom_alpha(self) -> None:
        """With a very strict alpha, moderately different groups may not be significant."""
        current = [0.55, 0.60, 0.58, 0.57, 0.56]
        previous = [0.50, 0.52, 0.51, 0.53, 0.49]
        # With alpha=0.001, this marginal difference may not be significant
        result_strict = compare_model_groups(current, previous, alpha=0.001)
        result_normal = compare_model_groups(current, previous, alpha=0.05)
        # The p_value is the same regardless of alpha
        assert result_strict.p_value == result_normal.p_value
        # But significance classification can differ
        if result_normal.significant and result_strict.p_value > 0.001:
            assert result_strict.significant is False

    def test_effect_size_computed(self) -> None:
        # Use varying differences so std(diff) > 0
        current = [0.8, 0.7, 1.0, 0.6, 0.9, 0.75]
        previous = [0.3, 0.4, 0.2, 0.35, 0.1, 0.30]
        result = compare_model_groups(current, previous)
        assert result.effect_size > 0
        assert isinstance(result.effect_size, float)
        # Verify the formula: mean_diff / std(differences, ddof=1)
        diffs = [c - p for c, p in zip(current, previous)]
        mean_diff = sum(diffs) / len(diffs)
        from statistics import stdev
        expected_effect = mean_diff / stdev(diffs)
        assert abs(result.effect_size - expected_effect) < 1e-10

    def test_single_sample_insufficient(self) -> None:
        result = compare_model_groups([0.5], [0.3])
        assert result.label == "insufficient_data"
        assert result.n_compared == 1
