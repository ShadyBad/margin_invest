"""Score endpoints for the Margin Invest API — DB-backed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    ScoreListResponse,
    ScoreResponse,
)

router = APIRouter(prefix="/api/v1/scores", tags=["scores"])


def _score_response_from_row(row) -> ScoreResponse:
    """Build a ScoreResponse from a DB query row.

    If score_detail JSONB is present, use it for full factor breakdowns.
    Otherwise, build a minimal response from summary columns.
    """
    # row is a Row tuple: (Score, ticker, asset_name)
    score = row[0] if hasattr(row[0], "composite_percentile") else row.Score
    ticker = row.ticker if hasattr(row, "ticker") else row[1]

    detail = score.score_detail
    if detail:
        return ScoreResponse(**detail)

    # Fallback: build from summary columns (no sub-score detail)
    return ScoreResponse(
        ticker=ticker,
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


@router.get("/{ticker}", response_model=ScoreResponse)
async def get_score(
    ticker: str,
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

    return _score_response_from_row(row)
