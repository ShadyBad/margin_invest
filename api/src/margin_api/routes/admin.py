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
            "message": "Scoring enqueued: v2 score → v3 score → v4 score (skipping ingest)",
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


@router.get("/ml/v4score-diagnostic")
@limiter.limit("5/minute")
async def v4score_diagnostic(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Diagnostic: check V4Score detail health for ML training."""
    _verify_admin_key(x_admin_key)

    # Total V4Score rows
    total_result = await session.execute(select(func.count(V4Score.id)))
    total = total_result.scalar() or 0

    # Rows with non-null detail
    non_null_result = await session.execute(
        select(func.count(V4Score.id)).where(V4Score.detail.isnot(None))
    )
    non_null = non_null_result.scalar() or 0

    # Get latest scored_at
    latest_result = await session.execute(
        select(func.max(V4Score.scored_at))
    )
    latest_scored_at = latest_result.scalar()

    # Count latest batch (rows with max scored_at)
    latest_batch = 0
    latest_with_detail = 0
    sample_details = []
    if latest_scored_at:
        batch_result = await session.execute(
            select(func.count(V4Score.id)).where(V4Score.scored_at == latest_scored_at)
        )
        latest_batch = batch_result.scalar() or 0

        detail_result = await session.execute(
            select(func.count(V4Score.id)).where(
                V4Score.scored_at == latest_scored_at,
                V4Score.detail.isnot(None),
            )
        )
        latest_with_detail = detail_result.scalar() or 0

        # Sample 3 rows with detail to inspect structure
        sample_result = await session.execute(
            select(V4Score.detail, Asset.ticker)
            .join(Asset, V4Score.asset_id == Asset.id)
            .where(V4Score.scored_at == latest_scored_at, V4Score.detail.isnot(None))
            .limit(3)
        )
        for detail, ticker in sample_result.all():
            if detail:
                # Check which keys exist and sub_score null counts
                info = {"ticker": ticker, "keys": list(detail.keys())[:15]}
                for factor in ["quality", "value", "momentum"]:
                    f = detail.get(factor)
                    if f and isinstance(f, dict):
                        subs = f.get("sub_scores", [])
                        nulls = [
                            s.get("name")
                            for s in subs
                            if isinstance(s, dict)
                            and (s.get("raw_value") is None or s.get("percentile_rank") is None)
                        ]
                        info[factor] = {
                            "sub_score_count": len(subs),
                            "null_values": nulls,
                        }
                    else:
                        info[factor] = None
                sample_details.append(info)

    return {
        "total_v4_scores": total,
        "with_detail": non_null,
        "without_detail": total - non_null,
        "latest_scored_at": latest_scored_at.isoformat() if latest_scored_at else None,
        "latest_batch_count": latest_batch,
        "latest_batch_with_detail": latest_with_detail,
        "sample_details": sample_details,
    }
