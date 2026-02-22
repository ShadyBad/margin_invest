"""Health check endpoint."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api import __version__
from margin_api.config import get_settings
from margin_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)) -> dict:
    """Return service health status with DB and Redis connectivity checks."""
    checks: dict[str, str] = {"version": __version__}

    # Database check
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.warning("Health check: database unreachable")
        checks["database"] = "error"

    # Redis check
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        checks["redis"] = "ok"
        await r.aclose()
    except Exception:
        logger.warning("Health check: redis unreachable")
        checks["redis"] = "error"

    status = "ok" if checks.get("database") == "ok" and checks.get("redis") == "ok" else "degraded"
    checks["status"] = status
    return checks
