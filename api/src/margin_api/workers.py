"""ARQ worker configuration and job definitions.

Runs the daily pipeline: ingest → v2 scoring → v3 scoring.
Also handles live price polling and quarantined ticker retries.

Start the worker with:
    arq margin_api.workers.WorkerSettings
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import pandas as pd
import redis.asyncio as aioredis
import sentry_sdk
import yfinance as yf
from arq import cron
from arq import func as arq_func
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import (
    Asset,
    BacktestRun,
    Event,
    FilingMetadata,
    FilingText,
    FinancialData,
    GovernanceEvent,
    HistoricalScore,
    IngestionRun,
    IngestionTickerStatus,
    JobRun,
    MlModelRun,
    PipelineApproval,
    PITDailyPrice,
    PITFinancialSnapshot,
    PITUniverseMembership,
    RarityDistributionSnapshot,
    RarityScore,
    ReproducibilityAudit,
    Score,
    SeedValidationReport,
    ShadowPortfolioSnapshot,
    SICSectorMap,
    UniverseSnapshot,
    V3Score,
    V4Score,
)
from margin_api.db.session import get_engine, get_session_factory, reset_engine_cache
from margin_api.routes.events import add_event, add_notification
from margin_api.services.edgar.backfill import run_edgar_backfill
from margin_api.services.edgar.index_builder import (
    USER_AGENT,
    EdgarUnavailableError,
    load_cik_ticker_sic_map,
)
from margin_api.services.edgar.price_backfill import backfill_prices_for_tickers
from margin_api.services.edgar.universe_assembly import assemble_universe, fill_last_known_prices
from margin_api.services.live_prices import LivePriceService
from margin_api.services.universe import get_active_snapshot
from margin_api.ws.scores import ScoreChangeMessage, manager

if TYPE_CHECKING:
    from margin_engine.models.scoring import CompositeScore, FactorBreakdown

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Timeout (seconds) for scoring worker functions.
# score_v3 typically completes in ~3 min; score_v4 in ~7 min.
# These generous limits catch hangs without interfering with large universes.
SCORING_V3_TIMEOUT = 600  # 10 minutes
SCORING_V4_TIMEOUT = 900  # 15 minutes

# Auto-approval threshold: if conviction changes are below this percentage
# of scored tickers, the approval is auto-approved and published immediately.
# Above this threshold, manual operator approval is required.
AUTO_APPROVE_MAX_CONVICTION_CHANGE_PCT = 0.10  # 10%


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
    from margin_api.services.seed_result import SeedResult

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

        # Resume check: skip if already seeded today (by fetched_at timestamp)
        async with session_factory() as session:
            start_of_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            resume_check = await session.execute(
                select(FinancialData)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker == ticker, FinancialData.fetched_at >= start_of_today)
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
        try:
            async with session_factory() as session:
                result = await asyncio.wait_for(
                    seed_ticker_data(
                        ticker=ticker,
                        provider=provider,
                        session=session,
                        fallback_provider=(
                            fmp_provider
                            if (fmp_breaker is None or fmp_breaker.allow_request())
                            else None
                        ),
                    ),
                    timeout=120,  # 2 min per ticker — prevents batch-level hangs
                )
        except TimeoutError:
            logger.warning("%s %s TIMEOUT after 120s", label, ticker)
            result = SeedResult(status="failed", error_message="Timeout after 120s")
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

    Updates the IngestionRun record with final stats, then enqueues full_score_v3.
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
        await redis.enqueue_job("full_score_v3", pipeline_id)
        logger.info("%s Enqueued full_score_v3 (pipeline=%s)", label, pipeline_id)

    return {
        "status": "completed",
        "pipeline_id": pipeline_id,
        "succeeded": run.tickers_succeeded or 0,
        "failed": run.tickers_failed or 0,
        "duration_seconds": run.duration_seconds,
    }


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
        await asyncio.wait_for(run_scoring_v3(), timeout=SCORING_V3_TIMEOUT)
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

    except TimeoutError:
        logger.error("[score_v3] V3 scoring timed out after %ds", SCORING_V3_TIMEOUT)
        status = "failed"
        error = f"score_v3 timed out after {SCORING_V3_TIMEOUT}s"
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = error
            job.completed_at = datetime.now(UTC)
            await session.commit()

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
        scored_at = await asyncio.wait_for(run_scoring_v4(), timeout=SCORING_V4_TIMEOUT)
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

        # Reproducibility audit
        try:
            from margin_engine.ml.reproducibility import capture_environment, compute_data_hash

            async with session_factory() as session:
                snapshot = await get_active_snapshot(session)
                scored_tickers_list = sorted(snapshot.tickers) if snapshot else []
                audit = ReproducibilityAudit(
                    pipeline_stage="full_score_v4",
                    config_hash=compute_data_hash(
                        scored_tickers_list,
                        str(datetime.now(UTC).date()),
                    ),
                    environment_snapshot=capture_environment(),
                    input_data_hash=compute_data_hash(
                        scored_tickers_list,
                        str(datetime.now(UTC).date()),
                    ),
                )
                session.add(audit)
                await session.commit()
        except Exception as e:
            logger.warning("[v4] Reproducibility audit failed (non-fatal): %s", e)

    except TimeoutError:
        error_msg = f"score_v4 timed out after {SCORING_V4_TIMEOUT}s"
        logger.error("[score_v4] %s", error_msg)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "pipeline_id": pipeline_id, "error": error_msg}

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
        scored_at_iso = scored_at.isoformat()
        await redis.enqueue_job(
            "stage_scores",
            pipeline_id,
            job_id,
            scored_at_iso,
            _job_id=f"stage_scores:{uuid.uuid4().hex[:8]}",
        )
        logger.info("[score_v4] Chained -> stage_scores (pipeline=%s)", pipeline_id)
        # Enqueue rarity computation as independent sidecar
        await redis.enqueue_job(
            "compute_rarity",
            pipeline_id,
            job_id,
            scored_at_iso,
            _job_id=f"compute_rarity:{uuid.uuid4().hex[:8]}",
        )
        logger.info(
            "[score_v4] Chained -> compute_rarity (parallel sidecar, pipeline=%s)", pipeline_id
        )
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

    # Evaluate auto-approval: if conviction change rate is below threshold
    # and we actually scored something, auto-approve and skip manual gate.
    conviction_change_pct = (conviction_changes / ticker_count) if ticker_count > 0 else 1.0
    if ticker_count > 0 and conviction_change_pct < AUTO_APPROVE_MAX_CONVICTION_CHANGE_PCT:
        approval.status = "approved"
        approval.decided_at = datetime.now(UTC)
        approval.decision_reason = (
            f"Auto-approved: conviction change rate {conviction_change_pct:.1%}"
            f" < {AUTO_APPROVE_MAX_CONVICTION_CHANGE_PCT:.0%} threshold"
            f" ({conviction_changes}/{ticker_count} tickers)"
        )
        status = "auto_approved"
        logger.info(
            "[stage_scores] Auto-approved %d scores (%s, approval=%d)",
            ticker_count,
            approval.decision_reason,
            approval_id,
        )
    else:
        status = "staged"
        if ticker_count > 0:
            logger.info(
                "[stage_scores] Manual approval required: conviction change rate %.1f%%"
                " >= %.0f%% threshold (%d/%d tickers, approval=%d)",
                conviction_change_pct * 100,
                AUTO_APPROVE_MAX_CONVICTION_CHANGE_PCT * 100,
                conviction_changes,
                ticker_count,
                approval_id,
            )
        else:
            logger.info(
                "[stage_scores] Staged empty approval (0 scores, approval=%d)",
                approval_id,
            )

    await session.commit()

    return {
        "status": status,
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

        # If auto-approved, chain directly to publish_scores
        if result.get("status") == "auto_approved":
            redis: ArqRedis | None = ctx.get("redis")
            if redis:
                await redis.enqueue_job(
                    "publish_scores",
                    result["approval_id"],
                    None,  # decided_by (system)
                    "Auto-approved by stage_scores",
                    _job_id=f"publish_scores:{uuid.uuid4().hex[:8]}",
                )
                logger.info(
                    "[stage_scores] Auto-approved → chained to publish_scores (approval=%d)",
                    result["approval_id"],
                )
            else:
                logger.warning("[stage_scores] Auto-approved but no redis — cannot chain")

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
# Compute rarity (parallel sidecar after full_score_v4)
# ---------------------------------------------------------------------------


async def compute_rarity(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
    scored_at_iso: str | None = None,
) -> dict:
    """Worker entry point: compute rarity scores for V4-scored universe.

    Runs as an independent parallel sidecar immediately after full_score_v4.
    Reads V4Score rows for the given scored_at, reconstructs CompositeScore
    objects from the detail JSONB, fetches macro regime data, and writes
    RarityScore + RarityDistributionSnapshot rows.
    """
    import numpy as np
    from margin_engine.models.scoring import CompositeScore
    from margin_engine.rarity.models import RarityConfig
    from margin_engine.rarity.rarity_engine import compute_rarity_for_universe
    from margin_engine.rarity.regime import classify_regime

    from margin_api.data.macro_data_client import (
        fetch_credit_spread,
        fetch_vix,
        fetch_yield_curve_slope,
    )

    logger.info(
        "[compute_rarity] Starting (pipeline=%s, parent=%s, scored_at=%s)",
        pipeline_id,
        parent_job_id,
        scored_at_iso,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="compute_rarity",
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

        # Load V4Score rows with Asset join for the given scored_at
        async with session_factory() as session:
            result = await session.execute(
                select(V4Score, Asset)
                .join(Asset, V4Score.asset_id == Asset.id)
                .where(V4Score.scored_at == scored_at)
            )
            rows = result.all()

        if not rows:
            logger.warning(
                "[compute_rarity] No V4Score rows found for scored_at=%s — skipping", scored_at_iso
            )
            async with session_factory() as session:
                job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = job_result.scalar_one()
                job.status = "completed"
                job.progress = 1.0
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "pipeline_id": pipeline_id, "rarity_count": 0}

        # Reconstruct CompositeScore objects from detail JSONB
        composites: list[CompositeScore] = []
        asset_id_by_ticker: dict[str, int] = {}
        for v4_score, asset in rows:
            if not v4_score.detail:
                continue
            try:
                composite = CompositeScore(**v4_score.detail)
                composites.append(composite)
                asset_id_by_ticker[composite.ticker] = asset.id
            except Exception as exc:
                logger.warning(
                    "[compute_rarity] Failed to reconstruct CompositeScore for asset_id=%d: %s",
                    v4_score.asset_id,
                    exc,
                )

        if not composites:
            logger.warning("[compute_rarity] All detail JSONB failed to reconstruct — skipping")
            async with session_factory() as session:
                job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = job_result.scalar_one()
                job.status = "completed"
                job.progress = 1.0
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "pipeline_id": pipeline_id, "rarity_count": 0}

        # Fetch macro regime indicators (all fallback gracefully)
        vix = await fetch_vix()
        yield_curve = await fetch_yield_curve_slope()
        credit_spread = await fetch_credit_spread()
        regime = classify_regime(vix, yield_curve, credit_spread)

        logger.info(
            "[compute_rarity] Regime: %s (vix=%.1f, yield_curve=%.2f, credit_spread=%.2f)",
            regime,
            vix,
            yield_curve,
            credit_spread,
        )

        # Compute rarity for all composites
        config = RarityConfig()
        results = compute_rarity_for_universe(composites, regime, [], config)

        # Write RarityScore rows
        rarity_rows: list[RarityScore] = []
        for rr in results:
            asset_id = asset_id_by_ticker.get(rr.ticker)
            if asset_id is None:
                logger.warning("[compute_rarity] No asset_id for ticker=%s — skipping", rr.ticker)
                continue
            rarity_rows.append(
                RarityScore(
                    asset_id=asset_id,
                    scored_at=scored_at,
                    rarity_score=rr.rarity_score,
                    joint_rarity_pctl=rr.dimensions.joint_rarity_pctl,
                    convergence_score=rr.dimensions.convergence_score,
                    historical_frequency=rr.dimensions.historical_frequency,
                    quality_momentum=rr.dimensions.quality_momentum,
                    smart_money_score=rr.dimensions.smart_money_score,
                    regime_alignment=rr.dimensions.regime_alignment,
                    combination_signature=rr.combination_signature,
                    regime=str(regime),
                    conviction_score=rr.conviction_score,
                    is_generational=rr.is_generational,
                    detail={
                        "pillar_percentiles": rr.pillar_percentiles,
                        "passed_gates": rr.passed_gates,
                        "composite_tier": rr.composite_tier,
                        "composite_raw_score": rr.composite_raw_score,
                    },
                    universe_size=rr.universe_size,
                )
            )

        async with session_factory() as session:
            session.add_all(rarity_rows)
            await session.commit()

        logger.info("[compute_rarity] Wrote %d RarityScore rows", len(rarity_rows))

        # Build distribution snapshots from pillar_percentiles across all results
        pillar_buckets: dict[str, list[float]] = {}
        for rr in results:
            for fname, val in rr.pillar_percentiles.items():
                pillar_buckets.setdefault(fname, []).append(val)

        snapshot_rows: list[RarityDistributionSnapshot] = []
        for fname, vals in pillar_buckets.items():
            if not vals:
                continue
            arr = np.array(vals)
            snap = RarityDistributionSnapshot(
                scored_at=scored_at,
                scope="universe",
                factor_name=fname,
                n_obs=len(vals),
                percentiles={
                    f"p{p}": round(float(np.percentile(arr, p)), 2)
                    for p in [5, 10, 25, 50, 75, 90, 95]
                },
                mean=round(float(arr.mean()), 2),
                std=round(float(arr.std()), 2),
            )
            snapshot_rows.append(snap)

        if snapshot_rows:
            async with session_factory() as session:
                session.add_all(snapshot_rows)
                await session.commit()
            logger.info(
                "[compute_rarity] Wrote %d RarityDistributionSnapshot rows", len(snapshot_rows)
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

        logger.info(
            "[compute_rarity] Complete: %d rarity scores, regime=%s", len(rarity_rows), regime
        )
        return {
            "status": "completed",
            "pipeline_id": pipeline_id,
            "rarity_count": len(rarity_rows),
            "regime": str(regime),
        }

    except Exception as e:
        logger.exception("[compute_rarity] Failed: %s", e)
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
            result = await _publish_scores_impl(session, approval_id, decided_by, decision_reason)

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
# Expiry daemon
# ---------------------------------------------------------------------------


async def _expire_stale_approvals_impl(session: AsyncSession) -> int:
    """Expire staged PipelineApprovals that are past their deadline.

    Queries PipelineApproval where status='staged' AND expires_at < now(UTC).
    Sets each to status='expired' and decided_at=now(UTC).
    Commits if any were expired.

    Returns count of expired approvals.
    """
    now = datetime.now(UTC)
    result = await session.execute(
        select(PipelineApproval).where(
            PipelineApproval.status == "staged",
            PipelineApproval.expires_at < now,
        )
    )
    stale = result.scalars().all()

    for approval in stale:
        approval.status = "expired"
        approval.decided_at = now

    if stale:
        await session.commit()

    return len(stale)


async def expire_stale_approvals(ctx: dict) -> dict:
    """Worker entry point: expire staged PipelineApprovals past their deadline.

    Runs every 12 hours. Uses a Redis lock to detect unexpected re-triggering.
    """
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)

    try:
        # Dedup guard: skip if already executed recently (5h lock)
        acquired = await redis_client.set("expire_approvals_lock", "1", nx=True, ex=18000)
        if not acquired:
            logger.warning("[expire_stale_approvals] Skipped — lock exists (ran recently)")
            return {"status": "skipped_dedup"}
    except Exception:
        logger.debug("[expire_stale_approvals] Redis lock check failed, proceeding anyway")
    finally:
        await redis_client.aclose()

    logger.info("[expire_stale_approvals] Starting expiry check")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        expired_count = await _expire_stale_approvals_impl(session)

    logger.info("[expire_stale_approvals] Expired %d stale approvals", expired_count)
    return {"status": "completed", "expired_count": expired_count}


# ---------------------------------------------------------------------------
# Governance event rollup (Redis stream → DB)
# ---------------------------------------------------------------------------

GOVERNANCE_STREAM_KEY = "governance:events"


async def _rollup_governance_events_impl(session: AsyncSession, redis: object) -> int:
    """Read governance events from Redis stream and batch-insert into DB.

    Returns the count of events inserted.
    """
    entries = await redis.xrange(GOVERNANCE_STREAM_KEY)  # type: ignore[union-attr]
    if not entries:
        return 0

    for _entry_id, fields in entries:
        # Redis fields may be bytes — decode them
        def _decode(val: bytes | str) -> str:
            return val.decode() if isinstance(val, bytes) else val

        event_type = _decode(fields.get(b"event_type", fields.get("event_type", b"")))
        source = _decode(fields.get(b"source", fields.get("source", b"")))
        detail_raw = _decode(fields.get(b"detail", fields.get("detail", b"null")))
        created_at_raw = _decode(fields.get(b"created_at", fields.get("created_at", b"")))

        detail = json.loads(detail_raw)
        created_at = datetime.fromisoformat(created_at_raw)

        session.add(
            GovernanceEvent(
                event_type=event_type,
                source=source,
                detail=detail,
                created_at=created_at,
            )
        )

    await session.commit()
    await redis.xtrim(GOVERNANCE_STREAM_KEY, maxlen=10000)  # type: ignore[union-attr]
    return len(entries)


async def rollup_governance_events(ctx: dict) -> dict:
    """Worker entry point: read governance events from Redis stream and persist to DB.

    Runs every 6 hours (03:00, 09:00, 15:00, 21:00 UTC).
    """
    logger.info("[rollup_governance_events] Starting rollup")

    settings = get_settings()
    raw_redis = aioredis.from_url(settings.redis_url, decode_responses=False)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    try:
        async with session_factory() as session:
            count = await _rollup_governance_events_impl(session, raw_redis)
    finally:
        await raw_redis.aclose()

    logger.info("[rollup_governance_events] Inserted %d events", count)
    return {"status": "completed", "events_count": count}


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
            "old_composite_tier": old_score.conviction_level,
            "new_composite_tier": new_score.conviction_level,
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


def _rebuild_composite_from_historical(
    ticker: str,
    composite_score: float,
    sub_scores: dict,
) -> CompositeScore | None:
    """Reconstruct a CompositeScore from HistoricalScore sub_scores JSONB.

    HistoricalScore.sub_scores format:
        {"quality": [{"name": "gp", "raw_value": 0.5, "percentile_rank": 80.0}, ...],
         "value": [...], "momentum": [...], "growth": [...]}

    Returns None if required pillars are missing.
    """
    from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore

    if not sub_scores:
        return None

    def _rebuild_breakdown(pillar: str, weight: float) -> FactorBreakdown | None:
        pillar_data = sub_scores.get(pillar)
        if not pillar_data or not isinstance(pillar_data, list) or len(pillar_data) == 0:
            return None
        scores = []
        for s in pillar_data:
            if not isinstance(s, dict):
                return None
            name = s.get("name")
            raw_value = s.get("raw_value")
            percentile_rank = s.get("percentile_rank")
            if name is None or raw_value is None or percentile_rank is None:
                return None
            try:
                scores.append(
                    FactorScore(
                        name=str(name),
                        raw_value=float(raw_value),
                        percentile_rank=float(percentile_rank),
                    )
                )
            except (ValueError, TypeError):
                return None
        return FactorBreakdown(factor_name=pillar, weight=weight, sub_scores=scores)

    quality = _rebuild_breakdown("quality", 0.25)
    value = _rebuild_breakdown("value", 0.20)
    momentum = _rebuild_breakdown("momentum", 0.25)

    if quality is None or value is None or momentum is None:
        return None

    growth = _rebuild_breakdown("growth", 0.15) if "growth" in sub_scores else None

    try:
        return CompositeScore(
            ticker=ticker,
            composite_percentile=composite_score,
            composite_raw_score=composite_score,
            quality=quality,
            value=value,
            momentum=momentum,
            growth=growth,
            filters_passed=[],
            data_coverage=1.0,
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
    """Train ML cluster models on latest composite scores using multi-seed validation.

    Steps:
    1. Load latest composite scores from DB
    2. Reconstruct CompositeScore objects from JSONB
    3. Build feature matrix and forward returns
    4. Loop over N seeds (configurable via ml_n_seeds):
       - Cluster stocks, train LightGBM + VAE, compute rank IC
       - Store MlModelRun per seed with run_group_id
    5. Validate seed distribution (IC stability gate)
    6. Compare to previous run group (Wilcoxon test)
    7. Store SeedValidationReport and ReproducibilityAudit
    8. If gate passes: reject non-best seeds, stage best for approval
       If gate fails: reject all seeds, emit governance event
    """
    from margin_engine.factors.feature_matrix import build_feature_matrix
    from margin_engine.factors.registry import default_registry
    from margin_engine.ml.clustering import cluster_stocks
    from margin_engine.ml.signal_model import train_cluster_models

    settings = get_settings()
    logger.info("[ml] Starting ML model training...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Prevent concurrent training — OOMs the worker if multiple run at once
    # Only consider jobs started in the last 2 hours as "running" — older ones are zombies
    cutoff = datetime.now(UTC) - timedelta(hours=2)
    async with session_factory() as session:
        running_result = await session.execute(
            select(func.count(JobRun.id)).where(
                JobRun.job_type == "train_ml_models",
                JobRun.status == "running",
                JobRun.started_at >= cutoff,
            )
        )
        running_count = running_result.scalar() or 0
        if running_count > 0:
            logger.warning(
                "[ml] Skipping: %d train_ml_models job(s) already running (started after %s)",
                running_count,
                cutoff.isoformat(),
            )
            return {"status": "skipped", "reason": f"{running_count} already running"}

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
        # Load latest V4 scores with JSONB detail (V4Score.detail has full
        # CompositeScore breakdowns; Score.score_detail is only populated by
        # the legacy v2 pipeline and is often stale/empty).
        async with session_factory() as session:
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

        logger.info(
            "[ml] V4Score query returned %d rows (source=V4Score, fix=70aad86)",
            len(rows),
        )

        if len(rows) < settings.ml_train_min_samples:
            logger.warning(
                "[ml] Only %d V4 scores, need %d for training",
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

        # Reconstruct CompositeScore objects from V4Score.detail JSONB
        composites: list[CompositeScore] = []
        skipped = 0
        skip_reasons: dict[str, int] = {}
        for score, ticker in rows:
            detail = score.detail or {}
            if not detail:
                skip_reasons["empty_detail"] = skip_reasons.get("empty_detail", 0) + 1
                skipped += 1
                continue
            composite = _composite_from_score_detail(ticker, detail)
            if composite is None:
                # Log first few skip reasons for debugging
                if skipped < 3:
                    q = detail.get("quality")
                    v = detail.get("value")
                    m = detail.get("momentum")
                    logger.warning(
                        "[ml] Skipped %s: quality=%s, value=%s, momentum=%s",
                        ticker,
                        type(q).__name__ if q else "MISSING",
                        type(v).__name__ if v else "MISSING",
                        type(m).__name__ if m else "MISSING",
                    )
                skip_reasons["parse_failed"] = skip_reasons.get("parse_failed", 0) + 1
                skipped += 1
                continue
            composites.append(composite)

        if skipped:
            logger.info(
                "[ml] Skipped %d/%d V4 scores: reasons=%s",
                skipped,
                len(rows),
                skip_reasons,
            )

        logger.info(
            "[ml] Composites built: %d valid, %d skipped out of %d V4Score rows",
            len(composites),
            skipped,
            len(rows),
        )

        if len(composites) < 2:
            msg = (
                f"Only {len(composites)} valid composites from {len(rows)} V4Score rows "
                f"(skipped={skipped}, reasons={skip_reasons}). "
                f"Need at least 2 for ML training."
            )
            logger.error("[ml] %s", msg)
            async with session_factory() as session:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
                job.status = "failed"
                job.error_message = msg
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "failed", "message": msg}

        import numpy as np
        from margin_engine.ml.forward_returns import compute_forward_returns
        from margin_engine.ml.historical_forward_returns import (
            compute_historical_forward_returns,
        )

        # --- Step 1: Load historical scores (PIT-bootstrapped) ---
        hist_composites: list[CompositeScore] = []
        hist_fwd_returns: dict[str, float] = {}
        hist_cutoff = (datetime.now(UTC) - timedelta(days=365)).date()

        async with session_factory() as session:
            hist_result = await session.execute(
                select(HistoricalScore)
                .where(HistoricalScore.score_date <= hist_cutoff)
                .order_by(HistoricalScore.score_date)
            )
            hist_rows = hist_result.scalars().all()

        if hist_rows:
            # Group by quarter (score_date)
            quarters: dict[date, list] = {}
            for hs in hist_rows:
                quarters.setdefault(hs.score_date, []).append(hs)

            hist_skipped = 0
            for quarter_date, quarter_scores in quarters.items():
                quarter_tickers = [hs.ticker for hs in quarter_scores]

                # Load PIT prices per quarter (bounded dates to avoid OOM)
                price_start = quarter_date - timedelta(days=30)
                price_end = quarter_date + timedelta(days=400)  # ~252 trading days + buffer
                async with session_factory() as session:
                    pit_result = await session.execute(
                        select(PITDailyPrice).where(
                            PITDailyPrice.ticker.in_(quarter_tickers),
                            PITDailyPrice.date >= price_start,
                            PITDailyPrice.date <= price_end,
                        )
                    )
                    pit_rows = pit_result.scalars().all()

                # Build pit_prices dict: ticker -> list of bar dicts (sorted by date)
                pit_prices: dict[str, list[dict]] = {}
                for p in pit_rows:
                    pit_prices.setdefault(p.ticker, []).append(
                        {"date": p.date.isoformat(), "close": float(p.close)}
                    )
                for ticker_key in pit_prices:
                    pit_prices[ticker_key].sort(key=lambda b: b["date"])

                # Compute historical forward returns for this quarter
                quarter_fwd = compute_historical_forward_returns(pit_prices, quarter_date)
                hist_fwd_returns.update(quarter_fwd)

                # Reconstruct CompositeScore objects from sub_scores JSONB
                for hs in quarter_scores:
                    c = _rebuild_composite_from_historical(
                        hs.ticker, hs.composite_score, hs.sub_scores or {}
                    )
                    if c is not None:
                        hist_composites.append(c)
                    else:
                        hist_skipped += 1

            logger.info(
                "[ml] Historical data: %d composites from %d quarters, "
                "%d forward returns, %d skipped",
                len(hist_composites),
                len(quarters),
                len(hist_fwd_returns),
                hist_skipped,
            )

        # --- Step 2: Combine live + historical composites ---
        all_composites = composites + hist_composites

        # --- Step 3: Build feature matrix from combined data ---
        registry = default_registry()
        features, tickers, feature_names = build_feature_matrix(all_composites, registry)

        n_clusters = settings.ml_n_clusters

        # --- Step 4: Compute live forward returns (existing code) ---
        async with session_factory() as session:
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
        live_fwd_returns = compute_forward_returns(scored_entries, ticker_prices)

        # --- Step 5: Merge forward returns (historical + live) ---
        fwd_returns = {**hist_fwd_returns, **live_fwd_returns}

        # --- Step 6: Filter to valid tickers (THE FIX — no more 0.0 default) ---
        valid_mask = np.array([t in fwd_returns for t in tickers])
        n_with_returns = int(valid_mask.sum())
        logger.info(
            "[ml] Forward returns: %d/%d tickers have real data (live=%d, historical=%d)",
            n_with_returns,
            len(tickers),
            len(live_fwd_returns),
            len(hist_fwd_returns),
        )

        # --- Step 7: Min samples gate on combined dataset ---
        if n_with_returns < settings.ml_train_min_samples:
            msg = (
                f"Only {n_with_returns} tickers with forward returns "
                f"(need {settings.ml_train_min_samples}). "
                f"Live={len(live_fwd_returns)}, Historical={len(hist_fwd_returns)}."
            )
            logger.warning("[ml] %s", msg)
            async with session_factory() as session:
                result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = result.scalar_one()
                job.status = "completed"
                job.progress_detail = msg
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "message": msg}

        # --- Step 8: Re-index to only valid tickers ---
        valid_indices = np.where(valid_mask)[0]
        tickers = [tickers[i] for i in valid_indices]
        features = features[valid_indices]
        all_composites = [all_composites[i] for i in valid_indices]
        forward_returns = np.array([fwd_returns[t] for t in tickers])

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

        # --- Multi-seed training loop ---
        import pickle

        from margin_engine.ml.factor_vae import FactorVAEConfig, train_factor_vae
        from margin_engine.ml.model_comparison import compare_model_groups
        from margin_engine.ml.reproducibility import capture_environment, compute_data_hash
        from margin_engine.ml.seed_validation import validate_seed_distribution
        from margin_engine.ml.signal_model import predict_alpha
        from scipy.stats import spearmanr

        run_group_id = str(uuid.uuid4())
        n_seeds = settings.ml_n_seeds
        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
        seed_metrics_list: list[dict] = []
        seed_ml_run_ids: list[int] = []
        best_rank_ic = -999.0
        best_seed_idx = 0

        logger.info("[ml] Starting multi-seed training: %d seeds, group=%s", n_seeds, run_group_id)

        for seed_idx in range(n_seeds):
            # Cluster stocks with this seed
            clusters = cluster_stocks(features, tickers, n_clusters=n_clusters, seed=seed_idx)

            # Convert clusters from {cluster_id: [tickers]} to {cluster_id: [indices]}
            cluster_indices = {
                cid: [ticker_to_idx[t] for t in ctickers if t in ticker_to_idx]
                for cid, ctickers in clusters.items()
            }

            # Train per-cluster LightGBM models
            models = train_cluster_models(features, forward_returns, cluster_indices, seed=seed_idx)

            # Train FactorVAE (optional)
            vae_bytes = None
            vae_metrics = None
            if settings.vae_enable:
                try:
                    vae_config = FactorVAEConfig(
                        enable=True, latent_dim=8, hidden_dim=64, epochs=100
                    )
                    vae_bytes, vae_metrics = train_factor_vae(
                        features, forward_returns, vae_config, seed=seed_idx
                    )
                    logger.info(
                        "[ml] Seed %d VAE: rank_ic=%.4f, recon=%.4f",
                        seed_idx,
                        vae_metrics.rank_ic,
                        vae_metrics.reconstruction_loss,
                    )
                except Exception as e:
                    logger.warning("[ml] Seed %d VAE failed, continuing: %s", seed_idx, e)
            else:
                if seed_idx == 0:
                    logger.info("[ml] VAE training disabled via config")

            # Compute rank IC for this seed
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
            logger.info(
                "[ml] Seed %d: rank_ic=%.4f (qualifies=%s)",
                seed_idx,
                overall_rank_ic,
                model_qualifies,
            )

            # Collect cluster labels for ARI (assign each ticker to its cluster)
            cluster_labels = [0] * len(tickers)
            for cid, indices in cluster_indices.items():
                for idx in indices:
                    cluster_labels[idx] = cid

            # Serialize and store MlModelRun for this seed
            cluster_model_data = pickle.dumps(models)
            vae_model_data = vae_bytes

            raw_metrics = {
                "feature_names": feature_names,
                "cluster_sizes": {str(k): len(v) for k, v in cluster_indices.items()},
                "vae_metrics": (vae_metrics.model_dump() if vae_metrics else None),
            }

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
                    seed=seed_idx,
                    run_group_id=run_group_id,
                )
                session.add(ml_run)
                await session.commit()
                seed_ml_run_ids.append(ml_run.id)

            # Collect seed metrics for validation
            seed_metrics_list.append(
                {
                    "seed": seed_idx,
                    "rank_ic": float(overall_rank_ic),
                    "cluster_labels": cluster_labels,
                    "n_clusters": int(len(models)),
                }
            )

            if overall_rank_ic > best_rank_ic:
                best_rank_ic = overall_rank_ic
                best_seed_idx = seed_idx

            # Free per-seed memory to avoid OOM on constrained containers
            del clusters, cluster_indices, models, cluster_model_data
            del vae_bytes, vae_model_data, all_preds
            import gc

            gc.collect()

        # --- Post-loop: validate seed distribution ---
        logger.info(
            "[ml] Multi-seed complete. Best seed=%d (IC=%.4f). Validating...",
            best_seed_idx,
            best_rank_ic,
        )

        # Select thresholds based on bootstrap mode
        if settings.ml_bootstrap_mode:
            from margin_engine.ml.seed_validation import SeedValidationThresholds

            thresholds = SeedValidationThresholds(
                min_median_rank_ic=0.05,
                max_rank_ic_cv=0.50,
                min_worst_seed_ic=0.02,
            )
            validation = validate_seed_distribution(seed_metrics_list, thresholds)
        else:
            validation = validate_seed_distribution(seed_metrics_list)

        # Compare to previous run group (if one exists)
        previous_comparison: dict | None = None
        async with session_factory() as session:
            prev_report_result = await session.execute(
                select(SeedValidationReport)
                .where(SeedValidationReport.run_group_id != run_group_id)
                .order_by(SeedValidationReport.created_at.desc())
                .limit(1)
            )
            prev_report = prev_report_result.scalar_one_or_none()
            if prev_report:
                prev_runs = await session.execute(
                    select(MlModelRun.overall_rank_ic)
                    .where(MlModelRun.run_group_id == prev_report.run_group_id)
                    .order_by(MlModelRun.seed)
                )
                prev_ics = [r[0] or 0.0 for r in prev_runs.all()]
                current_ics = [m["rank_ic"] for m in seed_metrics_list]
                comparison_result = compare_model_groups(current_ics, prev_ics)
                previous_comparison = comparison_result.to_dict()

        # Store SeedValidationReport
        env_snapshot = capture_environment()
        async with session_factory() as session:
            report = SeedValidationReport(
                run_group_id=run_group_id,
                n_seeds=n_seeds,
                metric_distributions=_sanitize(
                    {k: v.to_dict() for k, v in validation.metric_distributions.items()}
                ),
                gate_passed=validation.gate_passed,
                gate_details=_sanitize(validation.gate_details),
                selected_seed=validation.selected_seed,
                previous_comparison=_sanitize(previous_comparison),
                environment_snapshot=env_snapshot,
            )
            session.add(report)
            await session.commit()

        # Store ReproducibilityAudit for this training run
        async with session_factory() as session:
            audit = ReproducibilityAudit(
                pipeline_stage="train_ml_models",
                config_hash=compute_data_hash(tickers, str(datetime.now(UTC).date())),
                environment_snapshot=env_snapshot,
                input_data_hash=compute_data_hash(sorted(tickers), str(datetime.now(UTC).date())),
            )
            session.add(audit)
            await session.commit()

        # --- Gate decision ---
        if validation.gate_passed:
            # Reject all seeds except the best; stage the best for approval
            best_ml_run_id = seed_ml_run_ids[best_seed_idx]

            async with session_factory() as session:
                # Mark non-best seeds as rejected
                for i, run_id in enumerate(seed_ml_run_ids):
                    if i != best_seed_idx:
                        await session.execute(
                            update(MlModelRun)
                            .where(MlModelRun.id == run_id)
                            .values(deployment_status="rejected")
                        )
                await session.commit()

            # Stage the best model for operator approval
            async with session_factory() as session:
                await _stage_ml_model_impl(session, best_ml_run_id)
                logger.info(
                    "[train_ml] Gate PASSED. Staged seed %d (run %d) for approval",
                    best_seed_idx,
                    best_ml_run_id,
                )
        else:
            # Gate failed — reject all seeds, create governance event
            async with session_factory() as session:
                for run_id in seed_ml_run_ids:
                    await session.execute(
                        update(MlModelRun)
                        .where(MlModelRun.id == run_id)
                        .values(deployment_status="rejected")
                    )
                event = GovernanceEvent(
                    event_type="seed_validation_failed",
                    source="train_ml_models",
                    detail=_sanitize(
                        {
                            "run_group_id": run_group_id,
                            "n_seeds": n_seeds,
                            "gate_details": validation.gate_details,
                            "best_rank_ic": best_rank_ic,
                            "best_seed": best_seed_idx,
                        }
                    ),
                )
                session.add(event)
                await session.commit()
            logger.warning("[train_ml] Gate FAILED for group %s. No model promoted.", run_group_id)

        # Update JobRun record
        async with session_factory() as session:
            result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.progress_detail = (
                f"{n_seeds} seeds, {n_clusters} clusters, "
                f"{len(feature_names)} features, "
                f"gate={'PASS' if validation.gate_passed else 'FAIL'}"
            )
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info(
            "[ml] Training complete: %d seeds, %d clusters, %d features, %d samples, gate=%s",
            n_seeds,
            n_clusters,
            len(feature_names),
            len(tickers),
            "PASS" if validation.gate_passed else "FAIL",
        )
        return {
            "status": "completed",
            "n_seeds": n_seeds,
            "n_clusters": n_clusters,
            "n_features": len(feature_names),
            "n_samples": len(tickers),
            "gate_passed": validation.gate_passed,
            "best_seed": best_seed_idx,
            "best_rank_ic": float(best_rank_ic),
            "run_group_id": run_group_id,
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
    result = await session.execute(select(MlModelRun).where(MlModelRun.id == model_run_id))
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
        update(MlModelRun).where(MlModelRun.id == model_id).values(deployment_status="active")
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


async def promote_ml_model(
    ctx: dict,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Worker entry point: promote ML model after operator approval."""
    logger.info(
        "[promote_ml_model] Starting (approval=%s, decided_by=%s)",
        approval_id,
        decided_by,
    )
    engine = get_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        return await _promote_ml_model_impl(session, approval_id, decided_by, decision_reason)


