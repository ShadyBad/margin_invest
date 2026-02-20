"""Scoring result models — outputs of the conviction engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class FilterVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class ConvictionLevel(StrEnum):
    EXCEPTIONAL = "exceptional"  # composite_raw_score >= 79
    HIGH = "high"               # composite_raw_score >= 72
    MEDIUM = "medium"           # composite_raw_score >= 65
    NONE = "none"               # < 65


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
    insufficient_data: bool = False
    missing_fields: list[str] | None = None
    computed_metrics: dict[str, float] | None = None
    warning: bool = False
    warning_reason: str | None = None

    @property
    def verdict(self) -> FilterVerdict:
        if self.insufficient_data:
            return FilterVerdict.INCONCLUSIVE
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
    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    margin_of_safety: float | None = None
    valuation_methods: dict[str, float] | None = None
    price_target_invalid_reason: str | None = None

    # v2 conviction engine fields
    opportunity_type: OpportunityType | None = None
    winning_track: str | None = None  # "compounder" or "mispricing"
    asymmetry_ratio: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None  # "buy_now", "add_on_pullback", "wait_for_catalyst"

    # Capital allocation pillar (Track A)
    capital_allocation: FactorBreakdown | None = None
    # Catalyst pillar (Track B)
    catalyst: FactorBreakdown | None = None

    @property
    def conviction_level(self) -> ConvictionLevel:
        if self.composite_raw_score >= 79.0:
            return ConvictionLevel.EXCEPTIONAL
        if self.composite_raw_score >= 72.0:
            return ConvictionLevel.HIGH
        if self.composite_raw_score >= 65.0:
            return ConvictionLevel.MEDIUM
        return ConvictionLevel.NONE

    @property
    def signal(self) -> Signal:
        level = self.conviction_level
        if level == ConvictionLevel.MEDIUM:
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

    @property
    def intrinsic_value(self) -> float | None:
        """Deprecated: use margin_invest_value."""
        return self.margin_invest_value


class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth)
    quality_weight: float = 0.35
    value_weight: float = 0.30
    momentum_weight: float = 0.35

    # Conviction thresholds (raw score) — absolute, universe-independent
    exceptional_threshold: float = 79.0
    high_threshold: float = 72.0
    medium_threshold: float = 65.0  # renamed from watchlist_threshold
    sell_threshold: float = 97.0

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
