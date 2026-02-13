"""Backtest API request and response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class BacktestConfigRequest(BaseModel):
    """Request body for triggering a backtest."""

    start_date: date = Field(default=date(2015, 1, 1))
    end_date: date | None = None  # defaults to today
    rebalance_frequency: str = "monthly"  # monthly or quarterly
    top_percentile: float = Field(default=0.05, gt=0, le=1.0)
    transaction_cost_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    benchmark_ticker: str = "SPY"


class MetricsResponse(BaseModel):
    """Performance metrics response."""

    cagr: float
    excess_cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    information_ratio: float
    total_return: float
    benchmark_total_return: float
    num_months: int
    avg_turnover: float


class ValidationCheckResponse(BaseModel):
    """Individual validation check result."""

    name: str
    threshold: float
    actual: float
    passed: bool


class ValidationResponse(BaseModel):
    """Validation gate response."""

    overall_pass: bool
    passed_count: int
    total_checks: int
    checks: list[ValidationCheckResponse]


class BacktestResultResponse(BaseModel):
    """Full backtest result response."""

    config: BacktestConfigRequest
    metrics: MetricsResponse
    validation: ValidationResponse | None = None
    num_snapshots: int
    run_at: datetime
    duration_seconds: float


class BacktestSummaryResponse(BaseModel):
    """Summary for listing multiple backtests."""

    id: str
    run_at: datetime
    config: BacktestConfigRequest
    overall_pass: bool | None
    excess_cagr: float
    sharpe_ratio: float


class BacktestListResponse(BaseModel):
    """List of backtest summaries."""

    results: list[BacktestSummaryResponse]
    total: int