async def live_price_poll(ctx: dict) -> dict:
    """Poll live prices for all scored tickers and cache bars + prices in Redis.

    Uses yfinance batch download (one HTTP call per batch of ~100 tickers) instead
    of per-ticker Ticker() calls.  Excludes quarantined assets and tickers that
    have failed price lookups repeatedly (tracked via Redis counter).
    """
    settings = get_settings()

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Only poll active (non-quarantined) assets that have been scored
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
            .where(Asset.ingestion_status != "quarantined")
        )
        scored_tickers = [row[0] for row in result.all()]

    if not scored_tickers:
        return {"status": "no_scored_tickers", "updated": 0}

    redis_client = aioredis.from_url(settings.redis_url)
    service = LivePriceService(redis_client)

    # Skip tickers that have failed 5+ consecutive price polls (likely delisted).
    # Counter resets on success.  Key expires after 24h so they get retried daily.
    fail_key_prefix = "price_fail:"
    max_consecutive_fails = 5
    try:
        pipe = redis_client.pipeline()
        for t in scored_tickers:
            pipe.get(f"{fail_key_prefix}{t}")
        fail_counts = await pipe.execute()

        eligible = []
        skipped = 0
        for ticker, count_raw in zip(scored_tickers, fail_counts):
            count = int(count_raw) if count_raw else 0
            if count >= max_consecutive_fails:
                skipped += 1
            else:
                eligible.append(ticker)

        if skipped:
            logger.info(
                "[prices] Skipping %d tickers with %d+ consecutive failures",
                skipped,
                max_consecutive_fails,
            )
    except Exception:
        eligible = scored_tickers
        skipped = 0

    logger.info("[prices] Polling prices for %d eligible tickers", len(eligible))

    batch_size = 100  # yf.download handles batches efficiently
    batch_timeout = 60  # seconds per batch download

    async def _download_batch(batch: list[str]) -> int:
        """Download prices for a batch of tickers via yf.download. Returns success count."""
        try:
            df = await _yf_download_with_timeout(batch, batch_timeout)
        except TimeoutError:
            # Batch timeout — retry once with split halves
            logger.warning(
                "[prices] Batch timeout (%ds) for %d tickers, retrying in halves",
                batch_timeout,
                len(batch),
            )
            mid = len(batch) // 2
            ok = 0
            for half in (batch[:mid], batch[mid:]):
                if not half:
                    continue
                try:
                    df_half = await _yf_download_with_timeout(half, batch_timeout)
                    ok += await _process_batch_df(half, df_half)
                except TimeoutError:
                    logger.warning(
                        "[prices] Half-batch timeout for %d tickers, skipping (no penalty)",
                        len(half),
                    )
                except Exception as exc:
                    logger.warning("[prices] Half-batch failed (infrastructure): %s", exc)
            return ok
        except Exception as exc:
            # Non-timeout infrastructure failure — do NOT penalize individual tickers
            logger.warning("[prices] Batch download failed (infrastructure): %s", exc)
            return 0

        return await _process_batch_df(batch, df)

    async def _yf_download_with_timeout(tickers: list[str], timeout: int) -> pd.DataFrame | None:
        """Run yf.download in a thread with asyncio timeout."""
        tickers_str = " ".join(tickers)
        async with asyncio.timeout(timeout):
            return await asyncio.to_thread(
                lambda: yf.download(
                    tickers_str,
                    period="1d",
                    progress=False,
                    threads=True,
                )
            )

    async def _process_batch_df(batch: list[str], df: pd.DataFrame | None) -> int:
        """Process a yfinance DataFrame and update Redis. Returns success count."""
        if df is None or df.empty:
            return 0

        ok = 0
        is_multi = len(batch) > 1 and isinstance(df.columns, pd.MultiIndex)

        for ticker in batch:
            try:
                if is_multi:
                    if ticker not in df.columns.get_level_values(1):
                        await _record_fail(redis_client, ticker)
                        continue
                    close = df[("Close", ticker)].dropna()
                    if close.empty:
                        await _record_fail(redis_client, ticker)
                        continue
                    last_close = float(close.iloc[-1])
                    last_row = {
                        col: float(df[(col, ticker)].iloc[-1])
                        for col in ("Open", "High", "Low", "Close")
                    }
                    last_row["Volume"] = int(df[("Volume", ticker)].iloc[-1])
                    bar_date = close.index[-1].strftime("%Y-%m-%d")
                else:
                    close_col = df.get("Close")
                    if close_col is None or close_col.dropna().empty:
                        await _record_fail(redis_client, ticker)
                        continue
                    close_col = close_col.dropna()
                    last_close = float(close_col.iloc[-1])
                    last_row = {
                        col: float(df[col].iloc[-1]) for col in ("Open", "High", "Low", "Close")
                    }
                    last_row["Volume"] = int(df["Volume"].iloc[-1])
                    bar_date = close_col.index[-1].strftime("%Y-%m-%d")

                if last_close > 0:
                    await service.set_price(ticker, last_close)
                    bar = {
                        "date": bar_date,
                        "open": last_row["Open"],
                        "high": last_row["High"],
                        "low": last_row["Low"],
                        "close": last_row["Close"],
                        "volume": last_row["Volume"],
                    }
                    await service.set_bar(ticker, bar)
                    # Reset failure counter on success
                    await redis_client.delete(f"{fail_key_prefix}{ticker}")
                    ok += 1
                else:
                    await _record_fail(redis_client, ticker)
            except Exception:
                logger.debug("[prices] Failed to extract %s from batch", ticker)
                await _record_fail(redis_client, ticker)

        return ok

    try:
        updated = 0
        failed = 0
        for i in range(0, len(eligible), batch_size):
            batch = eligible[i : i + batch_size]
            batch_ok = await _download_batch(batch)
            updated += batch_ok
            failed += len(batch) - batch_ok

        logger.info(
            "[prices] Updated %d/%d tickers (%d failed, %d skipped)",
            updated,
            len(eligible),
            failed,
            skipped,
        )
        return {
            "status": "completed",
            "updated": updated,
            "failed": failed,
            "skipped": skipped,
        }
    finally:
        await redis_client.aclose()


