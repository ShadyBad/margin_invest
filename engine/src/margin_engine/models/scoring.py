"""Scoring result models — outputs of the scoring engine."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FilterVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class CompositeTier(StrEnum):
    EXCEPTIONAL = "exceptional"  # composite_raw_score >= 76
    HIGH = "high"  # composite_raw_score >= 71
    MEDIUM = "medium"  # composite_raw_score >= 66
    NONE = "none"  # < 66


# Backward compat alias — use CompositeTier instead
ConvictionLevel = CompositeTier


class Signal(StrEnum):
    BUY = "strong"
    HOLD = "stable"
    WATCH = "emerging"
    SELL = "weak"
    URGENT_SELL = "failed"
    NO_ACTION = "neutral"


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


class InvestmentStyle(StrEnum):
    VALUE = "value"
    BLEND = "blend"
    GROWTH = "growth"


class FilterResult(BaseModel):
    """Result of a single elimination filter."""

    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    insufficient_data: bool = False
    missing_fields: list[str] | None = None
    computed_metrics: dict[str, float | str] | None = None
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
    stub: bool = False
    metadata: dict[str, Any] | None = None

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
        active = [s for s in self.sub_scores if not s.stub]
        if not active:
            return 0.0
        weights = [s.weight for s in active if s.weight is not None]
        if weights and len(weights) == len(active):
            total_weight = sum(weights)
            if total_weight > 0:
                return sum(s.percentile_rank * s.weight for s in active) / total_weight
        return sum(s.percentile_rank for s in active) / len(active)


class CompositeScore(BaseModel):
    """Complete scoring result for a single asset."""

    ticker: str
    composite_percentile: float = Field(ge=0.0, le=100.0)
    composite_raw_score: float = Field(ge=0.0, le=100.0, default=0.0)
    quality: FactorBreakdown
    value: FactorBreakdown
    momentum: FactorBreakdown
    growth: FactorBreakdown | None = None  # v4: growth factor dimension
    filters_passed: list[FilterResult]
    data_coverage: float = Field(ge=0.0, le=1.0)
    growth_stage: GrowthStage | None = None
    investment_style: InvestmentStyle | None = None

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
    conviction_override: CompositeTier | None = None

    # Capital allocation pillar (Track A)
    capital_allocation: FactorBreakdown | None = None
    # Catalyst pillar (Track B)
    catalyst: FactorBreakdown | None = None

    @property
    def composite_tier(self) -> CompositeTier:
        if self.conviction_override is not None:
            return self.conviction_override
        if self.composite_raw_score >= 76.0:
            return CompositeTier.EXCEPTIONAL
        if self.composite_raw_score >= 71.0:
            return CompositeTier.HIGH
        if self.composite_raw_score >= 66.0:
            return CompositeTier.MEDIUM
        return CompositeTier.NONE

    @property
    def conviction_level(self) -> CompositeTier:
        """Backward-compat alias — use composite_tier instead."""
        return self.composite_tier

    @property
    def signal(self) -> Signal:
        level = self.composite_tier
        if level == CompositeTier.MEDIUM:
            return Signal.WATCH
        if level == CompositeTier.NONE:
            return Signal.NO_ACTION
        # High/Exceptional tier: use price-aware signals if available
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
        # Fallback: tier-based
        return Signal.BUY

    @property
    def intrinsic_value(self) -> float | None:
        """Deprecated: use margin_invest_value."""
        return self.margin_invest_value


class ScenarioIV(BaseModel):
    """Bear/base/bull intrinsic value with confidence score."""

    bear_iv: float  # 25th percentile scenario
    base_iv: float  # 50th percentile scenario
    bull_iv: float  # 75th percentile scenario
    weighted_iv: float  # 0.25*bear + 0.50*base + 0.25*bull
    confidence: float = Field(ge=0.0, le=1.0)  # 1 - (range / base)
    range_pct: float  # (bull - bear) / base


_ANOMALY_Z_THRESHOLD = 3.0


class ConsistencyFlag(BaseModel):
    """Flag for a single field that deviates significantly from historical pattern."""

    field_name: str
    current_value: float
    historical_mean: float
    historical_std: float
    z_score: float
    periods_used: int

    @property
    def is_anomaly(self) -> bool:
        return abs(self.z_score) >= _ANOMALY_Z_THRESHOLD


class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth) — sum to 0.85; composite normalizes to 1.0
    quality_weight: float = 0.25
    value_weight: float = 0.20
    momentum_weight: float = 0.25
    growth_weight: float = 0.15

    # Conviction thresholds (raw score) — absolute, universe-independent
    exceptional_threshold: float = 76.0
    high_threshold: float = 71.0
    medium_threshold: float = 66.0  # renamed from watchlist_threshold
    sell_threshold: float = 97.0

    def weights_for_stage(self, stage: GrowthStage) -> tuple[float, float, float, float]:
        """Return (quality, value, momentum, growth) weights for a growth stage.

        All stage weight tuples sum to 0.85; the composite scorer normalizes
        to 1.0 based on which pillars have data.
        """
        stage_weights: dict[GrowthStage, tuple[float, float, float, float]] = {
            GrowthStage.HIGH_GROWTH: (0.20, 0.10, 0.25, 0.30),
            GrowthStage.STEADY_GROWTH: (0.25, 0.20, 0.25, 0.15),
            GrowthStage.MATURE: (0.25, 0.30, 0.15, 0.15),
            GrowthStage.CYCLICAL: (0.25, 0.20, 0.25, 0.15),
            GrowthStage.TURNAROUND: (0.25, 0.20, 0.25, 0.15),
        }
        return stage_weights[stage]
