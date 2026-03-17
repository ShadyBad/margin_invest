"""Response schemas for rarity API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class RarityDimensionsResponse(BaseModel):
    joint_rarity_pctl: float
    convergence_score: float
    historical_frequency: float
    quality_momentum: float
    smart_money_score: float
    regime_alignment: float


class RarityResponse(BaseModel):
    """Full rarity breakdown for a single ticker."""

    ticker: str
    rarity_score: float
    conviction_score: float
    is_generational: bool
    combination_signature: str
    regime: str
    dimensions: RarityDimensionsResponse
    pillar_percentiles: dict[str, float]
    universe_size: int
    scored_at: str | None = None


class RarityPickResponse(BaseModel):
    """Summary of a generational pick."""

    ticker: str
    name: str = ""
    sector: str | None = None
    rarity_score: float
    combination_signature: str
    is_generational: bool
    composite_tier: str = ""
    regime: str = ""


class RarityPicksListResponse(BaseModel):
    """List of top rarity picks."""

    picks: list[RarityPickResponse]
    regime: str
    universe_size: int
    scored_at: str | None = None