async def _record_fail(redis_client, ticker: str) -> None:
    """Increment the price-poll failure counter for a ticker.

    TTL (24h) is set only on first failure to create a fixed evaluation window.
    Includes a safety check for orphaned keys with no TTL.
    """
    key = f"price_fail:{ticker}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            # First failure in window — start the 24h countdown
            await redis_client.expire(key, 86400)
        else:
            # Safety: if key has no TTL (crash between INCR and EXPIRE), set it
            ttl = await redis_client.ttl(key)
            if ttl == -1:
                await redis_client.expire(key, 86400)
        logger.warning("price_fail:%s count=%d", ticker, count)
    except Exception:
        logger.debug("Redis error in _record_fail for %s", ticker, exc_info=True)


async def retry_quarantined(ctx: dict) -> dict:
    """Retry quarantined tickers (5+ consecutive failures).

    Samples up to 50 quarantined tickers, re-tests via yf.download in batches
    of 10. Clears failure counter for recovered tickers; resets inflated
    counters to max_consecutive_fails for still-failing ones.
    """
    import random

    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)
    max_consecutive_fails = 5
    max_sample = 50
    retry_batch_size = 10

    try:
        # Scan for quarantined tickers (price_fail:* with value >= threshold)
        quarantined = []
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match="price_fail:*", count=500)
            for key in keys:
                val = await redis_client.get(key)
                if val and int(val) >= max_consecutive_fails:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    ticker = key_str.replace("price_fail:", "")
                    quarantined.append(ticker)
            if cursor == 0:
                break

        if not quarantined:
            logger.info("[retry_quarantined] No quarantined tickers found")
            return {"status": "completed", "tested": 0, "recovered": 0, "still_failing": 0}

        sample = random.sample(quarantined, min(len(quarantined), max_sample))

        logger.info(
            "[retry_quarantined] Testing %d of %d quarantined tickers",
            len(sample),
            len(quarantined),
        )

        recovered = 0
        still_failing = 0

        for i in range(0, len(sample), retry_batch_size):
            batch = sample[i : i + retry_batch_size]
            tickers_str = " ".join(batch)

            try:
                df = await asyncio.to_thread(
                    lambda ts=tickers_str: yf.download(
                        ts, period="1d", progress=False, threads=True
                    )
                )
            except Exception as exc:
                logger.warning("[retry_quarantined] Batch download failed: %s", exc)
                continue

            is_multi = len(batch) > 1 and isinstance(getattr(df, "columns", None), pd.MultiIndex)

            for ticker in batch:
                has_data = False
                try:
                    if df is not None and not df.empty:
                        if is_multi:
                            if ticker in df.columns.get_level_values(1):
                                close = df[("Close", ticker)].dropna()
                                has_data = not close.empty and float(close.iloc[-1]) > 0
                        else:
                            close_col = df.get("Close")
                            if close_col is not None:
                                close_col = close_col.dropna()
                                has_data = not close_col.empty and float(close_col.iloc[-1]) > 0
                except Exception:
                    has_data = False

                key = f"price_fail:{ticker}"
                if has_data:
                    await redis_client.delete(key)
                    recovered += 1
                else:
                    await redis_client.set(key, str(max_consecutive_fails), ex=86400)
                    still_failing += 1

        logger.info(
            "[retry_quarantined] tested=%d, recovered=%d, still_failing=%d",
            len(sample),
            recovered,
            still_failing,
        )
        return {
            "status": "completed",
            "tested": len(sample),
            "recovered": recovered,
            "still_failing": still_failing,
        }
    finally:
        await redis_client.aclose()


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
# Backtest / Shadow Portfolio workers
# ---------------------------------------------------------------------------


