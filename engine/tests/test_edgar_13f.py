"""Tests for fund-centric 13F ingestion methods on EDGARProvider."""

from __future__ import annotations

from margin_engine.ingestion.providers.edgar_provider import EDGARProvider

SAMPLE_INFOTABLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>142300000</value>
    <shrsOrPrnAmt><sshPrnamt>915560382</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <putCall/>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>915560382</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>MICROSOFT CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>594918104</cusip>
    <value>89400000</value>
    <shrsOrPrnAmt><sshPrnamt>200000000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <putCall/>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>200000000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>"""

SAMPLE_SUBMISSIONS_JSON = {
    "cik": "0001067983",
    "name": "BERKSHIRE HATHAWAY INC",
    "filings": {
        "recent": {
            "accessionNumber": [
                "0001067983-26-000012",
                "0001067983-25-000050",
                "0001067983-25-000030",
            ],
            "form": ["13F-HR", "13F-HR", "10-K"],
            "filingDate": ["2026-02-14", "2025-11-14", "2025-03-01"],
            "reportDate": ["2025-12-31", "2025-09-30", "2024-12-31"],
        }
    },
}


class TestParseFullInfotable:
    """Tests for parse_full_infotable — parses ALL holdings from 13F XML."""

    def setup_method(self):
        self.provider = EDGARProvider(user_agent="Test test@example.com")

    def test_parse_all_holdings(self):
        """Should return all holdings (not filtered by company)."""
        holdings = self.provider.parse_full_infotable(
            xml_text=SAMPLE_INFOTABLE_XML,
            fund_name="BERKSHIRE HATHAWAY INC",
            fund_cik="0001067983",
            filing_date="2026-02-14",
            report_date="2025-12-31",
        )

        assert len(holdings) == 2

        apple = holdings[0]
        assert apple["fund_name"] == "BERKSHIRE HATHAWAY INC"
        assert apple["fund_cik"] == "0001067983"
        assert apple["issuer_name"] == "APPLE INC"
        assert apple["title_of_class"] == "COM"
        assert apple["cusip"] == "037833100"
        assert apple["value_thousands"] == 142300000
        assert apple["shares"] == 915560382
        assert apple["share_type"] == "SH"
        assert apple["put_call"] == "NONE"
        assert apple["investment_discretion"] == "SOLE"
        assert apple["voting_sole"] == 915560382
        assert apple["voting_shared"] == 0
        assert apple["voting_none"] == 0
        assert apple["filing_date"] == "2026-02-14"
        assert apple["report_date"] == "2025-12-31"

        msft = holdings[1]
        assert msft["issuer_name"] == "MICROSOFT CORP"
        assert msft["cusip"] == "594918104"
        assert msft["value_thousands"] == 89400000
        assert msft["shares"] == 200000000

    def test_parse_put_call_empty_is_none(self):
        """Empty <putCall/> element should produce 'NONE'."""
        holdings = self.provider.parse_full_infotable(
            xml_text=SAMPLE_INFOTABLE_XML,
            fund_name="Test Fund",
            fund_cik="0000000001",
            filing_date="2026-01-01",
            report_date="2025-12-31",
        )

        for h in holdings:
            assert h["put_call"] == "NONE"

    def test_parse_put_call_values(self):
        """PUT and CALL values should pass through as-is."""
        xml_with_put = SAMPLE_INFOTABLE_XML.replace(
            "<putCall/>",
            "<putCall>PUT</putCall>",
            1,  # only replace first occurrence
        )
        holdings = self.provider.parse_full_infotable(
            xml_text=xml_with_put,
            fund_name="Test Fund",
            fund_cik="0000000001",
            filing_date="2026-01-01",
            report_date="2025-12-31",
        )

        assert holdings[0]["put_call"] == "PUT"
        # Second entry still has empty putCall
        assert holdings[1]["put_call"] == "NONE"


class TestExtract13fFilings:
    """Tests for extract_13f_filings — extracts 13F entries from submissions JSON."""

    def setup_method(self):
        self.provider = EDGARProvider(user_agent="Test test@example.com")

    def test_extract_filing_list(self):
        """Should return only 13F filings, skipping 10-K."""
        filings = self.provider.extract_13f_filings(SAMPLE_SUBMISSIONS_JSON)

        assert len(filings) == 2

        first = filings[0]
        assert first["accession_number"] == "0001067983-26-000012"
        assert first["filing_type"] == "13F-HR"
        assert first["filed_date"] == "2026-02-14"
        assert first["period_of_report"] == "2025-12-31"
        assert first["is_amendment"] is False

        second = filings[1]
        assert second["accession_number"] == "0001067983-25-000050"
        assert second["filing_type"] == "13F-HR"
        assert second["filed_date"] == "2025-11-14"
        assert second["period_of_report"] == "2025-09-30"
        assert second["is_amendment"] is False

    def test_extract_amendment(self):
        """13F-HR/A should have is_amendment=True."""
        submissions_with_amendment = {
            "cik": "0001067983",
            "name": "BERKSHIRE HATHAWAY INC",
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0001067983-26-000015",
                        "0001067983-26-000012",
                    ],
                    "form": ["13F-HR/A", "13F-HR"],
                    "filingDate": ["2026-03-01", "2026-02-14"],
                    "reportDate": ["2025-12-31", "2025-12-31"],
                }
            },
        }

        filings = self.provider.extract_13f_filings(submissions_with_amendment)

        assert len(filings) == 2
        assert filings[0]["filing_type"] == "13F-HR/A"
        assert filings[0]["is_amendment"] is True
        assert filings[1]["filing_type"] == "13F-HR"
        assert filings[1]["is_amendment"] is False
