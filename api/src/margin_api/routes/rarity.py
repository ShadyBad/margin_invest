"""Rarity engine API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, RarityScore
from margin_api.db.session import get_db
from margin_api.schemas.rarity import (
    RarityDimensionsResponse,
    RarityPickResponse,
    RarityPicksListResponse,
    RarityResponse,
)

router = APIRouter(prefix="/api/v1/rarity", tags=["rarity"])


# /picks MUST be registered before /{ticker} to avoid greedy matching
@router.get("/picks", response_model=RarityPicksListResponse)
async def get_rarity_picks(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get top rarity picks (the generational opportunity list)."""
    latest = await db.execute(
        select(RarityScore.scored_at).order_by(RarityScore.scored_at.desc()).limit(1)
    )
    latest_row = latest.scalar_one_or_none()
    if not latest_row:
        return RarityPicksListResponse(picks=[], regime="unknown", universe_size=0)

    scored_at = latest_row
    result = await db.execute(
        select(RarityScore, Asset)
        .join(Asset, RarityScore.asset_id == Asset.id)
        .where(RarityScore.scored_at == scored_at)
        .order_by(RarityScore.rarity_score.desc())
        .limit(limit)
    )
    rows = result.all()

    picks = []
    regime = "unknown"
    universe_size = 0
    for rs, asset in rows:
        regime = rs.regime
        universe_size = rs.universe_size
        picks.append(
            RarityPickResponse(
                ticker=asset.ticker,
                name=asset.name or "",
                sector=asset.sector,
                rarity_score=rs.rarity_score,
                combination_signature=rs.combination_signature,
                is_generational=rs.is_generational,
                composite_tier=rs.detail.get("composite_tier", "") if rs.detail else "",
                regime=rs.regime,
            )
        )

    return RarityPicksListResponse(
        picks=picks,
        regime=regime,
        universe_size=universe_size,
        scored_at=scored_at.isoformat(),
    )


@router.get("/{ticker}", response_model=RarityResponse)
async def get_rarity(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get full rarity breakdown for a specific ticker."""
    result = await db.execute(
        select(RarityScore, Asset)
        .join(Asset, RarityScore.asset_id == Asset.id)
        .where(Asset.ticker == ticker.upper())
        .order_by(RarityScore.scored_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No rarity data for {ticker}")

    rs, asset = row
    detail = rs.detail or {}
    pillar_pctls = detail.get("pillar_percentiles", {})
    dims = detail.get("dimensions", {})

    return RarityResponse(
        ticker=asset.ticker,
        rarity_score=rs.rarity_score,
        conviction_score=rs.conviction_score,
        is_generational=rs.is_generational,
        combination_signature=rs.combination_signature,
        regime=rs.regime,
        dimensions=RarityDimensionsResponse(
            joint_rarity_pctl=dims.get("joint_rarity_pctl", rs.joint_rarity_pctl),
            convergence_score=dims.get("convergence_score", rs.convergence_score),
            historical_frequency=dims.get("historical_frequency", rs.historical_frequency),
            quality_momentum=dims.get("quality_momentum", rs.quality_momentum),
            smart_money_score=dims.get("smart_money_score", rs.smart_money_score),
            regime_alignment=dims.get("regime_alignment", rs.regime_alignment),
        ),
        pillar_percentiles=pillar_pctls,
        universe_size=rs.universe_size,
        scored_at=rs.scored_at.isoformat() if rs.scored_at else None,
    )
