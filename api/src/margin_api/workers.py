"""ARQ worker configuration and job definitions.

Runs the daily pipeline: ingest → v2 scoring → v3 scoring.
Also handles live price polling and quarantined ticker retries.

Start the worker with:
    arq margin_api.workers.WorkerSettings
"""

from __future__ import annotations

import logging
import math
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import redis.asyncio as aioredis
import yfinance as yf
from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import (
    Asset,
    Event,
    FilingMetadata,
    FinancialData,
    IngestionRun,
    IngestionTickerStatus,
    JobRun,
    MlModelRun,
    PipelineApproval,
    Score,
    UniverseSnapshot,
    V3Score,
    V4Score,
)
from margin_api.db.session import get_engine, get_session_factory, reset_engine_cache
from margin_api.routes.events import add_event, add_notification
from margin_api.services.live_prices import LivePriceService
from margin_api.services.universe import get_active_snapshot
from margin_api.ws.scores import ScoreChangeMessage, manager

if TYPE_CHECKING:
    from margin_engine.models.scoring import CompositeScore, FactorBreakdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alerting helpers
# ---------------------------------------------------------------------------


def _log_run_alerts(
    total: int,
    succeeded: int,
    failed: int,
    partial: int,
    cb_trips: int,
) -> None:
    """Log alerts based on run outcome thresholds."""
    if total == 0:
        return
    fail_rate = failed / total
    partial_rate = partial / total

    if fail_rate > 0.20:
        logger.error(
            "[ingest] ALERT: %.0f%% of tickers failed (%d/%d)",
            fail_rate * 100,
            failed,
            total,
        )
    if partial_rate > 0.10:
        logger.warning(
            "[ingest] ALERT: %.0f%% of tickers had partial data (%d/%d)",
            partial_rate * 100,
            partial,
            total,
        )
    if cb_trips > 0:
        logger.warning(
            "[ingest] ALERT: Circuit breaker tripped %d time(s) during run",
            cb_trips,
        )


# ---------------------------------------------------------------------------
# Pipeline jobs
# ---------------------------------------------------------------------------


async def orchestrate_ingest(ctx: dict) -> dict:
    """Orchestrate batched ingestion of the full universe.

    Loads the active universe snapshot, chunks tickers into batches,
    sets Redis coordination keys, and enqueues ingest_batch jobs.
    """
    from margin_api.cli import _load_foreign_skips

    pipeline_id = uuid.uuid4().hex[:16]
    logger.info("[orchestrate] Starting batched ingest (pipeline=%s)", pipeline_id)

    settings = get_settings()
    batch_size = settings.ingest_batch_size

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Load active universe
    async with session_factory() as session:
        snapshot = await get_active_snapshot(session)
        if snapshot is None:
            logger.error("[orchestrate] No active universe snapshot")
            return {"status": "error", "message": "No active universe snapshot"}

    tickers = list(snapshot.tickers)
    logger.info("[orchestrate] Universe v%s: %d tickers", snapshot.version, len(tickers))

    # Filter out known foreign tickers
    foreign_skips = _load_foreign_skips()
    if foreign_skips:
        before = len(tickers)
        tickers = [t for t in tickers if t not in foreign_skips]
        skipped = before - len(tickers)
        if skipped:
            logger.info("[orchestrate] Skipped %d known foreign tickers", skipped)

    # Create IngestionRun record
    async with session_factory() as session:
        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=len(tickers),
            status="running",
            started_at=datetime.now(UTC),
            pipeline_id=pipeline_id,
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    # Chunk tickers into batches
    batches = [tickers[i : i + batch_size] for i in range(0, len(tickers), batch_size)]
    total_batches = len(batches)

    logger.info(
        "[orchestrate] Dispatching %d batches of ~%d tickers (pipeline=%s)",
        total_batches,
        batch_size,
        pipeline_id,
    )

    # Set Redis coordination keys
    redis: ArqRedis | None = ctx.get("redis")
    if not redis:
        logger.error("[orchestrate] No redis in worker context")
        return {"status": "error", "message": "No redis in worker context"}

    coord_prefix = f"ingest:{run_id}"
    await redis.set(f"{coord_prefix}:total", total_batches, ex=86400)
    await redis.set(f"{coord_prefix}:completed", 0, ex=86400)

    # Enqueue batch jobs
    for batch_num, batch_tickers in enumerate(batches, start=1):
        await redis.enqueue_job(
            "ingest_batch",
            str(run_id),
            pipeline_id,
            batch_tickers,
            batch_num,
            _job_id=f"ingest-batch-{run_id}-{batch_num}",
        )

    logger.info("[orchestrate] All %d batches enqueued (pipeline=%s)", total_batches, pipeline_id)

    return {
        "status": "dispatched",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "total_batches": total_batches,
        "total_tickers": len(tickers),
    }


