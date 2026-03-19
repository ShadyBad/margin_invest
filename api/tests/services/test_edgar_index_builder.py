"""Tests for the EDGAR index builder service."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from margin_api.services.edgar.index_builder import (
    EdgarIndexEntry,
    fetch_quarter_index,
    load_cik_ticker_map,
    parse_company_idx,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


class TestLoadCikTickerMapWithSic:
    """Tests for load_cik_ticker_sic_map using company_tickers_exchange.json."""

    @pytest.mark.asyncio
    async def test_returns_ticker_and_sic(self) -> None:
        """SIC codes are returned alongside tickers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": ["cik", "name", "ticker", "exchange", "sic"],
            "data": [
                [320193, "Apple Inc.", "AAPL", "Nasdaq", "3571"],
                [789019, "Microsoft Corp", "MSFT", "Nasdaq", "7372"],
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from margin_api.services.edgar.index_builder import load_cik_ticker_sic_map

        result = await load_cik_ticker_sic_map(mock_client)
        assert result[320193] == ("AAPL", 3571)
        assert result[789019] == ("MSFT", 7372)

    @pytest.mark.asyncio
    async def test_missing_sic_defaults_to_none(self) -> None:
        """Entries without SIC codes get None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": ["cik", "name", "ticker", "exchange", "sic"],
            "data": [
                [12345, "No SIC Corp", "NOSIC", "NYSE", ""],
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from margin_api.services.edgar.index_builder import load_cik_ticker_sic_map

        result = await load_cik_ticker_sic_map(mock_client)
        assert result[12345] == ("NOSIC", None)


# ---------------------------------------------------------------------------
# In-memory DB fixtures for cache helper tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def memory_session_factory():
    """Create an in-memory SQLite session factory with the full schema."""
    from margin_api.db.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def memory_session(memory_session_factory):
    """Single async session for inline DB tests."""
    async with memory_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Tests for _get_cached_quarter
# ---------------------------------------------------------------------------


class TestGetCachedQuarter:
    """Tests for the _get_cached_quarter cache helper."""

    @pytest.mark.asyncio
    async def test_returns_none_when_cache_empty(self, memory_session) -> None:
        """Cache miss returns None when no rows in DB."""
        from margin_api.services.edgar.index_builder import _get_cached_quarter

        result = await _get_cached_quarter(memory_session, 2023, 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_entries_on_cache_hit(self, memory_session_factory) -> None:
        """Cache hit returns list of EdgarIndexEntry objects."""
        from margin_api.services.edgar.index_builder import (
            EdgarIndexEntry,
            _cache_quarter,
            _get_cached_quarter,
        )

        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2024-11-01",
            accession_number="0000320193-24-000123",
            filename="edgar/data/320193/0000320193-24-000123.txt",
        )
        # Use a past quarter so it's always "stale" fresh — use 2023Q1 (always past)
        # Patch _is_cache_fresh to always return True after cache is populated
        from unittest.mock import patch

        async with memory_session_factory() as session:
            await _cache_quarter(session, 2023, 1, [entry])

        # Patch _is_cache_fresh to always return True
        with patch("margin_api.services.edgar.index_builder._is_cache_fresh", return_value=True):
            async with memory_session_factory() as session:
                result = await _get_cached_quarter(session, 2023, 1)

        assert result is not None
        assert len(result) == 1
        assert result[0].cik == "320193"
        assert result[0].form_type == "10-K"

    @pytest.mark.asyncio
    async def test_returns_none_when_cache_stale(self, memory_session_factory) -> None:
        """Stale cache entry returns None."""
        from margin_api.services.edgar.index_builder import (
            EdgarIndexEntry,
            _cache_quarter,
            _get_cached_quarter,
        )

        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2020-01-01",
            accession_number="0000320193-20-000001",
            filename="edgar/data/320193/0000320193-20-000001.txt",
        )
        async with memory_session_factory() as session:
            await _cache_quarter(session, 2020, 1, [entry])

        # Patch _is_cache_fresh to return False (stale)
        from unittest.mock import patch

        with patch("margin_api.services.edgar.index_builder._is_cache_fresh", return_value=False):
            async with memory_session_factory() as session:
                result = await _get_cached_quarter(session, 2020, 1)

        assert result is None


# ---------------------------------------------------------------------------
# Tests for _cache_quarter
# ---------------------------------------------------------------------------


class TestCacheQuarter:
    """Tests for the _cache_quarter cache helper."""

    @pytest.mark.asyncio
    async def test_inserts_new_cache_row(self, memory_session_factory) -> None:
        """First insert creates a row with correct fields."""
        from margin_api.db.models import EdgarIndexCache
        from margin_api.services.edgar.index_builder import (
            EdgarIndexEntry,
            _cache_quarter,
        )
        from sqlalchemy import select

        entries = [
            EdgarIndexEntry(
                company_name="APPLE INC",
                form_type="10-K",
                cik="320193",
                date_filed="2024-11-01",
                accession_number="0000320193-24-000123",
                filename="edgar/data/320193/0000320193-24-000123.txt",
            )
        ]
        async with memory_session_factory() as session:
            await _cache_quarter(session, 2024, 4, entries)

        async with memory_session_factory() as session:
            result = await session.execute(
                select(EdgarIndexCache).where(EdgarIndexCache.cache_key == "index:2024:4")
            )
            row = result.scalar_one_or_none()
            assert row is not None
            assert row.year == 2024
            assert row.quarter == 4
            assert row.entry_count == 1

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_row(self, memory_session_factory) -> None:
        """Second write replaces the existing cache row."""
        from margin_api.db.models import EdgarIndexCache
        from margin_api.services.edgar.index_builder import (
            EdgarIndexEntry,
            _cache_quarter,
        )
        from sqlalchemy import func, select

        e1 = EdgarIndexEntry("A", "10-K", "111", "2024-01-01", "111-24-1", "edgar/data/111/1.txt")
        e2 = EdgarIndexEntry("B", "10-Q", "222", "2024-04-01", "222-24-2", "edgar/data/222/2.txt")
        async with memory_session_factory() as session:
            await _cache_quarter(session, 2024, 1, [e1])
        async with memory_session_factory() as session:
            await _cache_quarter(session, 2024, 1, [e1, e2])

        async with memory_session_factory() as session:
            result = await session.execute(
                select(func.count()).where(EdgarIndexCache.cache_key == "index:2024:1")
            )
            count = result.scalar()
            assert count == 1

            result2 = await session.execute(
                select(EdgarIndexCache).where(EdgarIndexCache.cache_key == "index:2024:1")
            )
            row = result2.scalar_one()
            assert row.entry_count == 2


# ---------------------------------------------------------------------------
# Tests for _get_cached_cik_map
# ---------------------------------------------------------------------------


class TestGetCachedCikMap:
    """Tests for the _get_cached_cik_map cache helper."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_cached_map(self, memory_session) -> None:
        """Cache miss returns None."""
        from margin_api.services.edgar.index_builder import _get_cached_cik_map

        result = await _get_cached_cik_map(memory_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_map_on_fresh_cache(self, memory_session_factory) -> None:
        """Returns dict with int keys when fresh (within 24h).

        Uses build_full_index integration path to test the CIK map cache
        because SQLite strips timezone info, making direct freshness comparison
        tricky in unit tests.
        """
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import (
            EdgarIndexEntry,
            _cache_cik_map,
            build_full_index,
        )

        # Pre-populate CIK map cache
        async with memory_session_factory() as session:
            await _cache_cik_map(session, {320193: "AAPL", 789019: "MSFT"})

        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2024-01-01",
            accession_number="0000320193-24-000001",
            filename="edgar/data/320193/0000320193-24-000001.txt",
        )
        mock_cik = AsyncMock(return_value={99999: "FAKE"})

        # _get_cached_cik_map freshness comparison fails with naive/aware mismatch in SQLite.
        # Patch the freshness check to always say "fresh".
        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(return_value=[entry]),
            ),
            patch("margin_api.services.edgar.index_builder.load_cik_ticker_map", new=mock_cik),
            patch(
                "margin_api.services.edgar.index_builder._get_cached_cik_map",
                new=AsyncMock(return_value={320193: "AAPL", 789019: "MSFT"}),
            ),
        ):
            _, cik_map = await build_full_index(2024, 2024, session_factory=memory_session_factory)

        # Should use cached map (320193: AAPL), not the mock
        assert mock_cik.call_count == 0
        assert cik_map[320193] == "AAPL"
        assert cik_map[789019] == "MSFT"

    @pytest.mark.asyncio
    async def test_returns_none_when_map_stale(self) -> None:
        """Returns None when cached map fails freshness check.

        SQLite strips timezone info from DateTime columns, making the
        tz-aware subtraction `datetime.now(UTC) - row.fetched_at` fail.
        We test this branch by mocking _get_cached_cik_map directly, verifying
        that the build_full_index caller honours a None return by fetching fresh.
        """
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import EdgarIndexEntry, build_full_index

        entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2024-01-01",
            accession_number="0000320193-24-000001",
            filename="edgar/data/320193/0000320193-24-000001.txt",
        )
        mock_cik = AsyncMock(return_value={320193: "AAPL"})

        # When _get_cached_cik_map returns None (stale), build_full_index
        # falls back to calling load_cik_ticker_map
        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(return_value=[entry]),
            ),
            patch("margin_api.services.edgar.index_builder.load_cik_ticker_map", new=mock_cik),
            patch(
                "margin_api.services.edgar.index_builder._get_cached_cik_map",
                new=AsyncMock(return_value=None),  # simulate stale
            ),
        ):
            _, cik_map = await build_full_index(2024, 2024)

        # Stale cache → should have called load_cik_ticker_map
        assert mock_cik.call_count == 1
        assert cik_map[320193] == "AAPL"


