"""V3 Score API endpoints."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, V3Score
from margin_api.db.session import get_db

router = APIRouter(prefix="/api/v3/scores", tags=["v3-scores"])


class V3ScoreResponse(BaseModel):
    ticker: str
    name: str
    opportunity_type: str
    conviction: str
    track_a: dict | None = None
    track_b: dict | None = None
    timing_signal: str
    max_position_pct: float
    regime: str
    composite_score: float
    scored_at: str


class V3ScoreListResponse(BaseModel):
    scores: list[V3ScoreResponse]
    total: int


def _latest_v3_subquery():
    """Subquery for the most recent v3 score per asset."""
    return (
        select(
            V3Score.asset_id,
            func.max(V3Score.scored_at).label("max_scored_at"),
        )
        .group_by(V3Score.asset_id)
        .subquery()
    )


@router.get("", response_model=V3ScoreListResponse)
async def list_v3_scores(
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> V3ScoreListResponse:
    """List latest v3 scores, optionally filtered by conviction level."""
    latest = _latest_v3_subquery()

    base = (
        select(V3Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, V3Score.asset_id == Asset.id)
        .join(
            latest,
            (V3Score.asset_id == latest.c.asset_id)
            & (V3Score.scored_at == latest.c.max_scored_at),
        )
    )

    if conviction:
        base = base.where(V3Score.conviction == conviction.lower())

    base = base.order_by(V3Score.composite_score.desc())

    result = await db.execute(base)
    rows = result.all()

    scores = []
    for row in rows:
        v3score = row[0] if hasattr(row[0], "composite_score") else row.V3Score
        scored_at = v3score.scored_at
        if scored_at is not None and scored_at.tzinfo is None:
            scored_at = scored_at.replace(tzinfo=UTC)
        scores.append(V3ScoreResponse(
            ticker=row.ticker,
            name=row.asset_name,
            opportunity_type=v3score.opportunity_type,
            conviction=v3score.conviction,
            track_a=v3score.track_a,
            track_b=v3score.track_b,
            timing_signal=v3score.timing_signal,
            max_position_pct=v3score.max_position_pct,
            regime=v3score.regime,
            composite_score=v3score.composite_score,
            scored_at=scored_at.isoformat() if scored_at else "",
        ))

    return V3ScoreListResponse(scores=scores, total=len(scores))


@router.get("/{ticker}", response_model=V3ScoreResponse)
async def get_v3_score(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> V3ScoreResponse:
    """Get the latest v3 score for a specific ticker."""
    ticker = ticker.upper()
    query = (
        select(V3Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, V3Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(V3Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No v3 score found for {ticker}")

    v3score = row[0] if hasattr(row[0], "composite_score") else row.V3Score
    scored_at = v3score.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)

    return V3ScoreResponse(
        ticker=row.ticker,
        name=row.asset_name,
        opportunity_type=v3score.opportunity_type,
        conviction=v3score.conviction,
        track_a=v3score.track_a,
        track_b=v3score.track_b,
        timing_signal=v3score.timing_signal,
        max_position_pct=v3score.max_position_pct,
        regime=v3score.regime,
        composite_score=v3score.composite_score,
        scored_at=scored_at.isoformat() if scored_at else "",
    )
