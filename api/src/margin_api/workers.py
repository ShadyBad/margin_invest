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
    FinancialData,
    IngestionRun,
    IngestionTickerStatus,
    JobRun,
    MlModelRun,
    Score,
    V3Score,
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
    from margin_api.services.ingestion import should_ingest_ticker

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

    # Construct FMP fallback provider if API key is available
    import os

    fmp_provider = None
    fmp_key = os.environ.get("FMP_API_KEY")
    if fmp_key:
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        fmp_provider = FMPProvider(api_key=fmp_key)
        logger.info("[ingest] FMP fallback provider enabled")

    successes = 0
    failures = 0
    partial_count = 0
    failed_tickers: list[str] = []
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        logger.info("[ingest] [%d/%d] Seeding %s", i, total, ticker)

        # Check if ticker should be ingested (skip quarantined/permanently_skipped)
        async with session_factory() as session:
            asset_check = await session.execute(select(Asset).where(Asset.ticker == ticker))
            existing_asset = asset_check.scalar_one_or_none()
            if existing_asset and not should_ingest_ticker(
                existing_asset.ingestion_status,
                existing_asset.consecutive_failures,
                existing_asset.last_retry_at,
            ):
                logger.info(
                    "[ingest] %s SKIPPED (status=%s)", ticker, existing_asset.ingestion_status
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
                logger.info("[ingest] %s SKIPPED (already seeded today)", ticker)
                continue

        tick_started = datetime.now(UTC)
        async with session_factory() as session:
            result = await seed_ticker_data(
                ticker=ticker,
                provider=provider,
                session=session,
                fallback_provider=fmp_provider,
            )
        tick_ended = datetime.now(UTC)
        duration_ms = int((tick_ended - tick_started).total_seconds() * 1000)

        # Record per-ticker audit trail
        if result.status in ("ok", "partial"):
            audit_status = "succeeded"
        else:
            audit_status = result.status
        async with session_factory() as session:
            ticker_status = IngestionTickerStatus(
                run_id=run_id,
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

    return {"status": "completed", "pipeline_id": pipeline_id}


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
                f"CAGR={bt_result.metrics.cagr:.2%}, "
                f"Sharpe={bt_result.metrics.sharpe_ratio:.2f}"
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
    import os

    from margin_engine.factors.feature_matrix import build_feature_matrix
    from margin_engine.factors.registry import default_registry
    from margin_engine.ml.clustering import cluster_stocks
    from margin_engine.ml.signal_model import train_cluster_models
    from margin_engine.models.scoring import (
        CompositeScore,
        FactorBreakdown,
        FactorScore,
        FilterResult,
    )

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

        # Reconstruct CompositeScore objects
        composites: list[CompositeScore] = []
        for score, ticker in rows:
            stub_factor = FactorBreakdown(
                factor_name="stub",
                weight=1.0,
                sub_scores=[FactorScore(name="stub", raw_value=0.0, percentile_rank=50.0)],
            )
            composites.append(
                CompositeScore(
                    ticker=ticker,
                    composite_percentile=score.composite_percentile,
                    composite_raw_score=score.composite_raw_score,
                    quality=stub_factor,
                    value=stub_factor,
                    momentum=stub_factor,
                    filters_passed=[FilterResult(name="stub", passed=True)],
                    data_coverage=score.data_coverage,
                )
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
                    str(score.scored_at.date())
                    if hasattr(score, "scored_at")
                    else "2024-01-01"
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
                vae_config = FactorVAEConfig(
                    enable=True, latent_dim=8, hidden_dim=64, epochs=100
                )
                vae_bytes, vae_metrics = train_factor_vae(
                    features, forward_returns, vae_config
                )
                logger.info(
                    "[ml] VAE trained: rank_ic=%.4f, recon_loss=%.4f",
                    vae_metrics.rank_ic,
                    vae_metrics.reconstruction_loss,
                )
            except Exception as e:
                logger.warning("[ml] VAE training failed, continuing without: %s", e)
        else:
            logger.info("[ml] VAE training disabled via config")

        # Save artifacts
        artifact_dir = settings.ml_artifact_dir
        os.makedirs(artifact_dir, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        artifact_path = os.path.join(artifact_dir, f"models_{ts}")
        os.makedirs(artifact_path, exist_ok=True)

        for cluster_id, model_bytes in models.items():
            model_file = os.path.join(artifact_path, f"cluster_{cluster_id}.pkl")
            with open(model_file, "wb") as f:
                f.write(model_bytes)

        # Save VAE artifact
        vae_artifact_path = None
        if vae_bytes:
            vae_artifact_path = os.path.join(artifact_path, "factor_vae.pt")
            with open(vae_artifact_path, "wb") as f:
                f.write(vae_bytes)

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
        logger.info(
            "[ml] Overall rank IC: %.4f (qualifies=%s)", overall_rank_ic, model_qualifies
        )

        # Record MlModelRun
        async with session_factory() as session:
            ml_run = MlModelRun(
                model_type="lightgbm_cluster",
                n_clusters=len(models),
                n_features=features.shape[1],
                n_samples=features.shape[0],
                train_metrics={
                    "feature_names": feature_names,
                    "cluster_sizes": {
                        str(k): len(v) for k, v in cluster_indices.items()
                    },
                    "vae_metrics": (
                        vae_metrics.model_dump() if vae_metrics else None
                    ),
                },
                artifact_path=artifact_path,
                model_qualifies=model_qualifies,
                overall_rank_ic=overall_rank_ic,
                vae_rank_ic=vae_metrics.rank_ic if vae_metrics else None,
                vae_artifact_path=vae_artifact_path,
            )
            session.add(ml_run)

            # Update JobRun
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
        full_score_v4,
        backtest_validate,
        train_ml_models,
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
        cron(train_ml_models, weekday=5, hour=2),  # Saturday 2 AM UTC
    ]
    # ARQ job timeout: 5 hours for the full pipeline (~3000 tickers, 4+ API calls each)
    job_timeout = 18000
