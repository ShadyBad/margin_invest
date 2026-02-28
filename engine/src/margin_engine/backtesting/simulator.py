"""Walk-forward simulation engine for backtesting investment strategies.

Runs a monthly (or quarterly) walk-forward simulation that:
1. Gets the scored stock universe at each rebalance date (point-in-time)
2. Selects the top N% by composite score
3. Equal-weights the selected stocks
4. Calculates turnover and deducts transaction costs
5. Tracks portfolio value and returns vs benchmark
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date
from typing import Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel

from margin_engine.backtesting.cost_model import CostModelConfig, compute_transaction_cost
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
    RebalanceFrequency,
    SelectionMode,
)
from margin_engine.backtesting.rank_ic import compute_rank_ic, compute_rank_ic_report
from margin_engine.backtesting.turnover import enforce_turnover_limit
from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
)
from margin_engine.optimization.alpha_mapper import calibrate_alpha, v4_to_candidates
from margin_engine.optimization.dro_meanvar import optimize_dro_meanvar
from margin_engine.risk.covariance import compute_covariance
from margin_engine.risk.returns import returns_from_price_bars

logger = logging.getLogger(__name__)

STARTING_CAPITAL = 1_000_000.0

# Conservative defaults for cost model when ADV/market_cap unavailable
_DEFAULT_ADV = 50_000_000.0  # $50M average daily volume
_DEFAULT_MARKET_CAP = 10_000_000_000.0  # $10B market cap


class ScoredStock(BaseModel):
    """A stock with its composite score at a point in time."""

    ticker: str
    composite_score: float
    price: float
    margin_of_safety: float | None = None


@runtime_checkable
class ScoredUniverseProvider(Protocol):
    """Provides the scored universe of stocks at a given point in time."""

    def get_scores(self, as_of_date: date) -> list[ScoredStock]: ...


@runtime_checkable
class BenchmarkProvider(Protocol):
    """Provides benchmark prices at a given point in time."""

    def get_price(self, ticker: str, as_of_date: date) -> float: ...


@runtime_checkable
class PriceHistoryProvider(Protocol):
    """Provides historical price bars for a set of tickers."""

    def get_price_bars(
        self, tickers: list[str], as_of_date: date, window_days: int = 252
    ) -> dict[str, list[PriceBar]]: ...


def _stub_factor(name: str = "stub") -> FactorBreakdown:
    """Build a minimal FactorBreakdown for CompositeScore construction.

    Alpha calibration only uses composite_raw_score, not individual factors,
    so we provide stub values.
    """
    return FactorBreakdown(
        factor_name=name,
        weight=1.0,
        sub_scores=[FactorScore(name="stub", raw_value=0.0, percentile_rank=50.0)],
    )


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
        price_history_provider: PriceHistoryProvider | None = None,
        cost_model_config: CostModelConfig | None = None,
    ) -> None:
        self._config = config
        self._universe_provider = universe_provider
        self._benchmark_provider = benchmark_provider
        self._price_history_provider = price_history_provider
        self._cost_model_config = cost_model_config
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
        ic_series: list[float] = []

        # Get initial benchmark price for tracking
        initial_benchmark_price = self._benchmark_provider.get_price(
            self._config.benchmark_ticker, rebalance_dates[0]
        )

        for i, rebal_date in enumerate(rebalance_dates):
            # 1. Get scored universe at this point in time
            scores = self._universe_provider.get_scores(rebal_date)

            # 2. Select holdings based on configured selection mode
            new_holdings = self._select_holdings(scores, prev_holdings, rebal_date=rebal_date)

            # Cache scores as a price lookup map to avoid redundant provider calls
            score_map = {s.ticker: s.price for s in scores}

            # 3. Calculate portfolio value change from previous period
            if i > 0:
                portfolio_value = self._calculate_portfolio_value(
                    prev_holdings, rebal_date, portfolio_value, score_map
                )

            # 4. Calculate turnover
            turnover = self._calculate_turnover(prev_holdings, new_holdings)

            # 5. Calculate transaction costs (non-linear if cost_model_config set)
            if self._cost_model_config and new_holdings:
                transaction_costs = self._compute_nonlinear_costs(
                    prev_holdings, new_holdings, portfolio_value
                )
            else:
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
                gross_return = 0.0
            else:
                prev_portfolio_value = snapshots[i - 1].portfolio_value
                if prev_portfolio_value > 0:
                    portfolio_return = (
                        portfolio_value_after_costs - prev_portfolio_value
                    ) / prev_portfolio_value
                    # Gross return uses pre-cost portfolio_value
                    gross_return = (
                        portfolio_value - prev_portfolio_value
                    ) / prev_portfolio_value
                else:
                    portfolio_return = 0.0
                    gross_return = 0.0

                prev_benchmark_value = snapshots[i - 1].benchmark_value
                if prev_benchmark_value > 0:
                    benchmark_return = (
                        benchmark_value - prev_benchmark_value
                    ) / prev_benchmark_value
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
                gross_return=gross_return,
            )
            snapshots.append(snapshot)

            # Rank IC tracking: compare previous scores to realized returns
            if self._config.selection_mode == SelectionMode.OPTIMIZED and i > 0 and prev_holdings:
                ic = self._compute_period_ic(prev_holdings, score_map)
                if ic is not None:
                    ic_series.append(ic)

            prev_holdings = new_holdings

        metrics = self._metrics_calculator.calculate(snapshots)
        duration = time.monotonic() - start_time

        # Build Rank IC report for OPTIMIZED mode
        rank_ic_report = None
        if self._config.selection_mode == SelectionMode.OPTIMIZED and ic_series:
            rank_ic_report = compute_rank_ic_report(ic_series)

        return BacktestResult(
            config=self._config,
            snapshots=snapshots,
            metrics=metrics,
            rank_ic_report=rank_ic_report,
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

    def _select_holdings(
        self,
        scores: list[ScoredStock],
        prev_holdings: list[HoldingRecord],
        rebal_date: date | None = None,
    ) -> list[HoldingRecord]:
        """Select portfolio holdings based on configured selection mode."""
        if self._config.selection_mode == SelectionMode.OPTIMIZED:
            return self._select_by_optimization(scores, prev_holdings, rebal_date)
        if self._config.selection_mode == SelectionMode.CONVICTION_MOS:
            return self._select_by_conviction_mos(scores, prev_holdings)
        return self._select_by_top_percentile(scores)

    def _select_by_top_percentile(self, scores: list[ScoredStock]) -> list[HoldingRecord]:
        """Select top N% by composite score, equal weight.

        Sorts by composite_score descending, takes top ceil(len * top_percentile)
        stocks, and assigns equal weight (1/N) to each.
        """
        if not scores:
            return []

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

    def _select_by_conviction_mos(
        self, scores: list[ScoredStock], prev_holdings: list[HoldingRecord]
    ) -> list[HoldingRecord]:
        """Select stocks using two-tier precedence fill.

        Tier 1: Exceptional conviction (score >= min_conviction_score) with MoS above threshold.
        Tier 2: High conviction (score >= min_conviction_score_high) with MoS above threshold.

        Takes all tier 1 first (up to max_holdings), then fills remaining slots
        with tier 2 candidates. If zero eligible across both tiers, returns
        prev_holdings unchanged (hold-through).
        """

        def is_mos_eligible(s: ScoredStock) -> bool:
            return (
                s.margin_of_safety is not None
                and s.margin_of_safety > self._config.min_margin_of_safety
            )

        eligible_exceptional = [
            s
            for s in scores
            if s.composite_score >= self._config.min_conviction_score and is_mos_eligible(s)
        ]
        eligible_high = [
            s
            for s in scores
            if self._config.min_conviction_score_high
            <= s.composite_score
            < self._config.min_conviction_score
            and is_mos_eligible(s)
        ]

        def sort_key(s):
            return (-s.composite_score, -(s.margin_of_safety or 0), s.ticker)

        eligible_exceptional.sort(key=sort_key)
        eligible_high.sort(key=sort_key)

        max_h = self._config.max_holdings
        selected_stocks = eligible_exceptional[:max_h]
        if len(selected_stocks) < max_h:
            remaining = max_h - len(selected_stocks)
            selected_stocks += eligible_high[:remaining]

        if not selected_stocks:
            return prev_holdings

        weight = 1.0 / len(selected_stocks)
        return [
            HoldingRecord(
                ticker=stock.ticker,
                weight=weight,
                entry_price=stock.price,
                composite_score=stock.composite_score,
            )
            for stock in selected_stocks
        ]

    def _select_by_optimization(
        self,
        scores: list[ScoredStock],
        prev_holdings: list[HoldingRecord],
        rebal_date: date | None = None,
    ) -> list[HoldingRecord]:
        """Select holdings using DRO mean-variance optimization.

        Steps:
        1. Build CompositeScore objects from ScoredStock (for alpha calibration)
        2. calibrate_alpha() -> expected alphas
        3. Get price history -> return matrix -> covariance
        4. v4_to_candidates() -> candidates for optimizer
        5. optimize_dro_meanvar() -> optimal weights
        6. enforce_turnover_limit() if previous holdings exist
        7. Build HoldingRecord list with optimized (non-equal) weights

        Falls back to _select_by_top_percentile() if:
        - price_history_provider is None
        - Not enough price data for covariance
        - Optimizer returns infeasible solution
        """
        if not scores or self._price_history_provider is None or rebal_date is None:
            return self._select_by_top_percentile(scores)

        try:
            # 1. Build stub CompositeScore objects for alpha calibration
            composites = self._scores_to_composites(scores)
            if len(composites) < 2:
                return self._select_by_top_percentile(scores)

            # 2. Calibrate expected alphas
            calibrated_alphas = calibrate_alpha(composites)

            # 3. Get price history and compute covariance
            tickers = [s.ticker for s in scores]
            price_data = self._price_history_provider.get_price_bars(
                tickers, rebal_date, window_days=252
            )
            if not price_data or len(price_data) < 2:
                return self._select_by_top_percentile(scores)

            returns_matrix, valid_tickers = returns_from_price_bars(price_data, window_days=252)
            if len(valid_tickers) < 2 or returns_matrix.shape[0] < 30:
                return self._select_by_top_percentile(scores)

            cov_result = compute_covariance(returns_matrix, valid_tickers)

            # 4. Build candidates for the optimizer
            v4_dicts = [
                {"ticker": s.ticker, "opportunity_type": "unknown", "conviction": "medium"}
                for s in scores
                if s.ticker in set(valid_tickers)
            ]
            # Filter composites to valid tickers only
            valid_set = set(valid_tickers)
            filtered_composites = [c for c in composites if c.ticker in valid_set]
            filtered_alphas = {t: a for t, a in calibrated_alphas.items() if t in valid_set}

            candidates = v4_to_candidates(v4_dicts, filtered_composites, filtered_alphas)
            if not candidates:
                return self._select_by_top_percentile(scores)

            # 5. Optimize
            constraints = self._config.optimization_constraints
            dro_config = self._config.dro_config
            optimized = optimize_dro_meanvar(
                candidates,
                cov_result.matrix,
                list(valid_tickers),
                constraints=constraints,
                dro_config=dro_config,
            )

            if optimized.solver_status != "optimal" or not optimized.weights:
                logger.warning("Optimizer returned %s, falling back", optimized.solver_status)
                return self._select_by_top_percentile(scores)

            # 6. Enforce turnover constraint
            new_weights = optimized.weights
            if prev_holdings:
                old_weights = {h.ticker: h.weight for h in prev_holdings}
                max_turnover = 0.30
                if constraints:
                    max_turnover = constraints.max_turnover
                new_weights = enforce_turnover_limit(old_weights, new_weights, max_turnover)

            # 7. Build HoldingRecord list with optimized weights
            price_map = {s.ticker: s.price for s in scores}
            score_map = {s.ticker: s.composite_score for s in scores}
            holdings = [
                HoldingRecord(
                    ticker=ticker,
                    weight=weight,
                    entry_price=price_map.get(ticker, 0.0),
                    composite_score=score_map.get(ticker, 0.0),
                )
                for ticker, weight in new_weights.items()
                if weight > 1e-6
            ]

            if not holdings:
                return self._select_by_top_percentile(scores)

            return holdings

        except Exception:
            logger.exception("Optimization failed, falling back to top percentile")
            return self._select_by_top_percentile(scores)

    @staticmethod
    def _scores_to_composites(scores: list[ScoredStock]) -> list[CompositeScore]:
        """Convert ScoredStock objects to minimal CompositeScore for alpha calibration."""
        composites = []
        for s in scores:
            composites.append(
                CompositeScore(
                    ticker=s.ticker,
                    composite_percentile=s.composite_score,
                    composite_raw_score=s.composite_score,
                    quality=_stub_factor("quality"),
                    value=_stub_factor("value"),
                    momentum=_stub_factor("momentum"),
                    filters_passed=[
                        FilterResult(name="stub", passed=True, value=1.0, threshold=0.0)
                    ],
                    data_coverage=1.0,
                )
            )
        return composites

    def _compute_nonlinear_costs(
        self,
        old_holdings: list[HoldingRecord],
        new_holdings: list[HoldingRecord],
        portfolio_value: float,
    ) -> float:
        """Compute non-linear transaction costs for a rebalance.

        Iterates each holding, computes trade delta, and applies the non-linear
        cost model per trade. Uses conservative defaults for ADV and market_cap
        since those aren't available in ScoredStock.
        """
        old_map = {h.ticker: h.weight for h in old_holdings}
        new_map = {h.ticker: h.weight for h in new_holdings}
        all_tickers = set(old_map) | set(new_map)

        total_cost = 0.0
        for ticker in all_tickers:
            old_w = old_map.get(ticker, 0.0)
            new_w = new_map.get(ticker, 0.0)
            delta = abs(new_w - old_w)
            if delta < 1e-8:
                continue

            trade_value = portfolio_value * delta
            cost = compute_transaction_cost(
                trade_value=trade_value,
                adv=_DEFAULT_ADV,
                market_cap=_DEFAULT_MARKET_CAP,
                config=self._cost_model_config,
            )
            total_cost += trade_value * cost.total_bps / 10_000

        return total_cost

    @staticmethod
    def _compute_period_ic(
        prev_holdings: list[HoldingRecord],
        current_prices: dict[str, float],
    ) -> float | None:
        """Compute Rank IC for one period: prev composite_score vs realized return."""
        predicted = []
        realized = []
        for h in prev_holdings:
            if h.ticker in current_prices and h.entry_price > 0:
                predicted.append(h.composite_score)
                realized.append(current_prices[h.ticker] / h.entry_price - 1.0)

        if len(predicted) < 3:
            return None

        return compute_rank_ic(np.array(predicted), np.array(realized))

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
                current_price = self._benchmark_provider.get_price(holding.ticker, current_date)
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
