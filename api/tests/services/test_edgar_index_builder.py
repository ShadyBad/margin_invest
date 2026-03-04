"""Tests for the EDGAR index builder service."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from margin_api.services.edgar.index_builder import (
    EdgarIndexEntry,
    fetch_quarter_index,
    load_cik_ticker_map,
    parse_company_idx,
)

# --- Sample company.idx content (real SEC EDGAR fixed-width format) ---
# Column positions: Company Name (0), Form Type (62), CIK (74), Date Filed (86), File Name (98)

SAMPLE_IDX = """\
Description:           Master Index of EDGAR Dissemination Feed by Company Name
Last Data Received:    November 1, 2024
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/




Company Name                                                  Form Type   CIK         Date Filed  File Name
--------------------------------------------------------------------------------------------------------------------------------------
APPLE INC                                                     10-K             320193      2024-11-01  edgar/data/320193/0000320193-24-000123.txt
MICROSOFT CORP                                                10-Q             789019      2024-10-15  edgar/data/789019/0000789019-24-000456.txt
AMAZON COM INC                                                8-K              1018724     2024-10-20  edgar/data/1018724/0001018724-24-000789.txt
META PLATFORMS INC                                            10-K/A           1326801     2024-09-30  edgar/data/1326801/0001326801-24-001234.txt
"""

SAMPLE_IDX_NO_DATA = """\
Description:           Master Index of EDGAR Dissemination Feed by Company Name
Last Data Received:    November 1, 2024
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/




Company Name                                                  Form Type   CIK         Date Filed  File Name
--------------------------------------------------------------------------------------------------------------------------------------
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


class TestFetchQuarterIndexRetry:
    """Tests for fetch_quarter_index retry behavior."""

    @pytest.mark.asyncio
    async def test_retries_on_read_timeout(self) -> None:
        """Should retry on ReadTimeout and succeed on second attempt."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_IDX
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), mock_response])

        entries = await fetch_quarter_index(mock_client, 2024, 1)
        assert len(entries) == 3  # 10-K, 10-Q, 10-K/A from SAMPLE_IDX
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_connect_timeout(self) -> None:
        """Should retry on ConnectTimeout."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_IDX
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[httpx.ConnectTimeout("timeout"), mock_response])

        entries = await fetch_quarter_index(mock_client, 2024, 1)
        assert len(entries) == 3
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self) -> None:
        """Should retry on 5xx HTTP errors."""
        mock_response_ok = MagicMock()
        mock_response_ok.text = SAMPLE_IDX
        mock_response_ok.raise_for_status = MagicMock()

        error_request = httpx.Request("GET", "https://sec.gov/test")
        error_response = httpx.Response(503, request=error_request)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError("503", request=error_request, response=error_response),
                mock_response_ok,
            ]
        )

        entries = await fetch_quarter_index(mock_client, 2024, 1)
        assert len(entries) == 3
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self) -> None:
        """Should NOT retry on 4xx HTTP errors."""
        error_request = httpx.Request("GET", "https://sec.gov/test")
        error_response = httpx.Response(404, request=error_request)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=error_request, response=error_response)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_quarter_index(mock_client, 2024, 1)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """Should raise after exhausting all retries."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with pytest.raises(httpx.ReadTimeout):
            await fetch_quarter_index(mock_client, 2024, 1)
        assert mock_client.get.call_count == 5  # 5 attempts


class TestLoadCikTickerMapRetry:
    """Tests for load_cik_ticker_map retry behavior."""

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self) -> None:
        """Should retry on timeout and succeed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc"}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), mock_response])

        result = await load_cik_ticker_map(mock_client)
        assert result == {320193: "AAPL"}
        assert mock_client.get.call_count == 2


class TestIndexCaching:
    """Tests for per-quarter index caching helpers."""

    def test_is_cache_fresh_past_quarter_always_fresh(self) -> None:
        """Past quarters are always fresh (data doesn't change)."""
        from datetime import datetime

        from margin_api.services.edgar.index_builder import _is_cache_fresh

        old_time = datetime(2020, 1, 1, tzinfo=UTC)
        assert _is_cache_fresh(old_time, 2020, 1) is True

    def test_is_cache_fresh_current_quarter_under_24h(self) -> None:
        """Current quarter cache under 24h is fresh."""
        from datetime import datetime

        from margin_api.services.edgar.index_builder import _is_cache_fresh

        now = datetime.now(UTC)
        current_quarter = (now.month - 1) // 3 + 1
        assert _is_cache_fresh(now, now.year, current_quarter) is True

    def test_is_cache_fresh_current_quarter_over_24h(self) -> None:
        """Current quarter cache over 24h is stale."""
        from datetime import datetime, timedelta

        from margin_api.services.edgar.index_builder import _is_cache_fresh

        old_time = datetime.now(UTC) - timedelta(hours=25)
        now = datetime.now(UTC)
        current_quarter = (now.month - 1) // 3 + 1
        assert _is_cache_fresh(old_time, now.year, current_quarter) is False

    def test_is_cache_fresh_future_quarter_treated_as_current(self) -> None:
        """A future quarter (same year) should be treated as current and expire after 24h."""
        from datetime import datetime, timedelta

        from margin_api.services.edgar.index_builder import _is_cache_fresh

        now = datetime.now(UTC)
        # Use quarter 4 which is either current or future
        future_q = 4
        # If fetched recently, should be fresh
        assert _is_cache_fresh(now, now.year, future_q) is True
        # If fetched >24h ago and it's the current quarter, should be stale
        old_time = now - timedelta(hours=25)
        current_quarter = (now.month - 1) // 3 + 1
        if future_q >= current_quarter:
            assert _is_cache_fresh(old_time, now.year, future_q) is False

    def test_is_cache_fresh_previous_year_always_fresh(self) -> None:
        """Quarters from previous years are always fresh."""
        from datetime import datetime

        from margin_api.services.edgar.index_builder import _is_cache_fresh

        # Even with a very old fetched_at, past year quarters are always fresh
        ancient = datetime(2010, 6, 15, tzinfo=UTC)
        assert _is_cache_fresh(ancient, 2023, 3) is True


class TestConsecutiveFailureTracker:
    """Tests for ConsecutiveFailureTracker."""

    def test_no_trip_below_threshold(self) -> None:
        from margin_api.services.edgar.index_builder import ConsecutiveFailureTracker

        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        # 2 failures, threshold is 3 — should not raise

    def test_trips_at_threshold(self) -> None:
        from margin_api.services.edgar.index_builder import (
            ConsecutiveFailureTracker,
            EdgarUnavailableError,
        )

        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        with pytest.raises(EdgarUnavailableError, match="3 consecutive"):
            tracker.record_failure()

    def test_resets_on_success(self) -> None:
        from margin_api.services.edgar.index_builder import ConsecutiveFailureTracker

        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        tracker.record_success()  # Reset
        tracker.record_failure()
        tracker.record_failure()
        # Only 2 consecutive failures after reset — should not raise

    def test_trips_after_reset_and_new_failures(self) -> None:
        from margin_api.services.edgar.index_builder import (
            ConsecutiveFailureTracker,
            EdgarUnavailableError,
        )

        tracker = ConsecutiveFailureTracker(threshold=2)
        tracker.record_failure()
        tracker.record_success()
        tracker.record_failure()
        with pytest.raises(EdgarUnavailableError):
            tracker.record_failure()
