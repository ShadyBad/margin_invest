"""Tests for XBRL parser and US-GAAP tag mapping."""

import pytest
from margin_api.services.edgar.xbrl_parser import (
    GAAP_TAG_MAP,
    XBRLFinancials,
    extract_financials,
)

SAMPLE_XBRL = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:Revenues contextRef="FY2024" decimals="-6" unitRef="USD">391035000000</us-gaap:Revenues>
  <us-gaap:NetIncomeLoss contextRef="FY2024" decimals="-6" unitRef="USD">93736000000</us-gaap:NetIncomeLoss>
  <us-gaap:Assets contextRef="FY2024_instant" decimals="-6" unitRef="USD">352583000000</us-gaap:Assets>
  <us-gaap:Liabilities contextRef="FY2024_instant" decimals="-6" unitRef="USD">290437000000</us-gaap:Liabilities>
  <us-gaap:StockholdersEquity contextRef="FY2024_instant" decimals="-6" unitRef="USD">62146000000</us-gaap:StockholdersEquity>
  <us-gaap:NetCashProvidedByOperatingActivities contextRef="FY2024" decimals="-6" unitRef="USD">118254000000</us-gaap:NetCashProvidedByOperatingActivities>
  <us-gaap:PaymentsToAcquirePropertyPlantAndEquipment contextRef="FY2024" decimals="-6" unitRef="USD">9959000000</us-gaap:PaymentsToAcquirePropertyPlantAndEquipment>
  <us-gaap:CommonStockSharesOutstanding contextRef="FY2024_instant" decimals="0" unitRef="shares">15115823000</us-gaap:CommonStockSharesOutstanding>
</xbrl>
"""


class TestExtractFinancialsBasic:
    """Parse a sample XBRL snippet with ~8 tags, verify all values extracted correctly."""

    def test_revenue_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.income_statement["revenue"] == 391035000000.0

    def test_net_income_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.income_statement["net_income"] == 93736000000.0

    def test_total_assets_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.balance_sheet["total_assets"] == 352583000000.0

    def test_total_liabilities_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.balance_sheet["total_liabilities"] == 290437000000.0

    def test_total_equity_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.balance_sheet["total_equity"] == 62146000000.0

    def test_operating_cash_flow_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.cash_flow["operating_cash_flow"] == 118254000000.0

    def test_capex_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.cash_flow["capex"] == 9959000000.0

    def test_shares_outstanding_extracted(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert result.shares_outstanding == 15115823000

    def test_shares_outstanding_is_int(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        assert isinstance(result.shares_outstanding, int)

    def test_income_fields_are_float(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        for key, val in result.income_statement.items():
            if val is not None:
                assert isinstance(val, float), f"{key} should be float, got {type(val)}"

    def test_balance_fields_are_float(self) -> None:
        result = extract_financials(SAMPLE_XBRL)
        for key, val in result.balance_sheet.items():
            if val is not None:
                assert isinstance(val, float), f"{key} should be float, got {type(val)}"


class TestExtractFinancialsFallbackTag:
    """When primary tag is missing, fallback tag should work."""

    def test_fallback_revenue_tag(self) -> None:
        """SalesRevenueNet is a fallback for revenue when Revenues is absent."""
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2023">
  <us-gaap:SalesRevenueNet contextRef="FY2023" decimals="-6" unitRef="USD">50000000</us-gaap:SalesRevenueNet>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.income_statement["revenue"] == 50000000.0

    def test_fallback_equity_tag(self) -> None:
        """StockholdersEquityIncluding... is a fallback for total_equity."""
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest contextRef="FY2024" decimals="-6" unitRef="USD">99000000</us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.balance_sheet["total_equity"] == 99000000.0

    def test_primary_tag_wins_over_fallback(self) -> None:
        """When both primary and fallback tags are present, primary wins."""
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:Revenues contextRef="FY2024" decimals="-6" unitRef="USD">100000000</us-gaap:Revenues>
  <us-gaap:SalesRevenueNet contextRef="FY2024" decimals="-6" unitRef="USD">99000000</us-gaap:SalesRevenueNet>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.income_statement["revenue"] == 100000000.0

    def test_fallback_shares_outstanding(self) -> None:
        """WeightedAverage... is a fallback for shares_outstanding."""
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:WeightedAverageNumberOfSharesOutstandingBasic contextRef="FY2024" decimals="0" unitRef="shares">1000000</us-gaap:WeightedAverageNumberOfSharesOutstandingBasic>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.shares_outstanding == 1000000

    def test_different_taxonomy_year(self) -> None:
        """Tags from older taxonomy years (e.g. 2021) should still work."""
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2021">
  <us-gaap:Assets contextRef="FY2021" decimals="-6" unitRef="USD">200000000</us-gaap:Assets>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.balance_sheet["total_assets"] == 200000000.0


class TestExtractFinancialsEmptyXbrl:
    """Empty XBRL returns None values."""

    def test_empty_xbrl_returns_empty_dicts(self) -> None:
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.income_statement == {}
        assert result.balance_sheet == {}
        assert result.cash_flow == {}
        assert result.shares_outstanding is None

    def test_xbrl_with_non_gaap_tags_returns_empty(self) -> None:
        xbrl = """\
<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:custom="http://example.com/custom">
  <custom:SomeField contextRef="FY2024">12345</custom:SomeField>
</xbrl>
"""
        result = extract_financials(xbrl)
        assert result.income_statement == {}
        assert result.balance_sheet == {}
        assert result.cash_flow == {}
        assert result.shares_outstanding is None


class TestGaapTagMapHasRequiredFields:
    """Verify all critical fields are in the map."""

    REQUIRED_FIELDS = [
        "revenue",
        "cost_of_revenue",
        "gross_profit",
        "net_income",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "operating_cash_flow",
        "capex",
        "shares_outstanding",
        "ebit",
        "interest_expense",
        "long_term_debt",
        "retained_earnings",
        "sga_expense",
        "rd_expense",
        "current_assets",
        "current_liabilities",
        "cash_and_equivalents",
        "pp_and_e",
        "depreciation",
        "tax_provision",
        "receivables",
        "dividends_paid",
        "share_repurchases",
        "short_term_debt",
    ]

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_field_in_gaap_tag_map(self, field: str) -> None:
        assert field in GAAP_TAG_MAP, f"Missing required field: {field}"

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_field_has_at_least_one_tag(self, field: str) -> None:
        assert len(GAAP_TAG_MAP[field]) >= 1, f"Field {field} has no tags"

    def test_all_tags_are_strings(self) -> None:
        for field, tags in GAAP_TAG_MAP.items():
            for tag in tags:
                assert isinstance(tag, str), f"Tag for {field} is not a string: {tag}"


class TestExtractFinancialsInvalidXml:
    """Malformed XML returns empty XBRLFinancials."""

    def test_garbage_input(self) -> None:
        result = extract_financials("this is not xml at all")
        assert result.income_statement == {}
        assert result.balance_sheet == {}
        assert result.cash_flow == {}
        assert result.shares_outstanding is None

    def test_incomplete_xml(self) -> None:
        result = extract_financials("<?xml version='1.0'?><xbrl>")
        assert isinstance(result, XBRLFinancials)

    def test_empty_string(self) -> None:
        result = extract_financials("")
        assert isinstance(result, XBRLFinancials)
        assert result.shares_outstanding is None

    def test_returns_xbrl_financials_type(self) -> None:
        result = extract_financials("<broken>")
        assert isinstance(result, XBRLFinancials)
