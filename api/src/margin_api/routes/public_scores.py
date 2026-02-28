"""Public (ungated) score endpoint — no auth required."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score, V4Score
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.scores import PublicScoreFactorSummary, PublicScoreResponse

router = APIRouter(prefix="/api/v1/public", tags=["public"])


def _extract_factor_percentiles_v4(detail: dict) -> PublicScoreFactorSummary:
    """Extract factor percentiles from V4Score detail JSONB."""
    quality = detail.get("quality", {})
    value = detail.get("value", {})
    momentum = detail.get("momentum", {})
    return PublicScoreFactorSummary(
        quality_percentile=quality.get("average_percentile", 0.0),
        value_percentile=value.get("average_percentile", 0.0),
        momentum_percentile=momentum.get("average_percentile", 0.0),
    )


def _check_eliminated(detail: dict) -> tuple[bool, str | None]:
    """Check if any filter failed. Returns (eliminated, reason)."""
    filters = detail.get("filters_passed", [])
    for f in filters:
        if not f.get("passed", True):
            return True, f.get("name")
    return False, None


@router.get("/score/{ticker}", response_model=PublicScoreResponse)
@limiter.limit("30/minute")
async def get_public_score(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return a lightweight score summary for any ticker. No auth required."""
    ticker = ticker.upper()

    # 1. Try published V4Score
    v4_published_q = (
        select(V4Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker, V4Score.published == True)  # noqa: E712
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(v4_published_q)
    row = result.first()

    # 2. Fallback: any V4Score
    if row is None:
        v4_any_q = (
            select(V4Score, Asset.ticker, Asset.name.label("asset_name"))
            .join(Asset, V4Score.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
            .order_by(V4Score.scored_at.desc())
            .limit(1)
        )
        result = await db.execute(v4_any_q)
        row = result.first()

    if row is not None:
        v4 = row[0]
        detail = v4.detail or {}
        scored_at = v4.scored_at
        if scored_at is not None and scored_at.tzinfo is None:
            scored_at = scored_at.replace(tzinfo=UTC)

        factor_summary = _extract_factor_percentiles_v4(detail)
        eliminated, elimination_reason = _check_eliminated(detail)
        signal = detail.get("signal", "neutral")

        data = PublicScoreResponse(
            ticker=row.ticker,
            company_name=row.asset_name or "",
            composite_score=v4.composite_score,
            composite_tier=v4.conviction,
            signal=signal,
            factor_summary=factor_summary,
            eliminated=eliminated,
            elimination_reason=elimination_reason,
            scored_at=scored_at.isoformat() if scored_at else "",
        )
        return JSONResponse(
            content=data.model_dump(),
            headers={"Cache-Control": "public, max-age=300"},
        )

    # 3. Fallback: base Score
    score_q = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(score_q)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    score = row[0]
    scored_at = score.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)

    detail = score.score_detail or {}
    eliminated, elimination_reason = _check_eliminated(detail)

    data = PublicScoreResponse(
        ticker=row.ticker,
        company_name=row.asset_name or "",
        composite_score=score.composite_percentile,
        composite_tier=score.conviction_level or "none",
        signal=score.signal or "neutral",
        factor_summary=PublicScoreFactorSummary(
            quality_percentile=score.quality_percentile or 0.0,
            value_percentile=score.value_percentile or 0.0,
            momentum_percentile=score.momentum_percentile or 0.0,
        ),
        eliminated=eliminated,
        elimination_reason=elimination_reason,
        scored_at=scored_at.isoformat() if scored_at else "",
    )
    return JSONResponse(
        content=data.model_dump(),
        headers={"Cache-Control": "public, max-age=300"},
    )
