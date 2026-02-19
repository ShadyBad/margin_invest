"""Admin endpoints for pipeline management."""
from __future__ import annotations

import logging

from arq.connections import ArqRedis, create_pool
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from margin_api.config import get_settings

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

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job("full_ingest")
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue pipeline job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

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
