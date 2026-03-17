"""Tests for the EDGAR backfill service."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from margin_api.services.edgar.backfill import (
    _build_snapshot_row,
    _infer_fiscal_info,
    _infer_period_end,
    _select_xbrl_file,
    fetch_and_parse_filing,
    reparse_empty_filings,
)
from margin_api.services.edgar.index_builder import EdgarIndexEntry
from margin_api.services.edgar.xbrl_parser import XBRLFinancials


def _make_entry(
    *,
    form_type: str = "10-Q",
    date_filed: str = "2024-08-15",
    cik: str = "320193",
    accession_number: str = "0000320193-24-000081",
) -> EdgarIndexEntry:
    return EdgarIndexEntry(
        company_name="APPLE INC",
        form_type=form_type,
        cik=cik,
        date_filed=date_filed,
        accession_number=accession_number,
        filename="edgar/data/320193/0000320193-24-000081.txt",
    )


def _make_financials() -> XBRLFinancials:
    return XBRLFinancials(
        income_statement={"revenue": 94930000000.0, "net_income": 23636000000.0},
        balance_sheet={"total_assets": 352583000000.0, "total_equity": 56727000000.0},
        cash_flow={"operating_cash_flow": 26438000000.0},
        shares_outstanding=15334382000,
    )


class TestBuildSnapshotRow:
    """Tests for _build_snapshot_row."""

    def test_build_snapshot_row_complete(self) -> None:
        """Verify row dict has all required fields."""
        entry = _make_entry()
        financials = _make_financials()

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert row["cik"] == "320193"
        assert row["ticker"] == "AAPL"
        assert row["filing_date"] == date(2024, 8, 15)
        assert row["form_type"] == "10-Q"
        assert row["accession_number"] == "0000320193-24-000081"
        assert row["income_statement"] == {
            "revenue": 94930000000.0,
            "net_income": 23636000000.0,
        }
        assert row["balance_sheet"] == {
            "total_assets": 352583000000.0,
            "total_equity": 56727000000.0,
        }
        assert row["cash_flow"] == {"operating_cash_flow": 26438000000.0}
        assert row["shares_outstanding"] == 15334382000
        assert row["fiscal_year"] == 2024
        assert row["fiscal_quarter"] == 2
        assert row["period_end"] == date(2024, 6, 28)

    def test_build_snapshot_row_annual(self) -> None:
        """10-K filing: fiscal_quarter should be None."""
        entry = _make_entry(form_type="10-K", date_filed="2024-11-01")
        financials = _make_financials()

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, None)

        assert row["form_type"] == "10-K"
        assert row["fiscal_quarter"] is None
        assert row["fiscal_year"] == 2024
        assert row["period_end"] == date(2024, 12, 31)


class TestInferPeriodEnd:
    """Tests for _infer_period_end."""

    def test_infer_period_end_quarterly(self) -> None:
        """Q3 filing -> period_end of month 9."""
        result = _infer_period_end(date(2024, 11, 5), "10-Q", 2024, 3)

        assert result == date(2024, 9, 28)

    def test_infer_period_end_annual(self) -> None:
        """10-K filing -> period_end of Dec 31."""
        result = _infer_period_end(date(2024, 11, 1), "10-K", 2024, None)

        assert result == date(2024, 12, 31)

    def test_infer_period_end_q1(self) -> None:
        """Q1 filing -> period_end of month 3."""
        result = _infer_period_end(date(2024, 5, 3), "10-Q", 2024, 1)

        assert result == date(2024, 3, 28)

    def test_infer_period_end_q2(self) -> None:
        """Q2 filing -> period_end of month 6."""
        result = _infer_period_end(date(2024, 8, 2), "10-Q", 2024, 2)

        assert result == date(2024, 6, 28)

    def test_infer_period_end_q4(self) -> None:
        """Q4 filing -> period_end of month 12."""
        result = _infer_period_end(date(2025, 2, 10), "10-Q", 2024, 4)

        assert result == date(2024, 12, 28)


class TestInferFiscalInfo:
    """Tests for _infer_fiscal_info."""

    def test_infer_fiscal_info_10k(self) -> None:
        """10-K filed in November -> same year."""
        entry = _make_entry(form_type="10-K", date_filed="2024-11-01")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter is None

    def test_infer_fiscal_info_10k_early_filing(self) -> None:
        """10-K filed in February -> previous year."""
        entry = _make_entry(form_type="10-K", date_filed="2025-02-15")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter is None

    def test_infer_fiscal_info_10k_march_filing(self) -> None:
        """10-K filed in March -> previous year."""
        entry = _make_entry(form_type="10-K", date_filed="2025-03-10")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter is None

    def test_infer_fiscal_info_10q(self) -> None:
        """10-Q filed in August -> Q2 of same year."""
        entry = _make_entry(form_type="10-Q", date_filed="2024-08-02")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter == 2

    def test_infer_fiscal_info_10q_q1(self) -> None:
        """10-Q filed in February -> Q1 of same year (month 1-4 -> Q1)."""
        entry = _make_entry(form_type="10-Q", date_filed="2024-02-15")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter == 1

    def test_infer_fiscal_info_10q_q3(self) -> None:
        """10-Q filed in November -> Q3 of same year (month 7-10 -> Q3)."""
        entry = _make_entry(form_type="10-Q", date_filed="2024-11-05")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter == 3

    def test_infer_fiscal_info_10ka(self) -> None:
        """10-K/A (amended) treated same as 10-K."""
        entry = _make_entry(form_type="10-K/A", date_filed="2024-06-15")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter is None

    def test_infer_fiscal_info_10qa(self) -> None:
        """10-Q/A (amended) treated same as 10-Q."""
        entry = _make_entry(form_type="10-Q/A", date_filed="2024-05-10")

        fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

        assert fiscal_year == 2024
        assert fiscal_quarter == 1


class TestSelectXbrlFile:
    """Tests for _select_xbrl_file — picks the right XML from a filing index page."""

    def test_prefers_htm_xml_over_linkbases(self) -> None:
        """Modern filing: _htm.xml should be chosen over _cal/_def/_lab/_pre.xml."""
        html = """
        <a href="aapl-20230930_cal.xml">cal</a>
        <a href="aapl-20230930_def.xml">def</a>
        <a href="aapl-20230930_htm.xml">htm</a>
        <a href="aapl-20230930_lab.xml">lab</a>
        <a href="aapl-20230930_pre.xml">pre</a>
        """
        assert _select_xbrl_file(html) == "aapl-20230930_htm.xml"

    def test_traditional_xbrl_instance(self) -> None:
        """Older filing: plain .xml instance file (no _htm.xml) should be picked."""
        html = """
        <a href="aapl-20140927.xml">instance</a>
        <a href="aapl-20140927_cal.xml">cal</a>
        <a href="aapl-20140927_def.xml">def</a>
        <a href="aapl-20140927_lab.xml">lab</a>
        <a href="aapl-20140927_pre.xml">pre</a>
        <a href="FilingSummary.xml">summary</a>
        """
        assert _select_xbrl_file(html) == "aapl-20140927.xml"

    def test_skips_r_report_files(self) -> None:
        """R*.xml report files should never be selected."""
        html = """
        <a href="R1.xml">report1</a>
        <a href="R2.xml">report2</a>
        <a href="msft-20230630.xml">instance</a>
        """
        assert _select_xbrl_file(html) == "msft-20230630.xml"

    def test_skips_filing_summary(self) -> None:
        """FilingSummary.xml should never be selected."""
        html = """
        <a href="FilingSummary.xml">summary</a>
        <a href="goog-20231231_htm.xml">htm</a>
        """
        assert _select_xbrl_file(html) == "goog-20231231_htm.xml"

    def test_returns_none_when_no_xbrl(self) -> None:
        """Pre-XBRL filing with only HTML files returns None."""
        html = """
        <a href="filing.htm">the filing</a>
        <a href="exhibit1.htm">exhibit</a>
        """
        assert _select_xbrl_file(html) is None

    def test_htm_xml_preferred_even_if_plain_xml_exists(self) -> None:
        """If both _htm.xml and a plain .xml exist, prefer _htm.xml."""
        html = """
        <a href="aapl-20230930.xml">instance</a>
        <a href="aapl-20230930_htm.xml">htm</a>
        <a href="aapl-20230930_cal.xml">cal</a>
        """
        assert _select_xbrl_file(html) == "aapl-20230930_htm.xml"

    def test_returns_none_when_only_linkbases(self) -> None:
        """If only linkbase XMLs exist (no instance or _htm.xml), return None."""
        html = """
        <a href="aapl-20230930_cal.xml">cal</a>
        <a href="aapl-20230930_def.xml">def</a>
        <a href="aapl-20230930_lab.xml">lab</a>
        <a href="aapl-20230930_pre.xml">pre</a>
        <a href="FilingSummary.xml">summary</a>
        """
        assert _select_xbrl_file(html) is None

    def test_skips_generic_metadata_xml(self) -> None:
        """Generic XML files like edgar.xml should not be selected as XBRL instances."""
        html = """
        <a href="edgar.xml">metadata</a>
        <a href="jnj-20120701.xml">instance</a>
        <a href="jnj-20120701_cal.xml">cal</a>
        """
        assert _select_xbrl_file(html) == "jnj-20120701.xml"

    def test_returns_none_when_only_generic_xml(self) -> None:
        """If only generic XML files exist (no ticker-date pattern), return None."""
        html = """
        <a href="edgar.xml">metadata</a>
        <a href="primary_doc.xml">doc</a>
        <a href="FilingSummary.xml">summary</a>
        """
        assert _select_xbrl_file(html) is None

    def test_full_path_hrefs(self) -> None:
        """Handles full-path hrefs (starting with /Archives/...)."""
        html = """
        <a href="/Archives/edgar/data/320193/000032019323000106/aapl-20230930_htm.xml">htm</a>
        <a href="/Archives/edgar/data/320193/000032019323000106/aapl-20230930_cal.xml">cal</a>
        """
        result = _select_xbrl_file(html)
        assert result is not None
        assert result.endswith("_htm.xml")


class TestFetchAndParseFilingRetry:
    """Tests for fetch_and_parse_filing retry behavior."""

    def _make_entry(self) -> EdgarIndexEntry:
        return EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2024-11-01",
            accession_number="0000320193-24-000123",
            filename="edgar/data/320193/0000320193-24-000123.txt",
        )

    @pytest.mark.asyncio
    async def test_retries_on_read_timeout_then_succeeds(self) -> None:
        """Should retry on ReadTimeout and succeed if next attempt works."""
        entry = self._make_entry()

        index_response = MagicMock()
        index_response.text = '<a href="aapl-20241101.xml">XBRL</a>'
        index_response.raise_for_status = MagicMock()

        xbrl_response = MagicMock()
        xbrl_response.text = "<xbrl></xbrl>"
        xbrl_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[
                httpx.ReadTimeout("timeout"),
                index_response,
                xbrl_response,
            ]
        )

        with patch("margin_api.services.edgar.backfill.extract_financials") as mock_extract:
            mock_extract.return_value = MagicMock()
            result = await fetch_and_parse_filing(mock_client, entry)

        assert result is not None
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Should NOT retry on 404 — returns None immediately."""
        entry = self._make_entry()

        error_request = httpx.Request("GET", "https://sec.gov/test")
        error_response = httpx.Response(404, request=error_request)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=error_request, response=error_response)
        )

        result = await fetch_and_parse_filing(mock_client, entry)
        assert result is None
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_after_max_retries(self) -> None:
        """Should return None after exhausting retries (not raise)."""
        entry = self._make_entry()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        result = await fetch_and_parse_filing(mock_client, entry)
        assert result is None
        assert mock_client.get.call_count == 4  # stop_after_attempt(4)


