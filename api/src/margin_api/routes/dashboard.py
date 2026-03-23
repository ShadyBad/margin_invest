"""Dashboard endpoint — high-conviction picks and watchlist from DB.

Uses V4Score as the primary data source (same as /api/v1/scores endpoints)
to ensure cross-view consistency.  Falls back to the legacy Score table
only when no V4Score data exists.
"""

from __future__ import annotations

import logging
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
from margin_api.services.analytics import track_event
from margin_api.services.freshness import compute_freshness
from margin_api.services.universe import get_active_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Factor-percentile extraction from JSONB detail
# ---------------------------------------------------------------------------


def _extract_factor_avg(detail: dict, factor_key: str) -> float | None:
    """Return the average_percentile for a top-level factor in the detail JSONB.

    Handles both pre-computed ``average_percentile`` keys and manual
    calculation from ``sub_scores``.  Returns *None* when the factor is
    absent or has no usable sub-scores.
    """
    factor = detail.get(factor_key)
    if not isinstance(factor, dict):
        return None
    if "average_percentile" in factor:
        return round(float(factor["average_percentile"]), 1)
    subs = factor.get("sub_scores", [])
    active = [s for s in subs if isinstance(s, dict) and not s.get("stub", False)]
    if not active:
        return None
    total = sum(s.get("percentile_rank", 0) for s in active)
    return round(total / len(active), 1)


def _extract_sentiment_pct(detail: dict) -> float | None:
    """Extract the sentiment percentile from momentum's sub_scores."""
    momentum = detail.get("momentum")
    if not isinstance(momentum, dict):
        return None
    for ss in momentum.get("sub_scores", []):
        if isinstance(ss, dict) and ss.get("name") == "sentiment":
            return round(ss.get("percentile_rank", 0), 1)
    return None


# ---------------------------------------------------------------------------
# V4Score → PickSummary  (primary path)
# ---------------------------------------------------------------------------


def _pick_summary_from_v4_row(row) -> PickSummary:
    """Build a PickSummary from a V4Score DB query row.

    Expected row shape: (V4Score, ticker, asset_name, asset_sector).
    """
    v4 = row[0] if hasattr(row[0], "conviction") else row.V4Score
    ticker = row.ticker if hasattr(row, "ticker") else row[1]
    asset_name = row.asset_name if hasattr(row, "asset_name") else row[2]
    sector = row.asset_sector if hasattr(row, "asset_sector") else None

    detail = v4.detail or {}

    # Ensure scored_at is tz-aware
    scored_at: datetime | None = v4.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)

    # Factor percentiles from JSONB detail (same structure as CompositeScore.model_dump)
    quality_pct = _extract_factor_avg(detail, "quality") or 0.0
    value_pct = _extract_factor_avg(detail, "value") or 0.0
    momentum_pct = _extract_factor_avg(detail, "momentum") or 0.0
    sentiment_pct = _extract_sentiment_pct(detail)
    growth_pct = _extract_factor_avg(detail, "growth")

    # Price targets from detail JSONB
    actual_price = detail.get("actual_price")
    buy_price = detail.get("buy_price")
    sell_price = detail.get("sell_price")
    margin_invest_value = detail.get("margin_invest_value")
    invalid_reason = detail.get("price_target_invalid_reason")

    # Derive signal from conviction + price targets (matches engine logic)
    composite_tier = v4.conviction
    signal = detail.get("signal") or _derive_signal(
        composite_tier,
        actual_price,
        buy_price,
        sell_price,
    )

    composite_score = v4.composite_score
    composite_pct = float(detail.get("composite_percentile", composite_score))

    return PickSummary(
        score_id=v4.id,
        ticker=ticker,
        name=asset_name or "",
        score=composite_score,
        universe_percentile=composite_pct,
        composite_percentile=composite_pct,
        composite_tier=composite_tier,
        signal=signal,
        quality_percentile=quality_pct,
        value_percentile=value_pct,
        momentum_percentile=momentum_pct,
        sentiment_percentile=sentiment_pct,
        growth_percentile=growth_pct,
        actual_price=actual_price,
        buy_price=buy_price,
        sell_price=sell_price,
        price_upside=(
            round((margin_invest_value - actual_price) / actual_price, 4)
            if margin_invest_value and actual_price and not invalid_reason
            else None
        ),
        data_freshness=compute_freshness(scored_at),
        scored_at=scored_at.isoformat() if scored_at else None,
        price_source="daily_close",
        price_updated_at=scored_at.isoformat() if scored_at else None,
        opportunity_type=v4.opportunity_type,
        winning_track=detail.get("winning_track"),
        max_position_pct=v4.max_position_pct,
        timing_signal=v4.timing_signal,
        margin_of_safety=(
            round((margin_invest_value - actual_price) / margin_invest_value, 4)
            if margin_invest_value
            and actual_price
            and actual_price < margin_invest_value
            and not invalid_reason
            else None
        ),
        sector=sector,
        price_target_invalid_reason=invalid_reason,
        ml_override=v4.ml_override,
        style=v4.style,
    )


