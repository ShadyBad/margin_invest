"""Tests for Optuna weight optimizer."""

from __future__ import annotations

import pytest

optuna = pytest.importorskip("optuna", reason="optuna not installed (optional dep)")

from margin_engine.tuning.weight_optimizer import (  # noqa: E402
    build_config_from_trial,
    suggest_track_weights,
)


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


class TestBuildConfigFromTrial:
    FACTORS = ["a", "b", "c", "d"]

    def test_build_config_for_each_track(self):
        """A feasible trial yields a config with the weights on the right track."""
        for track, attr in (
            ("A", "track_a_weights"),
            ("B", "track_b_weights"),
            ("C", "track_c_weights"),
        ):
            trial = optuna.trial.FixedTrial(
                {
                    "a": 0.25,
                    "b": 0.25,
                    "c": 0.25,
                    "balance_bonus_multiplier": 1.05,
                    "balance_bonus_threshold": 0.40,
                }
            )
            config = build_config_from_trial(trial, track, self.FACTORS)
            assert config is not None
            assert config.balance_bonus_multiplier == 1.05
            assert config.balance_bonus_threshold == 0.40
            track_weights = getattr(config, attr)
            assert abs(sum(track_weights.weights.values()) - 1.0) < 1e-9

    def test_build_config_returns_none_when_weights_infeasible(self):
        """Weights that cannot sum to 1.0 within bounds propagate as None."""
        trial = optuna.trial.FixedTrial({"a": 0.5, "b": 0.5, "c": 0.5})
        assert build_config_from_trial(trial, "A", self.FACTORS) is None
