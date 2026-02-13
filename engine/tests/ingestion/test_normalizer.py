"""Tests for data normalizer that converts raw provider data to Pydantic models."""

from __future__ import annotations

from decimal import Decimal

from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_earnings_list,
    normalize_earnings_surprise,
    normalize_fundamentals,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    EarningsSurprise,
    IncomeStatement,
    PriceBar,
)


class TestNormalizeIncomeStatementCamelCase:
    """Test normalizing income statement from camelCase fields (FMP/yfinance style)."""

    def test_camel_case_fields(self):
        raw = {
            "totalRevenue": 394328000000,
            "costOfRevenue": 223546000000,
            "grossProfit": 170782000000,
            "sellingGeneralAndAdministrative": 24932000000,
            "researchAndDevelopment": 29915000000,
            "depreciationAndAmortization": 11519000000,
            "operatingIncome": 114301000000,
            "interestExpense": 3933000000,
            "incomeTaxExpense": 16741000000,
            "netIncome": 96995000000,
            "sharesOutstanding": 15460000000,
        }
        stmt = normalize_income_statement(raw)

        assert isinstance(stmt, IncomeStatement)
        assert stmt.revenue == Decimal("394328000000")
        assert stmt.cost_of_revenue == Decimal("223546000000")
        assert stmt.gross_profit == Decimal("170782000000")
        assert stmt.sga_expense == Decimal("24932000000")
        assert stmt.rd_expense == Decimal("29915000000")
        assert stmt.depreciation == Decimal("11519000000")
        assert stmt.ebit == Decimal("114301000000")
        assert stmt.interest_expense == Decimal("3933000000")
        assert stmt.tax_provision == Decimal("16741000000")
        assert stmt.net_income == Decimal("96995000000")
        assert stmt.shares_outstanding == 15460000000

    def test_revenue_key_variant(self):
        raw = {
            "revenue": 100000,
            "netIncome": 20000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.revenue == Decimal("100000")

    def test_cogs_key_variant(self):
        raw = {
            "revenue": 100000,
            "cogs": 60000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.cost_of_revenue == Decimal("60000")

    def test_cost_of_goods_sold_key_variant(self):
        raw = {
            "revenue": 100000,
            "costOfGoodsSold": 55000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.cost_of_revenue == Decimal("55000")

    def test_ebit_key(self):
        raw = {
            "revenue": 100000,
            "ebit": 30000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.ebit == Decimal("30000")

    def test_weighted_average_shares_variant(self):
        raw = {
            "revenue": 100000,
            "weightedAverageShsOut": 5000000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.shares_outstanding == 5000000


class TestNormalizeIncomeStatementYFinance:
    """Test normalizing income statement from yfinance title-case keys."""

    def test_yfinance_title_case_fields(self):
        raw = {
            "Total Revenue": 394328000000,
            "Cost Of Revenue": 223546000000,
            "Gross Profit": 170782000000,
            "Selling General And Administrative": 24932000000,
            "Research Development": 29915000000,
            "Depreciation Amortization Depletion": 11519000000,
            "EBIT": 114301000000,
            "Interest Expense": 3933000000,
            "Tax Provision": 16741000000,
            "Net Income": 96995000000,
            "Basic Average Shares": 15460000000,
        }
        stmt = normalize_income_statement(raw)

        assert isinstance(stmt, IncomeStatement)
        assert stmt.revenue == Decimal("394328000000")
        assert stmt.cost_of_revenue == Decimal("223546000000")
        assert stmt.gross_profit == Decimal("170782000000")
        assert stmt.sga_expense == Decimal("24932000000")
        assert stmt.rd_expense == Decimal("29915000000")
        assert stmt.depreciation == Decimal("11519000000")
        assert stmt.ebit == Decimal("114301000000")
        assert stmt.interest_expense == Decimal("3933000000")
        assert stmt.tax_provision == Decimal("16741000000")
        assert stmt.net_income == Decimal("96995000000")
        assert stmt.shares_outstanding == 15460000000

    def test_diluted_average_shares_variant(self):
        raw = {
            "Total Revenue": 100000,
            "Diluted Average Shares": 5000000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.shares_outstanding == 5000000


class TestNormalizeBalanceSheetYFinance:
    """Test normalizing balance sheet from yfinance title-case keys."""

    def test_yfinance_title_case_fields(self):
        raw = {
            "Total Assets": 352583000000,
            "Current Assets": 143566000000,
            "Cash And Cash Equivalents": 29965000000,
            "Accounts Receivable": 60932000000,
            "Total Liabilities Net Minority Interest": 290437000000,
            "Current Liabilities": 145308000000,
            "Long Term Debt": 98959000000,
            "Stockholders Equity": 62146000000,
            "Retained Earnings": 4336000000,
            "Net PPE": 43715000000,
            "Ordinary Shares Number": 15460000000,
        }
        bs = normalize_balance_sheet(raw)

        assert isinstance(bs, BalanceSheet)
        assert bs.total_assets == Decimal("352583000000")
        assert bs.current_assets == Decimal("143566000000")
        assert bs.cash_and_equivalents == Decimal("29965000000")
        assert bs.receivables == Decimal("60932000000")
        assert bs.total_liabilities == Decimal("290437000000")
        assert bs.current_liabilities == Decimal("145308000000")
        assert bs.long_term_debt == Decimal("98959000000")
        assert bs.total_equity == Decimal("62146000000")
        assert bs.retained_earnings == Decimal("4336000000")
        assert bs.pp_and_e == Decimal("43715000000")
        assert bs.shares_outstanding == 15460000000


class TestNormalizeCashFlowYFinance:
    """Test normalizing cash flow statement from yfinance title-case keys."""

    def test_yfinance_title_case_fields(self):
        raw = {
            "Operating Cash Flow": 110543000000,
            "Capital Expenditure": -10959000000,
            "Common Stock Dividend Paid": -15025000000,
            "Repurchase Of Capital Stock": -77550000000,
            "Issuance Of Capital Stock": 0,
        }
        cf = normalize_cash_flow(raw)

        assert isinstance(cf, CashFlowStatement)
        assert cf.operating_cash_flow == Decimal("110543000000")
        assert cf.capital_expenditures == Decimal("-10959000000")
        assert cf.dividends_paid == Decimal("-15025000000")
        assert cf.share_repurchases == Decimal("-77550000000")
        assert cf.share_issuance == Decimal("0")


class TestNormalizeIncomeStatementSnakeCase:
    """Test normalizing income statement from snake_case fields."""

    def test_snake_case_fields(self):
        raw = {
            "total_revenue": 200000000,
            "cost_of_revenue": 120000000,
            "gross_profit": 80000000,
            "sga_expense": 15000000,
            "rd_expense": 10000000,
            "depreciation": 5000000,
            "operating_income": 50000000,
            "interest_expense": 2000000,
            "tax_provision": 10000000,
            "net_income": 38000000,
            "shares_outstanding": 1000000000,
        }
        stmt = normalize_income_statement(raw)

        assert isinstance(stmt, IncomeStatement)
        assert stmt.revenue == Decimal("200000000")
        assert stmt.cost_of_revenue == Decimal("120000000")
        assert stmt.gross_profit == Decimal("80000000")
        assert stmt.sga_expense == Decimal("15000000")
        assert stmt.rd_expense == Decimal("10000000")
        assert stmt.depreciation == Decimal("5000000")
        assert stmt.ebit == Decimal("50000000")
        assert stmt.interest_expense == Decimal("2000000")
        assert stmt.tax_provision == Decimal("10000000")
        assert stmt.net_income == Decimal("38000000")
        assert stmt.shares_outstanding == 1000000000


class TestNormalizeBalanceSheet:
    """Test normalizing balance sheet with various field name formats."""

    def test_camel_case_fields(self):
        raw = {
            "totalAssets": 352583000000,
            "totalCurrentAssets": 143566000000,
            "cashAndCashEquivalents": 29965000000,
            "netReceivables": 60932000000,
            "totalLiabilities": 290437000000,
            "totalCurrentLiabilities": 145308000000,
            "longTermDebt": 98959000000,
            "totalStockholdersEquity": 62146000000,
            "retainedEarnings": 4336000000,
            "propertyPlantEquipmentNet": 43715000000,
            "sharesOutstanding": 15460000000,
        }
        bs = normalize_balance_sheet(raw)

        assert isinstance(bs, BalanceSheet)
        assert bs.total_assets == Decimal("352583000000")
        assert bs.current_assets == Decimal("143566000000")
        assert bs.cash_and_equivalents == Decimal("29965000000")
        assert bs.receivables == Decimal("60932000000")
        assert bs.total_liabilities == Decimal("290437000000")
        assert bs.current_liabilities == Decimal("145308000000")
        assert bs.long_term_debt == Decimal("98959000000")
        assert bs.total_equity == Decimal("62146000000")
        assert bs.retained_earnings == Decimal("4336000000")
        assert bs.pp_and_e == Decimal("43715000000")
        assert bs.shares_outstanding == 15460000000

    def test_snake_case_fields(self):
        raw = {
            "total_assets": 500000000,
            "current_assets": 200000000,
            "cash_and_equivalents": 50000000,
            "receivables": 30000000,
            "total_liabilities": 300000000,
            "current_liabilities": 100000000,
            "long_term_debt": 150000000,
            "total_equity": 200000000,
            "retained_earnings": 80000000,
            "pp_and_e": 120000000,
            "shares_outstanding": 500000000,
        }
        bs = normalize_balance_sheet(raw)

        assert isinstance(bs, BalanceSheet)
        assert bs.total_assets == Decimal("500000000")
        assert bs.current_assets == Decimal("200000000")
        assert bs.total_equity == Decimal("200000000")

    def test_cash_key_variant(self):
        raw = {
            "total_assets": 500000000,
            "cash": 50000000,
        }
        bs = normalize_balance_sheet(raw)
        assert bs.cash_and_equivalents == Decimal("50000000")

    def test_stockholders_equity_variant(self):
        raw = {
            "total_assets": 500000000,
            "stockholdersEquity": 200000000,
        }
        bs = normalize_balance_sheet(raw)
        assert bs.total_equity == Decimal("200000000")


class TestNormalizeCashFlow:
    """Test normalizing cash flow statement."""

    def test_camel_case_fields(self):
        raw = {
            "operatingCashFlow": 110543000000,
            "capitalExpenditure": -10959000000,
            "dividendsPaid": -15025000000,
            "commonStockRepurchased": -77550000000,
            "commonStockIssued": 0,
        }
        cf = normalize_cash_flow(raw)

        assert isinstance(cf, CashFlowStatement)
        assert cf.operating_cash_flow == Decimal("110543000000")
        assert cf.capital_expenditures == Decimal("-10959000000")
        assert cf.dividends_paid == Decimal("-15025000000")
        assert cf.share_repurchases == Decimal("-77550000000")
        assert cf.share_issuance == Decimal("0")

    def test_snake_case_fields(self):
        raw = {
            "operating_cash_flow": 50000000,
            "capital_expenditures": -10000000,
            "dividends_paid": -5000000,
            "share_repurchases": -8000000,
            "share_issuance": 1000000,
        }
        cf = normalize_cash_flow(raw)

        assert isinstance(cf, CashFlowStatement)
        assert cf.operating_cash_flow == Decimal("50000000")
        assert cf.capital_expenditures == Decimal("-10000000")
        assert cf.dividends_paid == Decimal("-5000000")
        assert cf.share_repurchases == Decimal("-8000000")
        assert cf.share_issuance == Decimal("1000000")

    def test_total_cash_from_operations_variant(self):
        raw = {
            "totalCashFromOperatingActivities": 75000000,
        }
        cf = normalize_cash_flow(raw)
        assert cf.operating_cash_flow == Decimal("75000000")

    def test_capital_expenditures_plural_variant(self):
        raw = {
            "capitalExpenditures": -20000000,
        }
        cf = normalize_cash_flow(raw)
        assert cf.capital_expenditures == Decimal("-20000000")


class TestNormalizePriceBar:
    """Test normalizing price bar data."""

    def test_standard_fields(self):
        raw = {
            "date": "2024-01-15",
            "open": 185.50,
            "high": 187.20,
            "low": 184.80,
            "close": 186.90,
            "volume": 50000000,
            "adjClose": 186.90,
        }
        bar = normalize_price_bar(raw)

        assert isinstance(bar, PriceBar)
        assert bar.date == "2024-01-15"
        assert bar.open == Decimal("185.5")
        assert bar.high == Decimal("187.2")
        assert bar.low == Decimal("184.8")
        assert bar.close == Decimal("186.9")
        assert bar.volume == 50000000
        assert bar.adj_close == Decimal("186.9")

    def test_capitalized_date_key(self):
        raw = {
            "Date": "2024-06-01",
            "open": 150.0,
            "high": 152.0,
            "low": 149.0,
            "close": 151.0,
            "volume": 30000000,
        }
        bar = normalize_price_bar(raw)
        assert bar.date == "2024-06-01"

    def test_adjusted_close_variant(self):
        raw = {
            "date": "2024-01-15",
            "open": 185.50,
            "high": 187.20,
            "low": 184.80,
            "close": 186.90,
            "volume": 50000000,
            "adjustedClose": 185.00,
        }
        bar = normalize_price_bar(raw)
        assert bar.adj_close == Decimal("185.0")

    def test_adj_close_snake_case(self):
        raw = {
            "date": "2024-01-15",
            "open": 185.50,
            "high": 187.20,
            "low": 184.80,
            "close": 186.90,
            "volume": 50000000,
            "adj_close": 184.50,
        }
        bar = normalize_price_bar(raw)
        assert bar.adj_close == Decimal("184.5")

    def test_capitalized_ohlcv_keys(self):
        raw = {
            "Date": "2024-03-10",
            "Open": 200.0,
            "High": 205.0,
            "Low": 198.0,
            "Close": 203.0,
            "Volume": 40000000,
        }
        bar = normalize_price_bar(raw)
        assert bar.open == Decimal("200.0")
        assert bar.high == Decimal("205.0")
        assert bar.low == Decimal("198.0")
        assert bar.close == Decimal("203.0")
        assert bar.volume == 40000000


class TestNormalizeFundamentals:
    """Test normalizing combined fundamentals response."""

    def test_combined_response(self):
        raw = {
            "income_statement": {
                "revenue": 100000,
                "costOfRevenue": 60000,
                "grossProfit": 40000,
                "ebit": 25000,
                "netIncome": 18000,
                "sharesOutstanding": 1000000,
            },
            "balance_sheet": {
                "totalAssets": 500000,
                "totalCurrentAssets": 200000,
                "totalLiabilities": 300000,
                "totalCurrentLiabilities": 100000,
                "totalStockholdersEquity": 200000,
            },
            "cash_flow": {
                "operatingCashFlow": 30000,
                "capitalExpenditure": -5000,
            },
        }
        income, balance, cash_flow = normalize_fundamentals(raw)

        assert isinstance(income, IncomeStatement)
        assert isinstance(balance, BalanceSheet)
        assert isinstance(cash_flow, CashFlowStatement)

        assert income.revenue == Decimal("100000")
        assert income.net_income == Decimal("18000")
        assert balance.total_assets == Decimal("500000")
        assert cash_flow.operating_cash_flow == Decimal("30000")

    def test_camel_case_section_keys(self):
        raw = {
            "incomeStatement": {
                "revenue": 80000,
            },
            "balanceSheet": {
                "totalAssets": 400000,
            },
            "cashFlow": {
                "operatingCashFlow": 25000,
            },
        }
        income, balance, cash_flow = normalize_fundamentals(raw)

        assert income.revenue == Decimal("80000")
        assert balance.total_assets == Decimal("400000")
        assert cash_flow.operating_cash_flow == Decimal("25000")

    def test_cash_flow_statement_section_key(self):
        raw = {
            "income_statement": {"revenue": 50000},
            "balance_sheet": {"totalAssets": 200000},
            "cash_flow_statement": {"operatingCashFlow": 15000},
        }
        income, balance, cash_flow = normalize_fundamentals(raw)

        assert income.revenue == Decimal("50000")
        assert balance.total_assets == Decimal("200000")
        assert cash_flow.operating_cash_flow == Decimal("15000")


class TestMissingFieldsUseDefaults:
    """Test that missing or None fields fall back to model defaults."""

    def test_income_statement_minimal(self):
        raw = {"revenue": 100000}
        stmt = normalize_income_statement(raw)

        assert stmt.revenue == Decimal("100000")
        assert stmt.cost_of_revenue == Decimal("0")
        assert stmt.gross_profit == Decimal("0")
        assert stmt.ebit == Decimal("0")
        assert stmt.net_income == Decimal("0")
        assert stmt.shares_outstanding == 0
        assert stmt.sga_expense is None
        assert stmt.rd_expense is None
        assert stmt.depreciation is None
        assert stmt.interest_expense is None
        assert stmt.tax_provision is None

    def test_balance_sheet_minimal(self):
        raw = {"totalAssets": 500000}
        bs = normalize_balance_sheet(raw)

        assert bs.total_assets == Decimal("500000")
        assert bs.current_assets == Decimal("0")
        assert bs.total_liabilities == Decimal("0")
        assert bs.current_liabilities == Decimal("0")
        assert bs.total_equity == Decimal("0")
        assert bs.shares_outstanding == 0
        assert bs.cash_and_equivalents is None
        assert bs.receivables is None
        assert bs.long_term_debt is None
        assert bs.retained_earnings is None
        assert bs.pp_and_e is None

    def test_cash_flow_empty(self):
        raw = {}
        cf = normalize_cash_flow(raw)

        assert cf.operating_cash_flow == Decimal("0")
        assert cf.capital_expenditures == Decimal("0")
        assert cf.dividends_paid is None
        assert cf.share_repurchases is None
        assert cf.share_issuance is None

    def test_none_values_treated_as_missing(self):
        raw = {
            "revenue": 100000,
            "costOfRevenue": None,
            "grossProfit": None,
            "netIncome": None,
        }
        stmt = normalize_income_statement(raw)

        assert stmt.revenue == Decimal("100000")
        assert stmt.cost_of_revenue == Decimal("0")
        assert stmt.gross_profit == Decimal("0")
        assert stmt.net_income == Decimal("0")

    def test_none_values_for_optional_fields(self):
        raw = {
            "revenue": 100000,
            "interestExpense": None,
            "sga_expense": None,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.interest_expense is None
        assert stmt.sga_expense is None


class TestModelsAreValidPydantic:
    """Verify all normalized results are proper Pydantic model instances."""

    def test_income_statement_model_dump(self):
        raw = {"revenue": 100000, "netIncome": 20000}
        stmt = normalize_income_statement(raw)
        dumped = stmt.model_dump()
        assert "revenue" in dumped
        assert "net_income" in dumped
        assert dumped["revenue"] == Decimal("100000")

    def test_balance_sheet_model_dump(self):
        raw = {"totalAssets": 500000, "totalEquity": 200000}
        bs = normalize_balance_sheet(raw)
        dumped = bs.model_dump()
        assert "total_assets" in dumped

    def test_cash_flow_model_dump(self):
        raw = {"operatingCashFlow": 30000}
        cf = normalize_cash_flow(raw)
        dumped = cf.model_dump()
        assert "operating_cash_flow" in dumped

    def test_price_bar_model_dump(self):
        raw = {
            "date": "2024-01-15",
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 103.0,
            "volume": 1000000,
        }
        bar = normalize_price_bar(raw)
        dumped = bar.model_dump()
        assert "date" in dumped
        assert "close" in dumped

    def test_income_statement_computed_properties_work(self):
        raw = {
            "revenue": 100000,
            "grossProfit": 40000,
            "netIncome": 15000,
        }
        stmt = normalize_income_statement(raw)
        assert stmt.gross_margin == 0.4
        assert stmt.net_margin == 0.15


class TestNormalizeEarningsSurprise:
    """Test normalizing earnings surprise data from various providers."""

    def test_snake_case_keys(self):
        raw = {
            "quarter": "2024-Q4",
            "actual_eps": 1.50,
            "expected_eps": 1.40,
        }
        es = normalize_earnings_surprise(raw)
        assert isinstance(es, EarningsSurprise)
        assert es.quarter == "2024-Q4"
        assert es.actual_eps == Decimal("1.5")
        assert es.expected_eps == Decimal("1.4")

    def test_camel_case_keys(self):
        raw = {
            "quarter": "2024-Q3",
            "actualEps": 2.10,
            "expectedEps": 2.00,
        }
        es = normalize_earnings_surprise(raw)
        assert es.quarter == "2024-Q3"
        assert es.actual_eps == Decimal("2.1")
        assert es.expected_eps == Decimal("2.0")

    def test_yfinance_keys(self):
        raw = {
            "Quarter": "2024-Q2",
            "Reported EPS": 3.25,
            "EPS Estimate": 3.10,
        }
        es = normalize_earnings_surprise(raw)
        assert es.quarter == "2024-Q2"
        assert es.actual_eps == Decimal("3.25")
        assert es.expected_eps == Decimal("3.1")

    def test_fmp_keys(self):
        raw = {
            "fiscalDateEnding": "2024-Q1",
            "reportedEPS": 0.95,
            "estimatedEPS": 1.00,
        }
        es = normalize_earnings_surprise(raw)
        assert es.quarter == "2024-Q1"
        assert es.actual_eps == Decimal("0.95")
        assert es.expected_eps == Decimal("1.0")

    def test_period_key_variant(self):
        raw = {
            "period": "2023-Q4",
            "actual_eps": 1.00,
            "expected_eps": 0.90,
        }
        es = normalize_earnings_surprise(raw)
        assert es.quarter == "2023-Q4"

    def test_surprise_property(self):
        raw = {
            "quarter": "2024-Q4",
            "actual_eps": 1.50,
            "expected_eps": 1.40,
        }
        es = normalize_earnings_surprise(raw)
        assert es.surprise == Decimal("0.1")


class TestNormalizeEarningsList:
    """Test normalizing a list of earnings dicts."""

    def test_multiple_quarters(self):
        raw_list = [
            {"quarter": "2024-Q4", "actual_eps": 1.50, "expected_eps": 1.40},
            {"quarter": "2024-Q3", "actualEps": 1.30, "expectedEps": 1.25},
            {"Quarter": "2024-Q2", "Reported EPS": 1.10, "EPS Estimate": 1.15},
        ]
        results = normalize_earnings_list(raw_list)
        assert len(results) == 3
        assert all(isinstance(r, EarningsSurprise) for r in results)
        assert results[0].quarter == "2024-Q4"
        assert results[1].quarter == "2024-Q3"
        assert results[2].quarter == "2024-Q2"

    def test_empty_list(self):
        results = normalize_earnings_list([])
        assert results == []

    def test_single_entry(self):
        raw_list = [
            {"quarter": "2024-Q4", "actual_eps": 2.00, "expected_eps": 1.80},
        ]
        results = normalize_earnings_list(raw_list)
        assert len(results) == 1
        assert results[0].actual_eps == Decimal("2.0")
        assert results[0].expected_eps == Decimal("1.8")
