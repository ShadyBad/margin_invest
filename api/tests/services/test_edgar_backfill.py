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
    fetch_and_parse_filing,
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
        assert mock_client.get.call_count == 5
