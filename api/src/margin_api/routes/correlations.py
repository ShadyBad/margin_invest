"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from margin_engine.models.financial import PriceBar

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

_SHOWCASE_TTL = 3600  # 1 hour

# Hardcoded fallback for showcase when cache is empty or < 5 tickers scored
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

_HIGH_CONVICTION_THRESHOLD = 71.0
_SHOWCASE_TICKER_COUNT = 5


async def _get_redis_cached() -> CorrelationResponse | None:
    """Try to read showcase correlation from Redis cache."""
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
        logger.debug("Redis unavailable for showcase correlations")
    return None


async def _cache_to_redis(response: CorrelationResponse) -> None:
    """Write showcase correlation result to Redis with TTL."""
    try:
        import redis.asyncio as aioredis

        from margin_api.config import get_settings

        client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        try:
            await client.set(
                "correlation:showcase",
                response.model_dump_json(),
                ex=_SHOWCASE_TTL,
            )
        finally:
            await client.aclose()
    except Exception:
        logger.debug("Failed to cache showcase correlations to Redis")


def _parse_bar(raw: dict) -> PriceBar | None:
    """Parse a price bar from yfinance-formatted JSONB."""
    from margin_engine.models.financial import PriceBar

    try:
        return PriceBar(
            date=raw.get("Date", raw.get("date", "")),
            open=raw.get("Open", raw.get("open", 0)),
            high=raw.get("High", raw.get("high", 0)),
            low=raw.get("Low", raw.get("low", 0)),
            close=raw.get("Close", raw.get("close", 0)),
            volume=int(raw.get("Volume", raw.get("volume", 0))),
            adj_close=raw.get("Adj Close", raw.get("adj_close")),
        )
    except Exception:
        return None


async def _compute_live_showcase(db: AsyncSession) -> CorrelationResponse | None:
    """Query DB for top conviction tickers and compute correlations.

    Returns None if fewer than 5 qualifying tickers have price data.
    """
    from margin_engine.correlation import compute_return_correlations

    # Get most recently scored tickers with composite_raw_score >= 72.0
    stmt = (
        select(Score, Asset.ticker)
        .join(Asset, Score.asset_id == Asset.id)
        .where(Score.composite_raw_score >= _HIGH_CONVICTION_THRESHOLD)
        .order_by(Score.scored_at.desc())
        .limit(_SHOWCASE_TICKER_COUNT)
    )
    rows = (await db.execute(stmt)).all()

    if len(rows) < _SHOWCASE_TICKER_COUNT:
        return None

    ticker_list = [r.ticker for r in rows]

    # Load price history for each ticker
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
                bars = [_parse_bar(bar) for bar in bars_raw]
                bars = [b for b in bars if b is not None]
                if bars:
                    price_data[ticker] = bars

    if len(price_data) < _SHOWCASE_TICKER_COUNT:
        return None

    result = compute_return_correlations(price_data, window_days=252)
    return CorrelationResponse(**result.model_dump())


@router.get("/showcase", response_model=CorrelationResponse)
async def get_showcase_correlations(
    db: AsyncSession = Depends(get_db),
) -> CorrelationResponse:
    """Public endpoint: correlation matrix for landing page.

    Checks Redis cache first. On miss, computes live from top-conviction
    tickers and caches for 1 hour. Falls back to static data if fewer
    than 5 qualifying tickers are available.
    """
    # 1. Try Redis cache
    cached = await _get_redis_cached()
    if cached:
        return cached

    # 2. Compute live from DB
    try:
        live = await _compute_live_showcase(db)
        if live:
            await _cache_to_redis(live)
            return live
    except Exception:
        logger.exception("Failed to compute live showcase correlations")

    # 3. Fall back to static data
    return _SHOWCASE_FALLBACK