async def ingest_batch(
    ctx: dict,
    run_id: str,
    pipeline_id: str,
    tickers: list[str],
    batch_num: int,
    is_sweep: bool = False,
) -> dict:
    """Process a batch of tickers for ingestion.

    Seeds each ticker via yfinance (rate-limited by Redis), records per-ticker
    status to the DB, and increments the Redis batch-completion counter.
    When this is the last batch to complete, enqueues ingest_sweep.
    When is_sweep=True (cleanup batch), enqueues ingest_sweep_complete instead.
    """
    from margin_engine.ingestion.circuit_breaker import CircuitBreaker
    from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

    from margin_api.cli import seed_ticker_data
    from margin_api.services.ingestion import should_ingest_ticker
    from margin_api.services.redis_rate_limiter import RedisRateLimiter

    label = f"[ingest:{run_id}:batch-{batch_num}]"
    logger.info("%s Starting — %d tickers (sweep=%s)", label, len(tickers), is_sweep)

    settings = get_settings()
    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Build rate limiter from Redis
    raw_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    limiter = RedisRateLimiter(raw_redis, max_per_minute=settings.ingest_rate_limit)

    # Don't pass limiter to provider — we rate-limit at the batch level
    provider = YFinanceProvider(rate_limiter=None)

    # Optional FMP fallback
    fmp_provider = None
    fmp_key = os.environ.get("FMP_API_KEY")
    if fmp_key:
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        fmp_provider = FMPProvider(api_key=fmp_key)

    yf_breaker = CircuitBreaker(failure_threshold=10, cooldown_seconds=900.0)
    fmp_breaker = (
        CircuitBreaker(failure_threshold=10, cooldown_seconds=900.0) if fmp_provider else None
    )

    successes = 0
    failures = 0
    partial_count = 0
    failed_tickers: list[str] = []
    total = len(tickers)
    int_run_id = int(run_id)
    coord_prefix = f"ingest:{run_id}"
    redis: ArqRedis | None = ctx.get("redis")

    for i, ticker in enumerate(tickers, start=1):
        logger.info("%s [%d/%d] Seeding %s", label, i, total, ticker)

        # Check if ticker should be ingested
        async with session_factory() as session:
            asset_check = await session.execute(select(Asset).where(Asset.ticker == ticker))
            existing_asset = asset_check.scalar_one_or_none()
            if existing_asset and not should_ingest_ticker(
                existing_asset.ingestion_status,
                existing_asset.consecutive_failures,
                existing_asset.last_retry_at,
            ):
                logger.info(
                    "%s %s SKIPPED (status=%s)", label, ticker, existing_asset.ingestion_status
                )
                continue

        # Resume check: skip if already seeded today
        async with session_factory() as session:
            today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
            resume_check = await session.execute(
                select(FinancialData)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker == ticker, FinancialData.period_end == today_iso)
                .limit(1)
            )
            if resume_check.scalar_one_or_none() is not None:
                logger.info("%s %s SKIPPED (already seeded today)", label, ticker)
                continue

        # Circuit breaker gate
        if not yf_breaker.allow_request():
            logger.warning("%s %s SKIPPED (circuit breaker open)", label, ticker)
            failures += 1
            failed_tickers.append(ticker)
            continue

        # Rate limit at batch level (shared Redis limiter)
        await limiter.wait_and_acquire()

        tick_started = datetime.now(UTC)
        async with session_factory() as session:
            result = await seed_ticker_data(
                ticker=ticker,
                provider=provider,
                session=session,
                fallback_provider=(
                    fmp_provider if (fmp_breaker is None or fmp_breaker.allow_request()) else None
                ),
            )
        tick_ended = datetime.now(UTC)
        duration_ms = int((tick_ended - tick_started).total_seconds() * 1000)

        # Update circuit breaker
        if result.status == "failed":
            yf_breaker.record_failure()
        else:
            yf_breaker.record_success()

        # Record per-ticker audit trail
        if result.status in ("ok", "partial"):
            audit_status = "succeeded"
        else:
            audit_status = result.status
        async with session_factory() as session:
            ticker_status = IngestionTickerStatus(
                run_id=int_run_id,
                ticker=ticker,
                status=audit_status,
                error_message=result.error_message if result.status == "failed" else None,
                data_fetched=result.data_categories_present if result.is_success else None,
                duration_ms=duration_ms,
                started_at=tick_started,
                completed_at=tick_ended,
            )
            session.add(ticker_status)
            await session.commit()

        if result.status == "ok":
            successes += 1
        elif result.status == "partial":
            successes += 1
            partial_count += 1
        elif result.status == "failed":
            failures += 1
            failed_tickers.append(ticker)
            logger.warning("%s %s FAILED: %s", label, ticker, result.error_message)

    # Push failed tickers to Redis list for sweep
    if failed_tickers and redis:
        await redis.rpush(f"{coord_prefix}:failed_tickers", *failed_tickers)

    # Update IngestionRun stats atomically
    async with session_factory() as session:
        ing_result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == int_run_id)
        )
        run = ing_result.scalar_one()
        run.tickers_succeeded = (run.tickers_succeeded or 0) + successes
        run.tickers_failed = (run.tickers_failed or 0) + failures
        run.tickers_partial = (run.tickers_partial or 0) + partial_count
        await session.commit()

    logger.info(
        "%s Complete: %d succeeded (%d partial), %d failed",
        label,
        successes,
        partial_count,
        failures,
    )

    # Completion coordination
    is_last_batch = False
    if redis:
        if is_sweep:
            # Sweep batch always goes to sweep_complete
            is_last_batch = True
            logger.info(
                "%s Sweep batch complete — enqueuing sweep_complete (pipeline=%s)",
                label,
                pipeline_id,
            )
            await redis.enqueue_job("ingest_sweep_complete", run_id, pipeline_id)
        else:
            completed = await redis.incr(f"{coord_prefix}:completed")
            total_batches = int(await redis.get(f"{coord_prefix}:total") or 0)
            if completed >= total_batches:
                is_last_batch = True
                logger.info(
                    "%s Last batch complete — enqueuing sweep (pipeline=%s)",
                    label,
                    pipeline_id,
                )
                await redis.enqueue_job("ingest_sweep", run_id, pipeline_id)

    # Cleanup Redis connection
    await raw_redis.aclose()

    return {
        "status": "completed",
        "batch_num": batch_num,
        "succeeded": successes,
        "partial": partial_count,
        "failed": failures,
        "is_last_batch": is_last_batch,
    }


async def ingest_sweep(ctx: dict, run_id: str, pipeline_id: str) -> dict:
    """Find tickers that were not successfully ingested and enqueue a cleanup batch.

    If all tickers succeeded, goes straight to ingest_sweep_complete.
    The sweep runs once — any tickers that fail the sweep are left for
    the weekly retry_quarantined cron.
    """
    label = f"[sweep:{run_id}]"
    logger.info("%s Starting sweep (pipeline=%s)", label, pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        run_result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == int(run_id))
        )
        run = run_result.scalar_one()

        snap_result = await session.execute(
            select(UniverseSnapshot).where(UniverseSnapshot.id == run.snapshot_id)
        )
        snapshot = snap_result.scalar_one()
        universe_tickers = set(snapshot.tickers)

        succeeded_result = await session.execute(
            select(IngestionTickerStatus.ticker).where(
                IngestionTickerStatus.run_id == int(run_id),
                IngestionTickerStatus.status == "succeeded",
            )
        )
        succeeded_tickers = {row[0] for row in succeeded_result.all()}

    missing_tickers = sorted(universe_tickers - succeeded_tickers)
    logger.info(
        "%s %d missing tickers out of %d", label, len(missing_tickers), len(universe_tickers)
    )

    redis: ArqRedis | None = ctx.get("redis")
    if not redis:
        return {"status": "error", "message": "No redis"}

    if missing_tickers:
        await redis.enqueue_job(
            "ingest_batch",
            run_id,
            pipeline_id,
            missing_tickers,
            0,  # batch_num=0 for sweep
            True,  # is_sweep=True
            _job_id=f"ingest-sweep-batch-{run_id}",
        )
        logger.info("%s Enqueued sweep batch with %d tickers", label, len(missing_tickers))
    else:
        await redis.enqueue_job("ingest_sweep_complete", run_id, pipeline_id)
        logger.info("%s No missing tickers — enqueuing sweep_complete", label)

    return {
        "status": "sweep_dispatched" if missing_tickers else "all_complete",
        "missing_count": len(missing_tickers),
    }


