"""Admin endpoints for pipeline management."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import redis.asyncio as aioredis
from arq.connections import ArqRedis, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from margin_engine.universe.config import load_universe_config
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import (
    Asset,
    JobRun,
    PipelineApproval,
    PITDailyPrice,
    PITFinancialSnapshot,
    PITUniverseMembership,
    UniverseSnapshot,
    V4Score,
)
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _verify_admin_key(x_admin_key: str = Header()) -> None:
    """Verify the admin API key from the X-Admin-Key header."""
    import hmac

    settings = get_settings()
    if not settings.admin_key:
        raise HTTPException(503, "Admin key not configured")
    if not hmac.compare_digest(x_admin_key or "", settings.admin_key):
        raise HTTPException(403, "Invalid admin key")


@router.post("/pipeline/trigger")
@limiter.limit("3/minute")
async def trigger_pipeline(request: Request, x_admin_key: str = Header()) -> JSONResponse:
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
        job = await redis.enqueue_job(
            "orchestrate_ingest",
            _job_id=f"orchestrate_ingest:{uuid.uuid4().hex[:8]}",
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue pipeline job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued orchestrate_ingest pipeline job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "orchestrate_ingest",
            "job_id": job.job_id,
            "message": "Pipeline enqueued: ingest → v2 score → v3 score → v4 score",
        },
    )


@router.post("/scoring/trigger")
@limiter.limit("3/minute")
async def trigger_scoring(request: Request, x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue the scoring pipeline.

    Skips ingestion — useful when data is already seeded but scoring
    hasn't run or failed. Requires X-Admin-Key header.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "full_score_v3",
            _job_id=f"full_score_v3:{uuid.uuid4().hex[:8]}",
        )
        job_name = "full_score_v3"
        message = "Scoring enqueued: v3 score → v4 score → stage"
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue scoring job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued %s job: %s", job_name, job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": job_name,
            "job_id": job.job_id,
            "message": message,
        },
    )


async def stage_universe_activation(session: AsyncSession, config_path: Path) -> dict:
    """Create a staging approval for universe activation instead of activating directly.

    Loads the proposed tickers from universe.yaml, diffs against the current active
    snapshot, and creates a PipelineApproval with gate_type="universe_activate".
    """
    config = load_universe_config(config_path)
    proposed_tickers = config.tickers

    # Get current active snapshot tickers
    result = await session.execute(
        select(UniverseSnapshot).where(UniverseSnapshot.is_active.is_(True))
    )
    current_snapshot = result.scalar_one_or_none()
    current_tickers: list[str] = current_snapshot.tickers if current_snapshot else []

    # Compute diff
    proposed_set = set(proposed_tickers)
    current_set = set(current_tickers)
    added_tickers = sorted(proposed_set - current_set)
    removed_tickers = sorted(current_set - proposed_set)

    approval = PipelineApproval(
        gate_type="universe_activate",
        status="staged",
        payload_ref={
            "config_path": str(config_path),
            "proposed_tickers": proposed_tickers,
        },
        impact_summary={
            "current_count": len(current_tickers),
            "proposed_count": len(proposed_tickers),
            "added_tickers": added_tickers,
            "removed_tickers": removed_tickers,
        },
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.commit()
    await session.refresh(approval)

    logger.info(
        "[admin] Staged universe activation: +%d/-%d tickers (approval_id=%d)",
        len(added_tickers),
        len(removed_tickers),
        approval.id,
    )

    return {
        "status": "staged",
        "approval_id": approval.id,
        "added_tickers": added_tickers,
        "removed_tickers": removed_tickers,
    }


@router.post("/universe/activate", status_code=202)
@limiter.limit("3/minute")
async def activate_universe_endpoint(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Stage a universe activation from the bundled engine/universe.yaml config.

    Creates a PipelineApproval record for review instead of activating immediately.
    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    Returns 202 Accepted with the staged approval details.
    """
    _verify_admin_key(x_admin_key)

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
        result = await stage_universe_activation(session, config_path)
    except Exception as e:
        logger.exception("[admin] Failed to stage universe activation")
        raise HTTPException(500, f"Failed to stage universe activation: {e}") from e

    return result


