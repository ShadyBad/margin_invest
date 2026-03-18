"""v3 Conviction Thresholds — absolute conviction levels per track.

Replaces universe-relative percentile thresholds (99.95, 99.3, 98.0).
Conviction determined by absolute quality of the opportunity, not rank vs peers.

Thresholds are loaded from ``ThresholdConfig`` (YAML-backed with Pydantic
defaults). All functions accept an optional ``config`` parameter; when
omitted, a module-level default config is used with values identical to the
previous hardcoded constants.
"""

from __future__ import annotations

from margin_engine.config.threshold_config import ThresholdConfig
from margin_engine.models.scoring import CompositeTier

_DEFAULT_CONFIG = ThresholdConfig()


def assess_track_a_conviction(
    gates_passed: int,
    total_gates: int,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float = 0.0,
    prior_conviction: CompositeTier | None = None,
    config: ThresholdConfig | None = None,
    conditional: bool = False,
) -> CompositeTier:
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
        config: Optional threshold configuration. When None, module-level
            defaults are used (identical to original hardcoded values).
        conditional: When True, cap maximum conviction at HIGH (trajectory-based
            passes cannot reach EXCEPTIONAL).
    """
    cfg = config or _DEFAULT_CONFIG

    computed = _compute_track_a(
        gates_passed,
        total_gates,
        compounding_power,
        moat_durability,
        growth_gap,
        growth_gap_adjustment,
        cfg,
        conditional,
    )

    if prior_conviction is None:
        return computed

    # Hysteresis only prevents demotion — never blocks promotion
    if _conviction_rank(computed) >= _conviction_rank(prior_conviction):
        return computed

    # Prior is higher than computed — check if within buffer
    if _within_buffer_track_a(
        prior_conviction, compounding_power, moat_durability, growth_gap, growth_gap_adjustment, cfg
    ):
        return prior_conviction

    return computed


def _compute_track_a(
    gates_passed: int,
    total_gates: int,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float,
    cfg: ThresholdConfig,
    conditional: bool = False,
) -> CompositeTier:
    """Core Track A conviction logic without hysteresis."""
    ta = cfg.track_a

    if gates_passed < ta.min_gates_medium or moat_durability < ta.medium_moat:
        return CompositeTier.NONE

    if (
        gates_passed >= ta.min_gates_full
        and compounding_power > ta.exceptional_power
        and moat_durability >= ta.exceptional_moat
        and growth_gap > ta.exceptional_gap + growth_gap_adjustment
    ):
        # Conditional passes (trajectory-based) cap at HIGH
        return CompositeTier.HIGH if conditional else CompositeTier.EXCEPTIONAL

    if (
        gates_passed >= ta.min_gates_full
        and compounding_power > ta.high_power
        and moat_durability >= ta.high_moat
        and growth_gap > ta.high_gap + growth_gap_adjustment
    ):
        return CompositeTier.HIGH

    if compounding_power > ta.medium_power:
        return CompositeTier.MEDIUM

    return CompositeTier.NONE


def _conviction_rank(level: CompositeTier) -> int:
    """Numeric rank for conviction ordering (higher is better)."""
    return {
        CompositeTier.NONE: 0,
        CompositeTier.MEDIUM: 1,
        CompositeTier.HIGH: 2,
        CompositeTier.EXCEPTIONAL: 3,
    }[level]


def _within_buffer_track_a(
    prior: CompositeTier,
    compounding_power: float,
    moat_durability: int,
    growth_gap: float,
    growth_gap_adjustment: float,
    cfg: ThresholdConfig,
) -> bool:
    """Check whether values stay within the hysteresis buffer of the prior tier.

    Applies a 10% relaxation to continuous thresholds (power, gap).
    Integer thresholds (moat, gates) are not buffered — the stock must still
    meet the prior tier's integer requirements exactly.
    """
    ta = cfg.track_a
    buf = 1.0 - cfg.hysteresis_buffer  # 0.90

    if prior == CompositeTier.EXCEPTIONAL:
        gap_threshold = (ta.exceptional_gap + growth_gap_adjustment) * buf
        return (
            compounding_power > ta.exceptional_power * buf
            and moat_durability >= ta.exceptional_moat
            and growth_gap > gap_threshold
        )

    if prior == CompositeTier.HIGH:
        gap_threshold = (ta.high_gap + growth_gap_adjustment) * buf
        return (
            compounding_power > ta.high_power * buf
            and moat_durability >= ta.high_moat
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
    config: ThresholdConfig | None = None,
    conditional: bool = False,
) -> CompositeTier:
    """Determine Track B conviction level from absolute thresholds.

    Args:
        asymmetry_adjustment: Offset applied to asymmetry_ratio thresholds for
            market regime adjustments. Positive tightens, negative relaxes.
        catalyst_percentile_override: If set, replaces the EXCEPTIONAL catalyst
            percentile threshold (e.g., euphoria regime raises the bar).
        config: Optional threshold configuration. When None, module-level
            defaults are used (identical to original hardcoded values).
        conditional: When True, cap maximum conviction at HIGH (trajectory-based
            passes cannot reach EXCEPTIONAL).
    """
    cfg = config or _DEFAULT_CONFIG
    tb = cfg.track_b

    if gates_passed < tb.min_gates_medium or asymmetry_ratio < tb.medium_asymmetry:
        return CompositeTier.NONE

    exceptional_catalyst = (
        catalyst_percentile_override
        if catalyst_percentile_override is not None
        else tb.exceptional_catalyst
    )

    if (
        gates_passed >= tb.min_gates_full
        and asymmetry_ratio > tb.exceptional_asymmetry + asymmetry_adjustment
        and catalyst_percentile > exceptional_catalyst
        and converging_methods >= tb.exceptional_converging
    ):
        # Conditional passes (trajectory-based) cap at HIGH
        return CompositeTier.HIGH if conditional else CompositeTier.EXCEPTIONAL

    if (
        gates_passed >= tb.min_gates_full
        and asymmetry_ratio > tb.high_asymmetry + asymmetry_adjustment
        and catalyst_percentile > tb.high_catalyst
        and converging_methods >= tb.high_converging
    ):
        return CompositeTier.HIGH

    return CompositeTier.MEDIUM
