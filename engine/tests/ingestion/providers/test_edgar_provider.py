"""Tests for SEC EDGAR data provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
from margin_engine.ingestion.types import DataCategory


def _make_response(json_data=None, text_data=None, success=True):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.is_success = success
    resp.raise_for_status = MagicMock()
    if not success:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    if json_data is not None:
        resp.json.return_value = json_data
    if text_data is not None:
        resp.text = text_data
    return resp


CIK_MAP_RESPONSE = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
}


class TestProviderInfo:
    def test_name(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.name == "edgar"

    def test_does_not_require_api_key(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.requires_api_key is False

    def test_supported_categories(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert set(provider.info.supported_categories) == {
            DataCategory.FUNDAMENTALS,
            DataCategory.INSIDER,
            DataCategory.INSTITUTIONAL,
        }

    def test_rate_limit(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.requests_per_minute == 600

    def test_category_priorities(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        cp = provider.info.category_priorities
        assert cp is not None
        assert cp[DataCategory.FUNDAMENTALS] == 2
        assert cp[DataCategory.INSIDER] == 10
        assert cp[DataCategory.INSTITUTIONAL] == 10

    def test_empty_user_agent_raises(self):
        with pytest.raises(ValueError, match="User-Agent"):
            EDGARProvider(user_agent="")


class TestCIKMapping:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_lookup(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        cik = provider._get_cik("AAPL")

        assert cik == "0000320193"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_zero_padded_to_10_digits(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        cik = provider._get_cik("MSFT")

        assert len(cik) == 10
        assert cik == "0000789019"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_case_insensitive(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider._get_cik("aapl") == "0000320193"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_unknown_ticker_raises(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        with pytest.raises(ValueError, match="No CIK found"):
            provider._get_cik("ZZZZ")

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_map_cached(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        provider._get_cik("AAPL")
        provider._get_cik("MSFT")

        # Only one HTTP call for the CIK map, not two
        assert mock_get.call_count == 1

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_company_name_lookup(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        name = provider._get_company_name("AAPL")

        assert name == "Apple Inc."


COMPANY_FACTS_RESPONSE = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 383285000000, "form": "10-K", "fy": 2023},
                        {"end": "2022-09-24", "val": 394328000000, "form": "10-K", "fy": 2022},
                        {"end": "2023-07-01", "val": 81797000000, "form": "10-Q", "fy": 2023},
                    ]
                }
            },
            "CostOfRevenue": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 214137000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "GrossProfit": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 169148000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "NetIncomeLoss": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 96995000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "EarningsPerShareBasic": {
                "units": {
                    "USD/shares": [
                        {"end": "2023-09-30", "val": 6.16, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "Assets": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 352755000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "StockholdersEquity": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 62146000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 110543000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
        }
    },
}


class TestFetchFundamentals:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_success(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.provider_name == "edgar"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.raw_data["income_statement"]["revenue"] == 383285000000
        assert result.raw_data["income_statement"]["net_income"] == 96995000000
        assert result.raw_data["balance_sheet"]["total_assets"] == 352755000000
        assert result.raw_data["cash_flow"]["operating_cash_flow"] == 110543000000

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_picks_latest_10k(self, mock_get):
        """Should pick the most recent 10-K, not 10-Q."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        # Should pick 2023 annual (383B), not 2023 quarterly (81B)
        assert result.raw_data["income_statement"]["revenue"] == 383285000000

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_usd_per_shares_unit(self, mock_get):
        """EPS uses USD/shares unit, not plain USD."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.raw_data["income_statement"]["eps_basic"] == 6.16

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_missing_tags_omitted(self, mock_get):
        """Fields with no matching XBRL tags are simply absent from raw_data."""
        sparse_facts = {"facts": {"us-gaap": {}}}
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=sparse_facts),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.raw_data["income_statement"] == {}
        assert result.raw_data["balance_sheet"] == {}
        assert result.raw_data["cash_flow"] == {}

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(success=False),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is False
        assert result.error is not None


SUBMISSIONS_RESPONSE = {
    "cik": "320193",
    "entityType": "operating",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-24-000006",
                "0000320193-24-000005",
                "0000320193-24-000004",
            ],
            "filingDate": ["2024-01-26", "2024-01-20", "2024-01-15"],
            "reportDate": ["2024-01-26", "2024-01-20", "2024-01-15"],
            "form": ["4", "10-K", "4"],
            "primaryDocument": ["xslF345X05.xml", "aapl-20231230.htm", "xslF345X05.xml"],
        }
    },
}

FORM4_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001767094</rptOwnerCik>
      <rptOwnerName>COOK TIMOTHY D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>true</isDirector>
      <isOfficer>true</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-01-25</value></transactionDate>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>50000</value></transactionShares>
        <transactionPricePerShare><value>195.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


class TestFetchInsiderTransactions:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_success(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),       # CIK map
            _make_response(json_data=SUBMISSIONS_RESPONSE),    # submissions
            _make_response(text_data=FORM4_XML),               # Form 4 filing 1
            _make_response(text_data=FORM4_XML),               # Form 4 filing 2
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.provider_name == "edgar"
        assert result.category == DataCategory.INSIDER
        txns = result.raw_data["transactions"]
        assert len(txns) == 2  # Two Form 4 filings, one transaction each
        assert txns[0]["owner_name"] == "COOK TIMOTHY D"
        assert txns[0]["transaction_code"] == "S"
        assert txns[0]["shares"] == 50000.0
        assert txns[0]["price_per_share"] == 195.50
        assert txns[0]["is_officer"] is True
        assert txns[0]["officer_title"] == "Chief Executive Officer"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_no_form4_filings(self, mock_get):
        no_form4 = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-24-000005"],
                    "filingDate": ["2024-01-20"],
                    "form": ["10-K"],
                    "primaryDocument": ["doc.htm"],
                }
            }
        }
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=no_form4),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.raw_data["transactions"] == []

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_xml_parse_error_skipped(self, mock_get):
        """If one filing has bad XML, it's skipped gracefully."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=SUBMISSIONS_RESPONSE),
            _make_response(text_data="<not valid xml"),         # bad XML
            _make_response(text_data=FORM4_XML),                # good XML
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert len(result.raw_data["transactions"]) == 1

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = Exception("network timeout")

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is False
        assert "network timeout" in result.error