@router.get("/redis/health")
@limiter.limit("3/minute")
async def redis_health(request: Request, x_admin_key: str = Header()) -> dict:
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
        # Check ARQ in-progress jobs
        in_progress_keys = await client.keys("arq:in-progress:*")
        in_progress = [
            (k.decode() if isinstance(k, bytes) else k).removeprefix("arq:in-progress:")
            for k in in_progress_keys
        ]
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
        "in_progress": in_progress,
        "recent_results": result_keys[:20],
    }


@router.post("/redis/flush-jobs")
@limiter.limit("3/minute")
async def flush_redis_jobs(request: Request, x_admin_key: str = Header()) -> dict:
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

        # Remove stale result keys so health check shows clean state
        result_keys = [
            k.decode() if isinstance(k, bytes) else k for k in await client.keys("arq:result:*")
        ]
        for key in result_keys:
            await client.delete(key)

        await client.aclose()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {
        "status": "flushed",
        "removed_jobs": job_ids,
        "removed_in_progress": in_progress,
        "removed_results": result_keys,
    }


@router.post("/ml/train")
@limiter.limit("3/minute")
async def trigger_ml_training(request: Request, x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue ML model training (clustering + LightGBM).

    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job("train_ml_models", _job_id=f"train_ml:{uuid.uuid4().hex[:8]}")
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


@router.post("/pit/backfill")
@limiter.limit("1/hour")
async def trigger_pit_backfill(request: Request, x_admin_key: str = Header()) -> JSONResponse:
    """Enqueue the PIT data bootstrap pipeline (EDGAR → prices → universe → backtest).

    Runs the full backfill chain as a background worker job. Safe to call
    multiple times — the worker skips if PIT tables already have data.

    Requires the X-Admin-Key header matching the MARGIN_ADMIN_KEY env var.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "bootstrap_pit_data",
            _job_id=f"bootstrap_pit:{uuid.uuid4().hex[:8]}",
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue PIT backfill job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued bootstrap_pit_data job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "bootstrap_pit_data",
            "job_id": job.job_id,
            "message": (
                "PIT backfill enqueued: EDGAR filings → daily prices → "
                "universe assembly → default backtest precompute"
            ),
        },
    )


@router.get("/pit/stats")
@limiter.limit("3/minute")
async def pit_stats(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return row counts for PIT tables to verify backfill progress."""
    _verify_admin_key(x_admin_key)

    snapshots = (
        await session.execute(select(func.count()).select_from(PITFinancialSnapshot))
    ).scalar_one()
    prices = (await session.execute(select(func.count()).select_from(PITDailyPrice))).scalar_one()
    memberships = (
        await session.execute(select(func.count()).select_from(PITUniverseMembership))
    ).scalar_one()

    return {
        "pit_financial_snapshots": snapshots,
        "pit_daily_prices": prices,
        "pit_universe_memberships": memberships,
    }


@router.post("/pit/assemble-universe")
@limiter.limit("3/minute")
async def trigger_universe_assembly(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Run only Phase 3 (universe assembly) of the PIT backfill.

    Useful when EDGAR and price data are already populated but universe
    assembly failed or needs re-running. Runs synchronously (not via worker).
    """
    _verify_admin_key(x_admin_key)

    from margin_api.services.edgar.universe_assembly import (
        assemble_universe,
        fill_last_known_prices,
    )

    result = await assemble_universe(session)
    updated = await fill_last_known_prices(session)
    result["last_known_prices_filled"] = updated
    return result


@router.post("/pit/reparse")
@limiter.limit("1/hour")
async def trigger_pit_reparse(
    request: Request,
    x_admin_key: str = Header(),
) -> JSONResponse:
    """Enqueue re-parse of EDGAR filings with empty data.

    Finds pit_financial_snapshots where income_statement IS NULL, deletes
    those rows, and re-downloads + re-parses using the fixed file selector
    that prefers _htm.xml over linkbase XMLs.

    Runs as a background worker job (may take minutes for large datasets).
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "reparse_pit_filings",
            _job_id=f"reparse_pit:{uuid.uuid4().hex[:8]}",
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue reparse job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued reparse_pit_filings job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "reparse_pit_filings",
            "job_id": job.job_id,
            "message": "Re-parse enqueued: deletes empty rows, re-downloads with fixed selector",
        },
    )


