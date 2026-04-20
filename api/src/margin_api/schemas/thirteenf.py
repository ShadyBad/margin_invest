"""13F holdings API response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class HolderResponse(BaseModel):
    manager_name: str
    tier: str
    shares_held: int
    value_millions: float
    shares_changed: int
    pct_portfolio: float | None = None
    is_new_position: bool = False
    quarters_held: int | None = None


class HoldingsSummary(BaseModel):
    total_holders: int
    curated_holders: int
    net_shares_changed: int
    signal_score: float


class HoldingsResponse(BaseModel):
    ticker: str
    period_of_report: date
    curated_holders: list[HolderResponse]
    other_holders: list[HolderResponse]
    summary: HoldingsSummary


class HoldingsHistoryQuarter(BaseModel):
    period: str
    curated_holders: int
    total_holders: int
    total_shares: int
    net_change: int


class HoldingsHistoryResponse(BaseModel):
    ticker: str
    quarters: list[HoldingsHistoryQuarter]


class ManagerResponse(BaseModel):
    id: int
    name: str
    tier: str
    aum_millions: float | None = None
    total_holdings: int
    top_positions: list[str]
    last_filing: date | None = None
    period_of_report: date | None = None


class PortfolioHolding(BaseModel):
    ticker: str | None = None
    cusip: str
    shares_held: int
    value_millions: float
    pct_portfolio: float
    shares_changed: int
    is_new_position: bool = False


class ChangesSummary(BaseModel):
    new_positions: list[str]
    exited_positions: list[str]
    increased: int
    decreased: int
    unchanged: int


class ManagerPortfolioResponse(BaseModel):
    manager: str
    period_of_report: date
    aum_millions: float | None = None
    holdings: list[PortfolioHolding]
    changes_summary: ChangesSummary


class OverlapEntry(BaseModel):
    ticker: str
    holder_count: int
    curated_count: int


class CrowdedTrade(BaseModel):
    ticker: str
    holder_count: int
    concentration_pct: float
    total_value_millions: float


class OverlapResponse(BaseModel):
    period_of_report: date
    most_held: list[OverlapEntry]
    crowded_trades: list[CrowdedTrade]
    total_managers: int | None = None


class NewPositionEntry(BaseModel):
    ticker: str
    managers: list[str]
    total_new_funds: int
    curated_new_funds: int
    total_value_millions: float


class NewPositionResponse(BaseModel):
    period_of_report: date
    previous_quarter: date
    new_positions: list[NewPositionEntry]


class ClonePerformance(BaseModel):
    return_1y: float | None = None
    cagr_3y: float | None = None
    max_drawdown: float | None = None
    sharpe: float | None = None


class ClonePosition(BaseModel):
    ticker: str
    target_weight: float


class CloneResponse(BaseModel):
    manager: str
    strategy: str
    period_of_report: date
    positions: list[ClonePosition]
    historical_performance: ClonePerformance | None = None


class SectorFlowItem(BaseModel):
    sector: str
    net_shares: int
    direction: str  # "up" | "down" | "flat"


class ConsensusPick(BaseModel):
    ticker: str
    curated_holders: int
    agreement_pct: float


class MarketPulseResponse(BaseModel):
    breadth_pct: float
    breadth_direction: str  # "up" | "down" | "flat"
    sector_flows: list[SectorFlowItem]
    consensus_picks: list[ConsensusPick]
    flow_trend_pct: float
    flow_trend_direction: str  # "up" | "down" | "flat"
    as_of_quarter: str
