"""Score-related API response schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from margin_engine.models.scoring import CompositeScore, FactorBreakdown


class FilterResultResponse(BaseModel):
    """API representation of a single filter result."""

    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    verdict: str  # "pass" or "fail"


class FactorScoreResponse(BaseModel):
    """API representation of a single factor score."""

    name: str
    raw_value: float
    percentile_rank: float
    detail: str = ""


class FactorBreakdownResponse(BaseModel):
    """API representation of a factor breakdown."""

    factor_name: str
    weight: float
    sub_scores: list[FactorScoreResponse]
    average_percentile: float


class PriceBarResponse(BaseModel):
    """Single OHLCV price bar."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None


class SignalTransitionResponse(BaseModel):
    """A signal transition record."""

    previous_signal: str
    new_signal: str
    previous_conviction: str
    new_conviction: str
    actual_price_at_transition: float | None = None
    intrinsic_value_at_transition: float | None = None
    composite_percentile: float
    transitioned_at: str


class ScoreResponse(BaseModel):
    """Full scoring result for a single ticker."""

    ticker: str
    name: str = ""
    score: float = 0.0  # Raw weighted average — the true quality measure
    universe_percentile: float = 0.0  # Universe-level rank (0-100)
    composite_percentile: float  # Kept for backwards compat
    composite_raw_score: float = 0.0  # Kept for backwards compat
    conviction_level: str  # "exceptional", "high", "watchlist", "none"
    signal: str  # "buy", "watch", "no_action", etc.
    quality: FactorBreakdownResponse
    value: FactorBreakdownResponse
    momentum: FactorBreakdownResponse
    filters_passed: list[FilterResultResponse]
    data_coverage: float
    growth_stage: str | None = None
    scored_at: str | None = None
    # Price target fields
    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    margin_of_safety: float | None = None
    valuation_methods: dict[str, float] | None = None
    price_target_invalid_reason: str | None = None
    # v2 Conviction Engine fields
    opportunity_type: str | None = None
    winning_track: str | None = None
    asymmetry_ratio: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None
    capital_allocation: FactorBreakdownResponse | None = None
    catalyst: FactorBreakdownResponse | None = None
    # Live price and freshness fields
    data_freshness: str = "expired"  # "fresh", "stale", "expired"
    price_source: str = "daily_close"  # "live" or "daily_close"
    price_updated_at: str | None = None
    # Conditionally included via ?include=
    price_history: list[PriceBarResponse] | None = None
    signal_history: list[SignalTransitionResponse] | None = None

    @classmethod
    def from_engine(cls, score: CompositeScore) -> ScoreResponse:
        """Convert an engine CompositeScore to an API response."""
        return cls(
            ticker=score.ticker,
            score=score.composite_raw_score,
            universe_percentile=score.composite_percentile,
            composite_percentile=score.composite_percentile,
            composite_raw_score=score.composite_raw_score,
            conviction_level=score.conviction_level.value,
            signal=score.signal.value,
            quality=_breakdown_from_engine(score.quality),
            value=_breakdown_from_engine(score.value),
            momentum=_breakdown_from_engine(score.momentum),
            filters_passed=[
                FilterResultResponse(
                    name=f.name,
                    passed=f.passed,
                    value=f.value,
                    threshold=f.threshold,
                    detail=f.detail,
                    verdict=f.verdict.value,
                )
                for f in score.filters_passed
            ],
            data_coverage=score.data_coverage,
            growth_stage=score.growth_stage.value if score.growth_stage else None,
            margin_invest_value=score.intrinsic_value,
            buy_price=score.buy_price,
            sell_price=score.sell_price,
            actual_price=score.actual_price,
            price_upside=score.price_upside,
            margin_of_safety=score.margin_of_safety,
            valuation_methods=score.valuation_methods,
            price_target_invalid_reason=score.price_target_invalid_reason,
            opportunity_type=score.opportunity_type.value if score.opportunity_type else None,
            winning_track=score.winning_track,
            asymmetry_ratio=score.asymmetry_ratio,
            max_position_pct=score.max_position_pct,
            timing_signal=score.timing_signal,
            capital_allocation=_breakdown_from_engine(score.capital_allocation) if score.capital_allocation else None,
            catalyst=_breakdown_from_engine(score.catalyst) if score.catalyst else None,
        )


class ScoreListResponse(BaseModel):
    """Paginated list of scores."""

    scores: list[ScoreResponse]
    total: int
    page: int = 1
    page_size: int = 50


def _breakdown_from_engine(
    breakdown: FactorBreakdown,
) -> FactorBreakdownResponse:
    """Convert an engine FactorBreakdown to an API response."""

    return FactorBreakdownResponse(
        factor_name=breakdown.factor_name,
        weight=breakdown.weight,
        sub_scores=[
            FactorScoreResponse(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=s.percentile_rank,
                detail=s.detail,
            )
            for s in breakdown.sub_scores
        ],
        average_percentile=breakdown.average_percentile,
    )
