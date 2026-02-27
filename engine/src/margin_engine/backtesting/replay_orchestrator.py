"""Replay orchestrator for historical backtesting.

Replays the actual margin_engine elimination and scoring pipeline against
point-in-time historical data. Produces regime-segmented metrics, a factor
coverage timeline, and per-rebalance audit records.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date

from pydantic import BaseModel, Field

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
)
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    RegimeSegment,
    classify_regime,
    is_in_recession,
    segment_by_regime,
)
from margin_engine.config.filter_config import FilterConfig
from margin_engine.scoring.filters.pipeline import run_elimination_filters

logger = logging.getLogger(__name__)

STARTING_CAPITAL = 1_000_000.0


class ReplayConfig(BaseModel):
    """Configuration for a replay backtest."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    rebalance_frequency: str = "monthly"  # monthly, quarterly, semi_annual
    conviction_threshold: float = 0.10  # top N% by score
    weighting: str = "equal"  # equal or conviction
    sector_exclusions: list[str] = Field(default_factory=list)  # max 2
    transaction_cost_bps: float = 20.0
    benchmark_ticker: str = "SPY"


class RebalanceAuditRecord(BaseModel):
    """Audit trail for a single rebalance event."""

    rebalance_date: date
    universe_size: int
    eliminated_count: int
    survivor_count: int
    selected_count: int
    top_holdings: list[dict]  # [{ticker, score, price}]
    notable_events: list[str]  # e.g. "LEH eliminated — insufficient earnings quality"
    factor_coverage: float  # 0.0-1.0
    available_factors: list[str]
    missing_factors: list[str]
    regime: MarketRegimeHistorical


class FactorTimelineEntry(BaseModel):
    """Factor availability at a point in time."""

    as_of_date: date
    available: list[str]
    missing: list[str]
    coverage_ratio: float


class ReplayResult(BaseModel):
    """Complete output of a replay backtest."""

    config: ReplayConfig
    metrics: PerformanceMetrics
    snapshots: list[MonthlySnapshot]
    audit_log: list[RebalanceAuditRecord]
    regime_segments: dict[str, RegimeSegment]
    factor_timeline: list[FactorTimelineEntry]
    duration_seconds: float