def _watchlist_item_from_v4_row(row) -> WatchlistItem:
    """Build a WatchlistItem from a V4Score DB query row."""
    v4 = row[0] if hasattr(row[0], "conviction") else row.V4Score
    detail = v4.detail or {}

    actual_price = detail.get("actual_price")
    margin_invest_value = detail.get("margin_invest_value")
    invalid_reason = detail.get("price_target_invalid_reason")

    return WatchlistItem(
        ticker=row.ticker if hasattr(row, "ticker") else row[1],
        name=row.asset_name if hasattr(row, "asset_name") else row[2],
        composite_raw_score=v4.composite_score,
        composite_tier=v4.conviction,
        sector=row.asset_sector if hasattr(row, "asset_sector") else None,
        actual_price=actual_price,
        price_upside=(
            round((margin_invest_value - actual_price) / actual_price, 4)
            if margin_invest_value and actual_price and not invalid_reason
            else None
        ),
        opportunity_type=v4.opportunity_type,
    )


# ---------------------------------------------------------------------------
# Legacy Score → PickSummary  (fallback when no V4Score data exists)
# ---------------------------------------------------------------------------


def _pick_summary_from_score_row(row) -> PickSummary:
    """Build a PickSummary from a legacy Score DB query row."""
    s = row.Score
    invalid_reason = getattr(s, "price_target_invalid_reason", None)

    detail = s.score_detail or {}
    sentiment_pct = _extract_sentiment_pct(detail)
    growth_pct = _extract_factor_avg(detail, "growth")

    return PickSummary(
        score_id=s.id,
        ticker=row.ticker,
        name=row.asset_name,
        score=s.composite_raw_score,
        universe_percentile=s.composite_percentile,
        composite_percentile=s.composite_percentile,
        composite_tier=s.conviction_level,
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


# ---------------------------------------------------------------------------
# Subqueries
# ---------------------------------------------------------------------------


def _latest_v4_score_subquery():
    """Subquery for the most recent V4Score per asset."""
    return (
        select(
            V4Score.asset_id,
            func.max(V4Score.scored_at).label("max_scored_at"),
        )
        .group_by(V4Score.asset_id)
        .subquery()
    )


def _latest_score_subquery():
    """Subquery for the most recent legacy Score per asset."""
    return (
        select(
            Score.asset_id,
            func.max(Score.scored_at).label("max_scored_at"),
        )
        .group_by(Score.asset_id)
        .subquery()
    )


# ---------------------------------------------------------------------------
# Core fetch logic — V4Score primary, Score fallback
# ---------------------------------------------------------------------------


async def _fetch_picks_and_watchlist(
    db: AsyncSession,
    v4_base,
    score_base,
) -> tuple[list[PickSummary], list[WatchlistItem]]:
    """Fetch picks and watchlist from V4Score (primary), Score fallback.

    Args:
        v4_base: V4Score base query (latest per asset, with universe filter).
        score_base: Legacy Score base query (only used when V4 yields nothing).
    """
    # ── V4Score primary path ──────────────────────────────────────────
    picks_result = await db.execute(
        v4_base.where(V4Score.conviction.in_(["exceptional", "high"])).order_by(
            V4Score.composite_score.desc()
        )
    )
    picks = [_pick_summary_from_v4_row(row) for row in picks_result.all()]

    watchlist_result = await db.execute(
        v4_base.where(V4Score.conviction.in_(["medium"])).order_by(V4Score.composite_score.desc())
    )
    watchlist = [_watchlist_item_from_v4_row(row) for row in watchlist_result.all()]

    # V4 fallback: show top-ranked if no conviction-based picks
    if not picks and not watchlist:
        top_result = await db.execute(v4_base.order_by(V4Score.composite_score.desc()).limit(10))
        picks = [_pick_summary_from_v4_row(row) for row in top_result.all()]

    # ── Legacy Score fallback (no V4 data at all) ─────────────────────
    if not picks and not watchlist and score_base is not None:
        legacy_picks_result = await db.execute(
            score_base.where(Score.conviction_level.in_(["exceptional", "high"])).order_by(
                Score.composite_raw_score.desc()
            )
        )
        picks = [_pick_summary_from_score_row(row) for row in legacy_picks_result.all()]

        legacy_wl_result = await db.execute(
            score_base.where(Score.conviction_level.in_(["medium", "watchlist"])).order_by(
                Score.composite_raw_score.desc()
            )
        )
        watchlist = [
            WatchlistItem(
                ticker=row.ticker,
                name=row.asset_name,
                composite_raw_score=row.Score.composite_raw_score,
                composite_tier=row.Score.conviction_level,
                sector=getattr(row, "asset_sector", None),
                actual_price=getattr(row.Score, "actual_price", None),
                price_upside=None,
                opportunity_type=getattr(row.Score, "opportunity_type", None),
            )
            for row in legacy_wl_result.all()
        ]

        if not picks and not watchlist:
            top_result = await db.execute(
                score_base.order_by(Score.composite_raw_score.desc()).limit(10)
            )
            picks = [_pick_summary_from_score_row(row) for row in top_result.all()]

    return picks, watchlist


def _derive_composite_tier(raw_score: float) -> str:
    """Re-derive composite_tier from raw_score using engine thresholds."""
    if raw_score >= 76.0:
        return "exceptional"
    if raw_score >= 71.0:
        return "high"
    if raw_score >= 66.0:
        return "medium"
    return "none"


def _derive_signal(
    composite_tier: str,
    actual_price=None,
    buy_price=None,
    sell_price=None,
) -> str:
    """Re-derive signal from composite_tier and price targets."""
    if composite_tier == "medium":
        return "emerging"
    if composite_tier == "none":
        return "neutral"
    if actual_price is not None and sell_price is not None and buy_price is not None:
        if actual_price > sell_price * 1.15:
            return "failed"
        if actual_price > sell_price:
            return "weak"
        if actual_price <= buy_price:
            return "strong"
        return "stable"
    return "strong"


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
            "composite_tier": s.conviction_level,
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

        derived_conviction = _derive_composite_tier(s.composite_raw_score)
        derived_signal = _derive_signal(
            derived_conviction,
            actual_price=getattr(s, "actual_price", None),
            buy_price=getattr(s, "buy_price", None),
            sell_price=getattr(s, "sell_price", None),
        )

        derived_values = {
            "composite_tier": derived_conviction,
            "signal": derived_signal,
        }

        mismatches = []
        if s.conviction_level != derived_conviction:
            mismatches.append(
                {
                    "field": "composite_tier",
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
    """Get dashboard with high-conviction picks and watchlist.

    Uses V4Score as the primary data source (consistent with /api/v1/scores
    endpoints).  Falls back to the legacy Score table when no V4Score data
    exists so the dashboard is never empty for older deployments.
    """
    latest_v4 = _latest_v4_score_subquery()
    latest_legacy = _latest_score_subquery()

    # Only show tickers in the active universe (excludes OTC/foreign stocks
    # from previous scoring runs).
    snapshot = await get_active_snapshot(db)
    active_tickers: list[str] | None = None
    if snapshot and snapshot.tickers:
        active_tickers = snapshot.tickers  # type: ignore[assignment]

    # V4Score base query: latest V4 score per asset joined with asset metadata.
    v4_base_unfiltered = (
        select(
            V4Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .join(
            latest_v4,
            (V4Score.asset_id == latest_v4.c.asset_id)
            & (V4Score.scored_at == latest_v4.c.max_scored_at),
        )
    )

    # Legacy Score base query (fallback only).
    score_base_unfiltered = (
        select(
            Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
        )
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest_legacy,
            (Score.asset_id == latest_legacy.c.asset_id)
            & (Score.scored_at == latest_legacy.c.max_scored_at),
        )
    )

    # Universe ticker subquery (shared between filters).
    universe_ticker_subq = None
    if active_tickers is not None and len(active_tickers) > 500:
        universe_ticker_subq = select(
            func.jsonb_array_elements_text(UniverseSnapshot.tickers)
        ).where(UniverseSnapshot.is_active.is_(True))

    # Apply universe filter when an active snapshot exists.
    v4_base = v4_base_unfiltered
    score_base = score_base_unfiltered
    if active_tickers is not None:
        if universe_ticker_subq is not None:
            v4_base = v4_base.where(Asset.ticker.in_(universe_ticker_subq))
            score_base = score_base.where(Asset.ticker.in_(universe_ticker_subq))
        else:
            v4_base = v4_base.where(Asset.ticker.in_(active_tickers))
            score_base = score_base.where(Asset.ticker.in_(active_tickers))

    picks, watchlist = await _fetch_picks_and_watchlist(db, v4_base, score_base)

    # Fallback: if universe filter produced zero results but scores exist
    # in the DB, bypass the filter so the dashboard isn't empty.
    if not picks and not watchlist and active_tickers is not None:
        picks, watchlist = await _fetch_picks_and_watchlist(
            db,
            v4_base_unfiltered,
            score_base_unfiltered,
        )

    # Total scored — count from V4Score (primary), fall back to Score.
    v4_count_q = select(func.count(func.distinct(V4Score.asset_id)))
    if active_tickers is not None:
        v4_count_q = v4_count_q.join(Asset, V4Score.asset_id == Asset.id)
        if universe_ticker_subq is not None:
            v4_count_q = v4_count_q.where(Asset.ticker.in_(universe_ticker_subq))
        else:
            v4_count_q = v4_count_q.where(Asset.ticker.in_(active_tickers))
    total_result = await db.execute(v4_count_q)
    total_scored = total_result.scalar() or 0

    # If no V4 data, count from legacy Score table.
    if total_scored == 0:
        legacy_count_q = select(func.count(func.distinct(Score.asset_id)))
        if active_tickers is not None:
            legacy_count_q = legacy_count_q.join(Asset, Score.asset_id == Asset.id)
            if universe_ticker_subq is not None:
                legacy_count_q = legacy_count_q.where(Asset.ticker.in_(universe_ticker_subq))
            else:
                legacy_count_q = legacy_count_q.where(Asset.ticker.in_(active_tickers))
        total_result = await db.execute(legacy_count_q)
        total_scored = total_result.scalar() or 0

    # Last updated — use the most recent scored_at across both Score and V4Score tables
    score_ts_result = await db.execute(select(func.max(Score.scored_at)))
    score_ts = score_ts_result.scalar()
    v4_ts_result = await db.execute(select(func.max(V4Score.scored_at)))
    v4_ts = v4_ts_result.scalar()
    last_updated_dt = max(filter(None, [score_ts, v4_ts]), default=None)
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

    # ── Autonomous-org PostHog events ────────────────────────────────
    # Fire events that the autonomous-org webhook handler maps to agents.
    # PostHog deduplicates by distinct_id + event within its pipeline.
    _fire_dashboard_events(picks, universe)

    return DashboardResponse(
        picks=picks,
        watchlist=watchlist,
        last_updated=last_updated,
        total_scored=total_scored,
        universe=universe,
        warnings=warnings,
    )


def _fire_dashboard_events(
    picks: list[PickSummary],
    universe: UniverseSummary | None,
) -> None:
    """Fire PostHog events consumed by the autonomous-org engine."""
    org_id = "margin_invest"

    # north_star_drop — portfolio conviction below "Moderate" threshold
    if picks:
        avg_score = sum(p.score or p.composite_percentile for p in picks) / len(picks)
        if avg_score < 30:
            track_event(
                org_id,
                "north_star_drop",
                {
                    "avg_score": round(avg_score, 1),
                    "pick_count": len(picks),
                    "label": "Weak",
                },
            )

    # pql_threshold_crossed — universe fully scored (product-qualified)
    if universe and universe.scoring_coverage >= 0.95:
        track_event(
            org_id,
            "pql_threshold_crossed",
            {
                "scoring_coverage": universe.scoring_coverage,
                "universe_size": universe.size,
                "version": universe.version,
            },
        )

    # churn_risk_threshold_crossed — expired data signals product failure
    expired_picks = [p for p in picks if p.data_freshness == "expired"]
    if expired_picks:
        expired_ratio = len(expired_picks) / len(picks) if picks else 0
        if expired_ratio >= 0.5:
            track_event(
                org_id,
                "churn_risk_threshold_crossed",
                {
                    "expired_count": len(expired_picks),
                    "total_picks": len(picks),
                    "expired_ratio": round(expired_ratio, 2),
                },
            )

    # feature_flag_stale — any pick with expired data freshness
    for p in expired_picks[:3]:  # cap to avoid noise
        track_event(
            org_id,
            "feature_flag_stale",
            {
                "ticker": p.ticker,
                "data_freshness": p.data_freshness,
                "scored_at": p.scored_at,
            },
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
    total_v4_scores = (await db.execute(select(func.count()).select_from(V4Score))).scalar() or 0

    total_assets_scored = (
        await db.execute(select(func.count(func.distinct(Score.asset_id))))
    ).scalar() or 0
    total_v4_assets_scored = (
        await db.execute(select(func.count(func.distinct(V4Score.asset_id))))
    ).scalar() or 0

    total_assets = (await db.execute(select(func.count()).select_from(Asset))).scalar() or 0

    latest_scored_at = (await db.execute(select(func.max(Score.scored_at)))).scalar()
    latest_v4_scored_at = (await db.execute(select(func.max(V4Score.scored_at)))).scalar()

    # Count scores matching universe tickers
    universe_scored = 0
    v4_universe_scored = 0
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
        v4_universe_scored = (
            await db.execute(
                select(func.count(func.distinct(V4Score.asset_id)))
                .join(Asset, V4Score.asset_id == Asset.id)
                .where(Asset.ticker.in_(universe_ticker_subq))
            )
        ).scalar() or 0

    # V4 conviction breakdown (primary — what the dashboard now uses)
    latest_v4 = _latest_v4_score_subquery()
    v4_conviction_counts: dict[str, int] = {}
    v4_rows = (
        await db.execute(
            select(V4Score.conviction, func.count())
            .join(
                latest_v4,
                (V4Score.asset_id == latest_v4.c.asset_id)
                & (V4Score.scored_at == latest_v4.c.max_scored_at),
            )
            .group_by(V4Score.conviction)
        )
    ).all()
    for row in v4_rows:
        v4_conviction_counts[row[0]] = row[1]

    # Legacy conviction breakdown
    latest = _latest_score_subquery()
    legacy_conviction_counts: dict[str, int] = {}
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
        legacy_conviction_counts[row[0]] = row[1]

    # Backward-compat: "scores" mirrors whichever source is primary
    # (V4 if available, legacy otherwise).
    primary_total = total_v4_scores if total_v4_scores > 0 else total_scores
    primary_assets = total_v4_assets_scored if total_v4_assets_scored > 0 else total_assets_scored
    primary_universe = v4_universe_scored if v4_universe_scored > 0 else universe_scored
    primary_ts = latest_v4_scored_at or latest_scored_at

    return {
        "snapshot": {
            "version": snapshot.version if snapshot else None,
            "ticker_count": snapshot.ticker_count if snapshot else 0,
            "is_active": snapshot.is_active if snapshot else False,
        },
        "scores": {
            "total_rows": primary_total,
            "unique_assets_scored": primary_assets,
            "universe_assets_scored": primary_universe,
            "latest_scored_at": primary_ts.isoformat() if primary_ts else None,
        },
        "v4_scores": {
            "total_rows": total_v4_scores,
            "unique_assets_scored": total_v4_assets_scored,
            "universe_assets_scored": v4_universe_scored,
            "latest_scored_at": (latest_v4_scored_at.isoformat() if latest_v4_scored_at else None),
        },
        "legacy_scores": {
            "total_rows": total_scores,
            "unique_assets_scored": total_assets_scored,
            "universe_assets_scored": universe_scored,
            "latest_scored_at": latest_scored_at.isoformat() if latest_scored_at else None,
        },
        "assets": {
            "total": total_assets,
        },
        "tier_breakdown": v4_conviction_counts,
        "legacy_tier_breakdown": legacy_conviction_counts,
    }
