"""Dashboard-related API response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from margin_api.schemas.universe import UniverseSummary, Warning


class PickSummary(BaseModel):
    """Summary of a high-conviction pick for the dashboard."""

    score_id: int  # DB primary key for traceability
    ticker: str
    name: str
    score: float = 0.0  # Raw weighted average
    universe_percentile: float = 0.0  # Universe-level rank
    composite_percentile: float  # Kept for backwards compat
    conviction_level: str
    signal: str
    quality_percentile: float
    value_percentile: float
    momentum_percentile: float
    sentiment_percentile: float | None = None
    growth_percentile: float | None = None
    actual_price: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    price_upside: float | None = None
    data_freshness: str = "expired"
    scored_at: str | None = None
    price_source: str = "daily_close"
    price_updated_at: str | None = None
    # v2 Conviction Engine fields
    opportunity_type: str | None = None
    winning_track: str | None = None
    margin_of_safety: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None
    sector: str | None = None
    price_target_invalid_reason: str | None = None


class WatchlistItem(BaseModel):
    """Summary of a watchlist item for the dashboard."""

    ticker: str
    name: str
    composite_raw_score: float
    conviction_level: str
    sector: str | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    opportunity_type: str | None = None


class DashboardResponse(BaseModel):
    """Dashboard data response."""

    picks: list[PickSummary]
    watchlist: list[WatchlistItem]
    last_updated: str  # ISO datetime
    total_scored: int
    universe: UniverseSummary | None = None
    warnings: list[Warning] = []
