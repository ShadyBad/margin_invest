"""Core financial data models for the Margin scoring engine.

All monetary values use Decimal for precision. Computed properties
derive ratios and metrics from raw financial data.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, field_validator


class GICSSector(StrEnum):
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
    sga_expense: Decimal | None = None
    rd_expense: Decimal | None = None
    depreciation: Decimal | None = None
    ebit: Decimal = Decimal("0")
    interest_expense: Decimal | None = None
    tax_provision: Decimal | None = None
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
    cash_and_equivalents: Decimal | None = None
    receivables: Decimal | None = None
    total_liabilities: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    long_term_debt: Decimal | None = None
    short_term_debt: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    retained_earnings: Decimal | None = None
    pp_and_e: Decimal | None = None
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
        """Total financial debt = long-term debt + short-term financial debt.

        Does NOT include non-financial current liabilities (AP, accrued expenses, etc.).
        """
        return (self.long_term_debt or Decimal("0")) + self.short_term_debt


class CashFlowStatement(BaseModel):
    """Annual or quarterly cash flow statement data."""

    operating_cash_flow: Decimal = Decimal("0")
    capital_expenditures: Decimal = Decimal("0")  # Usually negative
    dividends_paid: Decimal | None = None  # Usually negative
    share_repurchases: Decimal | None = None  # Usually negative
    share_issuance: Decimal | None = None

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
    prior_income: IncomeStatement | None = None
    current_balance: BalanceSheet
    prior_balance: BalanceSheet | None = None
    current_cash_flow: CashFlowStatement
    prior_cash_flow: CashFlowStatement | None = None

    @property
    def revenue_growth(self) -> float | None:
        if self.prior_income is None or self.prior_income.revenue == 0:
            return None
        return float(
            (self.current_income.revenue - self.prior_income.revenue) / self.prior_income.revenue
        )


class PriceBar(BaseModel):
    """Single OHLCV price bar."""

    date: str  # ISO date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_close: Decimal | None = None


class EarningsSurprise(BaseModel):
    """Single quarterly earnings surprise for SUE calculation."""

    quarter: str  # e.g. "2024-Q4"
    actual_eps: Decimal
    expected_eps: Decimal

    @property
    def surprise(self) -> Decimal:
        return self.actual_eps - self.expected_eps


class InsiderTransaction(BaseModel):
    """Single insider transaction (SEC Form 4)."""

    date: str  # ISO date
    insider_name: str
    title: str  # "CEO", "CFO", "Director", etc.
    transaction_type: str  # "buy" or "sell"
    shares: int
    price_per_share: Decimal
    value: Decimal
    insider_cik: str | None = None
    is_first_purchase: bool | None = None


class InstitutionalHolding(BaseModel):
    """13F institutional holding snapshot for a single fund."""

    fund_name: str
    quarter: str  # e.g. "2024-Q3"
    shares_held: int
    shares_changed: int  # positive = bought, negative = sold
    is_new_position: bool = False


class AssetProfile(BaseModel):
    """Static asset metadata and classification."""

    ticker: str
    name: str
    sector: GICSSector
    sub_industry: str | None = None
    market_cap: Decimal = Decimal("0")
    avg_daily_volume: Decimal = Decimal("0")
    shares_outstanding: int | None = None
    years_of_history: int = 0


class FinancialHistory(BaseModel):
    """Multi-year financial data for temporal analysis.

    Periods are sorted by period_end ascending on construction.
    """

    ticker: str
    periods: list[FinancialPeriod]

    @field_validator("periods")
    @classmethod
    def validate_periods(cls, v: list[FinancialPeriod]) -> list[FinancialPeriod]:
        if len(v) < 1:
            raise ValueError("FinancialHistory requires at least 1 period")
        return sorted(v, key=lambda p: p.period_end)

    @property
    def years_of_data(self) -> int:
        return len(self.periods)