class TestXBRLParserNamespaces:
    """Tests for XBRL parser namespace support across taxonomy eras."""

    def test_fasb_org_namespace_2024(self) -> None:
        """Modern fasb.org namespace (2024) should parse correctly."""
        from margin_api.services.edgar.xbrl_parser import extract_financials

        xml = """<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:us-gaap="http://fasb.org/us-gaap/2024">
          <us-gaap:Revenues contextRef="c1" unitRef="u1" decimals="-6">100000000</us-gaap:Revenues>
          <us-gaap:Assets contextRef="c1" unitRef="u1" decimals="-6">500000000</us-gaap:Assets>
        </xbrl>"""
        result = extract_financials(xml)
        assert result.income_statement["revenue"] == 100000000.0
        assert result.balance_sheet["total_assets"] == 500000000.0

    def test_fasb_org_namespace_2013(self) -> None:
        """Pre-2019 fasb.org namespace with date suffix should parse correctly."""
        from margin_api.services.edgar.xbrl_parser import extract_financials

        gaap = "http://fasb.org/us-gaap/2013-01-31"
        xml = f"""<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:g="{gaap}">
          <g:Revenues contextRef="c1" unitRef="u1">200000000</g:Revenues>
          <g:NetIncomeLoss contextRef="c1" unitRef="u1">50000000</g:NetIncomeLoss>
        </xbrl>"""
        result = extract_financials(xml)
        assert result.income_statement["revenue"] == 200000000.0
        assert result.income_statement["net_income"] == 50000000.0

    def test_xbrl_us_namespace_2009(self) -> None:
        """Pre-2012 xbrl.us namespace (2011 and earlier filings)."""
        from margin_api.services.edgar.xbrl_parser import extract_financials

        gaap = "http://xbrl.us/us-gaap/2009-01-31"
        dei = "http://xbrl.us/dei/2009-01-31"
        xml = f"""<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:g="{gaap}" xmlns:d="{dei}">
          <g:Revenues contextRef="c1" unitRef="u1">15683000000</g:Revenues>
          <g:Assets contextRef="c1" unitRef="u1">86742000000</g:Assets>
          <g:NetIncomeLoss contextRef="c1" unitRef="u1">3378000000</g:NetIncomeLoss>
          <d:EntityCommonStockSharesOutstanding contextRef="c1"
            unitRef="u2">921035475</d:EntityCommonStockSharesOutstanding>
        </xbrl>"""
        result = extract_financials(xml)
        assert result.income_statement["revenue"] == 15683000000.0
        assert result.balance_sheet["total_assets"] == 86742000000.0
        assert result.income_statement["net_income"] == 3378000000.0
        assert result.shares_outstanding == 921035475

    def test_xbrl_us_dei_ent_namespace(self) -> None:
        """The dei-ent variant namespace from pre-2012 filings."""
        from margin_api.services.edgar.xbrl_parser import extract_financials

        gaap = "http://xbrl.us/us-gaap/2009-01-31"
        dei = "http://xbrl.us/dei-ent/2009-01-31"
        xml = f"""<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:g="{gaap}" xmlns:d="{dei}">
          <g:Revenues contextRef="c1" unitRef="u1">1000000</g:Revenues>
          <d:EntityCommonStockSharesOutstanding contextRef="c1"
            unitRef="u2">500000</d:EntityCommonStockSharesOutstanding>
        </xbrl>"""
        result = extract_financials(xml)
        assert result.income_statement["revenue"] == 1000000.0
        assert result.shares_outstanding == 500000


