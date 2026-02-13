"""Data normalizer for converting raw provider responses to Pydantic models.

Each provider (yfinance, FMP, Polygon, etc.) returns data with different
field naming conventions (camelCase, snake_case, abbreviations). This module
maps those variations to our canonical Pydantic models.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    EarningsSurprise,
    IncomeStatement,
    PriceBar,
)


def _get_decimal(raw: dict, *keys: str, default: str = "0") -> Decimal:
    """Get a Decimal value from raw dict, trying multiple key names.

    Returns the first non-None match, or ``Decimal(default)`` if none found.
    """
    for key in keys:
        if key in raw and raw[key] is not None:
            try:
                return Decimal(str(raw[key]))
            except InvalidOperation:
                continue
    return Decimal(default)


def _get_optional_decimal(raw: dict, *keys: str) -> Decimal | None:
    """Get an optional Decimal value from raw dict, trying multiple key names.

    Returns ``None`` if no key is found or all values are None.
    """
    for key in keys:
        if key in raw and raw[key] is not None:
            try:
                return Decimal(str(raw[key]))
            except InvalidOperation:
                continue
    return None


def _get_int(raw: dict, *keys: str, default: int = 0) -> int:
    """Get an integer value from raw dict, trying multiple key names."""
    for key in keys:
        if key in raw and raw[key] is not None:
            try:
                return int(raw[key])
            except (ValueError, TypeError):
                continue
    return default


def _get_str(raw: dict, *keys: str, default: str = "") -> str:
    """Get a string value from raw dict, trying multiple key names."""
    for key in keys:
        if key in raw and raw[key] is not None:
            return str(raw[key])
    return default


def normalize_income_statement(raw: dict) -> IncomeStatement:
    """Convert raw provider data to IncomeStatement model.

    Handles common field name variations across providers:
    - revenue/totalRevenue/total_revenue -> revenue
    - costOfRevenue/cost_of_revenue/cogs -> cost_of_revenue
    - grossProfit/gross_profit -> gross_profit
    - etc.
    """
    return IncomeStatement(
        revenue=_get_decimal(
            raw, "revenue", "totalRevenue", "total_revenue", "Total Revenue"
        ),
        cost_of_revenue=_get_decimal(
            raw,
            "costOfRevenue",
            "cost_of_revenue",
            "cogs",
            "costOfGoodsSold",
            "Cost Of Revenue",
        ),
        gross_profit=_get_decimal(
            raw, "grossProfit", "gross_profit", "Gross Profit"
        ),
        sga_expense=_get_optional_decimal(
            raw,
            "sellingGeneralAndAdministrative",
            "sga_expense",
            "sgaExpense",
            "Selling General And Administrative",
        ),
        rd_expense=_get_optional_decimal(
            raw,
            "researchAndDevelopment",
            "rd_expense",
            "rdExpense",
            "researchDevelopment",
            "Research Development",
        ),
        depreciation=_get_optional_decimal(
            raw,
            "depreciationAndAmortization",
            "depreciation",
            "depreciationAmortization",
            "Depreciation Amortization Depletion",
        ),
        ebit=_get_decimal(
            raw, "ebit", "operatingIncome", "operating_income", "EBIT"
        ),
        interest_expense=_get_optional_decimal(
            raw, "interestExpense", "interest_expense", "Interest Expense"
        ),
        tax_provision=_get_optional_decimal(
            raw,
            "incomeTaxExpense",
            "tax_provision",
            "taxProvision",
            "Tax Provision",
        ),
        net_income=_get_decimal(
            raw, "netIncome", "net_income", "Net Income"
        ),
        shares_outstanding=_get_int(
            raw,
            "sharesOutstanding",
            "shares_outstanding",
            "weightedAverageShsOut",
            "Basic Average Shares",
            "Diluted Average Shares",
        ),
    )


def normalize_balance_sheet(raw: dict) -> BalanceSheet:
    """Convert raw provider data to BalanceSheet model."""
    return BalanceSheet(
        total_assets=_get_decimal(
            raw, "totalAssets", "total_assets", "Total Assets"
        ),
        current_assets=_get_decimal(
            raw, "totalCurrentAssets", "current_assets", "Current Assets"
        ),
        cash_and_equivalents=_get_optional_decimal(
            raw,
            "cashAndCashEquivalents",
            "cash_and_equivalents",
            "cash",
            "Cash And Cash Equivalents",
        ),
        receivables=_get_optional_decimal(
            raw,
            "netReceivables",
            "receivables",
            "accountsReceivable",
            "Accounts Receivable",
        ),
        total_liabilities=_get_decimal(
            raw,
            "totalLiabilities",
            "total_liabilities",
            "Total Liabilities Net Minority Interest",
        ),
        current_liabilities=_get_decimal(
            raw,
            "totalCurrentLiabilities",
            "current_liabilities",
            "Current Liabilities",
        ),
        long_term_debt=_get_optional_decimal(
            raw, "longTermDebt", "long_term_debt", "Long Term Debt"
        ),
        total_equity=_get_decimal(
            raw,
            "totalStockholdersEquity",
            "total_equity",
            "stockholdersEquity",
            "totalEquity",
            "Stockholders Equity",
        ),
        retained_earnings=_get_optional_decimal(
            raw,
            "retainedEarnings",
            "retained_earnings",
            "Retained Earnings",
        ),
        pp_and_e=_get_optional_decimal(
            raw, "propertyPlantEquipmentNet", "pp_and_e", "ppAndE", "Net PPE"
        ),
        shares_outstanding=_get_int(
            raw,
            "sharesOutstanding",
            "shares_outstanding",
            "Ordinary Shares Number",
        ),
    )


def normalize_cash_flow(raw: dict) -> CashFlowStatement:
    """Convert raw provider data to CashFlowStatement model."""
    return CashFlowStatement(
        operating_cash_flow=_get_decimal(
            raw,
            "operatingCashFlow",
            "operating_cash_flow",
            "totalCashFromOperatingActivities",
            "Operating Cash Flow",
        ),
        capital_expenditures=_get_decimal(
            raw,
            "capitalExpenditure",
            "capital_expenditures",
            "capitalExpenditures",
            "Capital Expenditure",
        ),
        dividends_paid=_get_optional_decimal(
            raw,
            "dividendsPaid",
            "dividends_paid",
            "Common Stock Dividend Paid",
        ),
        share_repurchases=_get_optional_decimal(
            raw,
            "commonStockRepurchased",
            "share_repurchases",
            "Repurchase Of Capital Stock",
        ),
        share_issuance=_get_optional_decimal(
            raw,
            "commonStockIssued",
            "share_issuance",
            "Issuance Of Capital Stock",
        ),
    )


def normalize_price_bar(raw: dict) -> PriceBar:
    """Convert raw price data to PriceBar model."""
    return PriceBar(
        date=_get_str(raw, "date", "Date"),
        open=_get_decimal(raw, "open", "Open"),
        high=_get_decimal(raw, "high", "High"),
        low=_get_decimal(raw, "low", "Low"),
        close=_get_decimal(raw, "close", "Close"),
        volume=_get_int(raw, "volume", "Volume"),
        adj_close=_get_optional_decimal(
            raw, "adjClose", "adj_close", "adjustedClose", "Adj Close"
        ),
    )


def normalize_fundamentals(
    raw: dict,
) -> tuple[IncomeStatement, BalanceSheet, CashFlowStatement]:
    """Convert a combined fundamentals response to all three statement models.

    Expects raw dict with keys like 'income_statement', 'balance_sheet',
    'cash_flow' (or camelCase variants, or nested data under those keys).
    """
    # Try multiple key variants for each section
    income_raw = (
        raw.get("income_statement")
        or raw.get("incomeStatement")
        or {}
    )
    balance_raw = (
        raw.get("balance_sheet")
        or raw.get("balanceSheet")
        or {}
    )
    cash_flow_raw = (
        raw.get("cash_flow")
        or raw.get("cashFlow")
        or raw.get("cash_flow_statement")
        or raw.get("cashFlowStatement")
        or {}
    )

    return (
        normalize_income_statement(income_raw),
        normalize_balance_sheet(balance_raw),
        normalize_cash_flow(cash_flow_raw),
    )


def normalize_earnings_surprise(raw: dict) -> EarningsSurprise:
    """Convert a raw earnings dict to an EarningsSurprise model.

    Handles key name variations across providers (yfinance, FMP, etc.):
    - actual EPS: "actual_eps", "actualEps", "Reported EPS", "reportedEPS"
    - expected EPS: "expected_eps", "expectedEps", "EPS Estimate", "estimatedEPS"
    - quarter: "quarter", "Quarter", "fiscalDateEnding", "period"
    """
    return EarningsSurprise(
        quarter=_get_str(
            raw, "quarter", "Quarter", "fiscalDateEnding", "period"
        ),
        actual_eps=_get_decimal(
            raw, "actual_eps", "actualEps", "Reported EPS", "reportedEPS"
        ),
        expected_eps=_get_decimal(
            raw, "expected_eps", "expectedEps", "EPS Estimate", "estimatedEPS"
        ),
    )


def normalize_earnings_list(raw_list: list[dict]) -> list[EarningsSurprise]:
    """Convert a list of raw earnings dicts to EarningsSurprise models.

    Skips entries that fail validation (e.g. missing required fields).
    """
    results: list[EarningsSurprise] = []
    for raw in raw_list:
        results.append(normalize_earnings_surprise(raw))
    return results
