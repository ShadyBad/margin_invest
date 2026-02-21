"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

# Hardcoded fallback for showcase when cache is empty
_SHOWCASE_FALLBACK = CorrelationResponse(
    tickers=["AAPL", "MSFT", "JNJ", "COST", "V"],
    method="returns",
    matrix=[
        [1.0, 0.82, 0.15, 0.28, 0.45],
        [0.82, 1.0, 0.12, 0.31, 0.51],
        [0.15, 0.12, 1.0, 0.62, 0.22],
        [0.28, 0.31, 0.62, 1.0, 0.35],
        [0.45, 0.51, 0.22, 0.35, 1.0],
    ],
    sample_sizes=[[252] * 5 for _ in range(5)],
    excluded=[],
    window_days=252,
    computed_at=datetime(2026, 1, 1, tzinfo=UTC),
)


@router.get("/showcase", response_model=CorrelationResponse)
async def get_showcase_correlations() -> CorrelationResponse:
    """Public endpoint: pre-computed correlation matrix for landing page."""
    try:
        import redis.asyncio as aioredis

        from margin_api.config import get_settings

        client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        try:
            cached = await client.get("correlation:showcase")
            if cached:
                data = json.loads(cached)
                return CorrelationResponse(**data)
        finally:
            await client.aclose()
    except Exception:
        logger.debug("Redis unavailable for showcase correlations, using fallback")
    return _SHOWCASE_FALLBACK


@router.get("", response_model=CorrelationResponse)
async def get_correlations(
    method: str = Query(..., pattern="^(returns|factors)$"),
    tickers: str | None = Query(None),
    window: int = Query(252, ge=30, le=504),
    db: AsyncSession = Depends(get_db),
) -> CorrelationResponse:
    """Compute correlation matrix for given tickers."""
    from margin_engine.correlation import (
        compute_factor_correlations,
        compute_return_correlations,
    )
    from margin_engine.models.financial import PriceBar
    from margin_engine.models.scoring import FactorBreakdown, FactorScore

    # Resolve ticker list
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")][:10]
    else:
        # Default: top picks (buy/strong_buy signals)
        stmt = (
            select(Score, Asset.ticker)
            .join(Asset, Score.asset_id == Asset.id)
            .where(Score.signal.in_(["buy", "strong_buy"]))
            .order_by(Score.composite_raw_score.desc())
            .limit(10)
        )
        rows = (await db.execute(stmt)).all()
        ticker_list = [r.ticker for r in rows]

    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers for correlation")

    if method == "returns":
        # Fetch price history for each ticker
        price_data: dict[str, list[PriceBar]] = {}
        for ticker in ticker_list:
            stmt = (
                select(FinancialData)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker == ticker)
                .order_by(FinancialData.period_end.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.price_history:
                price_hist = row.price_history
                bars_raw = price_hist.get("bars", []) if isinstance(price_hist, dict) else []
                if bars_raw:
                    bars = [PriceBar(**bar) for bar in bars_raw]
                    price_data[ticker] = bars

        if len(price_data) < 2:
            raise HTTPException(
                status_code=404,
                detail="No qualifying picks found. Score some tickers first.",
            )

        result = compute_return_correlations(price_data, window_days=window)

    else:  # factors
        # Fetch latest scores for each ticker
        factor_profiles: dict[str, dict[str, FactorBreakdown]] = {}
        for ticker in ticker_list:
            stmt = (
                select(Score)
                .join(Asset, Score.asset_id == Asset.id)
                .where(Asset.ticker == ticker)
                .order_by(Score.scored_at.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row and row.score_detail:
                detail = row.score_detail
                factors: dict[str, FactorBreakdown] = {}
                for factor_key in ("quality", "value", "momentum"):
                    factor_data = detail.get(factor_key)
                    if isinstance(factor_data, dict):
                        factors[factor_key] = _rebuild_factor(factor_data)
                if factors:
                    factor_profiles[ticker] = factors

        if len(factor_profiles) < 2:
            raise HTTPException(
                status_code=404,
                detail="No qualifying picks found. Score some tickers first.",
            )

        result = compute_factor_correlations(factor_profiles)

    return CorrelationResponse(**result.model_dump())


def _rebuild_factor(data: dict) -> FactorBreakdown:
    """Rebuild FactorBreakdown from JSONB dict."""
    from margin_engine.models.scoring import FactorBreakdown, FactorScore

    sub_scores = [FactorScore(**s) for s in data.get("sub_scores", [])]
    return FactorBreakdown(
        factor_name=data["factor_name"],
        weight=data["weight"],
        sub_scores=sub_scores,
    )
