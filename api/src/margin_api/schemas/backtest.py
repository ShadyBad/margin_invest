"""Backtest API request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator


class BacktestConfigRequest(BaseModel):
    """Request body for triggering a backtest."""

    start_date: date = Field(default=date(2015, 1, 1))
    end_date: date | None = None  # defaults to today
    rebalance_frequency: str = "monthly"  # monthly or quarterly
    top_percentile: float = Field(default=0.05, gt=0, le=1.0)
    transaction_cost_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    benchmark_ticker: str = "SPY"
    selection_mode: str = "top_percentile"
    min_conviction_score: float = Field(default=79.0, ge=0, le=100)
    min_margin_of_safety: float = Field(default=0.20, ge=-1.0, le=1.0)
    max_holdings: int = Field(default=5, ge=1, le=50)
    min_conviction_score_high: float = Field(default=72.0, ge=0, le=100)


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
    gross_cagr: float = 0.0
    gross_sharpe: float = 0.0
    gross_max_drawdown: float = 0.0
    cost_drag_bps: float = 0.0


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


# ---------------------------------------------------------------------------
# New replay-based backtest schemas (Task 8)
# ---------------------------------------------------------------------------


class ReplayConfigRequest(BaseModel):
    """Request for a custom replay backtest."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date | None = None
    rebalance_frequency: str = Field(
        default="monthly",
        pattern="^(monthly|quarterly|semi_annual)$",
    )
    conviction_threshold: float = Field(default=0.10, gt=0, le=0.50)
    weighting: str = Field(
        default="equal",
        pattern="^(equal|conviction)$",
    )
    sector_exclusions: list[str] = Field(default_factory=list, max_length=2)
    transaction_cost_bps: float = Field(default=20.0, ge=0)
    seed: int | None = None

    @model_validator(mode="after")
    def validate_constraints(self) -> Self:
        if len(self.sector_exclusions) > 2:
            raise ValueError("Maximum 2 sector exclusions allowed")
        return self


class BacktestTeaserResponse(BaseModel):
    """Teaser metrics for free users."""

    ticker: str | None = None
    model_return: float
    benchmark_return: float
    max_drawdown: float
    benchmark_max_drawdown: float
    start_date: date
    end_date: date


class RegimeSegmentResponse(BaseModel):
    """Regime-segmented performance."""

    regime: str
    num_months: int
    total_return: float
    benchmark_return: float
    max_drawdown: float


class AuditRecordResponse(BaseModel):
    """Single rebalance audit entry."""

    rebalance_date: date
    universe_size: int
    eliminated_count: int
    survivor_count: int
    selected_count: int
    top_holdings: list[dict]
    notable_events: list[str]
    factor_coverage: float
    regime: str


class FactorTimelineResponse(BaseModel):
    """Factor availability at a point in time."""

    as_of_date: date
    available: list[str]
    missing: list[str]
    coverage_ratio: float


class FailurePeriodResponse(BaseModel):
    """A worst-performing rebalance period."""

    rebalance_date: date
    portfolio_return: float
    benchmark_return: float
    relative_underperformance: float
    holdings: list[dict]
    regime: str
    regime_context: str


class CostSensitivityRow(BaseModel):
    """A single row in the cost sensitivity analysis."""

    multiplier: float
    cagr: float
    sharpe: float
    max_drawdown: float
    cost_drag_bps: float


class SensitivityResponse(BaseModel):
    """Cost sensitivity analysis across multiplier levels."""

    rows: list[CostSensitivityRow]


class CapacityRow(BaseModel):
    """A single row in the capacity analysis."""

    aum: float
    cagr: float
    sharpe: float
    avg_impact_bps: float


class CapacityResponse(BaseModel):
    """Strategy capacity analysis across AUM levels."""

    rows: list[CapacityRow]
    breakeven_aum: float | None


class CostValidationResponse(BaseModel):
    """Academic benchmark validation of cost assumptions."""

    model_cost_bps: float
    benchmark_range_bps: list[float]
    status: str
    source: str


class FullBacktestResponse(BaseModel):
    """Full backtest result for pro users."""

    config: ReplayConfigRequest
    metrics: MetricsResponse
    regime_segments: list[RegimeSegmentResponse]
    audit_log: list[AuditRecordResponse]
    factor_timeline: list[FactorTimelineResponse]
    failure_audit: list[FailurePeriodResponse]
    equity_curve: list[dict]
    walk_forward_note: str
    honesty_disclosure: str
    sensitivity: SensitivityResponse | None = None
    capacity: CapacityResponse | None = None
    cost_validation: CostValidationResponse | None = None


# ---------------------------------------------------------------------------
# Shadow portfolio schemas (Task 9)
# ---------------------------------------------------------------------------


class ShadowSnapshotResponse(BaseModel):
    """A single shadow portfolio snapshot."""

    as_of_date: date
    portfolio_value: float
    total_return: float | None
    num_positions: int
    positions: list[dict] | None = None


class ShadowPortfolioResponse(BaseModel):
    """Shadow portfolio summary for the API."""

    start_date: date
    snapshots: list[ShadowSnapshotResponse]
    total_return: float
    max_drawdown: float
    num_days: int
    cannot_be_backdated: bool = True


# ---------------------------------------------------------------------------
# Portfolio-level teaser schemas
# ---------------------------------------------------------------------------


class EquityCurvePoint(BaseModel):
    """Single month in the equity curve."""

    month: str  # "YYYY-MM" format
    portfolio: float
    benchmark: float


class PortfolioTeaserResponse(BaseModel):
    """Portfolio-level teaser for the landing page."""

    model_return: float
    benchmark_return: float
    max_drawdown: float
    sharpe_ratio: float
    num_months: int
    start_date: date
    end_date: date
    equity_curve: list[EquityCurvePoint]
