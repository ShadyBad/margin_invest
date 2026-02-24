"""Backtest API endpoints for the Margin Invest API."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path

from margin_api.schemas.backtest import (
    BacktestConfigRequest,
    BacktestListResponse,
    BacktestResultResponse,
    BacktestSummaryResponse,
    BacktestTeaserResponse,
    FullBacktestResponse,
    MetricsResponse,
    ReplayConfigRequest,
    ValidationCheckResponse,
    ValidationResponse,
)
from margin_api.services.backtest import (
    build_full_response,
    build_teaser_from_result,
    get_default_replay_result,
)

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
async def run_backtest(config: BacktestConfigRequest) -> BacktestResultResponse:
    """Trigger a backtest with the given configuration.

    Since we don't have real providers yet, create a mock/synthetic result
    for API testing. The real implementation will use WalkForwardSimulator
    with actual data providers.
    """
    start_time = time.monotonic()

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
) -> BacktestTeaserResponse:
    """Teaser metrics for free users -- 3 numbers + CTA."""
    result = get_default_replay_result()
    return build_teaser_from_result(result, ticker=ticker)


@router.get(
    "/backtest/default",
    response_model=FullBacktestResponse,
)
async def get_default_backtest() -> FullBacktestResponse:
    """Pre-computed default backtest for pro users."""
    result = get_default_replay_result()
    return build_full_response(result, failure_periods=[])


@router.post(
    "/backtest/replay",
    response_model=FullBacktestResponse,
    status_code=202,
)
async def run_replay(
    config: ReplayConfigRequest,
) -> FullBacktestResponse:
    """On-demand custom replay backtest.

    Validates constrained knobs (<50 parameter combos) and
    returns a full backtest result. Currently uses the same
    synthetic default result; will wire to real ReplayOrchestrator
    when PIT data providers are available.
    """
    # For now, return synthetic result with the user's config echoed
    result = get_default_replay_result()
    # Override config fields from the request
    result.config.rebalance_frequency = config.rebalance_frequency
    result.config.conviction_threshold = config.conviction_threshold
    result.config.weighting = config.weighting
    result.config.sector_exclusions = config.sector_exclusions
    result.config.transaction_cost_bps = config.transaction_cost_bps
    if config.start_date:
        result.config.start_date = config.start_date
    if config.end_date:
        result.config.end_date = config.end_date
    return build_full_response(result, failure_periods=[])