async def precompute_default_backtest(ctx: dict) -> dict:
    """Pre-compute the default backtest using real PIT data.

    Runs weekly (Sunday 03:00 UTC). Seeds SPY benchmark prices if needed,
    runs ReplayOrchestrator with default config (2011-present) and relaxed
    filter thresholds, stores results in backtest_runs, and logs a
    validation summary.

    Falls back gracefully when PIT tables are empty.
    """
    import traceback as tb_mod

    import numpy as np
    from margin_engine.backtesting.replay_orchestrator import ReplayConfig

    from margin_api.services.backtest import (
        compute_config_hash,
        compute_validation_summary,
        run_real_backtest,
    )
    from margin_api.services.pit_provider import DatabasePITProvider

    logger.info("[precompute_backtest] Starting precompute_default_backtest...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="precompute_default_backtest",
            status="running",
            triggered_by="schedule",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        # Check if PIT tables have any data
        async with session_factory() as session:
            result = await session.execute(select(func.count()).select_from(PITFinancialSnapshot))
            pit_count = result.scalar_one()

        if pit_count == 0:
            logger.info("[precompute_backtest] No PIT data available, skipping precompute")
            async with session_factory() as session:
                job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
                job = job_result.scalar_one()
                job.status = "completed"
                job.progress = 1.0
                job.progress_detail = "Skipped — no PIT data"
                job.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "skipped", "reason": "no_pit_data"}

        # PIT data exists — run the real backtest
        config = ReplayConfig(
            start_date=date(2011, 1, 1),
            rebalance_frequency="monthly",
        )
        config_hash = compute_config_hash(config)

        async with session_factory() as session:
            provider = DatabasePITProvider(session, min_market_cap=100_000_000)

            # Seed SPY prices if not already present
            spy_count_result = await session.execute(
                select(func.count()).select_from(PITDailyPrice).where(PITDailyPrice.ticker == "SPY")
            )
            spy_count = spy_count_result.scalar_one()

            if spy_count == 0:
                logger.info("[precompute_backtest] Seeding SPY prices via yfinance...")
                spy_df = yf.download("SPY", start="2011-01-01", auto_adjust=False, progress=False)
                # Flatten MultiIndex columns from single-ticker download
                if isinstance(spy_df.columns, pd.MultiIndex):
                    spy_df.columns = spy_df.columns.get_level_values(0)
                for idx, row in spy_df.iterrows():
                    d = pd.Timestamp(idx).date() if hasattr(idx, "date") else idx
                    close_val = float(row["Close"])
                    if pd.isna(close_val):
                        continue
                    adj = row.get("Adj Close")
                    if adj is None or pd.isna(adj):
                        adj = close_val
                    else:
                        adj = float(adj)
                    session.add(
                        PITDailyPrice(
                            ticker="SPY",
                            date=d,
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=close_val,
                            adj_close=adj,
                            volume=int(row["Volume"]),
                            source="yfinance",
                        )
                    )
                await session.commit()
                logger.info("[precompute_backtest] Seeded %d SPY price rows", len(spy_df))

            # Load SPY prices for benchmark
            spy_prices = await provider.get_price_series("SPY", config.start_date, config.end_date)
            logger.info("[precompute_backtest] Loaded %d SPY benchmark prices", len(spy_prices))

            # Get active universe snapshot for the backtest run record
            active_snap = await get_active_snapshot(session)
            universe_id = active_snap.id if active_snap else 1

            # Run the backtest with error capture
            run_started_at = datetime.now(UTC)
            try:
                replay_result = await run_real_backtest(
                    session, config, benchmark_prices=spy_prices
                )
            except Exception:
                error_msg = tb_mod.format_exc()
                logger.error("[precompute_backtest] Replay failed:\n%s", error_msg)
                async with session_factory() as err_session:
                    run = BacktestRun(
                        name="default",
                        universe_snapshot_id=universe_id,
                        start_date=config.start_date.isoformat(),
                        end_date=config.end_date.isoformat(),
                        rebalance_frequency=config.rebalance_frequency,
                        config=config.model_dump(mode="json"),
                        config_hash=config_hash,
                        status="failed",
                        error_message=error_msg,
                        started_at=run_started_at,
                        completed_at=datetime.now(UTC),
                    )
                    err_session.add(run)
                    await err_session.commit()
                # Re-raise so ARQ marks the job as failed
                raise

        logger.info(
            "[precompute_backtest] Replay complete: snapshots=%d, total_return=%.4f, "
            "cagr=%.4f, sharpe=%.4f, max_dd=%.4f",
            len(replay_result.snapshots),
            replay_result.metrics.total_return,
            replay_result.metrics.cagr,
            replay_result.metrics.sharpe_ratio,
            replay_result.metrics.max_drawdown,
        )

        # Compute benchmark Sharpe from SPY monthly returns
        spy_monthly_returns = []
        spy_dates = sorted(spy_prices.keys())
        for i in range(1, len(spy_dates)):
            prev_price = spy_prices[spy_dates[i - 1]]
            curr_price = spy_prices[spy_dates[i]]
            if prev_price > 0:
                spy_monthly_returns.append((curr_price / prev_price) - 1.0)

        if spy_monthly_returns:
            spy_mean = np.mean(spy_monthly_returns)
            spy_std = np.std(spy_monthly_returns)
            benchmark_sharpe = (spy_mean * 12) / (spy_std * (12**0.5)) if spy_std > 0 else 0.0
        else:
            benchmark_sharpe = 0.0

        validation = compute_validation_summary(
            replay_result.metrics, benchmark_sharpe=benchmark_sharpe
        )

        logger.info(
            "[precompute_backtest] Validation: %s (%d/%d gates passed)",
            "PASS" if validation["overall_pass"] else "FAIL",
            validation["passed_count"],
            validation["total_gates"],
        )
        for gate in validation["gates"]:
            status = "PASS" if gate["passed"] else "FAIL"
            logger.info(
                "  [%s] %s: %.4f (threshold: %s)",
                status,
                gate["name"],
                float(gate["value"]),
                gate["threshold"],
            )

        # Store in backtest_runs
        metrics = replay_result.metrics
        async with session_factory() as session:
            run = BacktestRun(
                name="default",
                universe_snapshot_id=universe_id,
                start_date=config.start_date.isoformat(),
                end_date=config.end_date.isoformat(),
                rebalance_frequency=config.rebalance_frequency,
                config=config.model_dump(mode="json"),
                config_hash=config_hash,
                status="complete",
                total_return=metrics.total_return,
                annualized_return=metrics.cagr,
                sharpe_ratio=metrics.sharpe_ratio,
                max_drawdown=metrics.max_drawdown,
                summary_stats=replay_result.model_dump(mode="json"),
                started_at=run_started_at,
                completed_at=datetime.now(UTC),
            )
            session.add(run)
            await session.commit()

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

        result_dict = {
            "status": "completed",
            "metrics": {
                "total_return": metrics.total_return,
                "cagr": metrics.cagr,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
            },
        }
        logger.info("[precompute_backtest] Complete: %s", result_dict)
        return result_dict

    except Exception as e:
        logger.exception("[precompute_backtest] Failed: %s", e)
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
        return {"status": "error", "message": str(e)}


