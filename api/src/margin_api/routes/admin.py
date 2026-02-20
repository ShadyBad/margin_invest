"""Admin endpoints for pipeline management."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from arq.connections import ArqRedis, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _verify_admin_key(x_admin_key: str = Header()) -> None:
    """Verify the admin API key from the X-Admin-Key header."""
    settings = get_settings()
    if not settings.admin_key:
        raise HTTPException(503, "Admin key not configured")
    if x_admin_key != settings.admin_key:
        raise HTTPException(403, "Invalid admin key")


@router.post("/pipeline/trigger")
async def trigger_pipeline(x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue a full pipeline run (ingest → v2 score → v3 score).

    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    Returns 202 Accepted with the enqueued job info.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    job_id = f"full_ingest:{today}"

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job("full_ingest", _job_id=job_id)
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue pipeline job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    if job is None:
        logger.info("[admin] full_ingest already enqueued today: %s", job_id)
        return JSONResponse(
            status_code=200,
            content={
                "status": "already_enqueued",
                "job": "full_ingest",
                "job_id": job_id,
                "message": "Pipeline already enqueued for today",
            },
        )

    logger.info("[admin] Enqueued full_ingest pipeline job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "full_ingest",
            "job_id": job.job_id,
            "message": "Pipeline enqueued: ingest → v2 score → v3 score",
        },
    )


@router.post("/universe/activate")
async def activate_universe_endpoint(
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Activate the universe from the bundled engine/universe.yaml config.

    Deactivates any existing active snapshot and creates a new one.
    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    """
    _verify_admin_key(x_admin_key)

    from margin_api.services.universe import activate_universe

    # Look for universe.yaml relative to the repo/container root
    candidates = [
        Path("/app/engine/universe.yaml"),  # Docker container
        Path(__file__).resolve().parents[4] / "engine" / "universe.yaml",  # Local dev
    ]

    config_path = None
    for candidate in candidates:
        if candidate.exists():
            config_path = candidate
            break

    if config_path is None:
        raise HTTPException(
            500,
            "universe.yaml not found. Searched: " + ", ".join(str(c) for c in candidates),
        )

    try:
        snapshot = await activate_universe(session, config_path)
    except Exception as e:
        logger.exception("[admin] Failed to activate universe")
        raise HTTPException(500, f"Failed to activate universe: {e}") from e

    logger.info(
        "[admin] Activated universe v%s (%d tickers)",
        snapshot.version,
        snapshot.ticker_count,
    )

    return {
        "status": "activated",
        "version": snapshot.version,
        "ticker_count": snapshot.ticker_count,
        "config_hash": snapshot.config_hash,
    }
