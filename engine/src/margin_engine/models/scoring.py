"""Scoring result models — outputs of the conviction engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class FilterVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class ConvictionLevel(StrEnum):
    EXCEPTIONAL = "exceptional"  # Top 1% (99-100)
    HIGH = "high"  # Top 5% (95-98)
    WATCHLIST = "watchlist"  # Top 10% (90-94)
    NONE = "none"  # Below 90


class Signal(StrEnum):
    BUY = "buy"
    HOLD = "hold"
    WATCH = "watch"
    SELL = "sell"
    URGENT_SELL = "urgent_sell"
    NO_ACTION = "no_action"


class GrowthStage(StrEnum):
    HIGH_GROWTH = "high_growth"
    STEADY_GROWTH = "steady_growth"
    MATURE = "mature"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"


class FilterResult(BaseModel):
    """Result of a single elimination filter."""

    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""

    @property
    def verdict(self) -> FilterVerdict:
        return FilterVerdict.PASS if self.passed else FilterVerdict.FAIL


class FactorScore(BaseModel):
    """Score for a single sub-factor (e.g., gross profitability)."""

    name: str
    raw_value: float
    percentile_rank: float = Field(ge=0.0, le=100.0)
    detail: str = ""

    @field_validator("percentile_rank")
    @classmethod
    def validate_percentile(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError(f"Percentile rank must be 0-100, got {v}")
        return v


class FactorBreakdown(BaseModel):
    """Breakdown of a top-level factor (quality, value, momentum)."""

    factor_name: str
    weight: float
    sub_scores: list[FactorScore]

    @property
    def average_percentile(self) -> float:
        if not self.sub_scores:
            return 0.0
        return sum(s.percentile_rank for s in self.sub_scores) / len(self.sub_scores)


class CompositeScore(BaseModel):
    """Complete scoring result for a single asset."""

    ticker: str
    composite_percentile: float = Field(ge=0.0, le=100.0)
    quality: FactorBreakdown
    value: FactorBreakdown
    momentum: FactorBreakdown
    filters_passed: list[FilterResult]
    data_coverage: float = Field(ge=0.0, le=1.0)
    growth_stage: GrowthStage | None = None

    @property
    def conviction_level(self) -> ConvictionLevel:
        if self.composite_percentile >= 99.0:
            return ConvictionLevel.EXCEPTIONAL
        elif self.composite_percentile >= 95.0:
            return ConvictionLevel.HIGH
        elif self.composite_percentile >= 90.0:
            return ConvictionLevel.WATCHLIST
        return ConvictionLevel.NONE

    @property
    def signal(self) -> Signal:
        level = self.conviction_level
        if level in (ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH):
            return Signal.BUY
        elif level == ConvictionLevel.WATCHLIST:
            return Signal.WATCH
        return Signal.NO_ACTION


class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth)
    quality_weight: float = 0.35
    value_weight: float = 0.30
    momentum_weight: float = 0.35

    # Conviction thresholds (percentile)
    exceptional_threshold: float = 99.0
    high_threshold: float = 95.0
    watchlist_threshold: float = 90.0
    sell_threshold: float = 85.0

    # Turnaround stocks need higher bar
    turnaround_threshold: float = 97.0  # Top 3% instead of top 5%

    def weights_for_stage(self, stage: GrowthStage) -> tuple[float, float, float]:
        """Return (quality, value, momentum) weights for a growth stage."""
        stage_weights = {
            GrowthStage.HIGH_GROWTH: (0.40, 0.25, 0.35),
            GrowthStage.STEADY_GROWTH: (0.35, 0.30, 0.35),
            GrowthStage.MATURE: (0.30, 0.40, 0.30),
            GrowthStage.CYCLICAL: (0.35, 0.30, 0.35),
            GrowthStage.TURNAROUND: (0.35, 0.30, 0.35),
        }
        return stage_weights[stage]
