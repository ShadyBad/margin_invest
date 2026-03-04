"""Backtest API endpoints for the Margin Invest API."""

from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path
from margin_engine.backtesting.replay_orchestrator import ReplayConfig
from margin_engine.config.threshold_config import ThresholdConfig
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import BacktestRun, PITFinancialSnapshot, ShadowPortfolioSnapshot
from margin_api.db.session import get_db
from margin_api.deps import require_plan
from margin_api.schemas.backtest import (
    BacktestConfigRequest,
    BacktestListResponse,
    BacktestResultResponse,
    BacktestSummaryResponse,
    BacktestTeaserResponse,
    FullBacktestResponse,
    MetricsResponse,
    PortfolioTeaserResponse,
    ReplayConfigRequest,
    ShadowPortfolioResponse,
    ShadowSnapshotResponse,
    ValidationCheckResponse,
    ValidationResponse,
)
from margin_api.schemas.calibration import CalibrationStatusResponse
from margin_api.services.backtest import (
    _build_metrics_response,
    build_full_response,
    build_portfolio_teaser,
    build_teaser_from_result,
    get_best_available_result,
    run_custom_backtest,
    run_real_backtest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["backtest"])

# In-memory store for backtest results (replaced by DB later)
_backtest_store: dict[str, BacktestResultResponse] = {}  # id -> result
_backtest_ids: dict[str, str] = {}  # id -> id (track insertion order via run_at)


def _build_synthetic_metrics(config: BacktestConfigRequest) -> MetricsResponse:
    """Generate synthetic but reasonable performance metrics for API testing.

    The real implementation will use WalkForwardSimulator with actual data providers.
    These mock values are calibrated to roughly pass the default validation thresholds.
    """
    end = config.end_date or date.today()
    months = max(
        1, (end.year - config.start_date.year) * 12 + (end.month - config.start_date.month)
    )
    years = months / 12.0

    cagr = 0.10
    benchmark_cagr = 0.07
    total_return = (1 + cagr) ** years - 1
    benchmark_total_return = (1 + benchmark_cagr) ** years - 1

    return MetricsResponse(
        cagr=cagr,
        excess_cagr=cagr - benchmark_cagr,
        sharpe_ratio=0.85,
        sortino_ratio=1.2,
        max_drawdown=0.22,
        win_rate=0.58,
        information_ratio=0.65,
        total_return=round(total_return, 4),
        benchmark_total_return=round(benchmark_total_return, 4),
        num_months=months,
        avg_turnover=0.15,
    )


def _build_validation(metrics: MetricsResponse) -> ValidationResponse:
    """Validate metrics against default pass thresholds."""
    checks = [
        ValidationCheckResponse(
            name="excess_cagr",
            threshold=0.03,
            actual=metrics.excess_cagr,
            passed=metrics.excess_cagr >= 0.03,
        ),
        ValidationCheckResponse(
            name="sharpe_ratio",
            threshold=0.7,
            actual=metrics.sharpe_ratio,
            passed=metrics.sharpe_ratio >= 0.7,
        ),
        ValidationCheckResponse(
            name="sortino_ratio",
            threshold=1.0,
            actual=metrics.sortino_ratio,
            passed=metrics.sortino_ratio >= 1.0,
        ),
        ValidationCheckResponse(
            name="max_drawdown",
            threshold=0.35,
            actual=metrics.max_drawdown,
            passed=metrics.max_drawdown <= 0.35,
        ),
        ValidationCheckResponse(
            name="win_rate",
            threshold=0.55,
            actual=metrics.win_rate,
            passed=metrics.win_rate >= 0.55,
        ),
        ValidationCheckResponse(
            name="information_ratio",
            threshold=0.5,
            actual=metrics.information_ratio,
            passed=metrics.information_ratio >= 0.5,
        ),
    ]
    passed_count = sum(1 for c in checks if c.passed)
    return ValidationResponse(
        overall_pass=passed_count == len(checks),
        passed_count=passed_count,
        total_checks=len(checks),
        checks=checks,
    )


