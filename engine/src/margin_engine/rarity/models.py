"""Pydantic models for rarity engine inputs and outputs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RarityRegime(StrEnum):
    EXPANSION = "expansion"
    LATE_CYCLE = "late_cycle"
    CONTRACTION = "contraction"
    CRISIS = "crisis"


class RarityConfig(BaseModel):
    """Tunable weights and thresholds for rarity scoring."""

    joint_rarity_weight: float = 0.35
    convergence_weight: float = 0.25
    historical_rarity_weight: float = 0.15
    quality_momentum_weight: float = 0.10
    smart_money_weight: float = 0.10
    regime_alignment_weight: float = 0.05

    min_pillar_pctl: float = 60.0
    convergence_gate: float = 50.0
    rarity_score_gate: float = 80.0
    hard_cap: int = 30
    sector_cap_pct: float = 0.40

    generational_joint_rarity_pctl: float = 97.0
    generational_composite_raw: float = 76.0
    generational_hist_freq: float = 0.02


class RarityDimensionScores(BaseModel):
    """Individual dimension scores that compose the rarity score."""

    joint_rarity_pctl: float = Field(ge=0.0, le=100.0)
    convergence_score: float = Field(ge=0.0, le=100.0)
    historical_frequency: float = Field(ge=0.0, le=100.0, default=50.0)
    quality_momentum: float = Field(ge=0.0, le=100.0, default=50.0)
    smart_money_score: float = Field(ge=0.0, le=100.0, default=50.0)
    regime_alignment: float = Field(ge=0.0, le=100.0, default=50.0)


class RarityResult(BaseModel):
    """Complete rarity assessment for a single ticker."""

    ticker: str
    rarity_score: float = Field(ge=0.0, le=100.0)
    conviction_score: float = Field(ge=0.0, le=100.0, default=0.0)  # Deferred: computed in Phase 3
    dimensions: RarityDimensionScores
    combination_signature: str
    pillar_percentiles: dict[str, float]
    regime: RarityRegime = RarityRegime.EXPANSION
    is_generational: bool = False
    passed_gates: list[bool] = []
    universe_size: int = 0
    composite_raw_score: float = 0.0
    composite_tier: str = "none"
    sector: str | None = None
