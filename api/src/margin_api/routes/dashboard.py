"""Dashboard endpoint — high-conviction picks and watchlist from DB."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score, UniverseSnapshot, V4Score
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
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

    # Extract optional factor percentiles from score_detail JSONB
    detail = s.score_detail or {}
    sentiment_pct = None
    growth_pct = None
    for factor_key in ("sentiment", "growth"):
        factor_data = detail.get(factor_key)
        if isinstance(factor_data, dict):
            sub_scores = factor_data.get("sub_scores", [])
            if sub_scores:
                total = sum(ss.get("percentile_rank", 0) for ss in sub_scores)
                if factor_key == "sentiment":
                    sentiment_pct = round(total / len(sub_scores), 1)
                else:
                    growth_pct = round(total / len(sub_scores), 1)

    return PickSummary(
        score_id=s.id,
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
        sentiment_percentile=sentiment_pct,
        growth_percentile=growth_pct,
        actual_price=getattr(s, "actual_price", None),
        buy_price=getattr(s, "buy_price", None),
        sell_price=getattr(s, "sell_price", None),
        price_upside=(
            round((s.margin_invest_value - s.actual_price) / s.actual_price, 4)
            if getattr(s, "margin_invest_value", None)
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
                (s.margin_invest_value - s.actual_price) / s.margin_invest_value,
                4,
            )
            if getattr(s, "margin_invest_value", None)
            and getattr(s, "actual_price", None)
            and s.actual_price < s.margin_invest_value
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


async def _fetch_picks_and_watchlist(
    db: AsyncSession,
    base,
) -> tuple[list[PickSummary], list[WatchlistItem]]:
    """Run picks + watchlist queries with a top-10 fallback."""
    picks_result = await db.execute(
        base.where(Score.conviction_level.in_(["exceptional", "high"])).order_by(
            Score.composite_raw_score.desc()
        )
    )
    picks = [_pick_summary_from_row(row) for row in picks_result.all()]

    watchlist_result = await db.execute(
        base.where(Score.conviction_level.in_(["medium", "watchlist"])).order_by(
            Score.composite_raw_score.desc()
        )
    )
    watchlist = [
        WatchlistItem(
            ticker=row.ticker,
            name=row.asset_name,
            composite_raw_score=row.Score.composite_raw_score,
            conviction_level=row.Score.conviction_level,
            sector=getattr(row, "asset_sector", None),
            actual_price=getattr(row.Score, "actual_price", None),
            price_upside=(
                round(
                    (row.Score.margin_invest_value - row.Score.actual_price)
                    / row.Score.actual_price,
                    4,
                )
                if getattr(row.Score, "margin_invest_value", None)
                and getattr(row.Score, "actual_price", None)
                and not getattr(row.Score, "price_target_invalid_reason", None)
                else None
            ),
            opportunity_type=getattr(row.Score, "opportunity_type", None),
        )
        for row in watchlist_result.all()
    ]

    # Fallback: when no conviction-based picks exist, show top-ranked tickers.
    if not picks and not watchlist:
        top_result = await db.execute(base.order_by(Score.composite_raw_score.desc()).limit(10))
        picks = [_pick_summary_from_row(row) for row in top_result.all()]

    # Enrich picks with V4 ML fields (ml_override, style)
    if picks:
        pick_tickers = [p.ticker for p in picks]
        v4_latest_subq = (
            select(
                V4Score.asset_id,
                func.max(V4Score.scored_at).label("max_scored_at"),
            )
            .where(V4Score.published == True)  # noqa: E712
            .group_by(V4Score.asset_id)
            .subquery()
        )
        v4_result = await db.execute(
            select(V4Score, Asset.ticker)
            .join(Asset, V4Score.asset_id == Asset.id)
            .join(
                v4_latest_subq,
                (V4Score.asset_id == v4_latest_subq.c.asset_id)
                & (V4Score.scored_at == v4_latest_subq.c.max_scored_at),
            )
            .where(Asset.ticker.in_(pick_tickers))
            .where(V4Score.published == True)  # noqa: E712
        )
        v4_map: dict[str, V4Score] = {}
        for row in v4_result.all():
            v4_map[row.ticker] = row[0]  # V4Score object

        for pick in picks:
            v4 = v4_map.get(pick.ticker)
            if v4:
                pick.ml_override = v4.ml_override
                pick.style = v4.style

    return picks, watchlist


def _derive_conviction_level(raw_score: float) -> str:
    """Re-derive conviction_level from raw_score using engine thresholds."""
    if raw_score >= 79.0:
        return "exceptional"
    if raw_score >= 72.0:
        return "high"
    if raw_score >= 65.0:
        return "medium"
    return "none"


def _derive_signal(
    conviction_level: str,
    actual_price=None,
    buy_price=None,
    sell_price=None,
) -> str:
    """Re-derive signal from conviction_level and price targets."""
    if conviction_level == "medium":
        return "watch"
    if conviction_level == "none":
        return "no_action"
    if actual_price is not None and sell_price is not None and buy_price is not None:
        if actual_price > sell_price * 1.15:
            return "urgent_sell"
        if actual_price > sell_price:
            return "sell"
        if actual_price <= buy_price:
            return "buy"
        return "hold"
    return "buy"


@router.get("/dashboard/audit")
@limiter.limit("20/minute")
async def audit_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Audit dashboard card values against DB and engine-derived values."""
    latest = _latest_score_subquery()
    base = (
        select(
            Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
        )
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id) & (Score.scored_at == latest.c.max_scored_at),
        )
        .order_by(Score.composite_raw_score.desc())
    )

    result = await db.execute(base)
    entries = []
    for row in result.all():
        s = row.Score

        db_values = {
            "score_id": s.id,
            "composite_raw_score": s.composite_raw_score,
            "composite_percentile": s.composite_percentile,
            "conviction_level": s.conviction_level,
            "signal": s.signal,
            "quality_percentile": s.quality_percentile,
            "value_percentile": s.value_percentile,
            "momentum_percentile": s.momentum_percentile,
            "actual_price": getattr(s, "actual_price", None),
            "buy_price": getattr(s, "buy_price", None),
            "sell_price": getattr(s, "sell_price", None),
            "margin_invest_value": getattr(s, "margin_invest_value", None),
            "scored_at": s.scored_at.isoformat() if s.scored_at else None,
        }

        derived_conviction = _derive_conviction_level(s.composite_raw_score)
        derived_signal = _derive_signal(
            derived_conviction,
            actual_price=getattr(s, "actual_price", None),
            buy_price=getattr(s, "buy_price", None),
            sell_price=getattr(s, "sell_price", None),
        )

        derived_values = {
            "conviction_level": derived_conviction,
            "signal": derived_signal,
        }

        mismatches = []
        if s.conviction_level != derived_conviction:
            mismatches.append(
                {
                    "field": "conviction_level",
                    "db_value": s.conviction_level,
                    "derived_value": derived_conviction,
                }
            )
        if s.signal != derived_signal:
            mismatches.append(
                {
                    "field": "signal",
                    "db_value": s.signal,
                    "derived_value": derived_signal,
                }
            )

        entries.append(
            {
                "ticker": row.ticker,
                "name": row.asset_name,
                "db_values": db_values,
                "derived_values": derived_values,
                "mismatches": mismatches,
            }
        )

    return {"entries": entries, "total": len(entries)}


