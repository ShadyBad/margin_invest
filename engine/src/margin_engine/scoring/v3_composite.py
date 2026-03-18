"""v3 Weighted Geometric Mean Composite Scoring.

Replaces pure multiplication with weighted geometric mean + floor.
A zero in any factor no longer kills the entire score — factors are floored
at ``config.factor_floor`` before the geometric mean is computed.

Formula: score = max(exp(sum(w_i * ln(max(f_i, floor)))), composite_floor)
"""

from __future__ import annotations

import math

from margin_engine.config.v3_scoring_config import V3CompositeConfig

_ASYMMETRY_CAP = 20.0
_DEFAULT_CONFIG = V3CompositeConfig()


def _weighted_geometric_mean(
    factors: list[float],
    weights: list[float],
    factor_floor: float,
    composite_floor: float,
) -> float:
    """Compute weighted geometric mean with per-factor floor.

    score = exp(sum(w_i * ln(max(f_i, factor_floor))))
    Final result is floored at composite_floor.
    """
    log_sum = 0.0
    for f, w in zip(factors, weights):
        floored = max(f, factor_floor)
        log_sum += w * math.log(floored)
    score = math.exp(log_sum)
    return max(score, composite_floor)


def _apply_balance_bonus(
    score: float,
    factors: list[float],
    threshold: float,
    multiplier: float,
) -> float:
    """Apply balance bonus if multiplier != 1.0 and all factors exceed threshold."""
    if multiplier == 1.0:
        return score
    if all(f > threshold for f in factors):
        return score * multiplier
    return score


def compute_track_a_score(
    moat_durability: float,
    compounding_power: float,
    capital_allocation: float,
    growth_gap: float,
    config: V3CompositeConfig | None = None,
) -> float:
    """Compute Track A (Compounder) score via weighted geometric mean.

    score = exp(sum(w_i * ln(max(factor_i, floor))))
    """
    cfg = config or _DEFAULT_CONFIG
    w = cfg.track_a_weights.weights
    factors = [moat_durability, compounding_power, capital_allocation, growth_gap]
    weights = [
        w["moat_durability"],
        w["compounding_power"],
        w["capital_allocation"],
        w["growth_gap"],
    ]
    score = _weighted_geometric_mean(factors, weights, cfg.factor_floor, cfg.composite_floor)
    return _apply_balance_bonus(
        score, factors, cfg.balance_bonus_threshold, cfg.balance_bonus_multiplier
    )


def compute_track_b_score(
    asymmetry_ratio: float,
    catalyst_strength: float,
    quality_floor_factor: float,
    valuation_convergence: float,
    config: V3CompositeConfig | None = None,
) -> float:
    """Compute Track B (Mispricing) score via weighted geometric mean.

    Asymmetry ratio is capped at _ASYMMETRY_CAP before the geometric mean.
    """
    cfg = config or _DEFAULT_CONFIG
    capped_asymmetry = min(asymmetry_ratio, _ASYMMETRY_CAP)
    w = cfg.track_b_weights.weights
    factors = [capped_asymmetry, catalyst_strength, quality_floor_factor, valuation_convergence]
    weights = [
        w["asymmetry_ratio"],
        w["catalyst_strength"],
        w["quality_floor_factor"],
        w["valuation_convergence"],
    ]
    score = _weighted_geometric_mean(factors, weights, cfg.factor_floor, cfg.composite_floor)
    return _apply_balance_bonus(
        score, factors, cfg.balance_bonus_threshold, cfg.balance_bonus_multiplier
    )


def compute_track_c_score(
    growth_efficiency: float,
    unit_economics: float,
    capital_efficiency: float,
    growth_durability: float,
    config: V3CompositeConfig | None = None,
) -> float:
    """Track C (Efficient Growth) score via weighted geometric mean."""
    cfg = config or _DEFAULT_CONFIG
    w = cfg.track_c_weights.weights
    factors = [growth_efficiency, unit_economics, capital_efficiency, growth_durability]
    weights = [
        w["growth_efficiency"],
        w["unit_economics"],
        w["capital_efficiency"],
        w["growth_durability"],
    ]
    score = _weighted_geometric_mean(factors, weights, cfg.factor_floor, cfg.composite_floor)
    return _apply_balance_bonus(
        score, factors, cfg.balance_bonus_threshold, cfg.balance_bonus_multiplier
    )