class TestBuildSnapshotRowNullHandling:
    """Tests for _build_snapshot_row omitting empty JSONB values for SQL NULL storage.

    SQLAlchemy JSON(none_as_null=False) converts Python None → JSON null.
    To get SQL NULL, we omit keys from the row dict so INSERT uses column default.
    """

    def test_empty_dict_income_statement_omitted(self) -> None:
        """Empty dict {} for income_statement should be omitted from row dict."""
        entry = _make_entry()
        financials = XBRLFinancials(
            income_statement={},
            balance_sheet={"total_assets": 100.0},
            cash_flow={"operating_cash_flow": 50.0},
            shares_outstanding=1000,
        )

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert "income_statement" not in row

    def test_empty_dict_balance_sheet_omitted(self) -> None:
        """Empty dict {} for balance_sheet should be omitted from row dict."""
        entry = _make_entry()
        financials = XBRLFinancials(
            income_statement={"revenue": 100.0},
            balance_sheet={},
            cash_flow={"operating_cash_flow": 50.0},
            shares_outstanding=1000,
        )

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert "balance_sheet" not in row

    def test_empty_dict_cash_flow_omitted(self) -> None:
        """Empty dict {} for cash_flow should be omitted from row dict."""
        entry = _make_entry()
        financials = XBRLFinancials(
            income_statement={"revenue": 100.0},
            balance_sheet={"total_assets": 100.0},
            cash_flow={},
            shares_outstanding=1000,
        )

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert "cash_flow" not in row

    def test_none_financials_omitted(self) -> None:
        """None values should also be omitted (not stored as JSON null)."""
        entry = _make_entry()
        financials = XBRLFinancials(
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
            shares_outstanding=None,
        )

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert "income_statement" not in row
        assert "balance_sheet" not in row
        assert "cash_flow" not in row

    def test_populated_dicts_preserved(self) -> None:
        """Non-empty dicts should be stored as-is."""
        entry = _make_entry()
        financials = _make_financials()

        row = _build_snapshot_row(entry, financials, "AAPL", 2024, 2)

        assert row["income_statement"] == {"revenue": 94930000000.0, "net_income": 23636000000.0}
        assert row["balance_sheet"] == {
            "total_assets": 352583000000.0,
            "total_equity": 56727000000.0,
        }
        assert row["cash_flow"] == {"operating_cash_flow": 26438000000.0}


