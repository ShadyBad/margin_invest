"""ARQ worker configuration and job definitions.

Runs the daily pipeline: ingest → v2 scoring → v3 scoring.
Also handles live price polling and quarantined ticker retries.

Start the worker with:
    arq margin_api.workers.WorkerSettings
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import yfinance as yf
from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import func, select

from margin_api.config import get_settings
from margin_api.db.models import (
    Asset,
    IngestionRun,
    JobRun,
    Score,
)
from margin_api.db.session import get_engine, get_session_factory, reset_engine_cache
from margin_api.services.live_prices import LivePriceService
from margin_api.services.universe import get_active_snapshot

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


async def full_ingest(
    ctx: dict,
    pipeline_id: str | None = None,
) -> dict:
    """Ingest full universe from active snapshot.

    Fetches financial data from yfinance for every ticker in the active
    universe and upserts it into the database. Always chains to full_score.
    """
    from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
    from margin_engine.ingestion.rate_limiter import RateLimiter

    from margin_api.cli import _load_foreign_skips, seed_ticker_data

    # Generate pipeline_id if not provided (top of the chain)
    if pipeline_id is None:
        pipeline_id = uuid.uuid4().hex[:16]

    logger.info("[ingest] Starting full ingest (pipeline=%s)...", pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Load active universe
    async with session_factory() as session:
        snapshot = await get_active_snapshot(session)
        if snapshot is None:
            logger.error("[ingest] No active universe snapshot")
            return {"status": "error", "message": "No active universe snapshot"}

    tickers = list(snapshot.tickers)
    logger.info("[ingest] Universe v%s: %d tickers", snapshot.version, len(tickers))

    # Filter out known foreign tickers
    foreign_skips = _load_foreign_skips()
    if foreign_skips:
        before = len(tickers)
        tickers = [t for t in tickers if t not in foreign_skips]
        skipped = before - len(tickers)
        if skipped:
            logger.info("[ingest] Skipped %d known foreign tickers", skipped)

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

    # Seed each ticker — provider owns rate limiting internally
    limiter = RateLimiter(requests_per_minute=12)
    provider = YFinanceProvider(rate_limiter=limiter)

    successes = 0
    failures = 0
    partial_count = 0
    failed_tickers: list[str] = []
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        logger.info("[ingest] [%d/%d] Seeding %s", i, total, ticker)

        async with session_factory() as session:
            result = await seed_ticker_data(ticker=ticker, provider=provider, session=session)

        if result.status == "ok":
            successes += 1
        elif result.status == "partial":
            successes += 1
            partial_count += 1
        elif result.status == "failed":
            failures += 1
            failed_tickers.append(ticker)
            logger.warning("[ingest] %s FAILED: %s", ticker, result.error_message)
        # "foreign" and "skipped" results are handled silently

    # Update IngestionRun record
    completed_at = datetime.now(UTC)
    async with session_factory() as session:
        result = await session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        run = result.scalar_one()
        run.tickers_succeeded = successes
        run.tickers_failed = failures
        run.tickers_skipped = total - successes - failures
        run.tickers_partial = partial_count
        run.failed_tickers = failed_tickers
        run.status = "failed" if failures > total * 0.5 else "completed"
        run.completed_at = completed_at
        run.duration_seconds = (completed_at - run.started_at).total_seconds()
        await session.commit()

    logger.info(
        "[ingest] Complete: %d succeeded (%d partial), %d failed out of %d tickers (%.0fs)",
        successes,
        partial_count,
        failures,
        total,
        run.duration_seconds or 0,
    )

    # Run threshold-based alerting
    _log_run_alerts(total, successes, failures, partial_count, 0)

    # Chain to scoring — always enqueue regardless of ingest outcome
    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        await redis.enqueue_job("full_score", pipeline_id)
        logger.info("[ingest] Enqueued full_score job (pipeline=%s)", pipeline_id)
    else:
        logger.warning("[ingest] No redis in worker context — cannot chain to full_score")

    return {
        "status": run.status,
        "pipeline_id": pipeline_id,
        "succeeded": successes,
        "partial": partial_count,
        "failed": failures,
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

    logger.info("[score_v3] Starting v3 scoring (pipeline=%s, parent=%s)...", pipeline_id, parent_job_id)

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

    return {"status": "completed", "pipeline_id": pipeline_id}


async def backtest_validate(ctx: dict) -> dict:
    """Run automatic backtest validation after scoring."""
    return {"status": "not_implemented"}


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
        """Log worker startup info for debugging connectivity."""
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

    functions = [
        full_ingest,
        full_score,
        full_score_v3,
        backtest_validate,
        live_price_poll,
        retry_quarantined,
    ]
    cron_jobs = [
        cron(full_ingest, hour=21, minute=30),  # 4:30 PM ET (21:30 UTC) — after market close
        cron(
            live_price_poll,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            run_at_startup=False,
        ),
        cron(retry_quarantined, weekday=6, hour=0),  # Sunday midnight
    ]
    # ARQ job timeout: 5 hours for the full pipeline (~3000 tickers, 4+ API calls each)
    job_timeout = 18000