@router.get("/dashboard", response_model=DashboardResponse)
@limiter.limit("20/minute")
async def get_dashboard(
    request: Request,
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

    # Base query: latest score per asset joined with asset metadata.
    base_unfiltered = (
        select(
            Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
        )
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id) & (Score.scored_at == latest.c.max_scored_at),
        )
    )

    # Apply universe filter when an active snapshot exists.
    base = base_unfiltered
    if active_tickers is not None:
        if len(active_tickers) > 500:
            # Large universe: use a server-side subquery to avoid asyncpg
            # bind-parameter limits (~3000 tickers as individual $N::VARCHAR
            # params causes compilation/performance failures).
            universe_ticker_subq = select(
                func.jsonb_array_elements_text(UniverseSnapshot.tickers)
            ).where(UniverseSnapshot.is_active.is_(True))
            base = base.where(Asset.ticker.in_(universe_ticker_subq))
        else:
            base = base.where(Asset.ticker.in_(active_tickers))

    picks, watchlist = await _fetch_picks_and_watchlist(db, base)

    # Fallback: if universe filter produced zero results but scores exist
    # in the DB, bypass the filter so the dashboard isn't empty.
    if not picks and not watchlist and active_tickers is not None:
        picks, watchlist = await _fetch_picks_and_watchlist(db, base_unfiltered)

    # Total scored (universe-aware for accurate coverage calculation)
    if active_tickers is not None:
        scored_count_q = select(func.count(func.distinct(Score.asset_id))).join(
            Asset, Score.asset_id == Asset.id
        )
        if len(active_tickers) > 500:
            scored_count_q = scored_count_q.where(Asset.ticker.in_(universe_ticker_subq))
        else:
            scored_count_q = scored_count_q.where(Asset.ticker.in_(active_tickers))
        total_result = await db.execute(scored_count_q)
    else:
        total_result = await db.execute(select(func.count(func.distinct(Score.asset_id))))
    total_scored = total_result.scalar() or 0

    # Last updated
    updated_result = await db.execute(select(func.max(Score.scored_at)))
    last_updated_dt = updated_result.scalar()
    last_updated = last_updated_dt.isoformat() if last_updated_dt else datetime.now(UTC).isoformat()

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
        scoring_coverage = (
            total_scored / snapshot.ticker_count if snapshot.ticker_count > 0 else 0.0
        )
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
                    message=(
                        f"Only {pct}% of the universe has been scored."
                        " Rankings may shift as more data arrives."
                    ),
                    severity="warning",
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