@router.post("/historical/backfill")
@limiter.limit("1/hour")
async def trigger_historical_backfill(
    request: Request, x_admin_key: str = Header()
) -> JSONResponse:
    """Enqueue historical score backfill from PIT data for ML training.

    Generates composite scores for every quarter from 2009-Q1 to 2025-Q4.
    Idempotent: skips quarters that already have scores.
    Expected runtime: 30-60 minutes. Timeout: 2 hours.
    """
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "backfill_historical_scores",
            _job_id=f"hist_backfill:{uuid.uuid4().hex[:8]}",
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue historical backfill job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued backfill_historical_scores job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "backfill_historical_scores",
            "job_id": job.job_id,
            "message": (
                "Historical score backfill enqueued: 67 quarters × ~3000 tickers from PIT data"
            ),
        },
    )


@router.get("/historical/stats")
@limiter.limit("10/minute")
async def historical_stats(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return row counts and date range for historical_scores table."""
    _verify_admin_key(x_admin_key)

    from margin_api.db.models import HistoricalScore

    total = (await session.execute(select(func.count()).select_from(HistoricalScore))).scalar_one()
    distinct_dates = (
        await session.execute(select(func.count(func.distinct(HistoricalScore.score_date))))
    ).scalar_one()

    min_date = max_date = None
    if total > 0:
        min_date = (
            await session.execute(select(func.min(HistoricalScore.score_date)))
        ).scalar_one()
        max_date = (
            await session.execute(select(func.max(HistoricalScore.score_date)))
        ).scalar_one()

    return {
        "historical_scores": total,
        "quarters_scored": distinct_dates,
        "min_date": str(min_date) if min_date else None,
        "max_date": str(max_date) if max_date else None,
    }


@router.patch("/jobs/{job_id}/status")
@limiter.limit("10/minute")
async def update_job_status(
    job_id: int,
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Update the status of a job run (e.g. mark a zombie job as cancelled)."""
    _verify_admin_key(x_admin_key)

    body = await request.json()
    new_status = body.get("status")
    if new_status not in ("completed", "failed", "cancelled"):
        raise HTTPException(400, "status must be one of: completed, failed, cancelled")

    result = await session.execute(select(JobRun).where(JobRun.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    old_status = job.status
    job.status = new_status
    if new_status in ("failed", "cancelled") and not job.completed_at:
        job.completed_at = datetime.now(UTC)
    if error_message := body.get("error_message"):
        job.error_message = error_message
    await session.commit()

    logger.info("[admin] Updated job %d status: %s → %s", job_id, old_status, new_status)
    return {"job_id": job_id, "old_status": old_status, "new_status": new_status}


@router.post("/jobs/cancel-zombies")
@limiter.limit("3/minute")
async def cancel_zombie_jobs(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel ALL 'running' jobs of a given type that are older than 1 hour."""
    _verify_admin_key(x_admin_key)

    body = await request.json() if request.headers.get("content-type") else {}
    job_type = body.get("job_type", "train_ml_models")
    cutoff = datetime.now(UTC) - timedelta(hours=1)

    result = await session.execute(
        select(JobRun).where(
            JobRun.job_type == job_type,
            JobRun.status == "running",
            JobRun.started_at < cutoff,
        )
    )
    zombies = result.scalars().all()

    cancelled_ids = []
    for job in zombies:
        job.status = "cancelled"
        job.error_message = "Cancelled: zombie cleanup"
        if not job.completed_at:
            job.completed_at = datetime.now(UTC)
        cancelled_ids.append(job.id)

    if cancelled_ids:
        await session.commit()

    logger.info(
        "[admin] Cancelled %d zombie %s jobs: %s", len(cancelled_ids), job_type, cancelled_ids
    )
    return {"cancelled": len(cancelled_ids), "job_ids": cancelled_ids}


@router.post("/backtest/precompute")
@limiter.limit("3/minute")
async def trigger_precompute_backtest(
    request: Request, x_admin_key: str = Header()
) -> JSONResponse:
    """Enqueue just the precompute_default_backtest job (skips full bootstrap)."""
    _verify_admin_key(x_admin_key)

    settings = get_settings()
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)
        job = await redis.enqueue_job(
            "precompute_default_backtest",
            _job_id=f"precompute_backtest:{uuid.uuid4().hex[:8]}",
        )
        await redis.aclose()
    except Exception as e:
        logger.exception("Failed to enqueue precompute backtest job")
        raise HTTPException(503, f"Failed to connect to Redis: {e}") from e

    logger.info("[admin] Enqueued precompute_default_backtest job: %s", job.job_id)

    return JSONResponse(
        status_code=202,
        content={
            "status": "enqueued",
            "job": "precompute_default_backtest",
            "job_id": job.job_id,
        },
    )


@router.get("/pit/data-quality")
@limiter.limit("5/minute")
async def pit_data_quality(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Diagnostic: check PIT financial snapshot data quality."""
    _verify_admin_key(x_admin_key)

    total = (
        await session.execute(select(func.count()).select_from(PITFinancialSnapshot))
    ).scalar_one()

    null_bs = (
        await session.execute(
            select(func.count())
            .select_from(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.balance_sheet.is_(None))
        )
    ).scalar_one()

    null_is = (
        await session.execute(
            select(func.count())
            .select_from(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.income_statement.is_(None))
        )
    ).scalar_one()

    null_cf = (
        await session.execute(
            select(func.count())
            .select_from(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.cash_flow.is_(None))
        )
    ).scalar_one()

    null_shares = (
        await session.execute(
            select(func.count())
            .select_from(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.shares_outstanding.is_(None))
        )
    ).scalar_one()

    # Filing year distribution
    year_dist = (
        await session.execute(
            select(
                PITFinancialSnapshot.fiscal_year,
                func.count().label("cnt"),
            )
            .group_by(PITFinancialSnapshot.fiscal_year)
            .order_by(PITFinancialSnapshot.fiscal_year)
        )
    ).all()

    # Sample: 5 rows with NULL balance_sheet
    sample_null_bs = (
        await session.execute(
            select(
                PITFinancialSnapshot.ticker,
                PITFinancialSnapshot.fiscal_year,
                PITFinancialSnapshot.form_type,
                PITFinancialSnapshot.accession_number,
            )
            .where(PITFinancialSnapshot.balance_sheet.is_(None))
            .limit(5)
        )
    ).all()

    # Sample: 5 rows WITH balance_sheet — check if total_assets present
    sample_with_bs = (
        await session.execute(
            select(
                PITFinancialSnapshot.ticker,
                PITFinancialSnapshot.fiscal_year,
                PITFinancialSnapshot.balance_sheet,
            )
            .where(PITFinancialSnapshot.balance_sheet.isnot(None))
            .limit(5)
        )
    ).all()

    return {
        "total_snapshots": total,
        "null_income_statement": null_is,
        "null_balance_sheet": null_bs,
        "null_cash_flow": null_cf,
        "null_shares_outstanding": null_shares,
        "year_distribution": {str(r.fiscal_year): r.cnt for r in year_dist},
        "sample_null_bs": [
            {
                "ticker": r.ticker,
                "year": r.fiscal_year,
                "form": r.form_type,
                "accession": r.accession_number,
            }
            for r in sample_null_bs
        ],
        "sample_with_bs": [
            {
                "ticker": r.ticker,
                "year": r.fiscal_year,
                "bs_keys": list(r.balance_sheet.keys()) if r.balance_sheet else [],
            }
            for r in sample_with_bs
        ],
    }


@router.get("/ingestion/quarantined")
@limiter.limit("3/minute")
async def get_quarantined_assets(
    request: Request,
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


@router.get("/ml/training-dry-run")
@limiter.limit("3/minute")
async def ml_training_dry_run(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Simulate ML training data load — same query + parsing as train_ml_models.

    Returns counts and sample data without actually training any models.
    This verifies the V4Score fix works in the deployed environment.
    """
    _verify_admin_key(x_admin_key)

    from margin_engine.models.scoring import (
        CompositeScore,
        FactorBreakdown,
        FactorScore,
        FilterResult,
    )

    def _parse_fb(data: dict) -> FactorBreakdown | None:
        if not isinstance(data, dict):
            return None
        sub_scores_raw = data.get("sub_scores")
        if not sub_scores_raw or not isinstance(sub_scores_raw, list):
            return None
        if len(sub_scores_raw) == 0:
            return None
        sub_scores: list[FactorScore] = []
        for ss in sub_scores_raw:
            if not isinstance(ss, dict):
                return None
            name = ss.get("name")
            raw_value = ss.get("raw_value")
            percentile_rank = ss.get("percentile_rank")
            if name is None or raw_value is None or percentile_rank is None:
                return None
            try:
                sub_scores.append(
                    FactorScore(
                        name=str(name),
                        raw_value=float(raw_value),
                        percentile_rank=float(percentile_rank),
                        weight=float(ss["weight"]) if ss.get("weight") is not None else None,
                    )
                )
            except (ValueError, TypeError):
                return None
        try:
            return FactorBreakdown(
                factor_name=str(data.get("factor_name", "")),
                weight=float(data.get("weight", 1.0)),
                sub_scores=sub_scores,
            )
        except (ValueError, TypeError):
            return None

    try:
        # Exact same query as train_ml_models
        latest_subq = (
            select(
                V4Score.asset_id,
                func.max(V4Score.scored_at).label("max_scored_at"),
            )
            .group_by(V4Score.asset_id)
            .subquery()
        )
        result = await session.execute(
            select(V4Score, Asset.ticker)
            .join(Asset, V4Score.asset_id == Asset.id)
            .join(
                latest_subq,
                (V4Score.asset_id == latest_subq.c.asset_id)
                & (V4Score.scored_at == latest_subq.c.max_scored_at),
            )
        )
        rows = result.all()

        # Parse composites — same logic as _composite_from_score_detail
        valid = 0
        skipped_empty = 0
        skipped_missing_factor = 0
        skipped_parse_fail = 0
        skipped_construct_fail = 0
        first_failures: list[dict] = []

        for score, ticker in rows:
            detail = score.detail
            if not detail or not isinstance(detail, dict):
                skipped_empty += 1
                continue

            q_raw = detail.get("quality")
            v_raw = detail.get("value")
            m_raw = detail.get("momentum")

            if q_raw is None or v_raw is None or m_raw is None:
                skipped_missing_factor += 1
                if len(first_failures) < 3:
                    first_failures.append(
                        {
                            "ticker": ticker,
                            "reason": "missing_factor",
                            "has_quality": q_raw is not None,
                            "has_value": v_raw is not None,
                            "has_momentum": m_raw is not None,
                        }
                    )
                continue

            quality = _parse_fb(q_raw)
            value = _parse_fb(v_raw)
            momentum = _parse_fb(m_raw)

            if quality is None or value is None or momentum is None:
                skipped_parse_fail += 1
                if len(first_failures) < 3:
                    # Find which sub_score caused the failure
                    fail_info: dict = {"ticker": ticker, "reason": "parse_fail"}
                    for fname, fraw in [("quality", q_raw), ("value", v_raw), ("momentum", m_raw)]:
                        if _parse_fb(fraw) is None and isinstance(fraw, dict):
                            subs = fraw.get("sub_scores", [])
                            for s in subs:
                                if isinstance(s, dict):
                                    if s.get("raw_value") is None:
                                        fail_info[f"{fname}_null_raw"] = s.get("name")
                                    if s.get("percentile_rank") is None:
                                        fail_info[f"{fname}_null_pct"] = s.get("name")
                    first_failures.append(fail_info)
                continue

            # Try constructing CompositeScore
            try:
                filters_passed_raw = detail.get("filters_passed", [])
                filters_passed = []
                if isinstance(filters_passed_raw, list):
                    for f in filters_passed_raw:
                        if isinstance(f, dict) and "name" in f:
                            filters_passed.append(
                                FilterResult(
                                    name=str(f["name"]),
                                    passed=bool(f.get("passed", True)),
                                    value=f.get("value"),
                                    threshold=f.get("threshold"),
                                    detail=str(f.get("detail", "")),
                                )
                            )
                CompositeScore(
                    ticker=ticker,
                    composite_percentile=float(detail.get("composite_percentile", 0.0)),
                    composite_raw_score=float(detail.get("composite_raw_score", 0.0)),
                    quality=quality,
                    value=value,
                    momentum=momentum,
                    filters_passed=filters_passed,
                    data_coverage=float(detail.get("data_coverage", 1.0)),
                )
                valid += 1
            except Exception as e:
                skipped_construct_fail += 1
                if len(first_failures) < 3:
                    first_failures.append(
                        {
                            "ticker": ticker,
                            "reason": "construct_fail",
                            "error": str(e)[:200],
                        }
                    )

        return {
            "v4score_rows": len(rows),
            "valid_composites": valid,
            "skipped_empty_detail": skipped_empty,
            "skipped_missing_factor": skipped_missing_factor,
            "skipped_parse_fail": skipped_parse_fail,
            "skipped_construct_fail": skipped_construct_fail,
            "first_failures": first_failures,
            "verdict": "READY" if valid >= 100 else "NOT_READY",
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
