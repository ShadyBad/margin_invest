"""Dashboard-related API response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from margin_api.schemas.universe import UniverseSummary, Warning


class PickSummary(BaseModel):
    """Summary of a high-conviction pick for the dashboard."""

    ticker: str
    name: str
    composite_percentile: float
    conviction_level: str
    signal: str
    quality_percentile: float
    value_percentile: float
    momentum_percentile: float
    actual_price: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    price_upside: float | None = None
    data_freshness: str = "expired"
    scored_at: str | None = None
    price_source: str = "daily_close"
    price_updated_at: str | None = None


class WatchlistItem(BaseModel):
    """Summary of a watchlist item."""

    ticker: str
    name: str
    composite_percentile: float
    conviction_level: str


class DashboardResponse(BaseModel):
    """Dashboard data response."""

    picks: list[PickSummary]
    watchlist: list[WatchlistItem]
    last_updated: str  # ISO datetime
    total_scored: int
    universe: UniverseSummary | None = None
    warnings: list[Warning] = []