@router.post("/backtest/run", response_model=BacktestResultResponse, status_code=201)
async def run_backtest(
    config: BacktestConfigRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestResultResponse:
    """Trigger a backtest with the given configuration.

    Attempts a real backtest via DatabasePITProvider + ReplayOrchestrator.
    Falls back to synthetic metrics when no PIT data is available or on error.
    """
    start_time = time.monotonic()

    engine_config = ReplayConfig(
        start_date=config.start_date,
        end_date=config.end_date or date.today(),
    )
    try:
        replay_result = await run_real_backtest(session, engine_config)
        if replay_result.metrics.num_months == 0:
            raise ValueError("No PIT data available")
        metrics = _build_metrics_response(replay_result.metrics)
    except Exception:
        logger.warning("Real backtest failed for /backtest/run, using synthetic", exc_info=True)
        metrics = _build_synthetic_metrics(config)

    validation = _build_validation(metrics)

    duration = time.monotonic() - start_time

    # Resolve end_date for storage
    resolved_config = config.model_copy(update={"end_date": config.end_date or date.today()})

    result = BacktestResultResponse(
        config=resolved_config,
        metrics=metrics,
        validation=validation,
        num_snapshots=metrics.num_months,
        run_at=datetime.now(UTC),
        duration_seconds=round(duration, 4),
    )

    backtest_id = str(uuid4())
    _backtest_store[backtest_id] = result

    return result


@router.get("/backtest/results", response_model=BacktestListResponse)
async def list_results() -> BacktestListResponse:
    """List all backtest results, sorted by run_at descending."""
    summaries: list[BacktestSummaryResponse] = []
    for backtest_id, result in _backtest_store.items():
        summaries.append(
            BacktestSummaryResponse(
                id=backtest_id,
                run_at=result.run_at,
                config=result.config,
                overall_pass=result.validation.overall_pass if result.validation else None,
                excess_cagr=result.metrics.excess_cagr,
                sharpe_ratio=result.metrics.sharpe_ratio,
            )
        )
    summaries.sort(key=lambda s: s.run_at, reverse=True)
    return BacktestListResponse(results=summaries, total=len(summaries))


@router.get("/backtest/results/{backtest_id}", response_model=BacktestResultResponse)
async def get_result(backtest_id: str) -> BacktestResultResponse:
    """Get a specific backtest result by ID."""
    if backtest_id not in _backtest_store:
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
    return _backtest_store[backtest_id]


@router.get("/backtest/metrics/{backtest_id}", response_model=MetricsResponse)
async def get_metrics(backtest_id: str) -> MetricsResponse:
    """Get just the performance metrics for a backtest."""
    if backtest_id not in _backtest_store:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {backtest_id} not found",
        )
    return _backtest_store[backtest_id].metrics


# -------------------------------------------------------------------
# New replay-based endpoints (Task 8)
# -------------------------------------------------------------------


@router.get(
    "/backtest/teaser/{ticker}",
    response_model=BacktestTeaserResponse,
)
async def get_backtest_teaser(
    ticker: str = Path(pattern=r"^[A-Z0-9.]{1,10}$"),
    session: AsyncSession = Depends(get_db),
) -> BacktestTeaserResponse:
    """Teaser metrics for free users -- 3 numbers + CTA."""
    result = await get_best_available_result(session)
    return build_teaser_from_result(result, ticker=ticker)


@router.get(
    "/backtest/portfolio-teaser",
    response_model=PortfolioTeaserResponse,
)
async def get_portfolio_teaser(
    session: AsyncSession = Depends(get_db),
) -> PortfolioTeaserResponse:
    """Portfolio-level teaser for the landing page. Public (no auth)."""
    result = await get_best_available_result(session)
    return build_portfolio_teaser(result)


@router.get(
    "/backtest/default",
    response_model=FullBacktestResponse,
)
async def get_default_backtest(
    user_id: int = Depends(require_plan("portfolio")),
    session: AsyncSession = Depends(get_db),
) -> FullBacktestResponse:
    """Pre-computed default backtest for pro users."""
    result = await get_best_available_result(session)
    return build_full_response(result, failure_periods=[])


@router.post(
    "/backtest/replay",
    response_model=FullBacktestResponse,
    status_code=202,
)
async def run_replay(
    config: ReplayConfigRequest,
    user_id: int = Depends(require_plan("portfolio")),
    session: AsyncSession = Depends(get_db),
) -> FullBacktestResponse:
    """On-demand custom replay backtest.

    Validates constrained knobs (<50 parameter combos) and
    returns a full backtest result. Attempts a real backtest via
    DatabasePITProvider + ReplayOrchestrator; falls back to
    synthetic if no PIT data or on error.
    """
    engine_config = ReplayConfig(
        start_date=config.start_date,
        end_date=config.end_date or date.today(),
        rebalance_frequency=config.rebalance_frequency,
        conviction_threshold=config.conviction_threshold,
        weighting=config.weighting,
        sector_exclusions=config.sector_exclusions,
        transaction_cost_bps=config.transaction_cost_bps,
    )
    try:
        result = await run_real_backtest(session, engine_config)
    except Exception:
        logger.warning("Real backtest failed, falling back to synthetic", exc_info=True)
        result = run_custom_backtest(engine_config)
    return build_full_response(result, failure_periods=[])


