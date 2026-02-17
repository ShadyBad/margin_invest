"""Scoring result models — outputs of the conviction engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class FilterVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class ConvictionLevel(StrEnum):
    EXCEPTIONAL = "exceptional"  # Top ~5 stocks (>=99.95)
    HIGH = "high"  # Top ~50 stocks (>=99.3)
    WATCHLIST = "watchlist"  # Top ~100 stocks (>=98.0)
    NONE = "none"  # Below 98.0


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


class OpportunityType(StrEnum):
    COMPOUNDER = "compounder"
    MISPRICING = "mispricing"
    BOTH = "both"
    NEITHER = "neither"


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
    weight: float | None = None  # optional sub-factor weight within pillar

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
        weights = [s.weight for s in self.sub_scores if s.weight is not None]
        if weights and len(weights) == len(self.sub_scores):
            total_weight = sum(weights)
            if total_weight > 0:
                return sum(
                    s.percentile_rank * s.weight for s in self.sub_scores
                ) / total_weight
        return sum(s.percentile_rank for s in self.sub_scores) / len(self.sub_scores)


class CompositeScore(BaseModel):
    """Complete scoring result for a single asset."""

    ticker: str
    composite_percentile: float = Field(ge=0.0, le=100.0)
    composite_raw_score: float = Field(ge=0.0, le=100.0, default=0.0)
    quality: FactorBreakdown
    value: FactorBreakdown
    momentum: FactorBreakdown
    filters_passed: list[FilterResult]
    data_coverage: float = Field(ge=0.0, le=1.0)
    growth_stage: GrowthStage | None = None

    # Price target fields (populated by PriceTargetCalculator)
    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    margin_of_safety: float | None = None
    valuation_methods: dict[str, float] | None = None
    price_target_invalid_reason: str | None = None

    @property
    def conviction_level(self) -> ConvictionLevel:
        if self.composite_percentile >= 99.95:
            return ConvictionLevel.EXCEPTIONAL
        high_threshold = (
            99.5 if self.growth_stage == GrowthStage.TURNAROUND else 99.3
        )
        if self.composite_percentile >= high_threshold:
            return ConvictionLevel.HIGH
        elif self.composite_percentile >= 98.0:
            return ConvictionLevel.WATCHLIST
        return ConvictionLevel.NONE

    @property
    def signal(self) -> Signal:
        level = self.conviction_level
        if level == ConvictionLevel.WATCHLIST:
            return Signal.WATCH
        if level == ConvictionLevel.NONE:
            return Signal.NO_ACTION
        # High/Exceptional conviction: use price-aware signals if available
        if (
            self.actual_price is not None
            and self.sell_price is not None
            and self.buy_price is not None
        ):
            if self.actual_price > self.sell_price * 1.15:
                return Signal.URGENT_SELL
            if self.actual_price > self.sell_price:
                return Signal.SELL
            if self.actual_price <= self.buy_price:
                return Signal.BUY
            return Signal.HOLD
        # Fallback: conviction-based
        return Signal.BUY


class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth)
    quality_weight: float = 0.35
    value_weight: float = 0.30
    momentum_weight: float = 0.35

    # Conviction thresholds (percentile) — tuned for ~7,700 ticker universe
    exceptional_threshold: float = 99.95  # ~5 stocks
    high_threshold: float = 99.3  # ~50 stocks
    watchlist_threshold: float = 98.0  # ~100 stocks
    sell_threshold: float = 97.0

    # Turnaround stocks need higher bar
    turnaround_threshold: float = 99.5

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
