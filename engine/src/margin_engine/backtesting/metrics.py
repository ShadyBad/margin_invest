"""Performance metrics calculator for backtesting.

Computes CAGR, Sharpe, Sortino, max drawdown, win rate, and information ratio
from a series of monthly portfolio snapshots. All calculations are pure math
with no external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import math

from margin_engine.backtesting.models import (
    MonthlySnapshot,
    PassThreshold,
    PerformanceMetrics,
    ValidationResult,
)

# Minimum threshold for standard deviation / tracking error to avoid
# division by near-zero values caused by floating-point arithmetic.
_EPS = 1e-12


class PerformanceCalculator:
    """Computes performance metrics from a series of monthly snapshots.

    All calculations are pure math -- deterministic with no external dependencies.
    """

    def __init__(self, risk_free_rate: float = 0.04) -> None:
        self._risk_free_rate = risk_free_rate

    def calculate(self, snapshots: list[MonthlySnapshot]) -> PerformanceMetrics:
        """Compute all performance metrics from monthly snapshots.

        Args:
            snapshots: Chronologically ordered list of monthly snapshots.
                       Must contain at least one snapshot.

        Returns:
            Fully populated PerformanceMetrics with all computed fields.
        """
        if not snapshots:
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
                gross_cagr=0.0,
                gross_sharpe=0.0,
                gross_max_drawdown=0.0,
                cost_drag_bps=0.0,
            )

        num_months = len(snapshots)
        portfolio_returns = [s.portfolio_return for s in snapshots]
        benchmark_returns = [s.benchmark_return for s in snapshots]
        portfolio_values = [s.portfolio_value for s in snapshots]

        # Total return ratios (cumulative product of 1+r)
        portfolio_total_ratio = math.prod(1.0 + r for r in portfolio_returns)
        benchmark_total_ratio = math.prod(1.0 + r for r in benchmark_returns)

        years = num_months / 12.0

        portfolio_cagr = self._cagr(portfolio_total_ratio, years)
        benchmark_cagr = self._cagr(benchmark_total_ratio, years)
        excess_cagr = portfolio_cagr - benchmark_cagr

        risk_free_monthly = self._risk_free_rate / 12.0

        sharpe = self._sharpe(portfolio_returns, risk_free_monthly)
        sortino = self._sortino(portfolio_returns, risk_free_monthly)
        max_dd = self._max_drawdown(portfolio_values)
        ir = self._information_ratio(portfolio_returns, benchmark_returns)

        # Win rate: fraction of months where portfolio beat benchmark
        wins = sum(1 for pr, br in zip(portfolio_returns, benchmark_returns) if pr > br)
        win_rate = wins / num_months

        avg_turnover = sum(s.turnover for s in snapshots) / num_months

        # Gross metrics (from pre-cost returns)
        gross_returns = [s.gross_return for s in snapshots]
        gross_total_ratio = math.prod(1.0 + r for r in gross_returns)
        gross_cagr = self._cagr(gross_total_ratio, years)
        gross_sharpe = self._sharpe(gross_returns, risk_free_monthly)

        # Gross portfolio values (reconstruct from gross returns for max drawdown)
        gross_values = [portfolio_values[0]] if portfolio_values else []
        gv = gross_values[0] if gross_values else 0.0
        for gr in gross_returns[1:]:
            gv = gv * (1.0 + gr)
            gross_values.append(gv)
        gross_max_dd = self._max_drawdown(gross_values) if len(gross_values) >= 2 else 0.0

        cost_drag = (gross_cagr - portfolio_cagr) * 10_000

        return PerformanceMetrics(
            cagr=portfolio_cagr,
            excess_cagr=excess_cagr,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            information_ratio=ir,
            total_return=portfolio_total_ratio - 1.0,
            benchmark_total_return=benchmark_total_ratio - 1.0,
            num_months=num_months,
            avg_turnover=avg_turnover,
            gross_cagr=gross_cagr,
            gross_sharpe=gross_sharpe,
            gross_max_drawdown=gross_max_dd,
            cost_drag_bps=max(cost_drag, 0.0),
        )

    def validate(
        self,
        metrics: PerformanceMetrics,
        thresholds: PassThreshold | None = None,
    ) -> ValidationResult:
        """Check metrics against pass thresholds.

        Args:
            metrics: Computed performance metrics to validate.
            thresholds: Custom thresholds, or None to use defaults.

        Returns:
            ValidationResult with individual and aggregate pass/fail results.
        """
        if thresholds is None:
            thresholds = PassThreshold()

        return ValidationResult(
            metrics=metrics,
            thresholds=thresholds,
            excess_cagr_pass=metrics.excess_cagr >= thresholds.min_excess_cagr,
            sharpe_pass=metrics.sharpe_ratio >= thresholds.min_sharpe,
            sortino_pass=metrics.sortino_ratio >= thresholds.min_sortino,
            drawdown_pass=metrics.max_drawdown <= thresholds.max_drawdown,
            win_rate_pass=metrics.win_rate >= thresholds.min_win_rate,
            information_ratio_pass=metrics.information_ratio >= thresholds.min_information_ratio,
        )

    @staticmethod
    def _cagr(total_return_ratio: float, years: float) -> float:
        """Compound annual growth rate.

        Args:
            total_return_ratio: Final value / initial value (e.g. 1.5 for 50% gain).
            years: Duration in years.

        Returns:
            Annualized growth rate as a decimal (e.g. 0.10 for 10%).
        """
        if years <= 0 or total_return_ratio <= 0:
            return 0.0
        return total_return_ratio ** (1.0 / years) - 1.0

    @staticmethod
    def _sharpe(returns: list[float], risk_free_monthly: float) -> float:
        """Annualized Sharpe ratio.

        Args:
            returns: Monthly portfolio returns.
            risk_free_monthly: Monthly risk-free rate (annual / 12).

        Returns:
            Annualized Sharpe ratio, or 0.0 if fewer than 2 data points
            or standard deviation is zero.
        """
        if len(returns) < 2:
            return 0.0

        excess = [r - risk_free_monthly for r in returns]
        n = len(excess)
        mean_excess = sum(excess) / n
        variance = sum((x - mean_excess) ** 2 for x in excess) / (n - 1)
        std_excess = math.sqrt(variance)

        if std_excess < _EPS:
            return 0.0

        return (mean_excess / std_excess) * math.sqrt(12)

    @staticmethod
    def _sortino(returns: list[float], risk_free_monthly: float) -> float:
        """Annualized Sortino ratio.

        Uses downside deviation (only negative excess returns) rather than
        total standard deviation.

        Args:
            returns: Monthly portfolio returns.
            risk_free_monthly: Monthly risk-free rate (annual / 12).

        Returns:
            Annualized Sortino ratio, or 0.0 if fewer than 2 data points
            or downside deviation is zero.
        """
        if len(returns) < 2:
            return 0.0

        excess = [r - risk_free_monthly for r in returns]
        n = len(excess)
        mean_excess = sum(excess) / n

        # Downside deviation uses full-sample denominator (n, not n-1)
        # per Sortino & Price (1994). This differs from Sharpe which uses n-1.
        downside_sq = [min(x, 0.0) ** 2 for x in excess]
        downside_deviation = math.sqrt(sum(downside_sq) / n)

        if downside_deviation < _EPS:
            return 0.0

        return (mean_excess / downside_deviation) * math.sqrt(12)

    @staticmethod
    def _max_drawdown(values: list[float]) -> float:
        """Maximum drawdown from peak.

        Args:
            values: Sequence of portfolio values (e.g. dollar amounts).

        Returns:
            Maximum drawdown as a positive fraction (e.g. 0.25 for 25% drawdown),
            or 0.0 if the sequence has fewer than 2 values.
        """
        if len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    @staticmethod
    def _information_ratio(portfolio_returns: list[float], benchmark_returns: list[float]) -> float:
        """Annualized information ratio.

        Args:
            portfolio_returns: Monthly portfolio returns.
            benchmark_returns: Monthly benchmark returns.

        Returns:
            Annualized information ratio, or 0.0 if fewer than 2 data points
            or tracking error is zero.
        """
        if len(portfolio_returns) < 2:
            return 0.0

        active = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        n = len(active)
        mean_active = sum(active) / n
        variance = sum((x - mean_active) ** 2 for x in active) / (n - 1)
        tracking_error = math.sqrt(variance) * math.sqrt(12)

        if tracking_error < _EPS:
            return 0.0

        return (mean_active * 12) / tracking_error


def run_sensitivity_analysis(
    snapshots: list[MonthlySnapshot],
    multipliers: list[float] | None = None,
    risk_free_rate: float = 0.04,
) -> list[dict[str, float]]:
    """Recompute performance metrics at different cost multiplier levels.

    Takes the gross_return and transaction_costs from each snapshot, scales
    costs by each multiplier, and recomputes net returns + metrics.

    Args:
        snapshots: Original snapshots with gross_return and transaction_costs populated.
        multipliers: Cost multiplier levels (default [1.0, 2.0, 3.0]).
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        List of dicts, one per multiplier, with keys:
        multiplier, cagr, sharpe, max_drawdown, cost_drag_bps.
    """
    if multipliers is None:
        multipliers = [1.0, 2.0, 3.0]

    if not snapshots:
        return [
            {
                "multiplier": m,
                "cagr": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "cost_drag_bps": 0.0,
            }
            for m in multipliers
        ]

    # Extract gross returns and dollar costs from snapshots
    gross_returns = [s.gross_return for s in snapshots]
    costs_dollars = [s.transaction_costs for s in snapshots]

    # Derive initial portfolio value from the first snapshot
    first = snapshots[0]
    if abs(1.0 + first.portfolio_return) > _EPS:
        initial_pv = first.portfolio_value / (1.0 + first.portfolio_return)
    else:
        initial_pv = first.portfolio_value

    # Compute gross CAGR (costs at 0x) for cost_drag calculation
    num_months = len(snapshots)
    years = num_months / 12.0
    gross_total_ratio = math.prod(1.0 + r for r in gross_returns)
    gross_cagr = PerformanceCalculator._cagr(gross_total_ratio, years)

    risk_free_monthly = risk_free_rate / 12.0

    results: list[dict[str, float]] = []

    for m in multipliers:
        pv = initial_pv
        net_returns: list[float] = []
        portfolio_values: list[float] = []

        for i in range(num_months):
            gross_pv = pv * (1.0 + gross_returns[i])
            adjusted_cost = costs_dollars[i] * m
            net_pv = gross_pv - adjusted_cost
            net_return = (net_pv - pv) / pv if abs(pv) > _EPS else 0.0
            net_returns.append(net_return)
            pv = net_pv
            portfolio_values.append(pv)

        # Compute metrics from the adjusted return series
        total_ratio = math.prod(1.0 + r for r in net_returns)
        cagr = PerformanceCalculator._cagr(total_ratio, years)
        sharpe = PerformanceCalculator._sharpe(net_returns, risk_free_monthly)
        max_dd = PerformanceCalculator._max_drawdown(portfolio_values)

        cost_drag_bps = (gross_cagr - cagr) * 10_000

        results.append(
            {
                "multiplier": m,
                "cagr": cagr,
                "sharpe": sharpe,
                "max_drawdown": max_dd,
                "cost_drag_bps": max(cost_drag_bps, 0.0),
            }
        )

    return results
