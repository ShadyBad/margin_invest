"""v3 Conviction Thresholds — absolute conviction levels per track.

Replaces universe-relative percentile thresholds (99.95, 99.3, 98.0).
Conviction determined by absolute quality of the opportunity, not rank vs peers.
"""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

# Track A thresholds
_A_EXCEPTIONAL_POWER = 0.15
_A_EXCEPTIONAL_MOAT = 3
_A_EXCEPTIONAL_GAP = 0.08
_A_HIGH_POWER = 0.08
_A_HIGH_MOAT = 2
_A_HIGH_GAP = 0.03
_A_MEDIUM_POWER = 0.04
_A_MEDIUM_MOAT = 2
_A_MIN_GATES_FULL = 4
_A_MIN_GATES_MEDIUM = 3

# Hysteresis buffer — 10% relaxation on thresholds to prevent conviction whipsaw
_HYSTERESIS_BUFFER = 0.10

# Track B thresholds
_B_EXCEPTIONAL_ASYMMETRY = 5.0
_B_EXCEPTIONAL_CATALYST = 55.0
_B_EXCEPTIONAL_CONVERGING = 4
_B_HIGH_ASYMMETRY = 3.0
_B_HIGH_CATALYST = 40.0
_B_HIGH_CONVERGING = 3
_B_MEDIUM_ASYMMETRY = 1.5
_B_MIN_GATES_FULL = 4
_B_MIN_GATES_MEDIUM = 3


def assess_track_a_conviction(
    gates_passed: int,
    total_gates: int,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float = 0.0,
    prior_conviction: ConvictionLevel | None = None,
) -> ConvictionLevel:
    """Determine Track A conviction level from absolute thresholds.

    Args:
        growth_gap_adjustment: Offset applied to growth_gap thresholds for
            market regime adjustments. Positive tightens (expensive regime),
            negative relaxes (cheap regime).
        prior_conviction: Previous conviction level for hysteresis. When set
            and the computed conviction would be a demotion, a 10% buffer is
            applied to the prior tier's thresholds. If the stock's values
            remain within that buffer, the prior conviction is retained.
            Hysteresis only prevents demotion, never prevents promotion.
    """
    computed = _compute_track_a(gates_passed, total_gates, compounding_power,
                                moat_durability, growth_gap, growth_gap_adjustment)

    if prior_conviction is None:
        return computed

    # Hysteresis only prevents demotion — never blocks promotion
    if _conviction_rank(computed) >= _conviction_rank(prior_conviction):
        return computed

    # Prior is higher than computed — check if within buffer
    if _within_buffer_track_a(prior_conviction, compounding_power,
                              moat_durability, growth_gap, growth_gap_adjustment):
        return prior_conviction

    return computed


def _compute_track_a(
    gates_passed: int,
    total_gates: int,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float,
) -> ConvictionLevel:
    """Core Track A conviction logic without hysteresis."""
    if gates_passed < _A_MIN_GATES_MEDIUM or moat_durability < _A_MEDIUM_MOAT:
        return ConvictionLevel.NONE

    if (
        gates_passed >= _A_MIN_GATES_FULL
        and compounding_power > _A_EXCEPTIONAL_POWER
        and moat_durability >= _A_EXCEPTIONAL_MOAT
        and growth_gap > _A_EXCEPTIONAL_GAP + growth_gap_adjustment
    ):
        return ConvictionLevel.EXCEPTIONAL

    if (
        gates_passed >= _A_MIN_GATES_FULL
        and compounding_power > _A_HIGH_POWER
        and moat_durability >= _A_HIGH_MOAT
        and growth_gap > _A_HIGH_GAP + growth_gap_adjustment
    ):
        return ConvictionLevel.HIGH

    if compounding_power > _A_MEDIUM_POWER:
        return ConvictionLevel.MEDIUM

    return ConvictionLevel.NONE


def _conviction_rank(level: ConvictionLevel) -> int:
    """Numeric rank for conviction ordering (higher is better)."""
    return {
        ConvictionLevel.NONE: 0,
        ConvictionLevel.MEDIUM: 1,
        ConvictionLevel.HIGH: 2,
        ConvictionLevel.EXCEPTIONAL: 3,
    }[level]


def _within_buffer_track_a(
    prior: ConvictionLevel,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float,
) -> bool:
    """Check whether values stay within the hysteresis buffer of the prior tier.

    Applies a 10% relaxation to continuous thresholds (power, gap).
    Integer thresholds (moat, gates) are not buffered — the stock must still
    meet the prior tier's integer requirements exactly.
    """
    buf = 1.0 - _HYSTERESIS_BUFFER  # 0.90

    if prior == ConvictionLevel.EXCEPTIONAL:
        gap_threshold = (_A_EXCEPTIONAL_GAP + growth_gap_adjustment) * buf
        return (
            compounding_power > _A_EXCEPTIONAL_POWER * buf
            and moat_durability >= _A_EXCEPTIONAL_MOAT
            and growth_gap > gap_threshold
        )

    if prior == ConvictionLevel.HIGH:
        gap_threshold = (_A_HIGH_GAP + growth_gap_adjustment) * buf
        return (
            compounding_power > _A_HIGH_POWER * buf
            and moat_durability >= _A_HIGH_MOAT
            and growth_gap > gap_threshold
        )

    # MEDIUM and NONE have no meaningful buffer to apply
    return False


def assess_track_b_conviction(
    gates_passed: int,
    total_gates: int,
    asymmetry_ratio: float,
    catalyst_percentile: float,
    converging_methods: int,
    asymmetry_adjustment: float = 0.0,
    catalyst_percentile_override: float | None = None,
) -> ConvictionLevel:
    """Determine Track B conviction level from absolute thresholds.

    Args:
        asymmetry_adjustment: Offset applied to asymmetry_ratio thresholds for
            market regime adjustments. Positive tightens, negative relaxes.
        catalyst_percentile_override: If set, replaces the EXCEPTIONAL catalyst
            percentile threshold (e.g., euphoria regime raises the bar).
    """
    if gates_passed < _B_MIN_GATES_MEDIUM or asymmetry_ratio < _B_MEDIUM_ASYMMETRY:
        return ConvictionLevel.NONE

    exceptional_catalyst = (
        catalyst_percentile_override
        if catalyst_percentile_override is not None
        else _B_EXCEPTIONAL_CATALYST
    )

    if (
        gates_passed >= _B_MIN_GATES_FULL
        and asymmetry_ratio > _B_EXCEPTIONAL_ASYMMETRY + asymmetry_adjustment
        and catalyst_percentile > exceptional_catalyst
        and converging_methods >= _B_EXCEPTIONAL_CONVERGING
    ):
        return ConvictionLevel.EXCEPTIONAL

    if (
        gates_passed >= _B_MIN_GATES_FULL
        and asymmetry_ratio > _B_HIGH_ASYMMETRY + asymmetry_adjustment
        and catalyst_percentile > _B_HIGH_CATALYST
        and converging_methods >= _B_HIGH_CONVERGING
    ):
        return ConvictionLevel.HIGH

    return ConvictionLevel.MEDIUM