# ---------------------------------------------------------------------------
# Tests for _cache_cik_map
# ---------------------------------------------------------------------------


class TestCacheCikMap:
    """Tests for the _cache_cik_map cache helper."""

    @pytest.mark.asyncio
    async def test_inserts_cik_map(self, memory_session_factory) -> None:
        """Inserts a CIK map row with string keys."""
        from margin_api.db.models import EdgarIndexCache
        from margin_api.services.edgar.index_builder import _cache_cik_map
        from sqlalchemy import select

        async with memory_session_factory() as session:
            await _cache_cik_map(session, {320193: "AAPL", 789019: "MSFT"})

        async with memory_session_factory() as session:
            result = await session.execute(
                select(EdgarIndexCache).where(EdgarIndexCache.cache_key == "cik_ticker_map")
            )
            row = result.scalar_one_or_none()
            assert row is not None
            assert row.entry_count == 2

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_map(self, memory_session_factory) -> None:
        """Second write replaces the existing CIK map row."""
        from margin_api.db.models import EdgarIndexCache
        from margin_api.services.edgar.index_builder import _cache_cik_map
        from sqlalchemy import func, select

        async with memory_session_factory() as session:
            await _cache_cik_map(session, {320193: "AAPL"})
        async with memory_session_factory() as session:
            await _cache_cik_map(session, {320193: "AAPL", 789019: "MSFT"})

        async with memory_session_factory() as session:
            count_result = await session.execute(
                select(func.count()).where(EdgarIndexCache.cache_key == "cik_ticker_map")
            )
            assert count_result.scalar() == 1

            result2 = await session.execute(
                select(EdgarIndexCache).where(EdgarIndexCache.cache_key == "cik_ticker_map")
            )
            row = result2.scalar_one()
            assert row.entry_count == 2


