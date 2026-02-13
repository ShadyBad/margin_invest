"""Golden test fixture: Apple Inc. FY2024 (10-K filed Nov 1, 2024).

All values sourced from Apple's actual SEC filing.
Used to verify scoring formulas produce correct results against
known real-world data.
"""

from decimal import Decimal

from margin_engine.models import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)

APPLE_PROFILE = AssetProfile(
    ticker="AAPL",
    name="Apple Inc.",
    sector=GICSSector.TECHNOLOGY,
    sub_industry="Technology Hardware, Storage & Peripherals",
    market_cap=Decimal("3500000000000"),  # ~$3.5T
    avg_daily_volume=Decimal("55000000"),
    years_of_history=20,
)

# FY2024 (ended Sept 28, 2024)
APPLE_INCOME_2024 = IncomeStatement(
    revenue=Decimal("391035000000"),
    cost_of_revenue=Decimal("210352000000"),
    gross_profit=Decimal("180683000000"),
    sga_expense=Decimal("26742000000"),
    rd_expense=Decimal("31370000000"),
    depreciation=Decimal("11445000000"),
    ebit=Decimal("122571000000"),
    interest_expense=Decimal("3583000000"),
    tax_provision=Decimal("29749000000"),
    net_income=Decimal("93736000000"),
    shares_outstanding=15408095000,
)

# FY2023 (ended Sept 30, 2023)
APPLE_INCOME_2023 = IncomeStatement(
    revenue=Decimal("383285000000"),
    cost_of_revenue=Decimal("214137000000"),
    gross_profit=Decimal("169148000000"),
    sga_expense=Decimal("24932000000"),
    rd_expense=Decimal("29915000000"),
    depreciation=Decimal("11519000000"),
    ebit=Decimal("114301000000"),
    interest_expense=Decimal("3933000000"),
    tax_provision=Decimal("16741000000"),
    net_income=Decimal("96995000000"),
    shares_outstanding=15460000000,
)

# Balance Sheet FY2024
APPLE_BALANCE_2024 = BalanceSheet(
    total_assets=Decimal("364980000000"),
    current_assets=Decimal("152987000000"),
    cash_and_equivalents=Decimal("29943000000"),
    receivables=Decimal("66243000000"),
    total_liabilities=Decimal("308030000000"),
    current_liabilities=Decimal("176392000000"),
    long_term_debt=Decimal("96811000000"),
    total_equity=Decimal("56950000000"),
    retained_earnings=Decimal("-19154000000"),
    pp_and_e=Decimal("44856000000"),
    shares_outstanding=15408095000,
)

# Balance Sheet FY2023
APPLE_BALANCE_2023 = BalanceSheet(
    total_assets=Decimal("352583000000"),
    current_assets=Decimal("143566000000"),
    cash_and_equivalents=Decimal("29965000000"),
    receivables=Decimal("60932000000"),
    total_liabilities=Decimal("290437000000"),
    current_liabilities=Decimal("145308000000"),
    long_term_debt=Decimal("95281000000"),
    total_equity=Decimal("62146000000"),
    retained_earnings=Decimal("4336000000"),
    pp_and_e=Decimal("43715000000"),
    shares_outstanding=15460000000,
)

# Cash Flow FY2024
APPLE_CASHFLOW_2024 = CashFlowStatement(
    operating_cash_flow=Decimal("118254000000"),
    capital_expenditures=Decimal("-9959000000"),
    dividends_paid=Decimal("-15234000000"),
    share_repurchases=Decimal("-94949000000"),
    share_issuance=Decimal("0"),
)

# Cash Flow FY2023
APPLE_CASHFLOW_2023 = CashFlowStatement(
    operating_cash_flow=Decimal("110543000000"),
    capital_expenditures=Decimal("-10959000000"),
    dividends_paid=Decimal("-15025000000"),
    share_repurchases=Decimal("-77550000000"),
    share_issuance=Decimal("0"),
)

APPLE_PERIOD_2024 = FinancialPeriod(
    period_end="2024-09-28",
    filing_date="2024-11-01",
    current_income=APPLE_INCOME_2024,
    prior_income=APPLE_INCOME_2023,
    current_balance=APPLE_BALANCE_2024,
    prior_balance=APPLE_BALANCE_2023,
    current_cash_flow=APPLE_CASHFLOW_2024,
    prior_cash_flow=APPLE_CASHFLOW_2023,
)

# Pre-computed expected values for verification
EXPECTED = {
    "gross_margin_2024": 0.4621,  # 180683 / 391035
    "gross_margin_2023": 0.4413,  # 169148 / 383285
    "revenue_growth": 0.0202,  # (391035 - 383285) / 383285
    "fcf_2024": 108295000000,  # 118254 - 9959 (millions)
    "net_buyback_2024": 94949000000,
    "working_capital_2024": -23405000000,  # 152987 - 176392 (millions)
    "current_ratio_2024": 0.8673,  # 152987 / 176392
    "roa_2024": 0.2568,  # 93736 / 364980
    "roa_2023": 0.2751,  # 96995 / 352583
}
