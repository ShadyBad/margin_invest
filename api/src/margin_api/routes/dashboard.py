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
from margin_api.schemas.universe import UniverseSummary, Warning
from margin_api.services.freshness import compute_freshness
from margin_api.services.universe import get_active_snapshot

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
            score=row.Score.composite_raw_score,
            universe_percentile=row.Score.composite_percentile,
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
                if getattr(row.Score, "intrinsic_value", None)
                and getattr(row.Score, "actual_price", None)
                and not getattr(row.Score, "price_target_invalid_reason", None)
                else None
            ),
            data_freshness=compute_freshness(row.Score.scored_at),
            scored_at=row.Score.scored_at.isoformat() if row.Score.scored_at else None,
            price_source="daily_close",
            price_updated_at=row.Score.scored_at.isoformat() if row.Score.scored_at else None,
            opportunity_type=getattr(row.Score, "opportunity_type", None),
            winning_track=getattr(row.Score, "winning_track", None),
            max_position_pct=getattr(row.Score, "max_position_pct", None),
            timing_signal=getattr(row.Score, "timing_signal", None),
            margin_of_safety=(
                round(
                    (row.Score.intrinsic_value - row.Score.actual_price)
                    / row.Score.intrinsic_value,
                    4,
                )
                if getattr(row.Score, "intrinsic_value", None)
                and getattr(row.Score, "actual_price", None)
                and row.Score.actual_price < row.Score.intrinsic_value
                and not getattr(row.Score, "price_target_invalid_reason", None)
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
                score=row.Score.composite_raw_score,
                universe_percentile=row.Score.composite_percentile,
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
                    if getattr(row.Score, "intrinsic_value", None)
                    and getattr(row.Score, "actual_price", None)
                    and not getattr(row.Score, "price_target_invalid_reason", None)
                    else None
                ),
                data_freshness=compute_freshness(row.Score.scored_at),
                scored_at=row.Score.scored_at.isoformat() if row.Score.scored_at else None,
                price_source="daily_close",
                price_updated_at=row.Score.scored_at.isoformat() if row.Score.scored_at else None,
                opportunity_type=getattr(row.Score, "opportunity_type", None),
                winning_track=getattr(row.Score, "winning_track", None),
                max_position_pct=getattr(row.Score, "max_position_pct", None),
                timing_signal=getattr(row.Score, "timing_signal", None),
                margin_of_safety=(
                    round(
                        (row.Score.intrinsic_value - row.Score.actual_price)
                        / row.Score.intrinsic_value,
                        4,
                    )
                    if getattr(row.Score, "intrinsic_value", None)
                    and getattr(row.Score, "actual_price", None)
                    and row.Score.actual_price < row.Score.intrinsic_value
                    and not getattr(row.Score, "price_target_invalid_reason", None)
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

    # Universe metadata
    snapshot = await get_active_snapshot(db)
    universe: UniverseSummary | None = None
    warnings: list[Warning] = []

    if snapshot is None:
        warnings.append(
            Warning(
                code="NO_UNIVERSE",
                message="No active universe snapshot. Run 'margin ingest universe activate' first.",
                severity="warning",
            )
        )
    else:
        scoring_coverage = total_scored / snapshot.ticker_count if snapshot.ticker_count > 0 else 0.0
        is_complete = scoring_coverage >= 0.95
        universe = UniverseSummary(
            version=snapshot.version,
            size=snapshot.ticker_count,
            scoring_coverage=round(scoring_coverage, 4),
            is_complete=is_complete,
            last_scoring_run=last_updated_dt,
        )
        if not is_complete:
            pct = round(scoring_coverage * 100, 1)
            warnings.append(
                Warning(
                    code="LOW_COVERAGE",
                    message=f"Only {pct}% of the universe has been scored.",
                    severity="warning" if scoring_coverage >= 0.5 else "error",
                )
            )

    return DashboardResponse(
        picks=picks,
        watchlist=watchlist,
        last_updated=last_updated,
        total_scored=total_scored,
        universe=universe,
        warnings=warnings,
    )
