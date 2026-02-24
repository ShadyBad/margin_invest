"""Admin endpoints for pipeline management."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import redis.asyncio as aioredis
from arq.connections import ArqRedis, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import Asset
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

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        # Use unique _job_id to bypass ARQ deduplication
        job = await redis.enqueue_job("full_ingest", _job_id=f"full_ingest:{uuid.uuid4().hex[:8]}")
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


@router.post("/scoring/trigger")
async def trigger_scoring(x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue just the scoring pipeline (v2 score → v3 score).

    Skips ingestion — useful when data is already seeded but scoring
    hasn't run or failed. Requires X-Admin-Key header.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        # Use unique _job_id to bypass ARQ deduplication
        job = await redis.enqueue_job("full_score", _job_id=f"full_score:{uuid.uuid4().hex[:8]}")
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue scoring job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued full_score job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "full_score",
            "job_id": job.job_id,
            "message": "Scoring enqueued: v2 score → v3 score (skipping ingest)",
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


@router.get("/redis/health")
async def redis_health(x_admin_key: str = Header()) -> dict:
    """Check Redis connectivity and inspect ARQ queue state.

    Returns connection info, pending job count, and any queued job IDs
    so we can verify the API and worker share the same Redis instance.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    # Redact password from URL for display
    url = settings.redis_url
    redacted = url
    if "@" in url:
        # redis://:password@host:port -> redis://***@host:port
        pre, post = url.split("@", 1)
        scheme = pre.split("://")[0]
        redacted = f"{scheme}://***@{post}"

    try:
        client = aioredis.from_url(settings.redis_url)
        # Basic ping
        pong = await client.ping()
        # Check ARQ queue for pending jobs
        queued_jobs = await client.zrangebyscore("arq:queue", "-inf", "+inf")
        job_ids = [j.decode() if isinstance(j, bytes) else j for j in queued_jobs]
        # Check ARQ results for recent job results
        result_keys = [
            k.decode() if isinstance(k, bytes) else k for k in await client.keys("arq:result:*")
        ]
        await client.aclose()
    except Exception as e:
        return {
            "status": "error",
            "redis_url": redacted,
            "error": str(e),
        }

    return {
        "status": "connected" if pong else "no_pong",
        "redis_url": redacted,
        "queued_jobs": job_ids,
        "queued_count": len(job_ids),
        "recent_results": result_keys[:20],
    }


@router.post("/redis/flush-jobs")
async def flush_redis_jobs(x_admin_key: str = Header()) -> dict:
    """Remove all pending jobs from the ARQ queue and their associated keys.

    Use this to clear stale/stuck jobs before re-triggering the pipeline.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    try:
        client = aioredis.from_url(settings.redis_url)
        # Get all queued job IDs before clearing
        queued = await client.zrangebyscore("arq:queue", "-inf", "+inf")
        job_ids = [j.decode() if isinstance(j, bytes) else j for j in queued]

        # Remove the queue sorted set
        _removed = await client.delete("arq:queue")

        # Remove job data keys (arq:job:<id>) for each stale job
        for jid in job_ids:
            await client.delete(f"arq:job:{jid}")

        # Remove any in-progress markers
        in_progress = [
            k.decode() if isinstance(k, bytes) else k
            for k in await client.keys("arq:in-progress:*")
        ]
        for key in in_progress:
            await client.delete(key)

        await client.aclose()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {
        "status": "flushed",
        "removed_jobs": job_ids,
        "removed_in_progress": in_progress,
    }


@router.post("/ml/train")
async def trigger_ml_training(x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue ML model training (clustering + LightGBM).

    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "train_ml_models", _job_id=f"train_ml:{uuid.uuid4().hex[:8]}"
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue ML training job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued train_ml_models job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "train_ml_models",
            "job_id": job.job_id,
            "message": "ML training enqueued: clustering + LightGBM models",
        },
    )


@router.get("/ingestion/quarantined")
async def get_quarantined_assets(
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all quarantined and permanently skipped assets for triage."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(Asset)
        .where(Asset.ingestion_status.in_(["quarantined", "permanently_skipped"]))
        .order_by(Asset.ticker)
    )
    assets = result.scalars().all()

    return [
        {
            "ticker": a.ticker,
            "name": a.name,
            "ingestion_status": a.ingestion_status,
            "consecutive_failures": a.consecutive_failures,
            "last_failure_reason": a.last_failure_reason,
            "quarantined_at": a.quarantined_at.isoformat() if a.quarantined_at else None,
            "last_retry_at": a.last_retry_at.isoformat() if a.last_retry_at else None,
        }
        for a in assets
    ]
