"""Score endpoints for the Margin Invest API — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, MlModelRun, Score, V4Score
from margin_api.db.session import get_db
from margin_api.schemas.score_history import ScoreHistoryPoint, ScoreHistoryResponse
from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    ScoreListResponse,
    ScoreResponse,
)
from margin_api.schemas.valuation_audit import ValuationAuditResponse
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
            detail.setdefault("scored_at", scored_at.isoformat() if scored_at else None)
            for f in detail.get("filters_passed", []):
                f.setdefault("verdict", "pass" if f.get("passed") else "fail")
            for factor_key in (
                "quality",
                "value",
                "momentum",
                "capital_allocation",
                "catalyst",
            ):
                factor = detail.get(factor_key)
                if (
                    factor is not None
                    and isinstance(factor, dict)
                    and "average_percentile" not in factor
                ):
                    subs = factor.get("sub_scores", [])
                    avg = (
                        sum(s.get("percentile_rank", 0) for s in subs) / len(subs) if subs else 0.0
                    )
                    factor["average_percentile"] = avg
            # Populate score and universe_percentile from raw score / percentile
            detail.setdefault(
                "score",
                detail.get("composite_raw_score", score.composite_raw_score),
            )
            detail.setdefault(
                "universe_percentile",
                detail.get("composite_percentile", score.composite_percentile),
            )
            # Include price target fields from DB columns
            detail.setdefault("margin_invest_value", getattr(score, "margin_invest_value", None))
            detail.setdefault("buy_price", getattr(score, "buy_price", None))
            detail.setdefault("sell_price", getattr(score, "sell_price", None))
            detail.setdefault("actual_price", getattr(score, "actual_price", None))
            detail.setdefault(
                "price_target_invalid_reason",
                getattr(score, "price_target_invalid_reason", None),
            )
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
        margin_invest_value=getattr(score, "margin_invest_value", None),
        buy_price=getattr(score, "buy_price", None),
        sell_price=getattr(score, "sell_price", None),
        actual_price=actual_price,
        price_upside=(
            round((score.margin_invest_value - score.actual_price) / score.actual_price, 4)
            if getattr(score, "margin_invest_value", None)
            and getattr(score, "actual_price", None)
            and not invalid_reason
            else None
        ),
        margin_of_safety=(
            round((score.margin_invest_value - actual_price) / score.margin_invest_value, 4)
            if getattr(score, "margin_invest_value", None)
            and actual_price is not None
            and actual_price < score.margin_invest_value
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


def _v4_score_response_from_row(
    row,
    ml_model: MlModelRun | None = None,
    live_price_data: dict | None = None,
) -> ScoreResponse:
    """Build a ScoreResponse from a V4Score DB query row.

    Args:
        row: DB query row (V4Score, ticker, asset_name, asset_sector).
        ml_model: Optional latest MlModelRun for model metadata.
        live_price_data: Optional dict from LivePriceService.get_price().
    """
    v4 = row[0] if hasattr(row[0], "conviction") else row.V4Score
    ticker = row.ticker if hasattr(row, "ticker") else row[1]
    asset_name = row.asset_name if hasattr(row, "asset_name") else row[2]

    # Ensure scored_at is tz-aware (SQLite returns naive datetimes)
    scored_at: datetime | None = v4.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)
    freshness = compute_freshness(scored_at)

    if live_price_data:
        price_source = "live"
        price_updated_at = live_price_data.get("updated_at")
    else:
        price_source = "daily_close"
        price_updated_at = scored_at.isoformat() if scored_at else None

    detail = v4.detail or {}

    # Populate computed properties that @property methods would provide
    detail.setdefault("conviction_level", v4.conviction)
    detail.setdefault("signal", detail.get("signal", "no_action"))
    detail.setdefault("name", asset_name or "")
    detail.setdefault("ticker", ticker)
    detail.setdefault("scored_at", scored_at.isoformat() if scored_at else None)

    for f in detail.get("filters_passed", []):
        f.setdefault("verdict", "pass" if f.get("passed") else "fail")

    for factor_key in ("quality", "value", "momentum", "capital_allocation", "catalyst"):
        factor = detail.get(factor_key)
        if factor is not None and isinstance(factor, dict) and "average_percentile" not in factor:
            subs = factor.get("sub_scores", [])
            avg = sum(s.get("percentile_rank", 0) for s in subs) / len(subs) if subs else 0.0
            factor["average_percentile"] = avg

    detail.setdefault("score", detail.get("composite_raw_score", v4.composite_score))
    detail.setdefault("universe_percentile", detail.get("composite_percentile", 0.0))
    detail.setdefault("composite_percentile", v4.composite_score)
    detail.setdefault("data_coverage", detail.get("data_coverage", 1.0))

    # V4-specific fields
    detail["opportunity_type"] = v4.opportunity_type
    detail["timing_signal"] = v4.timing_signal
    detail["max_position_pct"] = v4.max_position_pct

    # ML fields
    detail["ml_alpha"] = v4.ml_alpha
    detail["ml_confidence"] = v4.ml_confidence
    detail["ml_override"] = v4.ml_override
    detail["rules_conviction"] = v4.rules_conviction
    detail["style"] = v4.style
    detail["regime"] = v4.regime
    detail["track_a"] = v4.track_a
    detail["track_b"] = v4.track_b
    detail["track_c"] = v4.track_c

    # ML model metadata
    if ml_model is not None:
        detail["ml_model_qualified"] = ml_model.model_qualifies
        detail["ml_model_rank_ic"] = ml_model.overall_rank_ic
        ml_trained_at = ml_model.created_at
        if ml_trained_at is not None and ml_trained_at.tzinfo is None:
            ml_trained_at = ml_trained_at.replace(tzinfo=UTC)
        detail["ml_model_trained_at"] = ml_trained_at.isoformat() if ml_trained_at else None

    # Override actual_price with live price if available
    if live_price_data:
        detail["actual_price"] = live_price_data["price"]

    # Freshness fields
    detail["data_freshness"] = freshness
    detail["price_source"] = price_source
    detail["price_updated_at"] = price_updated_at

    return ScoreResponse(**detail)


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
            (Score.asset_id == latest.c.asset_id) & (Score.scored_at == latest.c.max_scored_at),
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

        points.append(
            ScoreHistoryPoint(
                scored_at=scored_at,
                composite_percentile=row.composite_percentile,
                composite_raw_score=row.composite_raw_score,
                quality_percentile=row.quality_percentile,
                value_percentile=row.value_percentile,
                momentum_percentile=row.momentum_percentile,
                conviction_level=row.conviction_level,
                signal=row.signal,
                margin_invest_value=(
                    float(row.margin_invest_value) if row.margin_invest_value is not None else None
                ),
                buy_price=float(row.buy_price) if row.buy_price is not None else None,
                sell_price=float(row.sell_price) if row.sell_price is not None else None,
                actual_price=float(row.actual_price) if row.actual_price is not None else None,
                delta=delta,
            )
        )

    return ScoreHistoryResponse(ticker=ticker, points=points, total_runs=total)


@router.get("/{ticker}/valuation-audit", response_model=ValuationAuditResponse)
async def get_valuation_audit(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> ValuationAuditResponse:
    """Get the full valuation audit breakdown for a ticker."""
    ticker = ticker.upper()
    query = (
        select(Score)
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    score = result.scalar()
    if score is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    # Extract valuation_audit from score_detail JSONB
    detail = score.score_detail or {}
    audit_data = detail.get("valuation_audit")
    if audit_data is None:
        raise HTTPException(status_code=404, detail=f"No valuation audit available for {ticker}")

    return ValuationAuditResponse(**audit_data)


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

    # Try V4Score first (ML-enhanced scoring)
    v4_query = (
        select(
            V4Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
    v4_result = await db.execute(v4_query)
    v4_row = v4_result.first()

    # Try to get live price from Redis (graceful fallback)
    live_price_data = await _try_get_live_price(ticker)

    if v4_row is not None:
        # Fetch latest ML model run for metadata
        ml_model_query = select(MlModelRun).order_by(MlModelRun.created_at.desc()).limit(1)
        ml_result = await db.execute(ml_model_query)
        ml_model = ml_result.scalar_one_or_none()

        response = _v4_score_response_from_row(v4_row, ml_model=ml_model, live_price_data=live_price_data)
        # Use v4_row for asset_id reference in include queries below
        row = v4_row
    else:
        # Fallback to Score table (v2)
        query = (
            select(Score, Asset.ticker, Asset.name.label("asset_name"), Asset.sector.label("asset_sector"))
            .join(Asset, Score.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
            .order_by(Score.scored_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        row = result.first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

        response = _score_response_from_row(row, live_price_data=live_price_data)

    # Populate asset context: sector, universe stats, sector survivors
    sector = row.asset_sector if hasattr(row, "asset_sector") else None
    response.sector = sector

    # Universe size from active snapshot
    from margin_api.db.models import UniverseSnapshot

    snap_result = await db.execute(
        select(UniverseSnapshot.ticker_count)
        .where(UniverseSnapshot.is_active.is_(True))
        .limit(1)
    )
    universe_size = snap_result.scalar()
    response.universe_size = universe_size

    # Total scored (distinct assets with at least one score)
    total_result = await db.execute(select(func.count(func.distinct(Score.asset_id))))
    response.total_scored = total_result.scalar() or 0

    # Count filter survivors across all scored stocks, and sector-specific survivors
    latest = _latest_score_subquery()
    all_details_q = (
        select(
            Score.score_detail,
            Asset.sector.label("asset_sector_col"),
            Asset.ticker.label("asset_ticker_col"),
        )
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
    )
    all_details_result = await db.execute(all_details_q)
    all_detail_rows = all_details_result.all()

    filters_survived_count = 0
    sector_survivor_count = 0
    for detail_row in all_detail_rows:
        d = detail_row[0]  # score_detail
        row_sector = detail_row[1]
        row_ticker = detail_row[2]
        if d and isinstance(d, dict):
            filters = d.get("filters_passed", [])
            if filters and all(f.get("passed") for f in filters):
                filters_survived_count += 1
                if sector and row_sector == sector and row_ticker != ticker:
                    sector_survivor_count += 1

    response.filters_survived_count = filters_survived_count
    if sector:
        response.sector_survivor_count = sector_survivor_count

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
                response.price_history = [PriceBarResponse(**_normalize_bar(bar)) for bar in fd_row]
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
