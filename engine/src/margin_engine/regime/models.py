"""Data models for multi-dimensional market regime classification.

Four independent axes describe the current market environment:
  - Volatility (VIX-derived)
  - Trend (price momentum / drawdown)
  - Valuation (aggregate market multiples)
  - Credit (spread conditions)

Each axis has four ordered states from benign to stressed.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Threshold constant
# ---------------------------------------------------------------------------

EXTREME_CONFIDENCE_THRESHOLD: float = 0.98
"""Confidence above this value indicates an extreme (high-conviction) reading."""


# ---------------------------------------------------------------------------
# Axis enums
# ---------------------------------------------------------------------------


class VolatilityState(StrEnum):
    """VIX-derived volatility regime."""

    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRISIS = "crisis"


class TrendState(StrEnum):
    """Price-trend / momentum regime."""

    BULL = "bull"
    SIDEWAYS = "sideways"
    BEAR = "bear"
    DRAWDOWN = "drawdown"


class ValuationState(StrEnum):
    """Aggregate market valuation regime."""

    CHEAP = "cheap"
    NORMAL = "normal"
    EXPENSIVE = "expensive"
    EUPHORIA = "euphoria"


class CreditState(StrEnum):
    """Credit-spread regime."""

    LOOSE = "loose"
    NORMAL = "normal"
    TIGHT = "tight"
    STRESS = "stress"


# ---------------------------------------------------------------------------
# Confidence model
# ---------------------------------------------------------------------------


class RegimeConfidence(BaseModel):
    """Per-axis confidence scores (0.0 to 1.0)."""

    model_config = ConfigDict(frozen=True)

    volatility: float = Field(ge=0.0, le=1.0)
    trend: float = Field(ge=0.0, le=1.0)
    valuation: float = Field(ge=0.0, le=1.0)
    credit: float = Field(ge=0.0, le=1.0)

    @property
    def min_confidence(self) -> float:
        """Return the lowest confidence across all four axes."""
        return min(self.volatility, self.trend, self.valuation, self.credit)


# ---------------------------------------------------------------------------
# Composite regime state
# ---------------------------------------------------------------------------


class RegimeState(BaseModel):
    """Snapshot of the four-axis market regime at a point in time."""

    model_config = ConfigDict(frozen=True)

    as_of_date: date
    volatility: VolatilityState
    trend: TrendState
    valuation: ValuationState
    credit: CreditState
    confidence: RegimeConfidence

    @property
    def regime_tuple(self) -> tuple[str, str, str, str]:
        """Four-element tuple of axis values (volatility, trend, valuation, credit)."""
        return (
            self.volatility.value,
            self.trend.value,
            self.valuation.value,
            self.credit.value,
        )

    @property
    def regime_key(self) -> str:
        """Pipe-delimited string of the regime tuple, e.g. ``'normal|bull|expensive|normal'``."""
        return "|".join(self.regime_tuple)

    @property
    def has_extreme_axis(self) -> bool:
        """True if any axis confidence strictly exceeds the extreme threshold."""
        return any(
            c > EXTREME_CONFIDENCE_THRESHOLD
            for c in (
                self.confidence.volatility,
                self.confidence.trend,
                self.confidence.valuation,
                self.confidence.credit,
            )
        )
