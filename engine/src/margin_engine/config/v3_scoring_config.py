"""V3 scoring configuration — geometric mean composite, conviction gates, mediocracy trajectory.

Pydantic models for the v3 scoring pipeline. All fields have defaults matching
the design spec so ``V3CompositeConfig()`` produces a working configuration
out of the box.

Usage:
    from margin_engine.config.v3_scoring_config import (
        V3CompositeConfig,
        ConvictionGateConfig,
        MediocracyTrajectoryConfig,
    )

    composite = V3CompositeConfig()
    gates = ConvictionGateConfig()
    trajectory = MediocracyTrajectoryConfig()
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TrackWeights(BaseModel):
    """Named factor weights for a scoring track.

    The weights dict maps factor names to their weight values.
    Weights must sum to 1.0 (within tolerance of 1e-6).
    """

    weights: dict[str, float]

    @model_validator(mode="after")
    def _weights_must_sum_to_one(self) -> TrackWeights:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            msg = f"weights must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self


def _default_track_a() -> TrackWeights:
    return TrackWeights(
        weights={
            "moat_durability": 0.25,
            "compounding_power": 0.25,
            "capital_allocation": 0.25,
            "growth_gap": 0.25,
        }
    )


def _default_track_b() -> TrackWeights:
    return TrackWeights(
        weights={
            "asymmetry_ratio": 0.25,
            "catalyst_strength": 0.25,
            "quality_floor_factor": 0.25,
            "valuation_convergence": 0.25,
        }
    )


def _default_track_c() -> TrackWeights:
    return TrackWeights(
        weights={
            "growth_efficiency": 0.25,
            "unit_economics": 0.25,
            "capital_efficiency": 0.25,
            "growth_durability": 0.25,
        }
    )


class V3CompositeConfig(BaseModel):
    """Configuration for the v3 geometric-mean composite scoring formula.

    Each track (A/B/C) has its own set of factor weights. The geometric mean
    is floored at ``factor_floor`` per factor and ``composite_floor`` for the
    final composite. ``balance_bonus_multiplier`` is stubbed at 1.0 (no-op).
    """

    factor_floor: float = 0.05
    composite_floor: float = 0.01
    track_a_weights: TrackWeights = Field(default_factory=_default_track_a)
    track_b_weights: TrackWeights = Field(default_factory=_default_track_b)
    track_c_weights: TrackWeights = Field(default_factory=_default_track_c)
    balance_bonus_threshold: float = 0.40
    balance_bonus_multiplier: float = 1.0  # stubbed, no-op


class ConvictionGateConfig(BaseModel):
    """ROIC-conditional conviction gate thresholds.

    Defines ROIC tiers (exceptional/strong/adequate/minimum) and reinvestment
    rate thresholds used to determine conviction level. Track B has its own
    hard floor and improving-trajectory thresholds.
    """

    roic_exceptional: float = 0.25
    roic_strong: float = 0.15
    roic_adequate: float = 0.10
    roic_minimum: float = 0.08
    reinvestment_strong: float = 0.10
    reinvestment_adequate: float = 0.20
    reinvestment_minimum: float = 0.30
    trajectory_min_delta: float = 0.02
    trajectory_min_periods: int = 3
    track_b_roic_hard_floor: float = 0.06
    track_b_improving_min_delta: float = 0.02
    track_b_improving_min_periods: int = 2


class SectorPercentileConfig(BaseModel):
    """Percentile thresholds for sector-relative conviction gates.

    Used by Financials and Real Estate sectors where absolute ROIC thresholds
    are inappropriate. Instead, conviction is determined by percentile rank
    within the sector universe.

    Thresholds are percentile values (0-100):
        - capital_light_bypass: >= this percentile bypasses reinvestment gate
        - exceptional/strong/adequate: conviction tier cutoffs
        - minimum: minimum percentile to avoid hard failure
    """

    capital_light_bypass: float = 90.0
    exceptional: float = 75.0
    strong: float = 60.0
    adequate: float = 50.0
    minimum: float = 50.0


class MediocracyTrajectoryConfig(BaseModel):
    """Configuration for the mediocracy gate trajectory override.

    Defines thresholds for determining whether an asset failing the mediocracy
    gate can be rescued by a positive trajectory (improving ROIC, expanding
    gross margins, or turning FCF-positive).
    """

    roic_min_delta_per_quarter: float = 0.02
    roic_min_consecutive: int = 3
    gm_approaching_distance: float = 0.03
    gm_min_annual_expansion: float = 0.03
    fcf_positive_recent_quarters: int = 2
    fcf_lookback_quarters: int = 6
    trajectory_stages: list[str] = Field(default_factory=lambda: ["turnaround", "high_growth"])
    conditional_score_multiplier: float = 0.90
