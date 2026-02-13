"""Walk-forward simulation engine for backtesting investment strategies.

Runs a monthly (or quarterly) walk-forward simulation that:
1. Gets the scored stock universe at each rebalance date (point-in-time)
2. Selects the top N% by composite score
3. Equal-weights the selected stocks
4. Calculates turnover and deducts transaction costs
5. Tracks portfolio value and returns vs benchmark
"""

from __future__ import annotations

import math
import time
from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
    RebalanceFrequency,
)

STARTING_CAPITAL = 1_000_000.0


class ScoredStock(BaseModel):
    """A stock with its composite score at a point in time."""

    ticker: str
    composite_score: float
    price: float


@runtime_checkable
class ScoredUniverseProvider(Protocol):
    """Provides the scored universe of stocks at a given point in time."""

    def get_scores(self, as_of_date: date) -> list[ScoredStock]: ...


@runtime_checkable
class BenchmarkProvider(Protocol):
    """Provides benchmark prices at a given point in time."""

    def get_price(self, ticker: str, as_of_date: date) -> float: ...


class WalkForwardSimulator:
    """Runs a walk-forward monthly simulation.

    At each rebalance date:
    1. Get scored universe (point-in-time only)
    2. Select top N% by composite score
    3. Equal-weight the selected stocks
    4. Calculate turnover from previous holdings
    5. Deduct transaction costs (total_cost_bps * turnover)
    6. Track portfolio value and returns
    """

    def __init__(
        self,
        config: BacktestConfig,
        universe_provider: ScoredUniverseProvider,
        benchmark_provider: BenchmarkProvider,
    ) -> None:
        self._config = config
        self._universe_provider = universe_provider
        self._benchmark_provider = benchmark_provider
        self._metrics_calculator = PerformanceCalculator()

    def run(self) -> BacktestResult:
        """Execute the walk-forward simulation and return results."""
        start_time = time.monotonic()

        rebalance_dates = self._generate_rebalance_dates()
        if not rebalance_dates:
            return self._empty_result(time.monotonic() - start_time)

        snapshots: list[MonthlySnapshot] = []
        portfolio_value = STARTING_CAPITAL
        benchmark_value = STARTING_CAPITAL
        prev_holdings: list[HoldingRecord] = []

        # Get initial benchmark price for tracking
        initial_benchmark_price = self._benchmark_provider.get_price(
            self._config.benchmark_ticker, rebalance_dates[0]
        )

        for i, rebal_date in enumerate(rebalance_dates):
            # 1. Get scored universe at this point in time
            scores = self._universe_provider.get_scores(rebal_date)

            # 2. Select top N% by composite score, equal weight
            new_holdings = self._select_holdings(scores)

            # Cache scores as a price lookup map to avoid redundant provider calls
            score_map = {s.ticker: s.price for s in scores}

            # 3. Calculate portfolio value change from previous period
            if i > 0:
                portfolio_value = self._calculate_portfolio_value(
                    prev_holdings, rebal_date, portfolio_value, score_map
                )

            # 4. Calculate turnover
            turnover = self._calculate_turnover(prev_holdings, new_holdings)

            # 5. Calculate transaction costs
            transaction_costs = portfolio_value * (
                turnover * self._config.total_cost_bps / 10_000
            )

            # 6. Deduct transaction costs from portfolio value
            portfolio_value_after_costs = portfolio_value - transaction_costs

            # 7. Track benchmark value
            current_benchmark_price = self._benchmark_provider.get_price(
                self._config.benchmark_ticker, rebal_date
            )
            if initial_benchmark_price > 0:
                benchmark_value = (
                    STARTING_CAPITAL * current_benchmark_price / initial_benchmark_price
                )

            # 8. Calculate returns
            if i == 0:
                portfolio_return = 0.0
                benchmark_return = 0.0
            else:
                prev_portfolio_value = snapshots[i - 1].portfolio_value
                if prev_portfolio_value > 0:
                    portfolio_return = (
                        (portfolio_value_after_costs - prev_portfolio_value) / prev_portfolio_value
                    )
                else:
                    portfolio_return = 0.0

                prev_benchmark_value = snapshots[i - 1].benchmark_value
                if prev_benchmark_value > 0:
                    benchmark_return = (
                        (benchmark_value - prev_benchmark_value) / prev_benchmark_value
                    )
                else:
                    benchmark_return = 0.0

            # Update portfolio value to post-cost value
            portfolio_value = portfolio_value_after_costs

            snapshot = MonthlySnapshot(
                date=rebal_date,
                holdings=new_holdings,
                portfolio_value=portfolio_value,
                benchmark_value=benchmark_value,
                portfolio_return=portfolio_return,
                benchmark_return=benchmark_return,
                turnover=turnover,
                transaction_costs=transaction_costs,
            )
            snapshots.append(snapshot)
            prev_holdings = new_holdings

        metrics = self._metrics_calculator.calculate(snapshots)
        duration = time.monotonic() - start_time

        return BacktestResult(
            config=self._config,
            snapshots=snapshots,
            metrics=metrics,
            duration_seconds=duration,
        )

    def _generate_rebalance_dates(self) -> list[date]:
        """Generate monthly (or quarterly) rebalance dates from start to end.

        Returns the first business day of each month (or quarter) between
        start_date and end_date inclusive.
        """
        dates: list[date] = []
        current = date(self._config.start_date.year, self._config.start_date.month, 1)

        step = 1 if self._config.rebalance_frequency == RebalanceFrequency.MONTHLY else 3

        while current <= self._config.end_date:
            # Find first business day of this month (Mon-Fri)
            first_business_day = self._first_business_day(current.year, current.month)
            if self._config.start_date <= first_business_day <= self._config.end_date:
                dates.append(first_business_day)

            # Advance to next rebalance month
            month = current.month + step
            year = current.year
            while month > 12:
                month -= 12
                year += 1
            current = date(year, month, 1)

        return dates

    @staticmethod
    def _first_business_day(year: int, month: int) -> date:
        """Return the first business day (Mon-Fri) of the given year/month."""
        d = date(year, month, 1)
        # weekday(): Monday=0, Sunday=6
        while d.weekday() >= 5:  # Saturday=5, Sunday=6
            d = d.replace(day=d.day + 1)
        return d

    def _select_holdings(self, scores: list[ScoredStock]) -> list[HoldingRecord]:
        """Select top N% by composite score, equal weight.

        Sorts by composite_score descending, takes top ceil(len * top_percentile)
        stocks, and assigns equal weight (1/N) to each.
        """
        if not scores:
            return []

        # Sort by composite_score descending, then by ticker for determinism
        sorted_scores = sorted(scores, key=lambda s: (-s.composite_score, s.ticker))

        n_select = max(1, math.ceil(len(sorted_scores) * self._config.top_percentile))
        selected = sorted_scores[:n_select]

        weight = 1.0 / len(selected)

        return [
            HoldingRecord(
                ticker=stock.ticker,
                weight=weight,
                entry_price=stock.price,
                composite_score=stock.composite_score,
            )
            for stock in selected
        ]

    @staticmethod
    def _calculate_turnover(
        old_holdings: list[HoldingRecord], new_holdings: list[HoldingRecord]
    ) -> float:
        """Calculate fraction of portfolio that changed (0.0 to 1.0).

        Turnover = (count of changed tickers) / max(count old, count new, 1).
        """
        old_tickers = {h.ticker for h in old_holdings}
        new_tickers = {h.ticker for h in new_holdings}

        if not old_tickers and not new_tickers:
            return 0.0

        # Tickers that were added or removed
        changed = old_tickers.symmetric_difference(new_tickers)
        denominator = max(len(old_tickers), len(new_tickers), 1)

        return min(len(changed) / denominator, 1.0)

    def _calculate_portfolio_value(
        self,
        holdings: list[HoldingRecord],
        current_date: date,
        prev_value: float,
        score_map: dict[str, float] | None = None,
    ) -> float:
        """Calculate portfolio value based on price changes of holdings.

        Each holding's contribution: weight * (current_price / entry_price - 1)
        Total return = sum of weighted returns
        New value = prev_value * (1 + total_return)

        Uses cached score_map for price lookup to avoid redundant provider calls.
        Falls back to benchmark provider if ticker not in score_map.
        """
        if not holdings:
            return prev_value

        total_return = 0.0
        for holding in holdings:
            if score_map and holding.ticker in score_map:
                current_price = score_map[holding.ticker]
            else:
                current_price = self._benchmark_provider.get_price(
                    holding.ticker, current_date
                )
            if holding.entry_price > 0:
                stock_return = (current_price / holding.entry_price) - 1.0
                total_return += holding.weight * stock_return

        return prev_value * (1.0 + total_return)

    @staticmethod
    def _zero_metrics() -> PerformanceMetrics:
        """Return zeroed-out performance metrics."""
        return PerformanceMetrics(
            cagr=0.0,
            excess_cagr=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            information_ratio=0.0,
            total_return=0.0,
            benchmark_total_return=0.0,
            num_months=0,
            avg_turnover=0.0,
        )

    def _empty_result(self, duration: float) -> BacktestResult:
        """Return an empty backtest result when no rebalance dates exist."""
        return BacktestResult(
            config=self._config,
            snapshots=[],
            metrics=self._zero_metrics(),
            duration_seconds=duration,
        )