@router.get("/dashboard/status")
@limiter.limit("20/minute")
async def get_dashboard_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Diagnostic endpoint for debugging empty dashboard issues."""
    snapshot = await get_active_snapshot(db)

    total_scores = (await db.execute(select(func.count()).select_from(Score))).scalar() or 0

    total_assets_scored = (
        await db.execute(select(func.count(func.distinct(Score.asset_id))))
    ).scalar() or 0

    total_assets = (await db.execute(select(func.count()).select_from(Asset))).scalar() or 0

    latest_scored_at = (await db.execute(select(func.max(Score.scored_at)))).scalar()

    # Count scores matching universe tickers
    universe_scored = 0
    if snapshot and snapshot.tickers and len(snapshot.tickers) > 0:
        universe_ticker_subq = select(
            func.jsonb_array_elements_text(UniverseSnapshot.tickers)
        ).where(UniverseSnapshot.is_active.is_(True))
        universe_scored = (
            await db.execute(
                select(func.count(func.distinct(Score.asset_id)))
                .join(Asset, Score.asset_id == Asset.id)
                .where(Asset.ticker.in_(universe_ticker_subq))
            )
        ).scalar() or 0

    # Conviction level breakdown of latest scores
    latest = _latest_score_subquery()
    conviction_counts = {}
    rows = (
        await db.execute(
            select(Score.conviction_level, func.count())
            .join(
                latest,
                (Score.asset_id == latest.c.asset_id) & (Score.scored_at == latest.c.max_scored_at),
            )
            .group_by(Score.conviction_level)
        )
    ).all()
    for row in rows:
        conviction_counts[row[0]] = row[1]

    return {
        "snapshot": {
            "version": snapshot.version if snapshot else None,
            "ticker_count": snapshot.ticker_count if snapshot else 0,
            "is_active": snapshot.is_active if snapshot else False,
        },
        "scores": {
            "total_rows": total_scores,
            "unique_assets_scored": total_assets_scored,
            "universe_assets_scored": universe_scored,
            "latest_scored_at": latest_scored_at.isoformat() if latest_scored_at else None,
        },
        "assets": {
            "total": total_assets,
        },
        "conviction_breakdown": conviction_counts,
    }
