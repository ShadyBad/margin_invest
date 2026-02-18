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


def _pick_summary_from_row(row) -> PickSummary:
    """Build a PickSummary from a DB query row (Score, ticker, asset_name)."""
    s = row.Score
    invalid_reason = getattr(s, "price_target_invalid_reason", None)
    return PickSummary(
        ticker=row.ticker,
        name=row.asset_name,
        score=s.composite_raw_score,
        universe_percentile=s.composite_percentile,
        composite_percentile=s.composite_percentile,
        conviction_level=s.conviction_level,
        signal=s.signal,
        quality_percentile=s.quality_percentile,
        value_percentile=s.value_percentile,
        momentum_percentile=s.momentum_percentile,
        actual_price=getattr(s, "actual_price", None),
        buy_price=getattr(s, "buy_price", None),
        sell_price=getattr(s, "sell_price", None),
        price_upside=(
            round((s.intrinsic_value - s.actual_price) / s.actual_price, 4)
            if getattr(s, "intrinsic_value", None)
            and getattr(s, "actual_price", None)
            and not invalid_reason
            else None
        ),
        data_freshness=compute_freshness(s.scored_at),
        scored_at=s.scored_at.isoformat() if s.scored_at else None,
        price_source="daily_close",
        price_updated_at=s.scored_at.isoformat() if s.scored_at else None,
        opportunity_type=getattr(s, "opportunity_type", None),
        winning_track=getattr(s, "winning_track", None),
        max_position_pct=getattr(s, "max_position_pct", None),
        timing_signal=getattr(s, "timing_signal", None),
        margin_of_safety=(
            round(
                (s.intrinsic_value - s.actual_price) / s.intrinsic_value,
                4,
            )
            if getattr(s, "intrinsic_value", None)
            and getattr(s, "actual_price", None)
            and s.actual_price < s.intrinsic_value
            and not invalid_reason
            else None
        ),
        sector=getattr(row, "asset_sector", None),
        price_target_invalid_reason=invalid_reason,
    )


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

    # Only show tickers in the active universe (excludes OTC/foreign stocks
    # from previous scoring runs).
    snapshot = await get_active_snapshot(db)
    active_tickers: list[str] | None = None
    if snapshot and snapshot.tickers:
        active_tickers = snapshot.tickers  # type: ignore[assignment]

    base = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"), Asset.sector.label("asset_sector"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
    )

    if active_tickers is not None:
        base = base.where(Asset.ticker.in_(active_tickers))

    # Picks: exceptional + high conviction
    picks_result = await db.execute(
        base.where(Score.conviction_level.in_(["exceptional", "high"]))
        .order_by(Score.composite_percentile.desc())
    )
    picks = [_pick_summary_from_row(row) for row in picks_result.all()]

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
        picks = [_pick_summary_from_row(row) for row in top_result.all()]

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

    # Universe metadata (reuse snapshot fetched above)
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
