"""Backtesting data models and configuration.

Defines the data structures for walk-forward monthly simulation,
portfolio snapshots, performance metrics, and validation gates.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from margin_engine.backtesting.rank_ic import RankICReport
from margin_engine.optimization.models import DROConfig, OptimizationConstraints


class RebalanceFrequency(StrEnum):
    """Portfolio rebalance cadence."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class SelectionMode(StrEnum):
    """Portfolio stock selection strategy."""

    TOP_PERCENTILE = "top_percentile"
    CONVICTION_MOS = "conviction_mos"
    OPTIMIZED = "optimized"


class BacktestConfig(BaseModel):
    """Configuration for a backtest run.

    Controls the simulation period, rebalance frequency, selection criteria,
    transaction cost assumptions, and benchmark index.
    """

    start_date: date = Field(default=date(2015, 1, 1))
    end_date: date = Field(default_factory=date.today)
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY
    top_percentile: float = Field(default=0.05, description="Fraction of scored stocks to select")
    transaction_cost_bps: float = Field(default=10.0, description="Transaction cost in basis pts")
    slippage_bps: float = Field(default=5.0, description="Slippage estimate in basis points")
    benchmark_ticker: str = Field(default="SPY")
    selection_mode: SelectionMode = SelectionMode.TOP_PERCENTILE
    min_conviction_score: float = Field(
        default=79.0, description="Minimum composite_raw_score for CONVICTION_MOS mode"
    )
    min_margin_of_safety: float = Field(
        default=0.20, description="Minimum margin of safety for CONVICTION_MOS mode"
    )
    max_holdings: int = Field(
        default=5, description="Maximum number of holdings for CONVICTION_MOS mode"
    )
    min_conviction_score_high: float = Field(
        default=72.0,
        description="Minimum composite_raw_score for High-conviction tier 2 backfill",
    )
    optimization_constraints: OptimizationConstraints | None = Field(
        default=None, description="Optimization constraints for OPTIMIZED mode"
    )
    dro_config: DROConfig | None = Field(default=None, description="DRO config for OPTIMIZED mode")

    @model_validator(mode="after")
    def validate_date_range(self) -> BacktestConfig:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self

    @property
    def total_cost_bps(self) -> float:
        """Total round-trip cost in basis points (transaction + slippage)."""
        return self.transaction_cost_bps + self.slippage_bps


class HoldingRecord(BaseModel):
    """A single position in the portfolio at a point in time."""

    ticker: str
    weight: float
    entry_price: float
    composite_score: float


class MonthlySnapshot(BaseModel):
    """Portfolio state at the end of a calendar month."""

    date: date
    holdings: list[HoldingRecord]
    portfolio_value: float
    benchmark_value: float
    portfolio_return: float = Field(description="Month-over-month portfolio return")
    benchmark_return: float = Field(description="Month-over-month benchmark return")
    turnover: float = Field(description="Fraction of portfolio traded this month")
    transaction_costs: float
    gross_return: float | None = Field(
        default=None,
        description="Month-over-month return BEFORE transaction costs",
    )

    @model_validator(mode="after")
    def _default_gross_return(self) -> MonthlySnapshot:
        if self.gross_return is None:
            self.gross_return = self.portfolio_return
        return self

    @property
    def excess_return(self) -> float:
        """Portfolio return minus benchmark return for this month."""
        return self.portfolio_return - self.benchmark_return


class PerformanceMetrics(BaseModel):
    """Aggregate performance statistics computed over the full backtest period."""

    cagr: float
    excess_cagr: float = Field(description="CAGR above benchmark")
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float = Field(description="Fraction of months with positive excess return")
    information_ratio: float
    total_return: float
    benchmark_total_return: float
    num_months: int
    avg_turnover: float


class PassThreshold(BaseModel):
    """Minimum thresholds that a backtest must meet to be considered viable.

    Defaults match the design specification:
    - Excess CAGR > 3%
    - Sharpe > 0.7
    - Sortino > 1.0
    - Max drawdown < 35%
    - Win rate > 55%
    - Information ratio > 0.5
    """

    min_excess_cagr: float = 0.03
    min_sharpe: float = 0.7
    min_sortino: float = 1.0
    max_drawdown: float = 0.35
    min_win_rate: float = 0.55
    min_information_ratio: float = 0.5


class ValidationResult(BaseModel):
    """Result of validating backtest metrics against pass thresholds.

    All six checks must pass for overall_pass to be True.
    """

    metrics: PerformanceMetrics
    thresholds: PassThreshold
    excess_cagr_pass: bool
    sharpe_pass: bool
    sortino_pass: bool
    drawdown_pass: bool
    win_rate_pass: bool
    information_ratio_pass: bool

    @property
    def overall_pass(self) -> bool:
        """True only if every individual check passes."""
        return (
            self.excess_cagr_pass
            and self.sharpe_pass
            and self.sortino_pass
            and self.drawdown_pass
            and self.win_rate_pass
            and self.information_ratio_pass
        )

    @property
    def passed_count(self) -> int:
        """Number of individual checks that passed."""
        return sum(
            [
                self.excess_cagr_pass,
                self.sharpe_pass,
                self.sortino_pass,
                self.drawdown_pass,
                self.win_rate_pass,
                self.information_ratio_pass,
            ]
        )

    @property
    def total_checks(self) -> int:
        """Total number of validation checks (always 6)."""
        return 6


class BacktestResult(BaseModel):
    """Complete output of a backtest run."""

    config: BacktestConfig
    snapshots: list[MonthlySnapshot]
    metrics: PerformanceMetrics
    validation: ValidationResult | None = None
    rank_ic_report: RankICReport | None = None
    haircut_metrics: PerformanceMetrics | None = None
    run_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float
