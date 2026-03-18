"""Optuna-based weight and balance bonus optimization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import optuna

from margin_engine.config.v3_scoring_config import TrackWeights, V3CompositeConfig


@dataclass
class WeightTuneResult:
    """Result of a weight tuning optimization run."""

    track: str
    best_weights: dict[str, float]
    best_multiplier: float
    best_threshold: float
    best_sharpe: float
    baseline_sharpe: float
    improvement_pct: float
    n_trials: int


def suggest_track_weights(
    trial: optuna.Trial,
    factor_names: list[str],
    min_weight: float = 0.10,
    max_weight: float = 0.50,
) -> dict[str, float] | None:
    """Suggest a valid set of factor weights that sum to 1.0.

    Samples N-1 weights freely, derives the Nth as 1.0 - sum(others).
    Returns None if the derived weight falls outside [min_weight, max_weight].
    """
    weights: dict[str, float] = {}
    running_sum = 0.0

    for name in factor_names[:-1]:
        remaining_factors = len(factor_names) - len(weights) - 1
        upper = min(max_weight, 1.0 - running_sum - remaining_factors * min_weight)
        lower = max(min_weight, 1.0 - running_sum - remaining_factors * max_weight - max_weight)
        lower = max(lower, min_weight)

        if upper < lower:
            return None

        w = trial.suggest_float(name, lower, upper)
        weights[name] = w
        running_sum += w

    last = 1.0 - running_sum
    if last < min_weight or last > max_weight:
        return None
    weights[factor_names[-1]] = last

    return weights


def build_config_from_trial(
    trial: optuna.Trial,
    track: str,
    factor_names: list[str],
) -> V3CompositeConfig | None:
    """Build a V3CompositeConfig from Optuna trial suggestions.

    Returns None if weight constraints cannot be satisfied.
    """
    weights = suggest_track_weights(trial, factor_names)
    if weights is None:
        return None

    multiplier = trial.suggest_float("balance_bonus_multiplier", 1.0, 1.15)
    threshold = trial.suggest_float("balance_bonus_threshold", 0.25, 0.55)

    track_weights = TrackWeights(weights=weights)

    config = V3CompositeConfig(
        balance_bonus_multiplier=multiplier,
        balance_bonus_threshold=threshold,
    )

    if track == "A":
        config.track_a_weights = track_weights
    elif track == "B":
        config.track_b_weights = track_weights
    elif track == "C":
        config.track_c_weights = track_weights

    return config


TRACK_FACTORS: dict[str, list[str]] = {
    "A": ["moat_durability", "compounding_power", "capital_allocation", "growth_gap"],
    "B": ["asymmetry_ratio", "catalyst_strength", "quality_floor_factor", "valuation_convergence"],
    "C": ["growth_efficiency", "unit_economics", "capital_efficiency", "growth_durability"],
}
