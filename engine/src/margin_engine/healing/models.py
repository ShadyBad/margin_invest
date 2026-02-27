"""Healing subsystem data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealingConfig(BaseModel):
    """Configuration for the healing pipeline."""

    # Tier 1: Deterministic impossibility thresholds
    pe_ratio_max: float = Field(default=10_000.0, description="Max plausible P/E ratio")
    pe_ratio_min: float = Field(default=-10_000.0, description="Min plausible P/E ratio")
    debt_equity_max: float = Field(default=500.0, description="Max plausible D/E ratio")

    # Tier 2: MAD-based outlier detection
    mad_threshold: float = Field(
        default=5.0,
        description="Number of MADs from median to flag as outlier",
    )

    # Tier 3: Cross-sectional consistency
    sector_iqr_multiplier: float = Field(
        default=3.0,
        description="IQR multiplier for cross-sectional outlier detection",
    )

    # Circuit breakers
    sector_breadth_threshold: float = Field(
        default=0.15,
        description=(
            "Fraction of sector tickers that must be flagged before corrections are suspended"
        ),
    )
    variance_compression_floor: float = Field(
        default=0.85,
        description=(
            "Minimum ratio of corrected-to-raw standard deviation before warning fires"
        ),
    )
