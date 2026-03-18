"""Tests for Optuna weight optimizer."""

from __future__ import annotations

import pytest

optuna = pytest.importorskip("optuna", reason="optuna not installed (optional dep)")

from margin_engine.tuning.weight_optimizer import suggest_track_weights  # noqa: E402


class TestWeightConstraints:
    def test_weights_sum_to_one(self):
        """All suggested weight sets must sum to 1.0."""
        study = optuna.create_study(direction="maximize")

        def objective(trial):
            weights = suggest_track_weights(
                trial,
                factor_names=["a", "b", "c", "d"],
                min_weight=0.10,
                max_weight=0.50,
            )
            if weights is None:
                raise optuna.TrialPruned()
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-9
            return 1.0

        study.optimize(objective, n_trials=20, show_progress_bar=False)

    def test_all_weights_within_bounds(self):
        """Each weight must be within [min_weight, max_weight]."""
        study = optuna.create_study(direction="maximize")

        def objective(trial):
            weights = suggest_track_weights(
                trial,
                factor_names=["a", "b", "c", "d"],
                min_weight=0.10,
                max_weight=0.50,
            )
            if weights is None:
                raise optuna.TrialPruned()
            for w in weights.values():
                assert 0.10 <= w <= 0.50
            return 1.0

        study.optimize(objective, n_trials=20, show_progress_bar=False)