async def snapshot_shadow_portfolio(ctx: dict) -> dict:
    """Take a daily snapshot of the current scored portfolio.

    Runs daily at 22:30 UTC. Queries the latest published V4Scores,
    builds a portfolio snapshot, and appends to shadow_portfolio_snapshots.
    Uses on_conflict_do_nothing on as_of_date for idempotency.
    """

    logger.info("[shadow_portfolio] Starting snapshot_shadow_portfolio...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="snapshot_shadow_portfolio",
            status="running",
            triggered_by="schedule",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        async with session_factory() as session:
            # Query latest published V4Scores with their assets
            result = await session.execute(
                select(V4Score, Asset.ticker)
                .join(Asset, V4Score.asset_id == Asset.id)
                .where(V4Score.published.is_(True))
                .order_by(V4Score.composite_score.desc())
            )
            rows = result.all()

        if not rows:
            logger.info("[shadow_portfolio] No published V4Scores found, recording empty snapshot")
            positions: list[dict] = []
            num_positions = 0
        else:
            # Build positions list
            positions = []
            for v4_score, ticker in rows:
                weight = 1.0 / len(rows) if len(rows) > 0 else 0.0
                positions.append(
                    {
                        "ticker": ticker,
                        "score": v4_score.composite_score,
                        "conviction": v4_score.conviction,
                        "weight": round(weight, 6),
                    }
                )
            num_positions = len(positions)

        portfolio_value = 1_000_000.0
        as_of = date.today().isoformat()

        # Insert with idempotent upsert (skip if date already recorded)
        async with session_factory() as session:
            # Check if snapshot already exists for today
            existing = await session.execute(
                select(ShadowPortfolioSnapshot).where(ShadowPortfolioSnapshot.as_of_date == as_of)
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("[shadow_portfolio] Snapshot for %s already exists, skipping", as_of)
            else:
                snapshot = ShadowPortfolioSnapshot(
                    as_of_date=as_of,
                    portfolio_value=portfolio_value,
                    num_positions=num_positions,
                    positions_json=positions,
                )
                session.add(snapshot)
                await session.commit()
                logger.info(
                    "[shadow_portfolio] Recorded snapshot for %s with %d positions",
                    as_of,
                    num_positions,
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

        result_dict = {"status": "completed", "positions": num_positions}
        logger.info("[shadow_portfolio] Complete: %s", result_dict)
        return result_dict

    except Exception as e:
        logger.exception("[shadow_portfolio] Failed: %s", e)
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
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Daily PIT update
# ---------------------------------------------------------------------------


async def daily_pit_update(ctx: dict) -> dict:
    """Daily PIT data update — new EDGAR filings + price append + universe refresh.

    Runs daily at 23:00 UTC. Checks EDGAR for new 10-K/10-Q filings,
    appends recent prices for all active universe tickers, and refreshes
    universe membership near quarter ends. Passes the ARQ redis connection
    so newly inserted filings can have analyze_filing_text jobs enqueued.
    """
    from margin_api.services.edgar.daily_update import run_daily_pit_update

    engine = get_engine()
    session_factory = get_session_factory(engine)
    redis: ArqRedis | None = ctx.get("redis")
    result = await run_daily_pit_update(session_factory, redis=redis)
    return result


# ---------------------------------------------------------------------------
# PIT Reparse Empty Filings
# ---------------------------------------------------------------------------


async def reparse_pit_filings(ctx: dict) -> dict:
    """Re-parse EDGAR filings that have empty data (income_statement IS NULL).

    Deletes empty rows and re-downloads using the fixed file selector that
    prefers _htm.xml over linkbase XMLs. Triggered via admin endpoint.
    """
    from margin_api.services.edgar.backfill import reparse_empty_filings

    engine = get_engine()
    session_factory = get_session_factory(engine)
    result = await reparse_empty_filings(session_factory=session_factory)
    logger.info("[reparse_pit] Complete: %s", result)
    return result


# ---------------------------------------------------------------------------
# PIT Data Bootstrap
# ---------------------------------------------------------------------------


async def bootstrap_pit_data(ctx: dict) -> dict:
    """Bootstrap PIT data pipeline: EDGAR backfill → price backfill → universe assembly.

    Idempotent: safe to re-run at any time. Each phase uses ON CONFLICT
    DO NOTHING or accession_number dedup, so only missing data is fetched.

    Auto-triggered on worker startup when PIT tables are empty.
    Can also be triggered manually via POST /admin/pit/backfill to
    resume a partial backfill or catch up on new historical data.
    """
    logger.info("[bootstrap_pit] Starting PIT data bootstrap...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Log current state for observability
    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(PITFinancialSnapshot))
        existing_count = result.scalar_one()
    logger.info("[bootstrap_pit] Current filing count: %d", existing_count)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="bootstrap_pit_data",
            status="running",
            triggered_by="startup",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        # Load CIK → SIC code map for populating sic_code on snapshots and memberships
        cik_sic_map: dict[int, int | None] | None = None
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=httpx.Timeout(60),
            ) as client:
                full_map = await load_cik_ticker_sic_map(client)
                # Extract CIK → SIC code (discard the ticker from the tuple)
                cik_sic_map = {cik: sic for cik, (_ticker, sic) in full_map.items()}
            logger.info("[bootstrap_pit] Loaded CIK→SIC map: %d entries", len(cik_sic_map))
        except Exception:
            logger.warning(
                "[bootstrap_pit] Failed to load CIK→SIC map, proceeding without SIC codes",
                exc_info=True,
            )

        # Phase 1: EDGAR backfill (2011-present, pre-2011 uses unsupported xbrl.us namespace)
        logger.info("[bootstrap_pit] Phase 1/4: EDGAR backfill...")
        edgar_result = await run_edgar_backfill(
            start_year=2011,
            end_year=datetime.now(UTC).year,
            session_factory=session_factory,
            concurrency=4,
            cik_sic_map=cik_sic_map,
        )
        logger.info("[bootstrap_pit] EDGAR backfill complete: %s", edgar_result)

        # Phase 2: Price backfill for all tickers found in filings
        logger.info("[bootstrap_pit] Phase 2/4: Price backfill...")
        async with session_factory() as session:
            result = await session.execute(select(PITFinancialSnapshot.ticker).distinct())
            tickers = [row[0] for row in result.all()]

        if tickers:
            price_result = await backfill_prices_for_tickers(
                tickers=tickers,
                start_date="2011-01-01",
                session_factory=session_factory,
            )
            logger.info("[bootstrap_pit] Price backfill complete: %d tickers", len(price_result))
        else:
            price_result = {}
            logger.warning("[bootstrap_pit] No tickers found for price backfill")

        # Phase 3: Universe assembly
        logger.info("[bootstrap_pit] Phase 3/4: Universe assembly...")
        async with session_factory() as session:
            universe_result = await assemble_universe(session, cik_sic_map=cik_sic_map)
            await fill_last_known_prices(session)
        logger.info("[bootstrap_pit] Universe assembly complete: %s", universe_result)

        # Phase 4: Trigger precompute_default_backtest via ARQ
        logger.info("[bootstrap_pit] Phase 4/4: Enqueueing default backtest precompute...")
        try:
            redis_pool: ArqRedis = ctx.get("redis")  # type: ignore[assignment]
            if redis_pool is not None:
                await redis_pool.enqueue_job(
                    "precompute_default_backtest",
                    _job_id=f"precompute_backtest:{uuid.uuid4().hex[:8]}",
                )
                logger.info("[bootstrap_pit] Enqueued precompute_default_backtest")
        except Exception:
            logger.warning(
                "[bootstrap_pit] Could not enqueue precompute, will run on next cron",
                exc_info=True,
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

        summary = {
            "status": "completed",
            "edgar": edgar_result,
            "prices_tickers": len(price_result),
            "universe": universe_result,
        }
        logger.info("[bootstrap_pit] Bootstrap complete: %s", summary)
        return summary

    except EdgarUnavailableError as e:
        logger.error("[bootstrap_pit] SEC EDGAR unavailable, aborting: %s", e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "failed"
            job.error_message = f"SEC EDGAR unavailable: {e}"[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "error", "message": f"SEC EDGAR unavailable: {e}"}

    except Exception as e:
        logger.exception("[bootstrap_pit] Bootstrap failed: %s", e)
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
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Historical Score Backfill
# ---------------------------------------------------------------------------


def _generate_quarter_ends(start_year: int = 2009, end_year: int = 2025) -> list[date]:
    """Generate quarter-end dates from start_year Q1 to end_year Q4."""
    quarter_ends: list[date] = []
    for year in range(start_year, end_year + 1):
        quarter_ends.append(date(year, 3, 31))
        quarter_ends.append(date(year, 6, 30))
        quarter_ends.append(date(year, 9, 30))
        quarter_ends.append(date(year, 12, 31))
    return quarter_ends


async def backfill_historical_scores(ctx: dict) -> dict:
    """Backfill historical composite scores using PIT data for ML training.

    Generates quarter-end dates from 2009-Q1 to 2025-Q4 (67 quarters),
    loads PIT snapshots + prices for each quarter, runs the full scoring
    pipeline via score_universe_at_date(), and bulk-inserts results into
    the historical_scores table.

    Idempotent: skips quarters that already have HistoricalScore rows.
    """
    from margin_engine.scoring.historical_scorer import score_universe_at_date

    logger.info("[historical] Starting backfill_historical_scores...")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun record
    async with session_factory() as session:
        job = JobRun(
            job_type="backfill_historical_scores",
            status="running",
            triggered_by="manual",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        quarter_ends = _generate_quarter_ends(2009, 2025)
        total_quarters = len(quarter_ends)
        total_scored = 0
        quarters_done = 0

        # Load SIC → GICS sector mapping once
        sic_to_gics: dict[int, str] = {}
        async with session_factory() as session:
            sic_result = await session.execute(
                select(SICSectorMap.sic_code, SICSectorMap.gics_sector)
            )
            for row in sic_result.all():
                sic_to_gics[row[0]] = row[1]
        logger.info("[historical] Loaded SIC→GICS map: %d entries", len(sic_to_gics))

        for qe in quarter_ends:
            # --- Idempotency check: skip if already scored ---
            async with session_factory() as session:
                existing = await session.execute(
                    select(func.count())
                    .select_from(HistoricalScore)
                    .where(HistoricalScore.score_date == qe)
                )
                if existing.scalar_one() > 0:
                    quarters_done += 1
                    logger.info(
                        "[historical] %s: already scored, skipping (%d/%d)",
                        qe.isoformat(),
                        quarters_done,
                        total_quarters,
                    )
                    continue

            # --- Load active tickers from PITUniverseMembership ---
            async with session_factory() as session:
                membership_result = await session.execute(
                    select(PITUniverseMembership).where(
                        PITUniverseMembership.quarter_date == qe,
                        PITUniverseMembership.is_active.is_(True),
                    )
                )
                memberships = membership_result.scalars().all()

            if not memberships:
                quarters_done += 1
                logger.info(
                    "[historical] %s: no active memberships, skipping (%d/%d)",
                    qe.isoformat(),
                    quarters_done,
                    total_quarters,
                )
                continue

            active_tickers = {m.ticker for m in memberships}
            # Build ticker → (market_cap, sic_code) from memberships
            ticker_meta: dict[str, tuple[float | None, int | None]] = {
                m.ticker: (m.market_cap, m.sic_code) for m in memberships
            }

            # --- Load PIT snapshots with filing_date <= quarter_end ---
            async with session_factory() as session:
                snap_result = await session.execute(
                    select(PITFinancialSnapshot).where(
                        PITFinancialSnapshot.filing_date <= qe,
                        PITFinancialSnapshot.ticker.in_(active_tickers),
                    )
                )
                snapshots = snap_result.scalars().all()

            if not snapshots:
                quarters_done += 1
                logger.info(
                    "[historical] %s: no PIT snapshots, skipping (%d/%d)",
                    qe.isoformat(),
                    quarters_done,
                    total_quarters,
                )
                continue

            # Convert ORM snapshots to dicts for engine
            pit_snapshots: list[dict] = []
            for s in snapshots:
                meta = ticker_meta.get(s.ticker)
                market_cap = meta[0] if meta and meta[0] else 0.0
                sic_code = s.sic_code or (meta[1] if meta else None)
                default_sector = "Information Technology"
                sector = sic_to_gics.get(sic_code, default_sector) if sic_code else default_sector

                pit_snapshots.append(
                    {
                        "ticker": s.ticker,
                        "filing_date": s.filing_date.isoformat() if s.filing_date else "",
                        "period_end": s.period_end.isoformat() if s.period_end else "",
                        "income_statement": s.income_statement or {},
                        "balance_sheet": s.balance_sheet or {},
                        "cash_flow": s.cash_flow or {},
                        "sector": sector,
                        "market_cap": market_cap,
                        "shares_outstanding": s.shares_outstanding,
                    }
                )

            # --- Load PIT prices (date-bounded to avoid OOM) ---
            # ~400 trading days trailing window for momentum factors
            price_start = qe - timedelta(days=400)
            async with session_factory() as session:
                price_result = await session.execute(
                    select(PITDailyPrice).where(
                        PITDailyPrice.ticker.in_(active_tickers),
                        PITDailyPrice.date >= price_start,
                        PITDailyPrice.date <= qe,
                    )
                )
                price_rows = price_result.scalars().all()

            # Group prices by ticker
            pit_prices: dict[str, list[dict]] = {}
            for p in price_rows:
                if p.ticker not in pit_prices:
                    pit_prices[p.ticker] = []
                pit_prices[p.ticker].append(
                    {
                        "date": p.date.isoformat(),
                        "open": p.open,
                        "high": p.high,
                        "low": p.low,
                        "close": p.close,
                        "adj_close": p.adj_close,
                        "volume": p.volume,
                    }
                )

            # --- Score the universe at this quarter end ---
            composites = score_universe_at_date(
                pit_snapshots=pit_snapshots,
                pit_prices=pit_prices,
                rebalance_date=qe.isoformat(),
                active_tickers=active_tickers,
            )

            if not composites:
                quarters_done += 1
                logger.info(
                    "[historical] %s: scoring returned 0 results (%d/%d)",
                    qe.isoformat(),
                    quarters_done,
                    total_quarters,
                )
                continue

            # --- Bulk-insert HistoricalScore rows ---
            async with session_factory() as session:
                for c in composites:
                    # Serialize sub_scores to JSONB
                    sub_scores_json: dict[str, list[dict]] = {}
                    for category in ("quality", "value", "momentum", "growth"):
                        breakdown = getattr(c, category, None)
                        if breakdown is not None:
                            sub_scores_json[category] = [
                                {
                                    "name": fs.name,
                                    "raw_value": fs.raw_value,
                                    "percentile_rank": fs.percentile_rank,
                                }
                                for fs in breakdown.sub_scores
                            ]

                    row = HistoricalScore(
                        ticker=c.ticker,
                        score_date=qe,
                        composite_score=c.composite_percentile,
                        composite_tier=c.composite_tier.value,
                        sub_scores=sub_scores_json,
                    )
                    session.add(row)
                await session.commit()

            scored_count = len(composites)
            total_scored += scored_count
            quarters_done += 1
            logger.info(
                "[historical] %s: scored %d tickers (total: %d, quarters: %d/%d)",
                qe.isoformat(),
                scored_count,
                total_scored,
                quarters_done,
                total_quarters,
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

        result_dict = {
            "status": "completed",
            "total_scored": total_scored,
            "quarters_processed": quarters_done,
            "total_quarters": total_quarters,
        }
        logger.info("[historical] Backfill complete: %s", result_dict)
        return result_dict

    except Exception as e:
        logger.exception("[historical] Backfill failed: %s", e)
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
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Sentiment signal ingestion
# ---------------------------------------------------------------------------


async def ingest_sentiment_signals(ctx: dict) -> str:
    """Fetch short interest and analyst recs from Finnhub for scored universe."""
    logger.info("ingest_sentiment_signals: starting")
    return "ingest_sentiment_signals: stub complete"


async def backfill_form4_history(ctx: dict) -> str:
    """One-time backfill of Form 4 filings from EDGAR full-text search index."""
    logger.info("backfill_form4_history: starting")
    return "backfill_form4_history: stub complete"


async def daily_form4_update(ctx: dict) -> str:
    """Daily fetch of new Form 4 filings from EDGAR."""
    logger.info("daily_form4_update: starting")
    return "daily_form4_update: stub complete"


# ---------------------------------------------------------------------------
# Drawdown re-screening workers
# ---------------------------------------------------------------------------


async def rescore_ticker(
    ctx: dict,
    ticker: str,
    trigger_reason: str = "drawdown",
) -> dict:
    """Per-ticker scoring worker — rescores a single ticker after a trigger event.

    Creates a JobRun record, logs the intent, and marks the job completed.
    Full per-ticker scoring extraction from run_scoring_v3 is deferred as a
    follow-up; this version serves as the integration point so the queue
    plumbing is wired and observable.

    Args:
        ctx: ARQ worker context.
        ticker: Ticker symbol to rescore.
        trigger_reason: Human-readable reason (e.g. "drawdown").

    Returns:
        Dict with status and ticker.
    """
    logger.info(
        "[rescore_ticker] Starting (ticker=%s, reason=%s)",
        ticker,
        trigger_reason,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        job = JobRun(
            job_type="rescore_ticker",
            status="running",
            triggered_by="chained",
            progress_detail=f"ticker={ticker} reason={trigger_reason}",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        # Placeholder: log the rescore intent.
        # Full per-ticker scoring is a follow-up — the worker wiring is live.
        logger.info(
            "[rescore_ticker] Would rescore %s (trigger=%s) — scoring impl deferred",
            ticker,
            trigger_reason,
        )

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

        logger.info("[rescore_ticker] Completed (ticker=%s)", ticker)
        return {"status": "completed", "ticker": ticker, "trigger_reason": trigger_reason}

    except Exception as e:
        logger.exception("[rescore_ticker] Failed for ticker=%s: %s", ticker, e)
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
        return {"status": "failed", "ticker": ticker, "error": str(e)}


async def analyze_filing_text(
    ctx: dict,
    ticker: str,
    pit_snapshot_id: int,
) -> dict:
    """Extract text sections from a PIT filing and run NLP analysis.

    Downloads the filing HTML from SEC EDGAR for the given PITFinancialSnapshot,
    extracts Business/Risk/MD&A text sections, stores them in filing_texts,
    and (if MARGIN_NLP_ENABLED=true) runs structured NLP analysis via Claude.

    Args:
        ctx: ARQ worker context.
        ticker: Ticker symbol.
        pit_snapshot_id: PK of the PITFinancialSnapshot row.

    Returns:
        Dict with status, ticker, pit_snapshot_id, and optional nlp_result.
    """
    import httpx

    from margin_api.services.edgar.index_builder import USER_AGENT
    from margin_api.services.edgar.text_extractor import FilingTextExtractor
    from margin_api.services.nlp_analyzer import NLPAnalyzer

    label = f"[analyze_filing_text:{ticker}:{pit_snapshot_id}]"
    logger.info("%s Starting", label)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Load the PIT snapshot record
    async with session_factory() as session:
        result = await session.execute(
            select(PITFinancialSnapshot).where(PITFinancialSnapshot.id == pit_snapshot_id)
        )
        snapshot = result.scalar_one_or_none()

    if snapshot is None:
        logger.warning("%s PITFinancialSnapshot not found — skipping", label)
        return {"status": "skipped", "reason": "snapshot_not_found", "ticker": ticker}

    # Build the filing index URL to locate the HTML document
    cik_int = int(snapshot.cik)
    accession_clean = snapshot.accession_number.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/"

    filing_html: str | None = None
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(60.0),
        ) as client:
            # Fetch the filing index page to find the main HTML document
            index_resp = await client.get(index_url + "index.json")
            if index_resp.status_code == 200:
                index_data = index_resp.json()
                # Find the first htm/html document that isn't the index itself
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith((".htm", ".html")) and "index" not in name.lower():
                        doc_url = index_url + name
                        doc_resp = await client.get(doc_url)
                        if doc_resp.status_code == 200:
                            filing_html = doc_resp.text
                        break
    except Exception:
        logger.warning("%s Failed to download filing HTML — skipping text extraction", label)

    extractor = FilingTextExtractor()
    if filing_html:
        sections = extractor.extract_sections(filing_html, snapshot.form_type)
    else:
        # No HTML available — nothing to store
        logger.info("%s No filing HTML — text extraction skipped", label)
        return {"status": "skipped", "reason": "no_html", "ticker": ticker}

    # Upsert FilingText record
    async with session_factory() as session:
        # Check if row already exists
        existing_result = await session.execute(
            select(FilingText).where(
                FilingText.ticker == ticker,
                FilingText.filing_type == snapshot.form_type,
                FilingText.period_end == snapshot.period_end,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            from datetime import UTC, datetime

            filing_text_row = FilingText(
                ticker=ticker,
                cik=snapshot.cik,
                filing_type=snapshot.form_type,
                filing_date=snapshot.filing_date,
                period_end=snapshot.period_end,
                business_text=sections.business,
                risk_factors_text=sections.risk_factors,
                mda_text=sections.mda,
                raw_html_hash=sections.html_hash,
                created_at=datetime.now(UTC),
            )
            session.add(filing_text_row)
            await session.commit()
            filing_text_id = filing_text_row.id
            logger.info("%s Stored filing text (id=%d)", label, filing_text_id)
        else:
            filing_text_id = existing.id
            logger.info("%s Filing text already exists (id=%d)", label, filing_text_id)

    # Run NLP analysis (no-op if MARGIN_NLP_ENABLED=false)
    nlp_result = None
    analyzer = NLPAnalyzer()
    async with session_factory() as session:
        nlp_result = await analyzer.analyze(
            session=session,
            filing_text_id=filing_text_id,
            ticker=ticker,
            mda_text=sections.mda,
            risk_text=sections.risk_factors,
        )

    logger.info(
        "%s Completed (filing_text_id=%d, nlp=%s)",
        label,
        filing_text_id,
        "done" if nlp_result else "skipped",
    )
    return {
        "status": "completed",
        "ticker": ticker,
        "pit_snapshot_id": pit_snapshot_id,
        "filing_text_id": filing_text_id,
        "nlp_result": nlp_result,
    }


async def screen_drawdown_candidates(ctx: dict) -> dict:
    """Daily cron: screen the scored universe for drawdown-triggered rescreening.

    Finds tickers down >= MARGIN_DRAWDOWN_THRESHOLD from their 52-week high,
    debounces recent rescreenings, and enqueues rescore_ticker jobs.

    Circuit breaker: if > 15 candidates are found, emits a governance event
    instead of mass-enqueueing (market-wide crash detection).

    Runs daily at 23:30 UTC.
    """
    from margin_api.services.drawdown_screener import DrawdownScreener

    logger.info("[screen_drawdown] Starting drawdown screening")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    screener = DrawdownScreener()

    circuit_breaker_threshold = 15

    try:
        async with session_factory() as session:
            candidates = await screener.find_candidates(session)

        logger.info(
            "[screen_drawdown] Found %d candidate(s)",
            len(candidates),
        )

        if len(candidates) > circuit_breaker_threshold:
            logger.warning(
                "[screen_drawdown] Circuit breaker: %d candidates exceeds threshold %d — "
                "emitting governance event instead of mass-enqueueing",
                len(candidates),
                circuit_breaker_threshold,
            )
            reset_engine_cache()
            engine = get_engine()
            session_factory = get_session_factory(engine)
            async with session_factory() as session:
                event = GovernanceEvent(
                    event_type="drawdown_circuit_breaker",
                    source="screen_drawdown_candidates",
                    detail={
                        "candidate_count": len(candidates),
                        "circuit_breaker_threshold": circuit_breaker_threshold,
                        "tickers": [c.ticker for c in candidates[:50]],
                    },
                )
                session.add(event)
                await session.commit()

            return {
                "status": "circuit_breaker",
                "candidate_count": len(candidates),
                "circuit_breaker_threshold": circuit_breaker_threshold,
            }

        if not candidates:
            logger.info("[screen_drawdown] No drawdown candidates found")
            return {"status": "completed", "candidate_count": 0, "rescreened": 0}

        redis: object | None = ctx.get("redis")
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            rescreened = await screener.trigger_rescreening(session, candidates, redis)

        logger.info("[screen_drawdown] Rescreened %d ticker(s)", rescreened)
        return {"status": "completed", "candidate_count": len(candidates), "rescreened": rescreened}

    except Exception as e:
        logger.exception("[screen_drawdown] Failed: %s", e)
        return {"status": "failed", "error": str(e)}


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
        # Sentry error tracking
        sentry_dsn = os.environ.get("SENTRY_DSN")
        if sentry_dsn:
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            logger.info("[worker] Sentry initialized")

        # Fix yfinance TzCache permission errors in containers
        yf.set_tz_cache_location("/tmp/yfinance-cache")

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

        # Clean up orphaned ARQ in-progress keys from previous worker crashes/deploys
        try:
            redis: ArqRedis | None = ctx.get("redis")
            if redis:
                keys = await redis.keys("arq:in-progress:*")
                if keys:
                    await redis.delete(*keys)
                    key_names = [k.decode() if isinstance(k, bytes) else k for k in keys]
                    logger.info(
                        "[worker] Cleared %d orphaned in-progress keys: %s",
                        len(keys),
                        key_names,
                    )
        except Exception:
            logger.exception("[worker] Failed to clean up orphaned ARQ keys")

        # One-time bulk reset of corrupted price_fail:* keys (misattribution bug fix)
        try:
            redis_pool: ArqRedis | None = ctx.get("redis")
            if redis_pool:
                already_done = await redis_pool.get("price_fail_bulk_reset_done")
                if not already_done:
                    deleted = 0
                    cursor = 0
                    while True:
                        cursor, keys = await redis_pool.scan(
                            cursor=cursor, match="price_fail:*", count=500
                        )
                        if keys:
                            await redis_pool.delete(*keys)
                            deleted += len(keys)
                        if cursor == 0:
                            break
                    await redis_pool.set("price_fail_bulk_reset_done", "1")
                    if deleted:
                        logger.info("[worker] Bulk-reset %d corrupted price_fail keys", deleted)
                else:
                    logger.debug("[worker] price_fail bulk reset already done, skipping")
        except Exception:
            logger.exception("[worker] Failed to bulk-reset price_fail keys")

        # Auto-bootstrap PIT data if tables are empty
        try:
            engine = get_engine()
            session_factory = get_session_factory(engine)
            async with session_factory() as session:
                result = await session.execute(
                    select(func.count()).select_from(PITFinancialSnapshot)
                )
                pit_count = result.scalar_one()

            if pit_count == 0:
                redis_pool: ArqRedis = ctx.get("redis")  # type: ignore[assignment]
                if redis_pool is not None:
                    # Check if a bootstrap job is already queued to avoid duplicates
                    queued = await redis_pool.zrangebyscore("arq:queue", "-inf", "+inf")
                    already_queued = any(
                        b"bootstrap_pit" in (j if isinstance(j, bytes) else j.encode())
                        for j in queued
                    )
                    if already_queued:
                        logger.info(
                            "[worker] PIT tables empty but bootstrap job already queued, skipping"
                        )
                    else:
                        job_id = f"bootstrap_pit:{uuid.uuid4().hex[:8]}"
                        await redis_pool.enqueue_job("bootstrap_pit_data", _job_id=job_id)
                        logger.info(
                            "[worker] PIT tables empty — enqueued bootstrap_pit_data: %s",
                            job_id,
                        )
            else:
                logger.info("[worker] PIT tables have %d filings, skipping bootstrap", pit_count)
        except Exception:
            logger.exception("[worker] Failed to check/enqueue PIT bootstrap")

    max_jobs = get_settings().ingest_concurrency

    functions = [
        orchestrate_ingest,
        ingest_batch,
        ingest_sweep,
        ingest_sweep_complete,
        # Scoring pipeline: 2h timeout — 3,000+ tickers take ~20-40 min
        arq_func(full_score_v3, timeout=7200),
        arq_func(full_score_v4, timeout=7200),
        stage_scores,
        arq_func(compute_rarity, timeout=300),
        publish_scores,
        promote_ml_model,
        backtest_validate,
        # ML training: 2h timeout — 20 seeds × sequential training
        arq_func(train_ml_models, timeout=7200),
        live_price_poll,
        retry_quarantined,
        full_13f_ingest,
        compute_accumulation_signals,
        expire_stale_approvals,
        rollup_governance_events,
        # 4h timeout — real backtest processes 204 months × 5000+ tickers
        arq_func(precompute_default_backtest, timeout=14400),
        snapshot_shadow_portfolio,
        daily_pit_update,
        # 24h timeout, max_tries=5 to survive deploy-induced cancellations
        arq_func(bootstrap_pit_data, timeout=86400, max_tries=5),
        # 2h timeout — re-downloads filings from SEC EDGAR
        arq_func(reparse_pit_filings, timeout=259200),  # 72h for full reparse
        # 2h timeout — scores 67 quarters of PIT data for ML training
        arq_func(backfill_historical_scores, timeout=7200),
        ingest_sentiment_signals,
        backfill_form4_history,
        daily_form4_update,
        rescore_ticker,
        screen_drawdown_candidates,
        analyze_filing_text,
    ]
    cron_jobs = [
        cron(orchestrate_ingest, hour=21, minute=30, run_at_startup=False),  # 4:30 PM ET
        cron(
            live_price_poll,
            minute={0, 15, 30, 45},
            run_at_startup=False,
            timeout=900,  # 15 min — batch yf.download, ~31 batches of 100 tickers
        ),
        cron(retry_quarantined, hour={0, 6, 12, 18}, run_at_startup=False),  # Every 6 hours
        cron(
            train_ml_models, weekday=5, hour=2, run_at_startup=False, timeout=7200
        ),  # Saturday 2 AM UTC, 2h
        cron(full_13f_ingest, hour=22, minute=0, run_at_startup=False),  # 5 PM ET
        cron(expire_stale_approvals, hour={0, 12}, run_at_startup=False),
        cron(rollup_governance_events, hour={3, 9, 15, 21}, run_at_startup=False),
        cron(
            precompute_default_backtest,
            weekday="sun",
            hour=3,
            minute=0,
            run_at_startup=False,
            timeout=14400,  # 4h — 204 months × 5000+ tickers
        ),  # Sunday 3 AM UTC
        cron(
            snapshot_shadow_portfolio, hour=22, minute=30, run_at_startup=False
        ),  # Daily 10:30 PM UTC
        cron(daily_pit_update, hour=23, minute=0, run_at_startup=False),  # Daily 11 PM UTC
        cron(
            daily_form4_update, hour=23, minute=30, run_at_startup=False
        ),  # Daily 11:30 PM UTC — Form 4 filings
        cron(
            ingest_sentiment_signals, hour=23, minute=45, run_at_startup=False
        ),  # Daily 11:45 PM UTC
        cron(
            screen_drawdown_candidates, hour=23, minute=30, run_at_startup=False
        ),  # Daily 11:30 PM UTC — drawdown re-screening
    ]
    # Default job timeout: 20 minutes (batch-scale, not pipeline-scale)
    job_timeout = 1200
