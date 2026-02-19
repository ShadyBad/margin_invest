"""Score endpoints for the Margin Invest API — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.schemas.score_history import ScoreHistoryPoint, ScoreHistoryResponse
from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    ScoreListResponse,
    ScoreResponse,
)
from margin_api.services.freshness import compute_freshness

router = APIRouter(prefix="/api/v1/scores", tags=["scores"])


def _score_response_from_row(
    row,
    live_price_data: dict | None = None,
) -> ScoreResponse:
    """Build a ScoreResponse from a DB query row.

    If score_detail JSONB is present, use it for full factor breakdowns.
    Otherwise, build a minimal response from summary columns.

    Args:
        row: DB query row (Score, ticker, asset_name).
        live_price_data: Optional dict from LivePriceService.get_price().
    """
    # row is a Row tuple: (Score, ticker, asset_name)
    score = row[0] if hasattr(row[0], "composite_percentile") else row.Score
    ticker = row.ticker if hasattr(row, "ticker") else row[1]

    # Compute freshness and price source
    # Ensure scored_at is tz-aware (SQLite returns naive datetimes)
    scored_at: datetime | None = score.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)
    freshness = compute_freshness(scored_at)

    if live_price_data:
        price_source = "live"
        price_updated_at = live_price_data.get("updated_at")
    else:
        price_source = "daily_close"
        price_updated_at = scored_at.isoformat() if scored_at else None

    detail = score.score_detail
    if detail:
        try:
            # Several fields are computed @property on engine models, not in model_dump().
            detail.setdefault("conviction_level", score.conviction_level)
            detail.setdefault("signal", score.signal)
            detail.setdefault("name", row.asset_name if hasattr(row, "asset_name") else "")
            detail.setdefault(
                "scored_at", scored_at.isoformat() if scored_at else None
            )
            for f in detail.get("filters_passed", []):
                f.setdefault("verdict", "pass" if f.get("passed") else "fail")
            for factor_key in ("quality", "value", "momentum", "capital_allocation", "catalyst"):
                factor = detail.get(factor_key)
                if factor is not None and isinstance(factor, dict) and "average_percentile" not in factor:
                    subs = factor.get("sub_scores", [])
                    avg = (
                        sum(s.get("percentile_rank", 0) for s in subs) / len(subs)
                        if subs
                        else 0.0
                    )
                    factor["average_percentile"] = avg
            # Populate score and universe_percentile from raw score / percentile
            detail.setdefault("score", detail.get("composite_raw_score", score.composite_raw_score))
            detail.setdefault("universe_percentile", detail.get("composite_percentile", score.composite_percentile))
            # Include price target fields from DB columns
            detail.setdefault("intrinsic_value", getattr(score, "intrinsic_value", None))
            detail.setdefault("buy_price", getattr(score, "buy_price", None))
            detail.setdefault("sell_price", getattr(score, "sell_price", None))
            detail.setdefault("actual_price", getattr(score, "actual_price", None))
            detail.setdefault("price_target_invalid_reason", getattr(score, "price_target_invalid_reason", None))
            # v2 conviction engine fields from DB columns
            detail.setdefault("opportunity_type", getattr(score, "opportunity_type", None))
            detail.setdefault("winning_track", getattr(score, "winning_track", None))
            detail.setdefault("asymmetry_ratio", getattr(score, "asymmetry_ratio", None))
            detail.setdefault("max_position_pct", getattr(score, "max_position_pct", None))
            detail.setdefault("timing_signal", getattr(score, "timing_signal", None))
            # Override actual_price with live price if available
            if live_price_data:
                detail["actual_price"] = live_price_data["price"]
            # Add freshness fields
            detail["data_freshness"] = freshness
            detail["price_source"] = price_source
            detail["price_updated_at"] = price_updated_at
            return ScoreResponse(**detail)
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to parse score_detail for %s, falling back to summary columns",
                ticker,
                exc_info=True,
            )
            # Fall through to summary-column path below

    # Fallback: build from summary columns (no sub-score detail)
    actual_price = getattr(score, "actual_price", None)
    if live_price_data:
        actual_price = live_price_data["price"]

    invalid_reason = getattr(score, "price_target_invalid_reason", None)
    return ScoreResponse(
        ticker=ticker,
        name=row.asset_name if hasattr(row, "asset_name") else "",
        score=score.composite_raw_score,
        universe_percentile=score.composite_percentile,
        composite_percentile=score.composite_percentile,
        conviction_level=score.conviction_level,
        signal=score.signal,
        quality=FactorBreakdownResponse(
            factor_name="quality",
            weight=0.35,
            sub_scores=[],
            average_percentile=score.quality_percentile,
        ),
        value=FactorBreakdownResponse(
            factor_name="value",
            weight=0.30,
            sub_scores=[],
            average_percentile=score.value_percentile,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[],
            average_percentile=score.momentum_percentile,
        ),
        filters_passed=[],
        data_coverage=score.data_coverage,
        growth_stage=score.growth_stage,
        scored_at=scored_at.isoformat() if scored_at else None,
        intrinsic_value=getattr(score, "intrinsic_value", None),
        buy_price=getattr(score, "buy_price", None),
        sell_price=getattr(score, "sell_price", None),
        actual_price=actual_price,
        price_upside=(
            round((score.intrinsic_value - score.actual_price) / score.actual_price, 4)
            if getattr(score, "intrinsic_value", None)
            and getattr(score, "actual_price", None)
            and not invalid_reason
            else None
        ),
        margin_of_safety=(
            round((score.intrinsic_value - actual_price) / score.intrinsic_value, 4)
            if getattr(score, "intrinsic_value", None)
            and actual_price is not None
            and actual_price < score.intrinsic_value
            and not invalid_reason
            else None
        ),
        price_target_invalid_reason=invalid_reason,
        opportunity_type=getattr(score, "opportunity_type", None),
        winning_track=getattr(score, "winning_track", None),
        asymmetry_ratio=getattr(score, "asymmetry_ratio", None),
        max_position_pct=getattr(score, "max_position_pct", None),
        timing_signal=getattr(score, "timing_signal", None),
        data_freshness=freshness,
        price_source=price_source,
        price_updated_at=price_updated_at,
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


@router.get("", response_model=ScoreListResponse)
async def list_scores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    min_percentile: float = Query(0.0, ge=0.0, le=100.0),
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ScoreListResponse:
    """List all scored assets with optional filtering and pagination."""
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

    if min_percentile > 0:
        base = base.where(Score.composite_percentile >= min_percentile)
    if conviction:
        base = base.where(Score.conviction_level == conviction.lower())

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    base = base.order_by(Score.composite_percentile.desc())
    base = base.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base)
    rows = result.all()

    return ScoreListResponse(
        scores=[_score_response_from_row(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticker}/history", response_model=ScoreHistoryResponse)
async def get_score_history(
    ticker: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ScoreHistoryResponse:
    """Get score history for a ticker across all scoring runs."""
    ticker = ticker.upper()
    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset_row = asset_result.scalar_one_or_none()
    if asset_row is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    # Get total count of scoring runs
    count_q = select(func.count()).where(Score.asset_id == asset_row.id)
    total = (await db.execute(count_q)).scalar() or 0

    query = (
        select(Score)
        .where(Score.asset_id == asset_row.id)
        .order_by(Score.scored_at.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    points: list[ScoreHistoryPoint] = []
    for i, row in enumerate(rows):
        delta = None
        if i > 0:
            delta = round(row.composite_percentile - rows[i - 1].composite_percentile, 2)

        # Ensure scored_at is tz-aware (SQLite returns naive datetimes)
        scored_at = row.scored_at
        if scored_at is not None and scored_at.tzinfo is None:
            scored_at = scored_at.replace(tzinfo=UTC)

        points.append(ScoreHistoryPoint(
            scored_at=scored_at,
            composite_percentile=row.composite_percentile,
            composite_raw_score=row.composite_raw_score,
            quality_percentile=row.quality_percentile,
            value_percentile=row.value_percentile,
            momentum_percentile=row.momentum_percentile,
            conviction_level=row.conviction_level,
            signal=row.signal,
            margin_invest_value=float(row.intrinsic_value) if row.intrinsic_value is not None else None,
            buy_price=float(row.buy_price) if row.buy_price is not None else None,
            sell_price=float(row.sell_price) if row.sell_price is not None else None,
            actual_price=float(row.actual_price) if row.actual_price is not None else None,
            delta=delta,
        ))

    return ScoreHistoryResponse(ticker=ticker, points=points, total_runs=total)


async def _try_get_live_price(ticker: str) -> dict | None:
    """Try to fetch a live price from Redis. Returns None if unavailable."""
    try:
        import redis.asyncio as aioredis

        from margin_api.services.live_prices import LivePriceService

        client = aioredis.Redis(host="localhost", port=6379, socket_connect_timeout=1)
        service = LivePriceService(client)
        try:
            return await service.get_price(ticker)
        finally:
            await client.aclose()
    except Exception:
        return None


@router.get("/{ticker}", response_model=ScoreResponse)
async def get_score(
    ticker: str,
    include: str | None = Query(None, description="Comma-separated: price_history,signal_history"),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """Get the latest scoring result for a specific ticker."""
    ticker = ticker.upper()
    query = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    # Try to get live price from Redis (graceful fallback)
    live_price_data = await _try_get_live_price(ticker)

    response = _score_response_from_row(row, live_price_data=live_price_data)

    includes = set((include or "").split(",")) if include else set()

    if "price_history" in includes:
        from margin_api.db.models import FinancialData
        from margin_api.schemas.scores import PriceBarResponse

        fd_query = (
            select(FinancialData.price_history)
            .where(FinancialData.asset_id == row[0].asset_id)
            .order_by(FinancialData.period_end.desc())
            .limit(1)
        )
        fd_result = await db.execute(fd_query)
        fd_row = fd_result.scalar()

        def _normalize_bar(bar: dict) -> dict:
            """Map yfinance capitalized keys to PriceBarResponse fields."""
            return {
                "date": bar.get("date") or bar.get("Date", ""),
                "open": bar.get("open") or bar.get("Open", 0),
                "high": bar.get("high") or bar.get("High", 0),
                "low": bar.get("low") or bar.get("Low", 0),
                "close": bar.get("close") or bar.get("Close", 0),
                "volume": int(bar.get("volume") or bar.get("Volume", 0)),
            }

        try:
            if fd_row and isinstance(fd_row, dict) and "bars" in fd_row:
                response.price_history = [
                    PriceBarResponse(**_normalize_bar(bar)) for bar in fd_row["bars"]
                ]
            elif fd_row and isinstance(fd_row, list):
                response.price_history = [
                    PriceBarResponse(**_normalize_bar(bar)) for bar in fd_row
                ]
            else:
                response.price_history = []
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to parse price_history for %s", ticker, exc_info=True
            )
            response.price_history = []

    if "signal_history" in includes:
        from margin_api.db.models import SignalTransition
        from margin_api.schemas.scores import SignalTransitionResponse

        st_query = (
            select(SignalTransition)
            .where(SignalTransition.asset_id == row[0].asset_id)
            .order_by(SignalTransition.transitioned_at.desc())
            .limit(50)
        )
        st_result = await db.execute(st_query)
        transitions = st_result.scalars().all()
        response.signal_history = [
            SignalTransitionResponse(
                previous_signal=t.previous_signal,
                new_signal=t.new_signal,
                previous_conviction=t.previous_conviction,
                new_conviction=t.new_conviction,
                actual_price_at_transition=t.actual_price_at_transition,
                intrinsic_value_at_transition=t.intrinsic_value_at_transition,
                composite_percentile=t.composite_percentile,
                transitioned_at=t.transitioned_at.isoformat(),
            )
            for t in transitions
        ]

    return response
