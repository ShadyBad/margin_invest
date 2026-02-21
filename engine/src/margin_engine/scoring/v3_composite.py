"""v3 Multiplicative Composite Scoring.

Replaces additive percentile averaging with multiplicative products.
A zero in any critical factor produces a zero score.
Magnitude differences are preserved (5x better = 5x higher score).
"""

from __future__ import annotations

_ASYMMETRY_CAP = 20.0


def compute_track_a_score(
    moat_durability: float,
    compounding_power: float,
    capital_allocation: float,
    growth_gap: float,
) -> float:
    """Compute Track A (Compounder) multiplicative score.

    score = moat_durability * compounding_power * capital_allocation * growth_gap
    """
    return moat_durability * compounding_power * capital_allocation * growth_gap


def compute_track_b_score(
    asymmetry_ratio: float,
    catalyst_strength: float,
    quality_floor_factor: float,
    valuation_convergence: float,
) -> float:
    """Compute Track B (Mispricing) multiplicative score.

    score = min(asymmetry, 20) * catalyst * quality_floor * convergence
    """
    capped_asymmetry = min(asymmetry_ratio, _ASYMMETRY_CAP)
    return capped_asymmetry * catalyst_strength * quality_floor_factor * valuation_convergence


def compute_track_c_score(
    growth_efficiency: float,
    unit_economics: float,
    capital_efficiency: float,
    growth_durability: float,
) -> float:
    """Track C multiplicative score: GE x UE x CE x GD."""
    return growth_efficiency * unit_economics * capital_efficiency * growth_durability