async def ingest_sweep_complete(ctx: dict, run_id: str, pipeline_id: str) -> dict:
    """Finalize the ingestion run and chain to scoring.

    Updates the IngestionRun record with final stats, then enqueues full_score.
    """
    label = f"[sweep_complete:{run_id}]"
    logger.info("%s Finalizing ingestion run (pipeline=%s)", label, pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    completed_at = datetime.now(UTC)
    async with session_factory() as session:
        run_result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == int(run_id))
        )
        run = run_result.scalar_one()
        run.status = (
            "failed" if (run.tickers_failed or 0) > run.tickers_requested * 0.5 else "completed"
        )
        run.completed_at = completed_at
        run.duration_seconds = (completed_at - run.started_at).total_seconds()
        await session.commit()

    logger.info(
        "%s Ingestion complete: %d succeeded, %d failed (%.0fs)",
        label,
        run.tickers_succeeded or 0,
        run.tickers_failed or 0,
        run.duration_seconds or 0,
    )

    # Run post-ingestion consistency validation (non-blocking)
    try:
        from margin_api.services.consistency import validate_universe_consistency

        async with session_factory() as session:
            # Get successfully ingested tickers for this run
            succeeded_result = await session.execute(
                select(IngestionTickerStatus.ticker).where(
                    IngestionTickerStatus.run_id == int(run_id),
                    IngestionTickerStatus.status == "succeeded",
                )
            )
            ingested_tickers = [row[0] for row in succeeded_result.all()]

            if ingested_tickers:
                logger.info(
                    "%s Running consistency validation on %d tickers",
                    label,
                    len(ingested_tickers),
                )
                await validate_universe_consistency(session, tickers=ingested_tickers)
                await session.commit()
                logger.info("%s Consistency validation complete", label)
            else:
                logger.info("%s No succeeded tickers — skipping consistency validation", label)
    except Exception:
        logger.exception("%s Consistency validation failed (non-blocking)", label)

    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        await redis.enqueue_job("full_score", pipeline_id)
        logger.info("%s Enqueued full_score (pipeline=%s)", label, pipeline_id)

    return {
        "status": "completed",
        "pipeline_id": pipeline_id,
        "succeeded": run.tickers_succeeded or 0,
        "failed": run.tickers_failed or 0,
        "duration_seconds": run.duration_seconds,
    }