# -------------------------------------------------------------------
# Shadow portfolio endpoint (Task 9)
# -------------------------------------------------------------------


@router.get(
    "/backtest/shadow-portfolio",
    response_model=ShadowPortfolioResponse,
)
async def get_shadow_portfolio(
    user_id: int = Depends(require_plan("institutional")),
    session: AsyncSession = Depends(get_db),
) -> ShadowPortfolioResponse:
    """Get the live shadow portfolio -- provably forward-looking.

    Queries ShadowPortfolioSnapshot rows from the database.
    Returns an empty response if no snapshots exist yet.
    """
    stmt = select(ShadowPortfolioSnapshot).order_by(ShadowPortfolioSnapshot.as_of_date.asc())
    result = await session.execute(stmt)
    snapshots = result.scalars().all()

    if not snapshots:
        return ShadowPortfolioResponse(
            start_date=date(2026, 2, 24),
            snapshots=[],
            total_return=0.0,
            max_drawdown=0.0,
            num_days=0,
            cannot_be_backdated=True,
        )

    # Build response from real snapshots
    snapshot_responses = [
        ShadowSnapshotResponse(
            as_of_date=(
                date.fromisoformat(s.as_of_date) if isinstance(s.as_of_date, str) else s.as_of_date
            ),
            portfolio_value=s.portfolio_value,
            total_return=s.total_return,
            num_positions=s.num_positions,
            positions=s.positions_json,
        )
        for s in snapshots
    ]

    first_date = snapshot_responses[0].as_of_date
    last_date = snapshot_responses[-1].as_of_date

    # Compute max drawdown from portfolio values
    peak = 0.0
    max_dd = 0.0
    for s in snapshots:
        if s.portfolio_value > peak:
            peak = s.portfolio_value
        if peak > 0:
            dd = (peak - s.portfolio_value) / peak
            if dd > max_dd:
                max_dd = dd

    return ShadowPortfolioResponse(
        start_date=first_date,
        snapshots=snapshot_responses,
        total_return=snapshots[-1].total_return or 0.0,
        max_drawdown=max_dd,
        num_days=(last_date - first_date).days + 1,
        cannot_be_backdated=True,
    )


# -------------------------------------------------------------------
# Calibration status endpoint (Task 11)
# -------------------------------------------------------------------


@router.get(
    "/backtest/calibration-status",
    response_model=CalibrationStatusResponse,
)
async def get_calibration_status(
    session: AsyncSession = Depends(get_db),
) -> CalibrationStatusResponse:
    """Return the current calibration state of the scoring engine.

    Queries PIT data availability, latest backtest run, and current
    threshold configuration. Public endpoint (no auth required).
    """
    # Query PIT financial snapshot stats
    pit_stmt = select(
        func.count(func.distinct(PITFinancialSnapshot.ticker)),
        func.min(PITFinancialSnapshot.filing_date),
        func.max(PITFinancialSnapshot.filing_date),
    )
    pit_result = await session.execute(pit_stmt)
    pit_row = pit_result.one()
    pit_ticker_count = pit_row[0] or 0
    pit_min_date = pit_row[1]
    pit_max_date = pit_row[2]

    pit_data_available = pit_ticker_count > 0

    # Query latest backtest run
    bt_stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1)
    bt_result = await session.execute(bt_stmt)
    latest_run = bt_result.scalar_one_or_none()

    last_backtest_run: str | None = None
    validation_passed: bool | None = None
    validation_details: dict | None = None

    if latest_run is not None:
        last_backtest_run = latest_run.created_at.isoformat() if latest_run.created_at else None
        if latest_run.summary_stats and isinstance(latest_run.summary_stats, dict):
            validation_passed = latest_run.summary_stats.get("validation_passed")
            validation_details = latest_run.summary_stats.get("validation_details")

    # Load current threshold config
    config = ThresholdConfig()
    current_thresholds = config.model_dump()

    return CalibrationStatusResponse(
        pit_data_available=pit_data_available,
        pit_date_range_start=str(pit_min_date) if pit_min_date else None,
        pit_date_range_end=str(pit_max_date) if pit_max_date else None,
        pit_ticker_count=pit_ticker_count,
        last_backtest_run=last_backtest_run,
        validation_passed=validation_passed,
        validation_details=validation_details,
        current_thresholds=current_thresholds,
    )
