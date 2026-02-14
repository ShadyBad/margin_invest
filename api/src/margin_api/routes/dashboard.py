"""Dashboard endpoint for high-conviction picks and watchlist."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from margin_api.schemas.dashboard import (
    DashboardResponse,
    PickSummary,
    WatchlistItem,
)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard() -> DashboardResponse:
    """Get dashboard with high-conviction picks and watchlist.

    Picks = scores with conviction_level in ('exceptional', 'high')
    Watchlist = scores with conviction_level == 'watchlist'

    NOTE: This endpoint currently returns empty data.
    It will be refactored to use DB queries in a later task.
    """
    all_scores: list = []

    picks: list[PickSummary] = []
    watchlist: list[WatchlistItem] = []

    for score in all_scores:
        if score.conviction_level in ("exceptional", "high"):
            picks.append(
                PickSummary(
                    ticker=score.ticker,
                    name=score.ticker,  # Name comes from asset lookup in later phase
                    composite_percentile=score.composite_percentile,
                    conviction_level=score.conviction_level,
                    signal=score.signal,
                    quality_percentile=score.quality.average_percentile,
                    value_percentile=score.value.average_percentile,
                    momentum_percentile=score.momentum.average_percentile,
                )
            )
        elif score.conviction_level == "watchlist":
            watchlist.append(
                WatchlistItem(
                    ticker=score.ticker,
                    name=score.ticker,
                    composite_percentile=score.composite_percentile,
                    conviction_level=score.conviction_level,
                )
            )

    # Sort picks by composite percentile descending
    picks.sort(key=lambda p: p.composite_percentile, reverse=True)
    watchlist.sort(key=lambda w: w.composite_percentile, reverse=True)

    return DashboardResponse(
        picks=picks,
        watchlist=watchlist,
        last_updated=datetime.now(UTC).isoformat(),
        total_scored=len(all_scores),
    )