async def full_score(
    ctx: dict,
    pipeline_id: str | None = None,
) -> dict:
    """Score all ingested assets using the v2 two-pass pipeline.

    Reuses run_scoring() from cli.py. Always chains to full_score_v3,
    even on failure, so the v3 pipeline can still run independently.
    """
    from margin_api.cli import run_scoring

    logger.info("[score_v2] Starting v2 scoring (pipeline=%s)...", pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="score_v2",
            status="running",
            triggered_by="chained",
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    status = "completed"
    error: str | None = None

    try:
        await run_scoring()
        reset_engine_cache()

        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[score_v2] Scoring complete")

    except Exception as e:
        logger.exception("[score_v2] Scoring failed: %s", e)
        status = "failed"
        error = str(e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()

    # Always chain to v3 scoring — v3 is independent and should run
    # regardless of v2 outcome
    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        await redis.enqueue_job("full_score_v3", pipeline_id, job_id)
        logger.info(
            "[score_v2] Enqueued full_score_v3 job (pipeline=%s, parent=%s)",
            pipeline_id,
            job_id,
        )
    else:
        logger.warning("[score_v2] No redis in worker context — cannot chain to full_score_v3")

    if error:
        return {"status": status, "pipeline_id": pipeline_id, "error": error}
    return {"status": status, "pipeline_id": pipeline_id}


async def full_score_v3(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
) -> dict:
    """Score all ingested assets using the v3 gate cascade pipeline.

    Reuses run_scoring_v3() from cli.py. Terminal job in the daily chain.
    """
    from margin_api.cli import run_scoring_v3

    logger.info(
        "[score_v3] Starting v3 scoring (pipeline=%s, parent=%s)...",
        pipeline_id,
        parent_job_id,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="score_v3",
            status="running",
            triggered_by="chained",
            parent_job_id=parent_job_id,
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    status = "completed"
    error: str | None = None

    try:
        await run_scoring_v3()
        reset_engine_cache()

        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[score_v3] V3 scoring complete")

    except Exception as e:
        logger.exception("[score_v3] V3 scoring failed: %s", e)
        status = "failed"
        error = str(e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()

    # Always chain to v4 scoring — v4 is independent and should run
    # regardless of v3 outcome
    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        await redis.enqueue_job(
            "full_score_v4",
            pipeline_id=pipeline_id,
            parent_job_id=job_id,
        )
        logger.info("[score_v3] Chained -> full_score_v4")
    else:
        logger.warning("[score_v3] No redis in worker context — cannot chain to full_score_v4")

    if error:
        return {"status": status, "pipeline_id": pipeline_id, "error": error}
    return {"status": status, "pipeline_id": pipeline_id}


async def full_score_v4(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
) -> dict:
    """Score all ingested assets using the v4 pipeline with ML override.

    Terminal job in the daily chain. Extends v3 with Track C, style, and ML.
    """
    from margin_api.cli import run_scoring_v4

    logger.info(
        "[score_v4] Starting v4 scoring (pipeline=%s, parent=%s)...",
        pipeline_id,
        parent_job_id,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="score_v4",
            status="running",
            triggered_by="chained",
            parent_job_id=parent_job_id,
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        await run_scoring_v4()
        reset_engine_cache()

        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[score_v4] V4 scoring complete")

    except Exception as e:
        logger.exception("[score_v4] V4 scoring failed: %s", e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "pipeline_id": pipeline_id, "error": str(e)}

    # Chain to stage_scores for governance approval before publishing
    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        scored_at_iso = datetime.now(UTC).isoformat()
        await redis.enqueue_job(
            "stage_scores",
            pipeline_id,
            job_id,
            scored_at_iso,
            _job_id=f"stage_scores:{uuid.uuid4().hex[:8]}",
        )
        logger.info("[score_v4] Chained -> stage_scores (pipeline=%s)", pipeline_id)
    else:
        logger.warning("[score_v4] No redis in worker context — cannot chain to stage_scores")

    return {"status": "completed", "pipeline_id": pipeline_id}


# ---------------------------------------------------------------------------
# Stage scores (governance gate before publishing)
# ---------------------------------------------------------------------------


async def _stage_scores_impl(
    session: AsyncSession,
    pipeline_id: str | None,
    scored_at: datetime,
) -> dict:
    """Create a PipelineApproval for unpublished V4Scores at the given scored_at.

    Compares each new score's conviction against the latest published score for
    the same asset to count conviction changes.

    Returns a dict with status, approval_id, and ticker_count.
    """
    # Find all unpublished V4Scores at this scored_at
    result = await session.execute(
        select(V4Score).where(
            V4Score.scored_at == scored_at,
            V4Score.published == False,  # noqa: E712
        )
    )
    new_scores = result.scalars().all()
    ticker_count = len(new_scores)

    # Count conviction changes vs latest published score per asset
    conviction_changes = 0
    for new_score in new_scores:
        prev_result = await session.execute(
            select(V4Score)
            .where(
                V4Score.asset_id == new_score.asset_id,
                V4Score.published == True,  # noqa: E712
            )
            .order_by(V4Score.scored_at.desc())
            .limit(1)
        )
        prev_score = prev_result.scalar_one_or_none()
        if prev_score and prev_score.conviction != new_score.conviction:
            conviction_changes += 1

    # Create the PipelineApproval
    approval = PipelineApproval(
        gate_type="score_publish",
        status="staged",
        pipeline_id=pipeline_id,
        payload_ref={
            "scored_at": scored_at.isoformat(),
            "ticker_count": ticker_count,
        },
        impact_summary={
            "ticker_count": ticker_count,
            "conviction_changes": conviction_changes,
        },
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.flush()

    approval_id = approval.id
    await session.commit()

    logger.info(
        "[stage_scores] Staged %d scores (conviction_changes=%d, approval=%d)",
        ticker_count,
        conviction_changes,
        approval_id,
    )

    return {
        "status": "staged",
        "approval_id": approval_id,
        "ticker_count": ticker_count,
    }


async def stage_scores(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
    scored_at_iso: str | None = None,
) -> dict:
    """Worker entry point: create a PipelineApproval for newly scored V4Scores.

    Chained from full_score_v4 after scoring completes.
    """
    logger.info(
        "[stage_scores] Starting (pipeline=%s, parent=%s, scored_at=%s)",
        pipeline_id,
        parent_job_id,
        scored_at_iso,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="stage_scores",
            status="running",
            triggered_by="chained",
            parent_job_id=parent_job_id,
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        scored_at = datetime.fromisoformat(scored_at_iso) if scored_at_iso else datetime.now(UTC)

        async with session_factory() as session:
            result = await _stage_scores_impl(session, pipeline_id, scored_at)

        # Mark job completed
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[stage_scores] Complete: %s", result)
        return result

    except Exception as e:
        logger.exception("[stage_scores] Failed: %s", e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "pipeline_id": pipeline_id, "error": str(e)}


# ---------------------------------------------------------------------------
# Publish scores (operator approval)
# ---------------------------------------------------------------------------


async def _publish_scores_impl(
    session: AsyncSession,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Flip V4Score.published=True for scores referenced by a PipelineApproval.

    Fetches the approval, validates it is in "staged" status, then bulk-updates
    all matching V4Score rows. Updates the approval to "approved" with decision
    metadata.

    Returns a dict with status, published_count, and approval_id.
    """
    # Fetch approval
    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if approval is None:
        return {"status": "error", "message": "not found"}

    if approval.status != "staged":
        return {"status": "error", "message": "not in staged status"}

    # Parse scored_at from payload_ref
    scored_at_str = approval.payload_ref["scored_at"]
    scored_at = datetime.fromisoformat(scored_at_str)

    # Bulk-update unpublished V4Scores at this scored_at
    update_result = await session.execute(
        update(V4Score)
        .where(
            V4Score.scored_at == scored_at,
            V4Score.published == False,  # noqa: E712
        )
        .values(published=True)
    )
    published_count = update_result.rowcount

    # Update approval status
    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decided_by = decided_by
    approval.decision_reason = decision_reason

    await session.commit()

    logger.info(
        "[publish_scores] Published %d scores (approval=%d, decided_by=%s)",
        published_count,
        approval_id,
        decided_by,
    )

    return {
        "status": "published",
        "published_count": published_count,
        "approval_id": approval_id,
    }


async def publish_scores(
    ctx: dict,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Worker entry point: publish staged V4Scores after operator approval.

    Calls _publish_scores_impl to flip published=True, then emits score change
    events and broadcasts them via WebSocket.
    """
    logger.info(
        "[publish_scores] Starting (approval=%s, decided_by=%s)",
        approval_id,
        decided_by,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="publish_scores",
            status="running",
            triggered_by="operator",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        async with session_factory() as session:
            result = await _publish_scores_impl(
                session, approval_id, decided_by, decision_reason
            )

        # If published, emit score change events and broadcast
        if result.get("status") == "published":
            reset_engine_cache()
            eng = get_engine()
            sf = get_session_factory(eng)
            async with sf() as session:
                n_events = await _emit_score_change_events(session)
                n_broadcast = await _broadcast_score_events(session)
                logger.info(
                    "[publish_scores] Emitted %d events, broadcast %d",
                    n_events,
                    n_broadcast,
                )

        # Mark job completed
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[publish_scores] Complete: %s", result)
        return result

    except Exception as e:
        logger.exception("[publish_scores] Failed: %s", e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "approval_id": approval_id, "error": str(e)}


# ---------------------------------------------------------------------------
# Score change event helpers
# ---------------------------------------------------------------------------


async def _emit_score_change_events(session: AsyncSession) -> int:
    """Compare latest vs previous scores per asset and emit score_change events.

    For each asset, fetch the two most recent scores. If the delta between
    new and old composite_percentile exceeds 5.0 in absolute value, create
    a score_change Event and a Notification.

    Returns the count of events created.
    """
    # Get all distinct asset_ids that have scores
    asset_ids_result = await session.execute(select(Score.asset_id).distinct())
    asset_ids = [row[0] for row in asset_ids_result.all()]

    n_events = 0

    for asset_id in asset_ids:
        # Get the two most recent scores for this asset
        result = await session.execute(
            select(Score, Asset.ticker)
            .join(Asset, Score.asset_id == Asset.id)
            .where(Score.asset_id == asset_id)
            .order_by(Score.scored_at.desc())
            .limit(2)
        )
        rows = result.all()

        if len(rows) < 2:
            continue

        new_score, ticker = rows[0]
        old_score, _ = rows[1]

        delta = new_score.composite_percentile - old_score.composite_percentile
        if abs(delta) <= 5.0:
            continue

        payload = {
            "old_score": old_score.composite_percentile,
            "new_score": new_score.composite_percentile,
            "delta": round(delta, 2),
            "old_conviction": old_score.conviction_level,
            "new_conviction": new_score.conviction_level,
        }

        event_db = await add_event(
            session,
            event_type="score_change",
            ticker=ticker,
            severity="minor",  # placeholder; ImpactClassifier overrides
            source="scoring_pipeline",
            payload=payload,
        )
        await add_notification(session, event_db)
        n_events += 1

    if n_events:
        await session.commit()

    return n_events


async def _broadcast_score_events(session: AsyncSession) -> int:
    """Broadcast recent score_change events via WebSocket.

    Queries score_change events created in the last 5 minutes and sends
    each one as a ScoreChangeMessage to all connected WebSocket clients.

    Returns the count of events broadcast.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    result = await session.execute(
        select(Event)
        .where(Event.event_type == "score_change")
        .where(Event.created_at >= cutoff)
        .order_by(Event.created_at.asc())
    )
    events = result.scalars().all()

    n_broadcast = 0
    for event_db in events:
        payload = event_db.payload or {}
        msg = ScoreChangeMessage(
            ticker=event_db.ticker,
            old_score=payload.get("old_score", 0.0),
            new_score=payload.get("new_score", 0.0),
            delta=payload.get("delta", 0.0),
            severity=event_db.severity,
            timestamp=event_db.timestamp,
            event_id=event_db.event_id,
        )
        await manager.broadcast(msg)
        n_broadcast += 1

    return n_broadcast


async def backtest_validate(ctx: dict) -> dict:
    """Run automatic backtest validation after scoring.

    Pre-loads all scored data from the DB in async context, builds in-memory
    providers, then runs the synchronous WalkForwardSimulator.
    """
    from datetime import date as date_type

    from margin_engine.backtesting.models import BacktestConfig, SelectionMode
    from margin_engine.backtesting.simulator import (
        ScoredStock,
        WalkForwardSimulator,
    )

    logger.info("[backtest] Starting backtest validation...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="backtest_validate",
            status="running",
            triggered_by="chained",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        # Load V3Scores grouped by date with asset tickers and prices
        scores_by_date: dict[str, list[ScoredStock]] = {}

        async with session_factory() as session:
            result = await session.execute(
                select(V3Score, Asset.ticker)
                .join(Asset, V3Score.asset_id == Asset.id)
                .order_by(V3Score.scored_at)
            )
            for v3_score, ticker in result.all():
                date_key = v3_score.scored_at.strftime("%Y-%m-%d")
                scored = ScoredStock(
                    ticker=ticker,
                    composite_score=v3_score.composite_score,
                    price=100.0,  # Placeholder; real prices from FinancialData
                )
                scores_by_date.setdefault(date_key, []).append(scored)

        if not scores_by_date:
            logger.warning("[backtest] No V3Score data found for backtesting")
            async with session_factory() as session:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
                job.status = "completed"
                job.progress = 1.0
                job.progress_detail = "No data for backtest"
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "message": "No V3Score data"}

        # Build in-memory providers
        class InMemoryScoredUniverseProvider:
            def __init__(self, data: dict[str, list[ScoredStock]]):
                self._data = data
                self._dates = sorted(data.keys())

            def get_scores(self, as_of_date: date_type) -> list[ScoredStock]:
                target = as_of_date.isoformat()
                # Return scores for nearest date <= as_of_date
                best = None
                for d in self._dates:
                    if d <= target:
                        best = d
                    else:
                        break
                return self._data.get(best, []) if best else []

        class InMemoryBenchmarkProvider:
            def get_price(self, ticker: str, as_of_date: date_type) -> float:
                return 100.0  # Flat benchmark for now

        # Determine backtest date range from available scores
        all_dates = sorted(scores_by_date.keys())
        start = date_type.fromisoformat(all_dates[0])
        end = date_type.fromisoformat(all_dates[-1])

        config = BacktestConfig(
            start_date=start,
            end_date=end,
            selection_mode=SelectionMode.TOP_PERCENTILE,
            top_percentile=0.05,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=InMemoryScoredUniverseProvider(scores_by_date),
            benchmark_provider=InMemoryBenchmarkProvider(),
        )
        bt_result = sim.run()

        # Update JobRun
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.progress_detail = (
                f"CAGR={bt_result.metrics.cagr:.2%}, Sharpe={bt_result.metrics.sharpe_ratio:.2f}"
            )
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info(
            "[backtest] Validation complete: CAGR=%.2f%%, Sharpe=%.2f, periods=%d",
            bt_result.metrics.cagr * 100,
            bt_result.metrics.sharpe_ratio,
            bt_result.metrics.num_months,
        )

        return {
            "status": "completed",
            "cagr": bt_result.metrics.cagr,
            "sharpe": bt_result.metrics.sharpe_ratio,
            "num_months": bt_result.metrics.num_months,
        }

    except Exception as e:
        logger.exception("[backtest] Validation failed: %s", e)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "error": str(e)}


def _parse_factor_breakdown(
    data: dict,
) -> FactorBreakdown | None:
    """Parse a FactorBreakdown from a score_detail JSONB sub-dict.

    Returns None if the data is malformed or has no sub_scores.
    """
    from margin_engine.models.scoring import FactorBreakdown, FactorScore

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


def _composite_from_score_detail(
    ticker: str,
    detail: dict,
) -> CompositeScore | None:
    """Build a CompositeScore from the score_detail JSONB dict.

    Returns None if required pillars (quality, value, momentum) are missing
    or malformed, so that malformed rows are skipped rather than injecting stubs.
    """
    from margin_engine.models.scoring import CompositeScore, FilterResult

    # Parse required pillars
    quality_raw = detail.get("quality")
    value_raw = detail.get("value")
    momentum_raw = detail.get("momentum")

    if quality_raw is None or value_raw is None or momentum_raw is None:
        return None

    quality = _parse_factor_breakdown(quality_raw)
    value = _parse_factor_breakdown(value_raw)
    momentum = _parse_factor_breakdown(momentum_raw)

    if quality is None or value is None or momentum is None:
        return None

    # Parse optional pillars (None if malformed or absent)
    growth = None
    growth_raw = detail.get("growth")
    if growth_raw is not None:
        growth = _parse_factor_breakdown(growth_raw)

    capital_allocation = None
    cap_alloc_raw = detail.get("capital_allocation")
    if cap_alloc_raw is not None:
        capital_allocation = _parse_factor_breakdown(cap_alloc_raw)

    catalyst = None
    catalyst_raw = detail.get("catalyst")
    if catalyst_raw is not None:
        catalyst = _parse_factor_breakdown(catalyst_raw)

    # Parse filters
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

    try:
        return CompositeScore(
            ticker=ticker,
            composite_percentile=float(detail.get("composite_percentile", 0.0)),
            composite_raw_score=float(detail.get("composite_raw_score", 0.0)),
            quality=quality,
            value=value,
            momentum=momentum,
            growth=growth,
            capital_allocation=capital_allocation,
            catalyst=catalyst,
            filters_passed=filters_passed,
            data_coverage=float(detail.get("data_coverage", 1.0)),
        )
    except (ValueError, TypeError):
        return None


async def train_ml_models(ctx: dict) -> dict:
    """Train ML cluster models on latest composite scores.

    Steps:
    1. Load latest composite scores from DB
    2. Reconstruct CompositeScore objects from JSONB
    3. Build feature matrix
    4. Cluster stocks
    5. Train per-cluster LightGBM models
    6. Save model artifacts
    7. Record MlModelRun in DB
    """
    from margin_engine.factors.feature_matrix import build_feature_matrix
    from margin_engine.factors.registry import default_registry
    from margin_engine.ml.clustering import cluster_stocks
    from margin_engine.ml.signal_model import train_cluster_models

    settings = get_settings()
    logger.info("[ml] Starting ML model training...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="schedule",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        # Load latest scores with JSONB detail
        async with session_factory() as session:
            latest_subq = (
                select(
                    Score.asset_id,
                    func.max(Score.scored_at).label("max_scored_at"),
                )
                .group_by(Score.asset_id)
                .subquery()
            )
            result = await session.execute(
                select(Score, Asset.ticker)
                .join(Asset, Score.asset_id == Asset.id)
                .join(
                    latest_subq,
                    (Score.asset_id == latest_subq.c.asset_id)
                    & (Score.scored_at == latest_subq.c.max_scored_at),
                )
            )
            rows = result.all()

        if len(rows) < settings.ml_train_min_samples:
            logger.warning(
                "[ml] Only %d scores, need %d for training",
                len(rows),
                settings.ml_train_min_samples,
            )
            async with session_factory() as session:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
                job.status = "completed"
                min_s = settings.ml_train_min_samples
                job.progress_detail = f"Insufficient data ({len(rows)} < {min_s})"
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "message": "Insufficient training data"}

        # Reconstruct CompositeScore objects from real JSONB data
        composites: list[CompositeScore] = []
        skipped = 0
        for score, ticker in rows:
            composite = _composite_from_score_detail(ticker, score.score_detail or {})
            if composite is None:
                skipped += 1
                continue
            composites.append(composite)

        if skipped:
            logger.info(
                "[ml] Skipped %d/%d scores with malformed or missing score_detail",
                skipped,
                len(rows),
            )

        # Build feature matrix
        registry = default_registry()
        features, tickers, feature_names = build_feature_matrix(composites, registry)

        # Cluster stocks
        n_clusters = settings.ml_n_clusters
        clusters = cluster_stocks(features, tickers, n_clusters=n_clusters)

        import numpy as np
        from margin_engine.ml.forward_returns import compute_forward_returns

        # Load price data for training tickers
        async with session_factory() as session:
            from margin_api.db.models import FinancialData

            price_result = await session.execute(
                select(FinancialData.price_history, Asset.ticker)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker.in_(tickers))
            )
            price_rows = price_result.all()

        # Build price_data dict: ticker -> bars
        ticker_prices: dict[str, list[dict]] = {}
        for ph, t in price_rows:
            if t and ph and isinstance(ph, dict):
                bars = ph.get("bars", [])
                if bars:
                    ticker_prices[t] = bars

        scored_entries = [
            {
                "ticker": t,
                "scored_at": (
                    str(score.scored_at.date()) if hasattr(score, "scored_at") else "2024-01-01"
                ),
            }
            for score, t in rows
            if t in ticker_prices
        ]
        fwd_returns = compute_forward_returns(scored_entries, ticker_prices)

        forward_returns = np.array([fwd_returns.get(t, 0.0) for t in tickers])
        n_with_returns = sum(1 for t in tickers if t in fwd_returns)
        logger.info(
            "[ml] Forward returns: %d/%d tickers have real data", n_with_returns, len(tickers)
        )

        # Convert clusters from {cluster_id: [tickers]} to {cluster_id: [indices]}
        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
        cluster_indices = {
            cid: [ticker_to_idx[t] for t in ctickers if t in ticker_to_idx]
            for cid, ctickers in clusters.items()
        }

        # Train models
        models = train_cluster_models(features, forward_returns, cluster_indices)

        # Train FactorVAE
        from margin_engine.ml.factor_vae import FactorVAEConfig, train_factor_vae

        vae_bytes = None
        vae_metrics = None
        if settings.vae_enable:
            try:
                vae_config = FactorVAEConfig(enable=True, latent_dim=8, hidden_dim=64, epochs=100)
                vae_bytes, vae_metrics = train_factor_vae(features, forward_returns, vae_config)
                logger.info(
                    "[ml] VAE trained: rank_ic=%.4f, recon_loss=%.4f",
                    vae_metrics.rank_ic,
                    vae_metrics.reconstruction_loss,
                )
            except Exception as e:
                logger.warning("[ml] VAE training failed, continuing without: %s", e)
        else:
            logger.info("[ml] VAE training disabled via config")

        # Serialize cluster models as pickled dict for DB storage
        import pickle

        cluster_model_data = pickle.dumps(models)
        vae_model_data = vae_bytes  # already bytes or None

        # Compute rank IC and model qualification
        from margin_engine.ml.signal_model import predict_alpha
        from scipy.stats import spearmanr

        all_preds = np.zeros(len(tickers))
        for cluster_id_ic, model_bytes_ic in models.items():
            c_indices = cluster_indices[cluster_id_ic]
            if c_indices:
                cluster_features = features[c_indices]
                preds = predict_alpha(model_bytes_ic, cluster_features)
                for j, idx in enumerate(c_indices):
                    all_preds[idx] = preds[j]

        mask = forward_returns != 0.0
        if mask.sum() > 10:
            overall_rank_ic, _ = spearmanr(all_preds[mask], forward_returns[mask])
            if np.isnan(overall_rank_ic):
                overall_rank_ic = 0.0
        else:
            overall_rank_ic = 0.0

        model_qualifies = overall_rank_ic > 0.15
        logger.info("[ml] Overall rank IC: %.4f (qualifies=%s)", overall_rank_ic, model_qualifies)

        # Sanitize values for JSONB — numpy types are not JSON-serializable
        def _sanitize(obj: object) -> object:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                v = float(obj)
                return None if (math.isnan(v) or math.isinf(v)) else v
            if isinstance(obj, np.ndarray):
                return _sanitize(obj.tolist())
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            return obj

        raw_metrics = {
            "feature_names": feature_names,
            "cluster_sizes": {str(k): len(v) for k, v in cluster_indices.items()},
            "vae_metrics": (vae_metrics.model_dump() if vae_metrics else None),
        }

        # Record MlModelRun
        async with session_factory() as session:
            ml_run = MlModelRun(
                model_type="lightgbm_cluster",
                n_clusters=int(len(models)),
                n_features=int(features.shape[1]),
                n_samples=int(features.shape[0]),
                train_metrics=_sanitize(raw_metrics),
                cluster_model_data=cluster_model_data,
                vae_model_data=vae_model_data,
                model_qualifies=bool(model_qualifies),
                overall_rank_ic=float(overall_rank_ic),
                vae_rank_ic=float(vae_metrics.rank_ic) if vae_metrics else None,
                deployment_status="candidate",
            )
            session.add(ml_run)

            # Update JobRun — use no_autoflush to prevent premature flush
            # of the ml_run INSERT when querying JobRun
            with session.no_autoflush:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.progress_detail = (
                f"{len(models)} cluster models, {len(feature_names)} features, "
                f"{len(tickers)} samples"
            )
            job.completed_at = datetime.now(UTC)
            await session.commit()
            ml_run_id = ml_run.id

        # Stage model for operator approval before it can be promoted to active
        async with session_factory() as session:
            stage_result = await _stage_ml_model_impl(session, ml_run_id)
            logger.info("[train_ml] Staged model %d for operator approval", ml_run_id)

        logger.info(
            "[ml] Training complete: %d clusters, %d features, %d samples",
            n_clusters,
            len(feature_names),
            len(tickers),
        )
        return {
            "status": "completed",
            "n_clusters": n_clusters,
            "n_features": len(feature_names),
            "n_samples": len(tickers),
        }

    except Exception as e:
        logger.exception("[ml] Training failed: %s", e)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# ML model deployment gate
# ---------------------------------------------------------------------------


async def _stage_ml_model_impl(
    session: AsyncSession,
    model_run_id: int,
) -> dict:
    """Create a PipelineApproval for an ML model awaiting operator approval.

    Fetches the MlModelRun, compares against the current active model (if any),
    and creates a staged approval with impact metrics.

    Returns a dict with status and approval_id.
    """
    # Fetch model run
    result = await session.execute(
        select(MlModelRun).where(MlModelRun.id == model_run_id)
    )
    model = result.scalar_one_or_none()

    if model is None:
        return {"status": "error", "message": "not found"}

    # Build impact summary
    impact_summary: dict = {
        "rank_ic": model.overall_rank_ic,
        "model_qualifies": model.model_qualifies,
        "n_clusters": model.n_clusters,
        "n_features": model.n_features,
        "n_samples": model.n_samples,
    }

    # Compare against currently active model
    active_result = await session.execute(
        select(MlModelRun).where(MlModelRun.deployment_status == "active").limit(1)
    )
    active_model = active_result.scalar_one_or_none()

    if active_model is not None:
        previous_ic = active_model.overall_rank_ic or 0.0
        current_ic = model.overall_rank_ic or 0.0
        impact_summary["previous_rank_ic"] = previous_ic
        impact_summary["rank_ic_delta"] = current_ic - previous_ic

    # Create PipelineApproval
    approval = PipelineApproval(
        gate_type="ml_model_deploy",
        status="staged",
        payload_ref={"ml_model_run_id": model.id},
        impact_summary=impact_summary,
        expires_at=datetime.now(UTC) + timedelta(hours=48),
    )
    session.add(approval)
    await session.flush()

    approval_id = approval.id
    await session.commit()

    logger.info(
        "[stage_ml] Staged model %d for operator approval (approval=%d)",
        model_run_id,
        approval_id,
    )

    return {"status": "staged", "approval_id": approval_id}


async def _promote_ml_model_impl(
    session: AsyncSession,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Promote a staged ML model to active after operator approval.

    Retires all currently active models, sets the candidate to active,
    and updates the PipelineApproval to approved.

    Returns a dict with status, model_id, and approval_id.
    """
    # Fetch approval
    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if approval is None:
        return {"status": "error", "message": "not found"}

    if approval.status != "staged":
        return {"status": "error", "message": "not in staged status"}

    # Get model ID from payload_ref
    model_id = approval.payload_ref["ml_model_run_id"]

    # Retire all currently active models
    await session.execute(
        update(MlModelRun)
        .where(MlModelRun.deployment_status == "active")
        .values(deployment_status="retired")
    )

    # Set candidate to active
    await session.execute(
        update(MlModelRun)
        .where(MlModelRun.id == model_id)
        .values(deployment_status="active")
    )

    # Update approval
    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decided_by = decided_by
    approval.decision_reason = decision_reason

    await session.commit()

    logger.info(
        "[promote_ml] Promoted model %d to active (approval=%d, decided_by=%s)",
        model_id,
        approval_id,
        decided_by,
    )

    return {"status": "promoted", "model_id": model_id, "approval_id": approval_id}


async def live_price_poll(ctx: dict) -> dict:
    """Poll live prices for high-conviction tickers and cache in Redis."""
    settings = get_settings()

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Query DB for tickers with high/exceptional conviction from latest scores
    async with session_factory() as session:
        latest_subq = (
            select(
                Score.asset_id,
                func.max(Score.scored_at).label("max_scored_at"),
            )
            .group_by(Score.asset_id)
            .subquery()
        )
        result = await session.execute(
            select(Asset.ticker)
            .join(Score, Score.asset_id == Asset.id)
            .join(
                latest_subq,
                (Score.asset_id == latest_subq.c.asset_id)
                & (Score.scored_at == latest_subq.c.max_scored_at),
            )
            .where(Score.conviction_level.in_(["exceptional", "high"]))
        )
        recommended = [row[0] for row in result.all()]

    if not recommended:
        return {"status": "no_recommendations", "updated": 0}

    logger.info("[prices] Polling prices for %d tickers", len(recommended))

    redis_client = aioredis.from_url(settings.redis_url)
    service = LivePriceService(redis_client)

    try:
        prices: dict[str, float] = {}
        for ticker in recommended:
            try:
                t = yf.Ticker(ticker)
                info = t.fast_info
                current = getattr(info, "last_price", None)
                if current and current > 0:
                    prices[ticker] = float(current)
            except Exception:
                continue

        if prices:
            await service.set_prices(prices)

        logger.info("[prices] Updated %d/%d prices", len(prices), len(recommended))
        return {"status": "completed", "updated": len(prices)}
    finally:
        await redis_client.aclose()


async def retry_quarantined(ctx: dict) -> dict:
    """Retry quarantined tickers weekly."""
    return {"status": "not_implemented"}


# ---------------------------------------------------------------------------
# 13F Institutional holdings ingestion
# ---------------------------------------------------------------------------


async def full_13f_ingest(ctx: dict, pipeline_id: str | None = None) -> dict:
    """Ingest 13F institutional holdings from SEC EDGAR.

    Fetches recent 13F-HR filings for a curated set of institutional managers,
    parses all holdings from each filing, and stores them in the database.
    Chains to ``compute_accumulation_signals`` on success.
    """
    from margin_engine.ingestion.providers.edgar_provider import EDGARProvider

    from margin_api.services.thirteenf_ingest import ThirteenFIngestService

    if pipeline_id is None:
        pipeline_id = uuid.uuid4().hex[:16]

    logger.info("[13f_ingest] Starting (pipeline=%s)...", pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun
    async with session_factory() as session:
        job_run = JobRun(
            job_type="13f_ingest",
            status="running",
            triggered_by="schedule",
            started_at=datetime.now(UTC),
            pipeline_id=pipeline_id,
        )
        session.add(job_run)
        await session.commit()
        job_run_id = job_run.id

    # Curated fund list -- expand over time
    curated_funds = [
        {
            "cik": "0001067983",
            "name": "BERKSHIRE HATHAWAY INC",
            "short_name": "Berkshire Hathaway",
            "tier": "curated",
        },
        {
            "cik": "0001336528",
            "name": "BRIDGEWATER ASSOCIATES LP",
            "short_name": "Bridgewater",
            "tier": "curated",
        },
        {
            "cik": "0001061768",
            "name": "BAUPOST GROUP LLC",
            "short_name": "Baupost Group",
            "tier": "curated",
        },
    ]

    try:
        edgar = EDGARProvider(user_agent="MarginInvest/1.0 support@margininvest.com")
        async with session_factory() as session:
            service = ThirteenFIngestService(session)
            managers = await service.upsert_managers(curated_funds)

            total_filings = 0
            total_holdings = 0
            for mgr in managers:
                try:
                    submissions = edgar.get_13f_submissions(mgr.cik)
                    filings = edgar.extract_13f_filings(submissions)
                    for f in filings:
                        if not await service.is_filing_new(f["accession_number"]):
                            continue
                        # Fetch and parse infotable
                        xml_text = edgar.fetch_infotable_xml(mgr.cik, f["accession_number"])
                        if xml_text is None:
                            continue
                        parsed = edgar.parse_full_infotable(
                            xml_text,
                            mgr.name,
                            mgr.cik,
                            f["filed_date"],
                            f["period_of_report"],
                        )
                        from datetime import date as date_cls

                        filing_meta = FilingMetadata(
                            manager_id=mgr.id,
                            accession_number=f["accession_number"],
                            filing_type=f["filing_type"],
                            period_of_report=date_cls.fromisoformat(f["period_of_report"]),
                            filed_date=date_cls.fromisoformat(f["filed_date"]),
                            total_value=sum(h["value_thousands"] for h in parsed),
                            total_holdings=len(parsed),
                            is_amendment=f["is_amendment"],
                        )
                        session.add(filing_meta)
                        await session.flush()
                        count = await service.store_holdings(filing_meta, mgr, parsed)
                        total_filings += 1
                        total_holdings += count
                        logger.info(
                            "[13f_ingest] %s: filed %s -- %d holdings",
                            mgr.short_name,
                            f["accession_number"],
                            count,
                        )
                except Exception:
                    logger.exception("[13f_ingest] Error processing %s", mgr.name)

        # Update job run
        async with session_factory() as session:
            job = await session.get(JobRun, job_run_id)
            if job:
                job.status = "completed"
                job.completed_at = datetime.now(UTC)
                job.progress = 100.0
                job.progress_detail = f"Ingested {total_filings} filings, {total_holdings} holdings"
                await session.commit()

        logger.info(
            "[13f_ingest] Complete: %d filings, %d holdings",
            total_filings,
            total_holdings,
        )

        # Chain to accumulation computation
        redis: ArqRedis = ctx.get("redis")
        if redis:
            await redis.enqueue_job("compute_accumulation_signals", pipeline_id=pipeline_id)

        return {"status": "ok", "filings": total_filings, "holdings": total_holdings}

    except Exception as exc:
        logger.exception("[13f_ingest] Fatal error")
        async with session_factory() as session:
            job = await session.get(JobRun, job_run_id)
            if job:
                job.status = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_message = str(exc)
                await session.commit()
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Accumulation signal computation
# ---------------------------------------------------------------------------


async def compute_accumulation_signals(ctx: dict, pipeline_id: str | None = None) -> dict:
    """Compute accumulation signals from ingested 13F holdings."""
    from margin_api.services.accumulation_service import AccumulationService

    if pipeline_id is None:
        pipeline_id = uuid.uuid4().hex[:16]

    logger.info("[accumulation] Starting (pipeline=%s)...", pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        job_run = JobRun(
            job_type="compute_accumulation",
            status="running",
            triggered_by="chain",
            started_at=datetime.now(UTC),
            pipeline_id=pipeline_id,
        )
        session.add(job_run)
        await session.commit()
        job_run_id = job_run.id

    try:
        async with session_factory() as session:
            service = AccumulationService(session)
            # Find all distinct periods that have holdings
            from margin_api.db.models import InstitutionalHolding

            periods_q = select(func.distinct(InstitutionalHolding.period_of_report)).order_by(
                InstitutionalHolding.period_of_report
            )
            result = await session.execute(periods_q)
            periods = [row[0] for row in result.all()]

            total_signals = 0
            for period in periods:
                count = await service.compute_signals(period_of_report=period)
                total_signals += count
                logger.info("[accumulation] %s: %d signals", period, count)

        async with session_factory() as session:
            job = await session.get(JobRun, job_run_id)
            if job:
                job.status = "completed"
                job.completed_at = datetime.now(UTC)
                job.progress = 100.0
                job.progress_detail = (
                    f"Computed {total_signals} signals across {len(periods)} quarters"
                )
                await session.commit()

        return {"status": "ok", "signals": total_signals, "quarters": len(periods)}

    except Exception as exc:
        logger.exception("[accumulation] Fatal error")
        async with session_factory() as session:
            job = await session.get(JobRun, job_run_id)
            if job:
                job.status = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_message = str(exc)
                await session.commit()
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Worker settings
# ---------------------------------------------------------------------------


def _parse_redis_settings() -> RedisSettings:
    """Parse the Redis URL from app settings into ARQ RedisSettings."""
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ worker settings.

    Run the worker with:
        arq margin_api.workers.WorkerSettings
    """

    redis_settings = _parse_redis_settings()

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Log worker startup info and clean up stale ingestion runs."""
        settings = get_settings()
        url = settings.redis_url
        # Redact password
        if "@" in url:
            scheme = url.split("://")[0]
            host_part = url.split("@", 1)[1]
            url = f"{scheme}://***@{host_part}"
        logger.info("[worker] Started — Redis: %s", url)
        logger.info(
            "[worker] Registered functions: %s",
            [f.__name__ if callable(f) else str(f) for f in WorkerSettings.functions],
        )

        # Mark stale "running" IngestionRuns as abandoned (from previous crashes/deploys)
        try:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            cutoff = datetime.now(UTC) - timedelta(hours=6)
            async with session_factory() as session:
                stale = await session.execute(
                    select(IngestionRun).where(
                        IngestionRun.status == "running",
                        IngestionRun.started_at < cutoff,
                    )
                )
                stale_runs = stale.scalars().all()
                for run in stale_runs:
                    run.status = "abandoned"
                    run.completed_at = datetime.now(UTC)
                    logger.warning(
                        "[worker] Marked stale IngestionRun %d as abandoned (started %s)",
                        run.id,
                        run.started_at,
                    )
                if stale_runs:
                    await session.commit()
                    logger.info("[worker] Cleaned up %d stale ingestion runs", len(stale_runs))
        except Exception:
            logger.exception("[worker] Failed to clean up stale ingestion runs")

    max_jobs = get_settings().ingest_concurrency

    functions = [
        orchestrate_ingest,
        ingest_batch,
        ingest_sweep,
        ingest_sweep_complete,
        full_score,
        full_score_v3,
        full_score_v4,
        stage_scores,
        publish_scores,
        backtest_validate,
        train_ml_models,
        live_price_poll,
        retry_quarantined,
        full_13f_ingest,
        compute_accumulation_signals,
    ]
    cron_jobs = [
        cron(orchestrate_ingest, hour=21, minute=30, run_at_startup=False),  # 4:30 PM ET
        cron(
            live_price_poll,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            run_at_startup=False,
        ),
        cron(retry_quarantined, weekday=6, hour=0, run_at_startup=False),  # Sunday midnight
        cron(train_ml_models, weekday=5, hour=2, run_at_startup=False),  # Saturday 2 AM UTC
        cron(full_13f_ingest, hour=22, minute=0, run_at_startup=False),  # 5 PM ET
    ]
    # Default job timeout: 20 minutes (batch-scale, not pipeline-scale)
    job_timeout = 1200
