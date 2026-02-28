"""Tests for the EDGAR index builder service."""

from __future__ import annotations

import pytest

from margin_api.services.edgar.index_builder import (
    EdgarIndexEntry,
    parse_company_idx,
)


# --- Sample company.idx content ---

SAMPLE_IDX = """\
CIK|Company Name|Form Type|Date Filed|Filename
----------------------------------------------------------------------
320193|APPLE INC|10-K|2024-11-01|edgar/data/320193/0000320193-24-000123.txt
789019|MICROSOFT CORP|10-Q|2024-10-15|edgar/data/789019/0000789019-24-000456.txt
1018724|AMAZON COM INC|8-K|2024-10-20|edgar/data/1018724/0001018724-24-000789.txt
1326801|META PLATFORMS INC|10-K/A|2024-09-30|edgar/data/1326801/0001326801-24-001234.txt
"""

SAMPLE_IDX_NO_DATA = """\
CIK|Company Name|Form Type|Date Filed|Filename
----------------------------------------------------------------------
"""


class TestEdgarIndexEntryFields:
    """Verify EdgarIndexEntry dataclass and properties."""

    def test_cik_int_strips_leading_zeros(self) -> None:
        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="0000320193",
            date_filed="2024-11-01",
            accession_number="0000320193-24-000123",
            filename="edgar/data/320193/0000320193-24-000123.txt",
        )
        assert entry.cik_int == 320193

    def test_cik_int_no_leading_zeros(self) -> None:
        entry = EdgarIndexEntry(
            company_name="TEST CORP",
            form_type="10-Q",
            cik="12345",
            date_filed="2024-01-01",
            accession_number="0000012345-24-000001",
            filename="edgar/data/12345/0000012345-24-000001.txt",
        )
        assert entry.cik_int == 12345

    def test_all_fields_populated(self) -> None:
        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2024-11-01",
            accession_number="0000320193-24-000123",
            filename="edgar/data/320193/0000320193-24-000123.txt",
        )
        assert entry.company_name == "APPLE INC"
        assert entry.form_type == "10-K"
        assert entry.cik == "320193"
        assert entry.date_filed == "2024-11-01"
        assert entry.accession_number == "0000320193-24-000123"
        assert entry.filename == "edgar/data/320193/0000320193-24-000123.txt"


class TestParseCompanyIdx:
    """Tests for parse_company_idx."""

    def test_parse_company_idx_extracts_10k(self) -> None:
        entries = parse_company_idx(SAMPLE_IDX)
        # Should get 10-K, 10-Q, 10-K/A (3 entries) but NOT 8-K
        assert len(entries) == 3

        # Check first entry (Apple 10-K)
        apple = entries[0]
        assert apple.company_name == "APPLE INC"
        assert apple.form_type == "10-K"
        assert apple.cik == "320193"
        assert apple.date_filed == "2024-11-01"
        assert apple.accession_number == "0000320193-24-000123"
        assert apple.filename == "edgar/data/320193/0000320193-24-000123.txt"

        # Check second entry (Microsoft 10-Q)
        msft = entries[1]
        assert msft.company_name == "MICROSOFT CORP"
        assert msft.form_type == "10-Q"
        assert msft.cik == "789019"

        # Check third entry (Meta 10-K/A)
        meta = entries[2]
        assert meta.company_name == "META PLATFORMS INC"
        assert meta.form_type == "10-K/A"
        assert meta.cik == "1326801"
        assert meta.accession_number == "0001326801-24-001234"

    def test_parse_company_idx_skips_non_target_forms(self) -> None:
        entries = parse_company_idx(SAMPLE_IDX)
        form_types = {e.form_type for e in entries}
        assert "8-K" not in form_types

    def test_parse_company_idx_custom_form_types(self) -> None:
        entries = parse_company_idx(SAMPLE_IDX, form_types={"8-K"})
        assert len(entries) == 1
        assert entries[0].company_name == "AMAZON COM INC"
        assert entries[0].form_type == "8-K"

    def test_parse_company_idx_empty(self) -> None:
        entries = parse_company_idx("")
        assert entries == []

    def test_parse_company_idx_header_only(self) -> None:
        entries = parse_company_idx(SAMPLE_IDX_NO_DATA)
        assert entries == []

    def test_parse_company_idx_accession_from_filename(self) -> None:
        """Accession number is extracted via regex from filename."""
        entries = parse_company_idx(SAMPLE_IDX)
        for entry in entries:
            assert entry.accession_number  # non-empty
            # Accession format: 10digits-2digits-6digits
            parts = entry.accession_number.split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 10
            assert len(parts[1]) == 2
            assert len(parts[2]) == 6
