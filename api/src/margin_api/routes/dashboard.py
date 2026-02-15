"""Dashboard endpoint — high-conviction picks and watchlist from DB."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.schemas.dashboard import (
    DashboardResponse,
    PickSummary,
    WatchlistItem,
)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _latest_score_subquery():
    """Subquery for the most recent score per asset."""
    return (
        select(
            Score.asset_id,
            func.max(Score.scored_at).label("max_scored_at"),
        )
        .group_by(Score.asset_id)
        .subquery()
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get dashboard with high-conviction picks and watchlist."""
    latest = _latest_score_subquery()

    base = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
    )

    # Picks: exceptional + high conviction
    picks_result = await db.execute(
        base.where(Score.conviction_level.in_(["exceptional", "high"]))
        .order_by(Score.composite_percentile.desc())
    )
    picks = [
        PickSummary(
            ticker=row.ticker,
            name=row.asset_name,
            composite_percentile=row.Score.composite_percentile,
            conviction_level=row.Score.conviction_level,
            signal=row.Score.signal,
            quality_percentile=row.Score.quality_percentile,
            value_percentile=row.Score.value_percentile,
            momentum_percentile=row.Score.momentum_percentile,
            actual_price=getattr(row.Score, "actual_price", None),
            buy_price=getattr(row.Score, "buy_price", None),
            sell_price=getattr(row.Score, "sell_price", None),
            price_upside=(
                round((row.Score.intrinsic_value - row.Score.actual_price) / row.Score.actual_price, 4)
                if getattr(row.Score, "intrinsic_value", None) and getattr(row.Score, "actual_price", None)
                else None
            ),
        )
        for row in picks_result.all()
    ]

    # Watchlist
    watchlist_result = await db.execute(
        base.where(Score.conviction_level == "watchlist")
        .order_by(Score.composite_percentile.desc())
    )
    watchlist = [
        WatchlistItem(
            ticker=row.ticker,
            name=row.asset_name,
            composite_percentile=row.Score.composite_percentile,
            conviction_level=row.Score.conviction_level,
        )
        for row in watchlist_result.all()
    ]

    # Fallback: when the universe is too small for conviction thresholds,
    # show the top-ranked tickers so the dashboard isn't empty.
    if not picks and not watchlist:
        top_result = await db.execute(
            base.order_by(Score.composite_percentile.desc()).limit(10)
        )
        picks = [
            PickSummary(
                ticker=row.ticker,
                name=row.asset_name,
                composite_percentile=row.Score.composite_percentile,
                conviction_level=row.Score.conviction_level,
                signal=row.Score.signal,
                quality_percentile=row.Score.quality_percentile,
                value_percentile=row.Score.value_percentile,
                momentum_percentile=row.Score.momentum_percentile,
                actual_price=getattr(row.Score, "actual_price", None),
                buy_price=getattr(row.Score, "buy_price", None),
                sell_price=getattr(row.Score, "sell_price", None),
                price_upside=(
                    round((row.Score.intrinsic_value - row.Score.actual_price) / row.Score.actual_price, 4)
                    if getattr(row.Score, "intrinsic_value", None) and getattr(row.Score, "actual_price", None)
                    else None
                ),
            )
            for row in top_result.all()
        ]

    # Total scored
    total_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id)))
    )
    total_scored = total_result.scalar() or 0

    # Last updated
    updated_result = await db.execute(select(func.max(Score.scored_at)))
    last_updated_dt = updated_result.scalar()
    last_updated = (
        last_updated_dt.isoformat() if last_updated_dt
        else datetime.now(UTC).isoformat()
    )

    return DashboardResponse(
        picks=picks,
        watchlist=watchlist,
        last_updated=last_updated,
        total_scored=total_scored,
    )
