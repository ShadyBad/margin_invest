"""Backtest validation gate — orchestrates threshold checks and methodology comparison.

Provides a higher-level ValidationGate that wraps PerformanceCalculator.validate()
and adds methodology comparison logic for deploy decisions.
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    BacktestResult,
    PassThreshold,
    PerformanceMetrics,
    ValidationResult,
)

# The five core metrics used for methodology comparison.
# For each: (attribute name, higher_is_better).
_CORE_METRICS: list[tuple[str, bool]] = [
    ("excess_cagr", True),
    ("sharpe_ratio", True),
    ("sortino_ratio", True),
    ("max_drawdown", False),  # lower drawdown is better
    ("win_rate", True),
]


class MethodologyComparison(BaseModel):
    """Result of comparing old vs new methodology backtest results."""

    old_metrics: PerformanceMetrics
    new_metrics: PerformanceMetrics
    metrics_compared: list[str]  # names of metrics compared
    new_wins: list[str]  # metrics where new is better
    old_wins: list[str]  # metrics where old is better
    ties: list[str]
    new_is_better: bool  # True if new wins >= 3 of 5 core metrics


class ValidationGate:
    """Validates backtest results against pass thresholds and methodology comparisons.

    Pass thresholds (from design spec):
    - CAGR excess vs S&P 500 > 3% annualized
    - Sharpe Ratio > 0.7
    - Sortino Ratio > 1.0
    - Max Drawdown < 35%
    - Win Rate > 55%
    - Information Ratio > 0.5

    For methodology changes: new must beat old on >= 3 of 5 core metrics before deploy.
    The 5 core metrics for comparison: excess_cagr, sharpe_ratio, sortino_ratio,
    max_drawdown, win_rate.
    """

    def __init__(
        self,
        thresholds: PassThreshold | None = None,
        calculator: PerformanceCalculator | None = None,
    ) -> None:
        self._thresholds = thresholds or PassThreshold()
        self._calculator = calculator or PerformanceCalculator()

    def validate(self, metrics: PerformanceMetrics) -> ValidationResult:
        """Check metrics against pass thresholds.

        Delegates to PerformanceCalculator.validate() with the gate's stored thresholds.

        Args:
            metrics: Computed performance metrics to validate.

        Returns:
            ValidationResult with individual and aggregate pass/fail results.
        """
        return self._calculator.validate(metrics, self._thresholds)

    def validate_result(self, result: BacktestResult) -> BacktestResult:
        """Validate a BacktestResult and return it with validation attached.

        Args:
            result: A completed backtest result (with metrics already computed).

        Returns:
            A copy of the BacktestResult with the validation field populated.
        """
        validation = self.validate(result.metrics)
        return result.model_copy(update={"validation": validation})

    def compare_methodologies(
        self,
        old_metrics: PerformanceMetrics,
        new_metrics: PerformanceMetrics,
    ) -> MethodologyComparison:
        """Compare old vs new methodology. New must beat old on >= 3 of 5 core metrics.

        Core metrics (higher is better except max_drawdown where lower is better):
        - excess_cagr
        - sharpe_ratio
        - sortino_ratio
        - max_drawdown (inverted: lower is better)
        - win_rate

        Args:
            old_metrics: Performance metrics from the current/old methodology.
            new_metrics: Performance metrics from the proposed/new methodology.

        Returns:
            MethodologyComparison with detailed win/loss/tie breakdown and
            overall new_is_better verdict.
        """
        metrics_compared: list[str] = []
        new_wins: list[str] = []
        old_wins: list[str] = []
        ties: list[str] = []

        for attr, higher_is_better in _CORE_METRICS:
            metrics_compared.append(attr)
            old_val = getattr(old_metrics, attr)
            new_val = getattr(new_metrics, attr)

            if higher_is_better:
                if new_val > old_val:
                    new_wins.append(attr)
                elif old_val > new_val:
                    old_wins.append(attr)
                else:
                    ties.append(attr)
            else:
                # Lower is better (e.g. max_drawdown)
                if new_val < old_val:
                    new_wins.append(attr)
                elif old_val < new_val:
                    old_wins.append(attr)
                else:
                    ties.append(attr)

        return MethodologyComparison(
            old_metrics=old_metrics,
            new_metrics=new_metrics,
            metrics_compared=metrics_compared,
            new_wins=new_wins,
            old_wins=old_wins,
            ties=ties,
            new_is_better=len(new_wins) >= 3,
        )
