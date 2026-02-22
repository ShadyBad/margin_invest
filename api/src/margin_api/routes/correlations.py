"""Correlation matrix endpoints."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from margin_api.schemas.correlations import CorrelationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/correlations", tags=["correlations"])

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