class TestReparseEmptyFilings:
    """Tests for reparse_empty_filings query and filtering."""

    def _make_mock_factory(self) -> MagicMock:
        """Create a mock session factory that returns no rows."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        return mock_factory

    @pytest.mark.asyncio
    async def test_reparse_query_catches_json_null(self) -> None:
        """WHERE clause should match JSON null values, not just SQL NULL."""
        mock_factory = self._make_mock_factory()

        await reparse_empty_filings(mock_factory)

        # Extract the compiled SQL to verify it checks for JSON null
        mock_session = mock_factory.return_value.__aenter__.return_value
        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": True}))
        # Should contain jsonb_typeof check for catching JSON null values
        assert "jsonb_typeof" in compiled.lower() or "cast" in compiled.lower(), (
            f"WHERE clause should detect JSON null values, got: {compiled}"
        )

    @pytest.mark.asyncio
    async def test_reparse_excludes_pre_2011_filings(self) -> None:
        """WHERE clause should filter out filings before 2011-01-01."""
        mock_factory = self._make_mock_factory()

        await reparse_empty_filings(mock_factory)

        mock_session = mock_factory.return_value.__aenter__.return_value
        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "filing_date" in compiled
        assert "2011" in compiled

    @pytest.mark.asyncio
    async def test_reparse_returns_zero_counts_when_no_rows(self) -> None:
        """When no empty rows found, should return all-zero counts."""
        mock_factory = self._make_mock_factory()

        result = await reparse_empty_filings(mock_factory)

        assert result == {"total": 0, "reparsed": 0, "failed": 0, "still_empty": 0}
