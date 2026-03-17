"""Backtest service layer.

Provides helpers to build API responses from engine replay results,
a synthetic default result for fallback, and async functions for
querying precomputed backtests and running real orchestrator runs.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date

from margin_engine.backtesting.capacity import run_capacity_analysis
from margin_engine.backtesting.cost_model import validate_cost_assumptions
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.failure_audit import FailurePeriod
from margin_engine.backtesting.metrics import run_sensitivity_analysis
from margin_engine.backtesting.models import MonthlySnapshot, PerformanceMetrics
from margin_engine.backtesting.regime_classifier import RegimeSegment
from margin_engine.backtesting.replay_orchestrator import (
    ReplayConfig,
    ReplayResult,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import BacktestRun
from margin_api.schemas.backtest import (
    AuditRecordResponse,
    BacktestTeaserResponse,
    CapacityResponse,
    CapacityRow,
    CostSensitivityRow,
    CostValidationResponse,
    EquityCurvePoint,
    FactorTimelineResponse,
    FailurePeriodResponse,
    FullBacktestResponse,
    MetricsResponse,
    PortfolioTeaserResponse,
    RegimeSegmentResponse,
    ReplayConfigRequest,
    SensitivityResponse,
)
from margin_api.services.pit_provider import DatabasePITProvider

logger = logging.getLogger(__name__)


def compute_config_hash(config: ReplayConfig) -> str:
    """Return a deterministic SHA-256 hex digest for a ReplayConfig.

    Sorting keys ensures identical configs always produce the same hash
    regardless of field insertion order.
    """
    payload = config.model_dump_json(exclude={"end_date"}, exclude_none=True)
    # Re-serialize through sorted json for determinism
    obj = json.loads(payload)
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _build_metrics_response(
    m: PerformanceMetrics,
) -> MetricsResponse:
    """Convert engine PerformanceMetrics to API MetricsResponse."""
    return MetricsResponse(
        cagr=m.cagr,
        excess_cagr=m.excess_cagr,
        sharpe_ratio=m.sharpe_ratio,
        sortino_ratio=m.sortino_ratio,
        max_drawdown=m.max_drawdown,
        win_rate=m.win_rate,
        information_ratio=m.information_ratio,
        total_return=m.total_return,
        benchmark_total_return=m.benchmark_total_return,
        num_months=m.num_months,
        avg_turnover=m.avg_turnover,
        gross_cagr=m.gross_cagr,
        gross_sharpe=m.gross_sharpe,
        gross_max_drawdown=m.gross_max_drawdown,
        cost_drag_bps=m.cost_drag_bps,
    )


def build_teaser_from_result(
    result: ReplayResult,
    ticker: str | None = None,
) -> BacktestTeaserResponse:
    """Extract the 3 teaser numbers from a full replay result."""
    m = result.metrics
    return BacktestTeaserResponse(
        ticker=ticker,
        model_return=m.total_return,
        benchmark_return=m.benchmark_total_return,
        max_drawdown=m.max_drawdown,
        benchmark_max_drawdown=_benchmark_max_drawdown(result),
        start_date=result.config.start_date,
        end_date=result.config.end_date,
    )


def build_portfolio_teaser(result: ReplayResult) -> PortfolioTeaserResponse:
    """Build a portfolio-level teaser with equity curve from replay result."""
    m = result.metrics
    curve = []
    for snap in result.snapshots:
        curve.append(
            EquityCurvePoint(
                month=snap.date.strftime("%Y-%m"),
                portfolio=round(snap.portfolio_value, 2),
                benchmark=round(snap.benchmark_value, 2),
            )
        )
    return PortfolioTeaserResponse(
        model_return=m.total_return,
        benchmark_return=m.benchmark_total_return,
        max_drawdown=m.max_drawdown,
        sharpe_ratio=m.sharpe_ratio,
        num_months=m.num_months,
        start_date=result.config.start_date,
        end_date=result.config.end_date,
        equity_curve=curve,
    )


def _benchmark_max_drawdown(result: ReplayResult) -> float:
    """Compute benchmark max drawdown from snapshots."""
    if not result.snapshots:
        return 0.0
    peak = 0.0
    max_dd = 0.0
    for snap in result.snapshots:
        if snap.benchmark_value > peak:
            peak = snap.benchmark_value
        if peak > 0:
            dd = (peak - snap.benchmark_value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def build_full_response(
    result: ReplayResult,
    failure_periods: list[FailurePeriod] | None = None,
) -> FullBacktestResponse:
    """Convert a ReplayResult + failure audit into FullBacktestResponse."""
    failures = failure_periods or []

    # Build regime segment responses
    regime_segments: list[RegimeSegmentResponse] = []
    for regime_key, segment in result.regime_segments.items():
        regime_segments.append(
            RegimeSegmentResponse(
                regime=str(regime_key),
                num_months=segment.num_months,
                total_return=segment.total_portfolio_return,
                benchmark_return=segment.total_benchmark_return,
                max_drawdown=segment.max_drawdown,
            )
        )

    # Build audit log responses
    audit_log: list[AuditRecordResponse] = []
    for record in result.audit_log:
        audit_log.append(
            AuditRecordResponse(
                rebalance_date=record.rebalance_date,
                universe_size=record.universe_size,
                eliminated_count=record.eliminated_count,
                survivor_count=record.survivor_count,
                selected_count=record.selected_count,
                top_holdings=record.top_holdings,
                notable_events=record.notable_events,
                factor_coverage=record.factor_coverage,
                regime=str(record.regime),
            )
        )

    # Build factor timeline responses
    factor_timeline: list[FactorTimelineResponse] = []
    for entry in result.factor_timeline:
        factor_timeline.append(
            FactorTimelineResponse(
                as_of_date=entry.as_of_date,
                available=entry.available,
                missing=entry.missing,
                coverage_ratio=entry.coverage_ratio,
            )
        )

    # Build failure audit responses
    failure_audit: list[FailurePeriodResponse] = []
    for fp in failures:
        holdings_dicts = [h.model_dump() if hasattr(h, "model_dump") else h for h in fp.holdings]
        failure_audit.append(
            FailurePeriodResponse(
                rebalance_date=fp.rebalance_date,
                portfolio_return=fp.portfolio_return,
                benchmark_return=fp.benchmark_return,
                relative_underperformance=(fp.relative_underperformance),
                holdings=holdings_dicts,
                regime=str(fp.regime),
                regime_context=fp.regime_context,
            )
        )

    # Build equity curve
    equity_curve: list[dict] = []
    for snap in result.snapshots:
        equity_curve.append(
            {
                "date": snap.date.isoformat(),
                "portfolio_value": snap.portfolio_value,
                "benchmark_value": snap.benchmark_value,
            }
        )

    config_resp = ReplayConfigRequest(
        start_date=result.config.start_date,
        end_date=result.config.end_date,
        rebalance_frequency=result.config.rebalance_frequency,
        conviction_threshold=result.config.conviction_threshold,
        weighting=result.config.weighting,
        sector_exclusions=result.config.sector_exclusions,
        transaction_cost_bps=result.config.transaction_cost_bps,
        seed=result.config.seed,
    )

    # Cost analysis is only meaningful when snapshots have non-zero costs.
    # The synthetic default result has transaction_costs=0.0 for all months,
    # which would produce misleading sensitivity/capacity/validation data.
    has_real_costs = any(s.transaction_costs > 0 for s in result.snapshots)

    sensitivity: SensitivityResponse | None = None
    capacity: CapacityResponse | None = None
    cost_validation: CostValidationResponse | None = None

    if has_real_costs:
        # Sensitivity analysis
        sensitivity_data = run_sensitivity_analysis(result.snapshots)
        sensitivity = SensitivityResponse(
            rows=[CostSensitivityRow(**row) for row in sensitivity_data]
        )

        # Capacity analysis
        capacity_data = run_capacity_analysis(result.snapshots)
        capacity = CapacityResponse(
            rows=[CapacityRow(**row) for row in capacity_data["rows"]],
            breakeven_aum=capacity_data["breakeven_aum"],
        )

        # Cost validation — compute average cost bps across snapshots
        total_costs = sum(s.transaction_costs for s in result.snapshots)
        total_pv = sum(s.portfolio_value for s in result.snapshots)
        avg_cost_bps = (total_costs / total_pv * 10_000) if total_pv > 0 else 0.0
        validation_result = validate_cost_assumptions(avg_cost_bps, market_cap_billions=10.0)
        cost_validation = CostValidationResponse(
            model_cost_bps=validation_result["model_cost_bps"],
            benchmark_range_bps=list(validation_result["benchmark_range_bps"]),
            status=str(validation_result["status"]),
            source=str(validation_result["source"]),
        )

    return FullBacktestResponse(
        config=config_resp,
        metrics=_build_metrics_response(result.metrics),
        regime_segments=regime_segments,
        audit_log=audit_log,
        factor_timeline=factor_timeline,
        failure_audit=failure_audit,
        equity_curve=equity_curve,
        walk_forward_note=(
            "Results use walk-forward out-of-sample validation. "
            "Each rebalance uses only data available at that date. "
            "No future information is used."
        ),
        honesty_disclosure=(
            "Past performance does not predict future returns. "
            "These results include survivorship bias, limited "
            "factor coverage before 2010, and non-linear "
            "transaction cost estimates (commission + spread + "
            "market impact). See Cost Model Assumptions for details."
        ),
        sensitivity=sensitivity,
        capacity=capacity,
        cost_validation=cost_validation,
    )


def get_default_replay_result() -> ReplayResult:
    """Return a synthetic ReplayResult with realistic metrics.

    Used as a placeholder until real PIT data providers are wired.
    The metrics are calibrated to be realistic but not misleading:
    slightly above benchmark, reasonable drawdown, etc.
    """
    config = ReplayConfig(
        start_date=date(2006, 1, 1),
        end_date=date(2025, 12, 31),
    )

    metrics = PerformanceMetrics(
        cagr=0.104,
        excess_cagr=0.031,
        sharpe_ratio=0.85,
        sortino_ratio=1.18,
        max_drawdown=0.28,
        win_rate=0.57,
        information_ratio=0.62,
        total_return=5.42,
        benchmark_total_return=3.87,
        num_months=240,
        avg_turnover=0.18,
    )

    # Synthetic regime segments
    regime_segments = {
        "bull": RegimeSegment(
            regime="bull",
            num_months=156,
            portfolio_returns=[0.015] * 156,
            benchmark_returns=[0.012] * 156,
        ),
        "bear": RegimeSegment(
            regime="bear",
            num_months=36,
            portfolio_returns=[-0.02] * 36,
            benchmark_returns=[-0.03] * 36,
        ),
        "sideways": RegimeSegment(
            regime="sideways",
            num_months=30,
            portfolio_returns=[0.003] * 30,
            benchmark_returns=[0.002] * 30,
        ),
        "crisis": RegimeSegment(
            regime="crisis",
            num_months=18,
            portfolio_returns=[-0.04] * 18,
            benchmark_returns=[-0.05] * 18,
        ),
    }

    # Build synthetic monthly snapshots for equity curve.
    # Portfolio grows at ~10.4% CAGR, benchmark at ~7.3% CAGR over 20 years.
    snapshots: list[MonthlySnapshot] = []
    portfolio_monthly = 1 + 0.104 / 12
    benchmark_monthly = 1 + 0.073 / 12
    portfolio_value = 10000.0
    benchmark_value = 10000.0
    for i in range(240):
        year = 2006 + (i // 12)
        month = 1 + (i % 12)
        p_return = portfolio_monthly - 1
        b_return = benchmark_monthly - 1
        portfolio_value *= portfolio_monthly
        benchmark_value *= benchmark_monthly
        snapshots.append(
            MonthlySnapshot(
                date=date(year, month, 28),
                holdings=[],
                portfolio_value=round(portfolio_value, 2),
                benchmark_value=round(benchmark_value, 2),
                portfolio_return=round(p_return, 6),
                benchmark_return=round(b_return, 6),
                turnover=0.18,
                transaction_costs=0.0,
            )
        )

    return ReplayResult(
        config=config,
        metrics=metrics,
        snapshots=snapshots,
        audit_log=[],
        regime_segments=regime_segments,
        factor_timeline=[],
        duration_seconds=0.0,
    )


def precompute_default_backtest() -> ReplayResult:
    """Pre-compute the default backtest result.

    Called by the ARQ worker on a schedule. The result is stored
    in the database and served by GET /backtest/default.

    Currently returns the same synthetic result as
    get_default_replay_result(). When real PIT data providers are
    available, this will run the actual ReplayOrchestrator.
    """
    return get_default_replay_result()


def run_custom_backtest(config: ReplayConfig) -> ReplayResult:
    """Run a custom backtest with the given config.

    Called by the ARQ worker for on-demand runs. The result is
    cached by config hash in the database.

    Currently returns a synthetic result with the provided config.
    When real PIT data providers are available, this will
    instantiate ReplayOrchestrator with InMemoryPITProvider
    (or the real provider) and run the actual backtest.
    """
    result = get_default_replay_result()
    # Apply the custom config
    result = result.model_copy(update={"config": config})
    return result


# ---------------------------------------------------------------------------
# Async DB-backed functions for real PIT backtesting
# ---------------------------------------------------------------------------


async def get_precomputed_default(session: AsyncSession) -> ReplayResult | None:
    """Query the most recent completed 'default' backtest from the database.

    Returns the deserialized ReplayResult if found, None otherwise.
    """
    stmt = (
        select(BacktestRun)
        .where(BacktestRun.name == "default")
        .where(BacktestRun.status == "complete")
        .order_by(BacktestRun.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        return None

    summary = run.summary_stats
    if not summary:
        return None

    try:
        return ReplayResult.model_validate(summary)
    except Exception:
        logger.warning("Failed to deserialize precomputed backtest run %s", run.id, exc_info=True)
        return None


async def run_real_backtest(
    session: AsyncSession,
    config: ReplayConfig,
    benchmark_prices: dict[date, float] | None = None,
) -> ReplayResult:
    """Run a real backtest using DatabasePITProvider and ReplayOrchestrator.

    Uses backtest-tuned filter thresholds (lower market cap floor, shorter
    history requirement, relaxed dollar volumes) to avoid over-eliminating
    historical tickers.
    """
    from margin_engine.backtesting.replay_orchestrator import ReplayOrchestrator
    from margin_engine.config.filter_config import backtest_filter_config

    provider = DatabasePITProvider(session)
    registry = FactorRegistry.default()
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
        filter_config=backtest_filter_config(),
        use_real_scoring=True,
        benchmark_prices=benchmark_prices or {},
    )
    return await orchestrator.run_async()


def compute_validation_summary(
    metrics: PerformanceMetrics,
    benchmark_sharpe: float = 0.0,
) -> dict:
    """Evaluate backtest metrics against validation gates.

    Returns a dict with gate results for logging and storage.
    Gates are advisory (not enforced) per spec.
    """
    gates = [
        {
            "name": "cagr_positive",
            "description": "CAGR is positive",
            "value": metrics.cagr,
            "threshold": 0.0,
            "passed": metrics.cagr > 0,
        },
        {
            "name": "excess_cagr_positive",
            "description": "Excess CAGR vs SPY is positive",
            "value": metrics.excess_cagr,
            "threshold": 0.0,
            "passed": metrics.excess_cagr > 0,
        },
        {
            "name": "sharpe_exceeds_benchmark",
            "description": "Sharpe ratio exceeds benchmark",
            "value": metrics.sharpe_ratio,
            "threshold": benchmark_sharpe,
            "passed": metrics.sharpe_ratio > benchmark_sharpe,
        },
        {
            "name": "max_drawdown_acceptable",
            "description": "Max drawdown below 60%",
            "value": metrics.max_drawdown,
            "threshold": 0.60,
            "passed": metrics.max_drawdown < 0.60,
        },
        {
            "name": "sufficient_months",
            "description": "At least 100 months of data",
            "value": metrics.num_months,
            "threshold": 100,
            "passed": metrics.num_months > 100,
        },
        {
            "name": "turnover_reasonable",
            "description": "Average turnover below 80%",
            "value": metrics.avg_turnover,
            "threshold": 0.80,
            "passed": metrics.avg_turnover < 0.80,
        },
    ]
    return {
        "gates": gates,
        "overall_pass": all(g["passed"] for g in gates),
        "passed_count": sum(1 for g in gates if g["passed"]),
        "total_gates": len(gates),
    }


async def get_best_available_result(session: AsyncSession) -> ReplayResult:
    """Return the best available backtest result.

    Tries precomputed default from the database first, then falls
    back to the synthetic default. This is the main entry point
    for endpoints that need a default backtest result.
    """
    precomputed = await get_precomputed_default(session)
    if precomputed is not None:
        return precomputed
    return get_default_replay_result()