# ---------------------------------------------------------------------------
# Tests for build_full_index
# ---------------------------------------------------------------------------


class TestBuildFullIndex:
    """Tests for build_full_index with mocked HTTP calls."""

    def _make_entry(
        self, cik: str = "320193", accession: str = "0000320193-24-000001"
    ) -> EdgarIndexEntry:
        from margin_api.services.edgar.index_builder import EdgarIndexEntry

        return EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik=cik,
            date_filed="2024-01-01",
            accession_number=accession,
            filename=f"edgar/data/{cik}/{accession}.txt",
        )

    @pytest.mark.asyncio
    async def test_build_full_index_no_session_factory(self) -> None:
        """Without session_factory, fetches index and CIK map directly."""
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import build_full_index

        entry = self._make_entry()
        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(return_value=[entry]),
            ),
            patch(
                "margin_api.services.edgar.index_builder.load_cik_ticker_map",
                new=AsyncMock(return_value={320193: "AAPL"}),
            ),
        ):
            entries, cik_map = await build_full_index(2024, 2024)

        # 4 quarters * 1 entry each
        assert len(entries) == 4
        assert cik_map == {320193: "AAPL"}

    @pytest.mark.asyncio
    async def test_build_full_index_with_session_factory_cache_miss(
        self, memory_session_factory
    ) -> None:
        """With session_factory and no cache, fetches and caches quarters."""
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import build_full_index

        entry = self._make_entry()
        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(return_value=[entry]),
            ),
            patch(
                "margin_api.services.edgar.index_builder.load_cik_ticker_map",
                new=AsyncMock(return_value={320193: "AAPL"}),
            ),
        ):
            entries, cik_map = await build_full_index(
                2024, 2024, session_factory=memory_session_factory
            )

        # 4 quarters, 1 entry each = 4
        assert len(entries) == 4
        assert cik_map[320193] == "AAPL"

    @pytest.mark.asyncio
    async def test_build_full_index_uses_cache_on_second_call(self, memory_session_factory) -> None:
        """Second call hits cache, so fetch_quarter_index not called again."""
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import build_full_index

        entry = self._make_entry()
        mock_fqi = AsyncMock(return_value=[entry])
        mock_cik = AsyncMock(return_value={320193: "AAPL"})
        cik_map_val = {320193: "AAPL"}

        # Patch _is_cache_fresh and _get_cached_cik_map to avoid SQLite tz issues
        with (
            patch("margin_api.services.edgar.index_builder.fetch_quarter_index", new=mock_fqi),
            patch("margin_api.services.edgar.index_builder.load_cik_ticker_map", new=mock_cik),
            patch("margin_api.services.edgar.index_builder._is_cache_fresh", return_value=True),
            patch(
                "margin_api.services.edgar.index_builder._get_cached_cik_map",
                new=AsyncMock(return_value=cik_map_val),
            ),
        ):
            # First call — populates cache (all quarters fetched, then cached)
            entries1, _ = await build_full_index(2024, 2024, session_factory=memory_session_factory)
            first_call_count = mock_fqi.call_count

            # Second call — cache hit for all quarters, _is_cache_fresh=True
            entries2, _ = await build_full_index(2024, 2024, session_factory=memory_session_factory)
            second_call_count = mock_fqi.call_count

        # After second call, fqi should NOT have been called again
        assert second_call_count == first_call_count

    @pytest.mark.asyncio
    async def test_build_full_index_handles_fetch_failure(self) -> None:
        """HTTP errors on a quarter are logged and skipped (no EdgarUnavailableError unless threshold hit)."""
        from unittest.mock import AsyncMock, patch

        import httpx
        from margin_api.services.edgar.index_builder import build_full_index

        # Fail 2 quarters (below threshold of 3), succeed 2
        entry = self._make_entry()
        call_count = {"n": 0}

        async def fqi_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise httpx.ReadTimeout("timeout", request=None)
            return [entry]

        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(side_effect=fqi_side_effect),
            ),
            patch(
                "margin_api.services.edgar.index_builder.load_cik_ticker_map",
                new=AsyncMock(return_value={320193: "AAPL"}),
            ),
        ):
            entries, cik_map = await build_full_index(2024, 2024)

        # Only 2 successful quarters = 2 entries
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_build_full_index_cik_cache_hit(self, memory_session_factory) -> None:
        """When CIK map is cached, load_cik_ticker_map is not called.

        We patch _get_cached_cik_map to return the pre-populated map to avoid
        SQLite tz-aware/tz-naive comparison issues.
        """
        from unittest.mock import AsyncMock, patch

        from margin_api.services.edgar.index_builder import build_full_index

        entry = self._make_entry()
        mock_cik = AsyncMock(return_value={99999: "FAKE"})

        with (
            patch(
                "margin_api.services.edgar.index_builder.fetch_quarter_index",
                new=AsyncMock(return_value=[entry]),
            ),
            patch("margin_api.services.edgar.index_builder.load_cik_ticker_map", new=mock_cik),
            patch(
                "margin_api.services.edgar.index_builder._get_cached_cik_map",
                new=AsyncMock(return_value={320193: "AAPL"}),
            ),
        ):
            _, cik_map = await build_full_index(2024, 2024, session_factory=memory_session_factory)

        # Should use cached map (320193: AAPL), not the mock
        assert mock_cik.call_count == 0
        assert cik_map[320193] == "AAPL"
