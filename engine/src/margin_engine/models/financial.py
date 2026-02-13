"""Core financial data models for the Margin scoring engine.

All monetary values use Decimal for precision. Computed properties
derive ratios and metrics from raw financial data.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GICSSector(str, Enum):
    """GICS sector classification. 11 sectors."""

    TECHNOLOGY = "Information Technology"
    HEALTHCARE = "Health Care"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    ENERGY = "Energy"
    INDUSTRIALS = "Industrials"
    MATERIALS = "Materials"
    REAL_ESTATE = "Real Estate"
    UTILITIES = "Utilities"
    COMMUNICATION_SERVICES = "Communication Services"

    @property
    def is_excluded_v1(self) -> bool:
        return self in (GICSSector.FINANCIALS, GICSSector.REAL_ESTATE)

    @property
    def is_cyclical(self) -> bool:
        return self in (
            GICSSector.ENERGY,
            GICSSector.MATERIALS,
            GICSSector.INDUSTRIALS,
            GICSSector.CONSUMER_DISCRETIONARY,
        )


class IncomeStatement(BaseModel):
    """Annual or quarterly income statement data."""

    revenue: Decimal
    cost_of_revenue: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    sga_expense: Optional[Decimal] = None
    rd_expense: Optional[Decimal] = None
    depreciation: Optional[Decimal] = None
    ebit: Decimal = Decimal("0")
    interest_expense: Optional[Decimal] = None
    tax_provision: Optional[Decimal] = None
    net_income: Decimal = Decimal("0")
    shares_outstanding: int = 0

    @property
    def gross_margin(self) -> float:
        if self.revenue == 0:
            return 0.0
        return float(self.gross_profit / self.revenue)

    @property
    def net_margin(self) -> float:
        if self.revenue == 0:
            return 0.0
        return float(self.net_income / self.revenue)

    @property
    def effective_tax_rate(self) -> float:
        if self.tax_provision is None or self.ebit == 0:
            return 0.21  # Default US corporate rate
        pretax = self.ebit - (self.interest_expense or Decimal("0"))
        if pretax <= 0:
            return 0.21
        return float(self.tax_provision / pretax)


class BalanceSheet(BaseModel):
    """Annual or quarterly balance sheet data."""

    total_assets: Decimal
    current_assets: Decimal = Decimal("0")
    cash_and_equivalents: Optional[Decimal] = None
    receivables: Optional[Decimal] = None
    total_liabilities: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    long_term_debt: Optional[Decimal] = None
    total_equity: Decimal = Decimal("0")
    retained_earnings: Optional[Decimal] = None
    pp_and_e: Optional[Decimal] = None
    shares_outstanding: int = 0

    @property
    def working_capital(self) -> Decimal:
        return self.current_assets - self.current_liabilities

    @property
    def debt_to_equity(self) -> float:
        if self.total_equity == 0:
            return float("inf")
        return float(self.total_debt / self.total_equity)

    @property
    def current_ratio(self) -> float:
        if self.current_liabilities == 0:
            return float("inf")
        return float(self.current_assets / self.current_liabilities)

    @property
    def total_debt(self) -> Decimal:
        return (self.long_term_debt or Decimal("0")) + self.current_liabilities


class CashFlowStatement(BaseModel):
    """Annual or quarterly cash flow statement data."""

    operating_cash_flow: Decimal = Decimal("0")
    capital_expenditures: Decimal = Decimal("0")  # Usually negative
    dividends_paid: Optional[Decimal] = None  # Usually negative
    share_repurchases: Optional[Decimal] = None  # Usually negative
    share_issuance: Optional[Decimal] = None

    @property
    def free_cash_flow(self) -> Decimal:
        return self.operating_cash_flow + self.capital_expenditures

    @property
    def net_buybacks(self) -> Decimal:
        repurchases = abs(self.share_repurchases or Decimal("0"))
        issuance = abs(self.share_issuance or Decimal("0"))
        return repurchases - issuance


class FinancialPeriod(BaseModel):
    """A complete financial snapshot: current and prior period for YoY comparisons."""

    period_end: str  # ISO date: "2024-09-28"
    filing_date: str  # ISO date: "2024-11-01"

    current_income: IncomeStatement
    prior_income: Optional[IncomeStatement] = None
    current_balance: BalanceSheet
    prior_balance: Optional[BalanceSheet] = None
    current_cash_flow: CashFlowStatement
    prior_cash_flow: Optional[CashFlowStatement] = None

    @property
    def revenue_growth(self) -> Optional[float]:
        if self.prior_income is None or self.prior_income.revenue == 0:
            return None
        return float(
            (self.current_income.revenue - self.prior_income.revenue)
            / self.prior_income.revenue
        )


class PriceBar(BaseModel):
    """Single OHLCV price bar."""

    date: str  # ISO date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_close: Optional[Decimal] = None


class AssetProfile(BaseModel):
    """Static asset metadata and classification."""

    ticker: str
    name: str
    sector: GICSSector
    sub_industry: Optional[str] = None
    market_cap: Decimal = Decimal("0")
    avg_daily_volume: Decimal = Decimal("0")
    years_of_history: int = 0

    @property
    def is_excluded(self) -> bool:
        return self.sector.is_excluded_v1