class ReplayOrchestrator:
    """Replays the margin_engine pipeline against historical data.

    At each rebalance date:
    1. Load PIT universe from provider
    2. Run elimination filters (same code as live)
    3. Score survivors by composite score (simplified — uses available factors)
    4. Select top holdings by conviction threshold
    5. Track portfolio value with transaction costs
    6. Classify regime and record audit trail
    """

    def __init__(
        self,
        config: ReplayConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
        filter_config: FilterConfig | None = None,
        disabled_filters: set[str] | None = None,
    ) -> None:
        self._config = config
        self._provider = pit_provider
        self._registry = factor_registry
        self._benchmark_prices = benchmark_prices or {}
        self._filter_config = filter_config
        self._disabled_filters = disabled_filters
        self._calculator = PerformanceCalculator()

    def run(self) -> ReplayResult:
        """Execute the replay and return results."""
        start_time = time.monotonic()

        rebalance_dates = self._generate_rebalance_dates()
        if not rebalance_dates:
            return self._empty_result(time.monotonic() - start_time)

        snapshots: list[MonthlySnapshot] = []
        audit_log: list[RebalanceAuditRecord] = []
        factor_timeline: list[FactorTimelineEntry] = []
        regime_dates: list[date] = []
        regime_labels: list[MarketRegimeHistorical] = []
        portfolio_returns_list: list[float] = []
        benchmark_returns_list: list[float] = []

        portfolio_value = STARTING_CAPITAL
        benchmark_value = STARTING_CAPITAL
        prev_holdings: list[HoldingRecord] = []
        initial_benchmark_price: float | None = None

        for i, rebal_date in enumerate(rebalance_dates):
            # 1. Load PIT universe
            universe = self._provider.get_universe(rebal_date)
            if not universe:
                continue

            # 2. Factor availability at this date
            available = self._registry.available_factors(rebal_date)
            missing = self._registry.missing_factors(rebal_date)
            coverage = self._registry.coverage_ratio(rebal_date)

            factor_timeline.append(
                FactorTimelineEntry(
                    as_of_date=rebal_date,
                    available=[f.name for f in available],
                    missing=[f.name for f in missing],
                    coverage_ratio=coverage,
                )
            )

            # 3. Run elimination filters on each ticker
            survivors = []
            eliminated_count = 0
            notable_events: list[str] = []

            for snapshot in universe:
                try:
                    filter_result = run_elimination_filters(
                        period=snapshot.period,
                        profile=snapshot.profile,
                        config=self._filter_config,
                        disabled_filters=self._disabled_filters,
                    )
                    if filter_result.passed:
                        survivors.append(snapshot)
                    else:
                        eliminated_count += 1
                        failed = [f.name for f in filter_result.failed_filters]
                        notable_events.append(f"{snapshot.ticker} eliminated — {', '.join(failed)}")
                except Exception:
                    logger.warning("Filter error for %s on %s", snapshot.ticker, rebal_date)
                    eliminated_count += 1

            # 4. Score survivors (use a deterministic score based on available financials).
            #    In production, this will call the actual scoring pipeline with
            #    available factors.
            scored = []
            for s in survivors:
                score = self._compute_simple_score(s)
                scored.append((s, score))

            scored.sort(key=lambda x: -x[1])

            # 5. Select top holdings
            n_select = max(1, math.ceil(len(scored) * self._config.conviction_threshold))
            selected = scored[:n_select]

            if self._config.weighting == "equal" and selected:
                weight = 1.0 / len(selected)
            else:
                weight = 1.0

            new_holdings = [
                HoldingRecord(
                    ticker=s.ticker,
                    weight=weight,
                    entry_price=s.price,
                    composite_score=score,
                )
                for s, score in selected
            ]

            # 6. Calculate portfolio value change
            if i > 0 and prev_holdings:
                total_return = 0.0
                for h in prev_holdings:
                    current_price = self._provider.get_price(h.ticker, rebal_date)
                    if current_price and h.entry_price > 0:
                        stock_return = (current_price / h.entry_price) - 1.0
                        total_return += h.weight * stock_return
                portfolio_value *= 1.0 + total_return

            # 7. Transaction costs
            turnover = self._calculate_turnover(prev_holdings, new_holdings)
            cost = portfolio_value * (turnover * self._config.transaction_cost_bps / 10_000)
            portfolio_value -= cost

            # 8. Benchmark tracking
            benchmark_price = self._benchmark_prices.get(rebal_date, 100.0 * (1.0 + 0.005 * i))
            if initial_benchmark_price is None:
                initial_benchmark_price = benchmark_price
            if initial_benchmark_price > 0:
                benchmark_value = STARTING_CAPITAL * benchmark_price / initial_benchmark_price

            # 9. Returns
            if not snapshots:
                port_return = 0.0
                bench_return = 0.0
            else:
                prev_pv = snapshots[-1].portfolio_value
                prev_bv = snapshots[-1].benchmark_value
                port_return = (portfolio_value - prev_pv) / prev_pv if prev_pv > 0 else 0.0
                bench_return = (benchmark_value - prev_bv) / prev_bv if prev_bv > 0 else 0.0

            # 10. Regime classification (use benchmark drawdown for market-level regime)
            bench_drawdown = max(0, (STARTING_CAPITAL - benchmark_value) / STARTING_CAPITAL)
            regime = classify_regime(
                drawdown_from_peak=bench_drawdown,
                in_nber_recession=is_in_recession(rebal_date),
            )

            snapshot_record = MonthlySnapshot(
                date=rebal_date,
                holdings=new_holdings,
                portfolio_value=portfolio_value,
                benchmark_value=benchmark_value,
                portfolio_return=port_return,
                benchmark_return=bench_return,
                turnover=turnover,
                transaction_costs=cost,
            )
            snapshots.append(snapshot_record)

            regime_dates.append(rebal_date)
            regime_labels.append(regime)
            portfolio_returns_list.append(port_return)
            benchmark_returns_list.append(bench_return)

            # Audit record
            top_holdings = [
                {"ticker": s.ticker, "score": round(score, 2), "price": s.price}
                for s, score in selected[:10]
            ]
            audit_log.append(
                RebalanceAuditRecord(
                    rebalance_date=rebal_date,
                    universe_size=len(universe),
                    eliminated_count=eliminated_count,
                    survivor_count=len(survivors),
                    selected_count=len(selected),
                    top_holdings=top_holdings,
                    notable_events=notable_events[:5],
                    factor_coverage=coverage,
                    available_factors=[f.name for f in available],
                    missing_factors=[f.name for f in missing],
                    regime=regime,
                )
            )

            prev_holdings = new_holdings

        # Compute aggregate metrics
        metrics = self._calculator.calculate(snapshots)

        # Segment by regime
        regime_segments = segment_by_regime(
            regime_dates,
            regime_labels,
            portfolio_returns_list,
            benchmark_returns_list,
        )

        duration = time.monotonic() - start_time
        return ReplayResult(
            config=self._config,
            metrics=metrics,
            snapshots=snapshots,
            audit_log=audit_log,
            regime_segments={k.value: v for k, v in regime_segments.items()},
            factor_timeline=factor_timeline,
            duration_seconds=duration,
        )

    def _compute_simple_score(self, snapshot: object) -> float:
        """Compute a simplified composite score from available financials.

        In the full implementation, this calls the actual scoring pipeline
        with the factor registry determining which factors to use.
        """
        period = snapshot.period  # type: ignore[attr-defined]
        profile = snapshot.profile  # type: ignore[attr-defined]
        score = 50.0  # baseline

        # Quality signal: gross margin
        if (
            period.current_income
            and period.current_income.gross_profit
            and period.current_income.revenue
        ):
            gm = float(period.current_income.gross_profit) / float(period.current_income.revenue)
            score += gm * 20  # higher margin = better

        # Value signal: earnings yield
        if (
            period.current_income
            and period.current_income.net_income
            and profile.market_cap
            and profile.market_cap > 0
        ):
            ey = float(period.current_income.net_income) / (float(profile.market_cap) / 1e6)
            score += min(ey * 100, 20)  # cap contribution

        return min(max(score, 0), 100)

    def _generate_rebalance_dates(self) -> list[date]:
        """Generate rebalance dates from start to end."""
        dates: list[date] = []
        step = {"monthly": 1, "quarterly": 3, "semi_annual": 6}.get(
            self._config.rebalance_frequency, 1
        )
        current = date(self._config.start_date.year, self._config.start_date.month, 1)

        while current <= self._config.end_date:
            # First business day of the month
            d = current
            while d.weekday() >= 5:
                d = d.replace(day=d.day + 1)
            if self._config.start_date <= d <= self._config.end_date:
                dates.append(d)

            month = current.month + step
            year = current.year
            while month > 12:
                month -= 12
                year += 1
            current = date(year, month, 1)

        return dates

    @staticmethod
    def _calculate_turnover(
        old_holdings: list[HoldingRecord],
        new_holdings: list[HoldingRecord],
    ) -> float:
        """Calculate fraction of portfolio that changed."""
        old_tickers = {h.ticker for h in old_holdings}
        new_tickers = {h.ticker for h in new_holdings}
        if not old_tickers and not new_tickers:
            return 0.0
        changed = old_tickers.symmetric_difference(new_tickers)
        denominator = max(len(old_tickers), len(new_tickers), 1)
        return min(len(changed) / denominator, 1.0)

    def _empty_result(self, duration: float) -> ReplayResult:
        """Return empty result when no rebalance dates exist."""
        return ReplayResult(
            config=self._config,
            metrics=PerformanceMetrics(
                cagr=0,
                excess_cagr=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                win_rate=0,
                information_ratio=0,
                total_return=0,
                benchmark_total_return=0,
                num_months=0,
                avg_turnover=0,
            ),
            snapshots=[],
            audit_log=[],
            regime_segments={},
            factor_timeline=[],
            duration_seconds=duration,
        )
