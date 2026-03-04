# EDGAR Fetch Resilience Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make SEC EDGAR fetching resilient to timeouts with tenacity retries, per-quarter index caching, an adaptive circuit breaker, and configurable timeouts.

**Architecture:** Add tenacity retry decorators to all SEC-facing HTTP functions. Introduce a new `edgar_index_cache` DB table so quarter index fetches survive worker restarts. A `ConsecutiveFailureTracker` detects when SEC is down vs temporarily slow. Timeouts become configurable via `MARGIN_EDGAR_TIMEOUT` env var.

**Tech Stack:** tenacity, httpx, SQLAlchemy 2.0 (async), Alembic, pytest

---

### Task 1: Add tenacity dependency

**Files:**
- Modify: `api/pyproject.toml:6-28`

**Step 1: Add tenacity to dependencies**

In `api/pyproject.toml`, add `"tenacity>=9.0.0"` to the `dependencies` list (after `"slowapi>=0.1.9"`):

```toml
    "slowapi>=0.1.9",
    "tenacity>=9.0.0",
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: Success, tenacity installed

**Step 3: Verify import**

Run: `uv run python -c "import tenacity; print(tenacity.__version__)"`
Expected: Prints version number (9.x.x)

**Step 4: Commit**

```bash
git add api/pyproject.toml uv.lock
git commit -m "chore: add tenacity dependency for EDGAR retry logic"
```

---

### Task 2: Add retry decorators to index_builder.py

**Files:**
- Modify: `api/src/margin_api/services/edgar/index_builder.py`
- Test: `api/tests/services/test_edgar_index_builder.py`

**Step 1: Write failing tests for retry behavior**

Add to `api/tests/services/test_edgar_index_builder.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from margin_api.services.edgar.index_builder import (
    EdgarIndexEntry,
    fetch_quarter_index,
    load_cik_ticker_map,
    parse_company_idx,
)


class TestFetchQuarterIndexRetry:
    """Tests for fetch_quarter_index retry behavior."""

    @pytest.mark.asyncio
    async def test_retries_on_read_timeout(self) -> None:
        """Should retry on ReadTimeout and succeed on second attempt."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_IDX
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[httpx.ReadTimeout("timeout"), mock_response]
        )

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
        mock_client.get = AsyncMock(
            side_effect=[httpx.ConnectTimeout("timeout"), mock_response]
        )

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
            side_effect=httpx.HTTPStatusError(
                "404", request=error_request, response=error_response
            )
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
        mock_client.get = AsyncMock(
            side_effect=[httpx.ReadTimeout("timeout"), mock_response]
        )

        result = await load_cik_ticker_map(mock_client)
        assert result == {320193: "AAPL"}
        assert mock_client.get.call_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py::TestFetchQuarterIndexRetry -v`
Expected: FAIL — functions don't retry yet

**Step 3: Add retry logic to index_builder.py**

Replace the imports and function signatures in `api/src/margin_api/services/edgar/index_builder.py`:

```python
"""EDGAR full-index parser and CIK-to-ticker mapper.

Parses SEC EDGAR company.idx files to discover 10-K/10-Q filings and maps
CIK numbers to tickers using the SEC company_tickers.json endpoint.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

SEC_BASE = "https://www.sec.gov"
USER_AGENT = "MarginInvest admin@margininvest.com"
FORM_TYPES: set[str] = {"10-K", "10-Q", "10-K/A", "10-Q/A"}

# Configurable timeout via environment variable (seconds)
EDGAR_TIMEOUT = float(os.environ.get("MARGIN_EDGAR_TIMEOUT", "60"))

_ACCESSION_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")
```

Keep the `_IDX_LINE_RE`, `EdgarIndexEntry`, and `parse_company_idx` unchanged.

Replace `fetch_quarter_index` (lines 124-144):

```python
def _is_retryable_http_error(exc: BaseException) -> bool:
    """Return True for 5xx HTTP errors (server-side, retryable)."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


@retry(
    retry=(
        retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectTimeout))
        | retry_if_exception_type(httpx.HTTPStatusError, _is_retryable_http_error)
    ),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
async def fetch_quarter_index(
    client: httpx.AsyncClient,
    year: int,
    quarter: int,
    form_types: set[str] | None = None,
) -> list[EdgarIndexEntry]:
    """Download and parse a single quarter's company.idx from EDGAR.

    Retries up to 5 times with exponential backoff on timeouts and 5xx errors.
    4xx errors are not retried (they indicate bad URLs, not transient issues).
    """
    url = f"{SEC_BASE}/Archives/edgar/full-index/{year}/QTR{quarter}/company.idx"
    logger.debug("Fetching quarter index: %s", url)
    resp = await client.get(url)
    resp.raise_for_status()
    return parse_company_idx(resp.text, form_types=form_types)
```

Replace `load_cik_ticker_map` (lines 147-167):

```python
@retry(
    retry=(
        retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectTimeout))
        | retry_if_exception_type(httpx.HTTPStatusError, _is_retryable_http_error)
    ),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
async def load_cik_ticker_map(client: httpx.AsyncClient) -> dict[int, str]:
    """Download the SEC company_tickers.json and return a CIK -> ticker mapping.

    Retries up to 5 times with exponential backoff on timeouts and 5xx errors.
    """
    url = f"{SEC_BASE}/files/company_tickers.json"
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    cik_map: dict[int, str] = {}
    for entry in data.values():
        cik = int(entry["cik_str"])
        ticker = str(entry["ticker"]).upper()
        cik_map[cik] = ticker

    return cik_map
```

Update `build_full_index` to use `EDGAR_TIMEOUT` (line 192):

```python
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_TIMEOUT),
    ) as client:
```

**Important note about tenacity's `retry_if_exception_type` with a predicate:** The syntax `retry_if_exception_type(httpx.HTTPStatusError, _is_retryable_http_error)` is NOT valid. Instead use:

```python
from tenacity import retry_if_exception

def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False
```

And then the decorator becomes:

```python
@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py -v`
Expected: All tests PASS (both old and new)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/index_builder.py api/tests/services/test_edgar_index_builder.py
git commit -m "feat(edgar): add tenacity retry to fetch_quarter_index and load_cik_ticker_map"
```

---

### Task 3: Add retry to fetch_and_parse_filing in backfill.py

**Files:**
- Modify: `api/src/margin_api/services/edgar/backfill.py:158-231`
- Test: `api/tests/services/test_edgar_backfill.py`

**Step 1: Write failing tests**

Add to `api/tests/services/test_edgar_backfill.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from margin_api.services.edgar.backfill import fetch_and_parse_filing
from margin_api.services.edgar.index_builder import EdgarIndexEntry


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

        # First call: index page (timeout), second: index page (success),
        # third: XBRL file (success)
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

        with patch(
            "margin_api.services.edgar.backfill.extract_financials"
        ) as mock_extract:
            mock_extract.return_value = MagicMock()
            result = await fetch_and_parse_filing(mock_client, entry)

        assert result is not None
        # 1 failed + 1 success (index) + 1 success (xbrl)
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Should NOT retry on 404 — returns None immediately."""
        entry = self._make_entry()

        error_request = httpx.Request("GET", "https://sec.gov/test")
        error_response = httpx.Response(404, request=error_request)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404", request=error_request, response=error_response
            )
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
        assert mock_client.get.call_count == 5  # 5 retry attempts
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_edgar_backfill.py::TestFetchAndParseFilingRetry -v`
Expected: FAIL — no retry logic yet

**Step 3: Implement retry in backfill.py**

Add imports at top of `api/src/margin_api/services/edgar/backfill.py`:

```python
import os

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)
```

Add the retryable predicate (near top, after imports):

```python
# Configurable timeout via environment variable (seconds)
EDGAR_FILING_TIMEOUT = float(os.environ.get("MARGIN_EDGAR_TIMEOUT", "45"))


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False
```

Split `fetch_and_parse_filing` into an inner retryable function and an outer function that catches permanent failures:

```python
@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
async def _fetch_filing_with_retry(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
    rate_limiter: _RateLimiter | None = None,
) -> XBRLFinancials | None:
    """Inner retryable filing fetch. Raises on transient errors for tenacity to retry."""
    cik_int = entry.cik_int
    accession_clean = entry.accession_number.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/"

    if rate_limiter:
        await rate_limiter.acquire()
    else:
        await asyncio.sleep(0.2)

    resp = await client.get(index_url)
    resp.raise_for_status()

    matches = _XBRL_FILE_RE.findall(resp.text)
    xbrl_file = None
    for match in matches:
        filename = match.rsplit("/", 1)[-1]
        if filename.startswith("R") and filename[1:2].isdigit():
            continue
        if filename.lower().endswith(".xml"):
            xbrl_file = match
            break

    if not xbrl_file:
        logger.warning("No XBRL file found for accession %s", entry.accession_number)
        return None

    if xbrl_file.startswith("http"):
        xbrl_url = xbrl_file
    elif xbrl_file.startswith("/"):
        xbrl_url = f"https://www.sec.gov{xbrl_file}"
    else:
        xbrl_url = f"{index_url}{xbrl_file}"

    if rate_limiter:
        await rate_limiter.acquire()
    else:
        await asyncio.sleep(0.2)

    xbrl_resp = await client.get(xbrl_url)
    xbrl_resp.raise_for_status()

    return extract_financials(xbrl_resp.text)


async def fetch_and_parse_filing(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
    rate_limiter: _RateLimiter | None = None,
) -> XBRLFinancials | None:
    """Download an XBRL filing from SEC EDGAR and parse it.

    Retries transient errors (timeouts, 5xx) up to 5 times.
    Returns None on permanent failures (4xx, parse errors).
    """
    try:
        return await _fetch_filing_with_retry(client, entry, rate_limiter)
    except (httpx.HTTPStatusError, httpx.ReadTimeout, httpx.ConnectTimeout):
        logger.warning(
            "Failed to fetch filing %s after retries",
            entry.accession_number,
            exc_info=True,
        )
        return None
    except Exception:
        logger.warning(
            "Failed to fetch/parse filing %s",
            entry.accession_number,
            exc_info=True,
        )
        return None
```

Also update the httpx client timeout in `run_edgar_backfill` (line 416):

```python
        timeout=httpx.Timeout(EDGAR_FILING_TIMEOUT),
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_edgar_backfill.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/backfill.py api/tests/services/test_edgar_backfill.py
git commit -m "feat(edgar): add tenacity retry to fetch_and_parse_filing"
```

---

### Task 4: Add EdgarIndexCache model and Alembic migration

**Files:**
- Modify: `api/src/margin_api/db/models.py` (after `PITFinancialSnapshot`, around line 1081)
- Create: Alembic migration via `alembic revision --autogenerate`

**Step 1: Write failing test for model**

Add new file `api/tests/test_edgar_index_cache_model.py`:

```python
"""Tests for EdgarIndexCache model."""

from __future__ import annotations

from margin_api.db.models import EdgarIndexCache


class TestEdgarIndexCacheModel:
    """Verify EdgarIndexCache model fields exist."""

    def test_tablename(self) -> None:
        assert EdgarIndexCache.__tablename__ == "edgar_index_cache"

    def test_has_required_columns(self) -> None:
        cols = {c.name for c in EdgarIndexCache.__table__.columns}
        assert "id" in cols
        assert "year" in cols
        assert "quarter" in cols
        assert "entries_json" in cols
        assert "entry_count" in cols
        assert "fetched_at" in cols
        assert "cache_key" in cols
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_edgar_index_cache_model.py -v`
Expected: FAIL — `EdgarIndexCache` not defined

**Step 3: Add model to models.py**

Insert after the `PITFinancialSnapshot` class (after line 1081) in `api/src/margin_api/db/models.py`:

```python
class EdgarIndexCache(Base):
    """Cache of parsed EDGAR quarter index entries for resumable backfills."""

    __tablename__ = "edgar_index_cache"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    cache_key: Mapped[str] = mapped_column(String(20), unique=True)
    entries_json: Mapped[dict | list] = mapped_column(JSONVariant)
    entry_count: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_edgar_index_cache_year_quarter", "year", "quarter", unique=True),
    )
```

The `cache_key` column will store either `"index:{year}:{quarter}"` or `"cik_ticker_map"` for the CIK map cache.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_edgar_index_cache_model.py -v`
Expected: PASS

**Step 5: Generate Alembic migration**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic revision --autogenerate -m "add edgar_index_cache table"`
Expected: New migration file created

**Step 6: Check for multiple heads**

Run: `uv run alembic heads`
Expected: Single head. If multiple, create a merge migration.

**Step 7: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/ api/tests/test_edgar_index_cache_model.py
git commit -m "feat(db): add EdgarIndexCache model and migration"
```

---

### Task 5: Implement per-quarter index caching in build_full_index

**Files:**
- Modify: `api/src/margin_api/services/edgar/index_builder.py:170-201`
- Test: `api/tests/services/test_edgar_index_builder.py`

**Step 1: Write failing tests**

Add to `api/tests/services/test_edgar_index_builder.py`:

```python
from datetime import datetime, timezone

from margin_api.services.edgar.index_builder import (
    _get_cached_quarter,
    _cache_quarter,
    _is_cache_fresh,
)


class TestIndexCaching:
    """Tests for per-quarter index caching helpers."""

    def test_is_cache_fresh_past_quarter_always_fresh(self) -> None:
        """Past quarters are always fresh (data doesn't change)."""
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert _is_cache_fresh(old_time, 2020, 1) is True

    def test_is_cache_fresh_current_quarter_under_24h(self) -> None:
        """Current quarter cache under 24h is fresh."""
        now = datetime.now(timezone.utc)
        assert _is_cache_fresh(now, now.year, (now.month - 1) // 3 + 1) is True

    def test_is_cache_fresh_current_quarter_over_24h(self) -> None:
        """Current quarter cache over 24h is stale."""
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        now = datetime.now(timezone.utc)
        current_quarter = (now.month - 1) // 3 + 1
        assert _is_cache_fresh(old_time, now.year, current_quarter) is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py::TestIndexCaching -v`
Expected: FAIL — functions not defined

**Step 3: Implement caching helpers and update build_full_index**

Add to `api/src/margin_api/services/edgar/index_builder.py` (after the existing functions, before `build_full_index`):

```python
from datetime import datetime, timedelta, timezone
from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


def _is_cache_fresh(fetched_at: datetime, year: int, quarter: int) -> bool:
    """Check if a cached quarter index is still fresh.

    Past quarters never change, so their cache is always fresh.
    Current quarter cache expires after 24 hours.
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_quarter = (now.month - 1) // 3 + 1

    if year < current_year or (year == current_year and quarter < current_quarter):
        return True  # Past quarters are immutable

    return (now - fetched_at) < timedelta(hours=24)


async def _get_cached_quarter(
    session: AsyncSession,
    year: int,
    quarter: int,
) -> list[EdgarIndexEntry] | None:
    """Load cached quarter index entries from DB, or None if not cached/stale."""
    from margin_api.db.models import EdgarIndexCache

    cache_key = f"index:{year}:{quarter}"
    result = await session.execute(
        select(EdgarIndexCache).where(EdgarIndexCache.cache_key == cache_key)
    )
    row = result.scalar_one_or_none()

    if row is None:
        return None

    if not _is_cache_fresh(row.fetched_at, year, quarter):
        return None

    return [
        EdgarIndexEntry(**entry)
        for entry in row.entries_json
    ]


async def _cache_quarter(
    session: AsyncSession,
    year: int,
    quarter: int,
    entries: list[EdgarIndexEntry],
) -> None:
    """Save quarter index entries to DB cache."""
    from margin_api.db.models import EdgarIndexCache
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    cache_key = f"index:{year}:{quarter}"
    entries_data = [asdict(e) for e in entries]

    stmt = pg_insert(EdgarIndexCache).values(
        year=year,
        quarter=quarter,
        cache_key=cache_key,
        entries_json=entries_data,
        entry_count=len(entries),
        fetched_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["cache_key"],
        set_={
            "entries_json": stmt.excluded.entries_json,
            "entry_count": stmt.excluded.entry_count,
            "fetched_at": stmt.excluded.fetched_at,
        },
    )
    await session.execute(stmt)
    await session.commit()


async def _get_cached_cik_map(session: AsyncSession) -> dict[int, str] | None:
    """Load cached CIK-to-ticker map from DB."""
    from margin_api.db.models import EdgarIndexCache

    cache_key = "cik_ticker_map"
    result = await session.execute(
        select(EdgarIndexCache).where(EdgarIndexCache.cache_key == cache_key)
    )
    row = result.scalar_one_or_none()

    if row is None:
        return None

    # CIK map refreshes daily
    if not _is_cache_fresh(row.fetched_at, datetime.now(timezone.utc).year,
                           (datetime.now(timezone.utc).month - 1) // 3 + 1):
        return None

    return {int(k): v for k, v in row.entries_json.items()}


async def _cache_cik_map(session: AsyncSession, cik_map: dict[int, str]) -> None:
    """Save CIK-to-ticker map to DB cache."""
    from margin_api.db.models import EdgarIndexCache
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    cache_key = "cik_ticker_map"
    # JSON keys must be strings
    json_data = {str(k): v for k, v in cik_map.items()}

    stmt = pg_insert(EdgarIndexCache).values(
        year=0,
        quarter=0,
        cache_key=cache_key,
        entries_json=json_data,
        entry_count=len(cik_map),
        fetched_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["cache_key"],
        set_={
            "entries_json": stmt.excluded.entries_json,
            "entry_count": stmt.excluded.entry_count,
            "fetched_at": stmt.excluded.fetched_at,
        },
    )
    await session.execute(stmt)
    await session.commit()
```

Update `build_full_index` signature and body:

```python
async def build_full_index(
    start_year: int,
    end_year: int,
    form_types: set[str] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> tuple[list[EdgarIndexEntry], dict[int, str]]:
    """Build a complete EDGAR filing index across multiple years.

    If session_factory is provided, uses per-quarter DB caching for
    resumable backfills. Otherwise fetches everything from SEC directly.
    """
    all_entries: list[EdgarIndexEntry] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_TIMEOUT),
    ) as client:
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                # Try cache first
                if session_factory is not None:
                    async with session_factory() as session:
                        cached = await _get_cached_quarter(session, year, quarter)
                    if cached is not None:
                        logger.debug("Using cached index for %d-Q%d (%d entries)", year, quarter, len(cached))
                        all_entries.extend(cached)
                        continue

                # Fetch from SEC
                entries = await fetch_quarter_index(client, year, quarter, form_types=form_types)
                all_entries.extend(entries)

                # Cache the result
                if session_factory is not None:
                    async with session_factory() as session:
                        await _cache_quarter(session, year, quarter, entries)
                    logger.debug("Cached index for %d-Q%d (%d entries)", year, quarter, len(entries))

        # CIK ticker map
        cik_map: dict[int, str] | None = None
        if session_factory is not None:
            async with session_factory() as session:
                cik_map = await _get_cached_cik_map(session)

        if cik_map is None:
            cik_map = await load_cik_ticker_map(client)
            if session_factory is not None:
                async with session_factory() as session:
                    await _cache_cik_map(session, cik_map)

    return all_entries, cik_map
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py -v`
Expected: All tests PASS

**Step 5: Update run_edgar_backfill to pass session_factory to build_full_index**

In `api/src/margin_api/services/edgar/backfill.py`, update line 298:

```python
    all_entries, cik_map = await build_full_index(
        start_year, end_year, session_factory=session_factory
    )
```

**Step 6: Run all EDGAR tests**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py api/tests/services/test_edgar_backfill.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/services/edgar/index_builder.py api/src/margin_api/services/edgar/backfill.py api/tests/services/test_edgar_index_builder.py
git commit -m "feat(edgar): add per-quarter index caching in build_full_index"
```

---

### Task 6: Add ConsecutiveFailureTracker and EdgarUnavailableError

**Files:**
- Modify: `api/src/margin_api/services/edgar/index_builder.py`
- Modify: `api/src/margin_api/services/edgar/backfill.py`
- Test: `api/tests/services/test_edgar_index_builder.py`
- Test: `api/tests/services/test_edgar_backfill.py`

**Step 1: Write failing tests for circuit breaker**

Add to `api/tests/services/test_edgar_index_builder.py`:

```python
from margin_api.services.edgar.index_builder import (
    ConsecutiveFailureTracker,
    EdgarUnavailableError,
)


class TestConsecutiveFailureTracker:
    """Tests for ConsecutiveFailureTracker."""

    def test_no_trip_below_threshold(self) -> None:
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        # 2 failures, threshold is 3 — should not raise

    def test_trips_at_threshold(self) -> None:
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        with pytest.raises(EdgarUnavailableError, match="3 consecutive"):
            tracker.record_failure()

    def test_resets_on_success(self) -> None:
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure()
        tracker.record_failure()
        tracker.record_success()  # Reset
        tracker.record_failure()
        tracker.record_failure()
        # Only 2 consecutive failures after reset — should not raise

    def test_trips_after_reset_and_new_failures(self) -> None:
        tracker = ConsecutiveFailureTracker(threshold=2)
        tracker.record_failure()
        tracker.record_success()
        tracker.record_failure()
        with pytest.raises(EdgarUnavailableError):
            tracker.record_failure()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py::TestConsecutiveFailureTracker -v`
Expected: FAIL — classes not defined

**Step 3: Implement ConsecutiveFailureTracker**

Add to `api/src/margin_api/services/edgar/index_builder.py` (before `build_full_index`):

```python
class EdgarUnavailableError(Exception):
    """Raised when SEC EDGAR appears to be down after consecutive failures."""


class ConsecutiveFailureTracker:
    """Tracks consecutive failures and raises EdgarUnavailableError at threshold.

    Resets the counter on any success. This distinguishes "SEC is temporarily
    slow" (occasional failures mixed with successes) from "SEC is down"
    (many consecutive failures).
    """

    def __init__(self, threshold: int = 3) -> None:
        self._threshold = threshold
        self._consecutive_failures = 0

    def record_success(self) -> None:
        """Reset failure counter on success."""
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Increment failure counter; raise if threshold reached."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            raise EdgarUnavailableError(
                f"SEC EDGAR appears unreachable: {self._consecutive_failures} consecutive "
                f"quarter fetches failed (threshold={self._threshold}). "
                f"Aborting to avoid wasting resources."
            )
```

Wire it into `build_full_index`:

```python
async def build_full_index(
    start_year: int,
    end_year: int,
    form_types: set[str] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> tuple[list[EdgarIndexEntry], dict[int, str]]:
    """Build a complete EDGAR filing index across multiple years.

    Uses per-quarter DB caching (if session_factory provided) and an adaptive
    circuit breaker that aborts if 3 consecutive quarters fail all retries.
    """
    all_entries: list[EdgarIndexEntry] = []
    tracker = ConsecutiveFailureTracker(threshold=3)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_TIMEOUT),
    ) as client:
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                # Try cache first
                if session_factory is not None:
                    async with session_factory() as session:
                        cached = await _get_cached_quarter(session, year, quarter)
                    if cached is not None:
                        logger.debug("Using cached index for %d-Q%d (%d entries)", year, quarter, len(cached))
                        all_entries.extend(cached)
                        tracker.record_success()
                        continue

                # Fetch from SEC with circuit breaker
                try:
                    entries = await fetch_quarter_index(client, year, quarter, form_types=form_types)
                    all_entries.extend(entries)
                    tracker.record_success()

                    if session_factory is not None:
                        async with session_factory() as session:
                            await _cache_quarter(session, year, quarter, entries)
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPStatusError) as exc:
                    logger.warning(
                        "Failed to fetch index for %d-Q%d after retries: %s",
                        year, quarter, exc,
                    )
                    tracker.record_failure()  # May raise EdgarUnavailableError

        # CIK ticker map
        cik_map: dict[int, str] | None = None
        if session_factory is not None:
            async with session_factory() as session:
                cik_map = await _get_cached_cik_map(session)

        if cik_map is None:
            cik_map = await load_cik_ticker_map(client)
            if session_factory is not None:
                async with session_factory() as session:
                    await _cache_cik_map(session, cik_map)

    return all_entries, cik_map
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py -v`
Expected: All PASS

**Step 5: Add filing-level circuit breaker to backfill.py**

In `api/src/margin_api/services/edgar/backfill.py`, import and use the tracker in `run_edgar_backfill`. Add a `ConsecutiveFailureTracker` with threshold=10 for filing-level failures:

```python
from margin_api.services.edgar.index_builder import (
    USER_AGENT,
    EdgarIndexEntry,
    EdgarUnavailableError,
    ConsecutiveFailureTracker,
    build_full_index,
)
```

In the `_process_one` inner function, track consecutive failures:

```python
    filing_tracker = ConsecutiveFailureTracker(threshold=10)

    async def _process_one(
        entry: EdgarIndexEntry,
        ticker: str,
        client: httpx.AsyncClient,
    ) -> None:
        async with semaphore:
            fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)
            financials = await fetch_and_parse_filing(client, entry, rate_limiter)

            async with lock:
                if financials is None:
                    counters["failed"] += 1
                    try:
                        filing_tracker.record_failure()
                    except EdgarUnavailableError:
                        logger.warning(
                            "[edgar-backfill] %d consecutive filing failures — "
                            "skipping rest of chunk",
                            filing_tracker._consecutive_failures,
                        )
                        raise
                else:
                    filing_tracker.record_success()
                    async with session_factory() as session:
                        was_inserted = await insert_pit_snapshot(
                            session, entry, financials, ticker, fiscal_year, fiscal_quarter
                        )
                        await session.commit()
                        if was_inserted:
                            counters["inserted"] += 1
                        else:
                            counters["skipped"] += 1

                counters["done"] += 1
                done = counters["done"]

            if done % 100 == 0 or done == total:
                logger.info(
                    "[edgar-backfill] Processed %d/%d filings (%d inserted, %d skipped, %d failed)",
                    done, total, counters["inserted"], counters["skipped"], counters["failed"],
                )
```

In the chunk loop, catch `EdgarUnavailableError` to skip chunks:

```python
        for chunk_start in range(0, total, chunk_size):
            chunk = entries_to_process[chunk_start : chunk_start + chunk_size]
            tasks = [_process_one(entry, ticker, client) for entry, ticker in chunk]
            try:
                await asyncio.gather(*tasks)
            except EdgarUnavailableError:
                logger.warning(
                    "[edgar-backfill] Chunk at offset %d aborted due to consecutive failures, "
                    "moving to next chunk",
                    chunk_start,
                )
                filing_tracker.record_success()  # Reset for next chunk

            if checkpoint_file and chunk:
                last_entry = chunk[-1][0]
                Path(checkpoint_file).write_text(last_entry.accession_number)
```

**Step 6: Run all tests**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py api/tests/services/test_edgar_backfill.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/services/edgar/index_builder.py api/src/margin_api/services/edgar/backfill.py api/tests/services/test_edgar_index_builder.py api/tests/services/test_edgar_backfill.py
git commit -m "feat(edgar): add adaptive circuit breaker for index and filing fetches"
```

---

### Task 7: Update bootstrap_pit_data to handle EdgarUnavailableError

**Files:**
- Modify: `api/src/margin_api/workers.py:2769-2852`
- Test: `api/tests/test_workers.py` (or whichever file tests bootstrap_pit_data, if it exists)

**Step 1: Update workers.py**

In `api/src/margin_api/workers.py`, add import:

```python
from margin_api.services.edgar.index_builder import EdgarUnavailableError
```

In `bootstrap_pit_data`, wrap the EDGAR phase to catch `EdgarUnavailableError` distinctly:

```python
    try:
        # Phase 1: EDGAR backfill (2009-present)
        logger.info("[bootstrap_pit] Phase 1/4: EDGAR backfill...")
        edgar_result = await run_edgar_backfill(
            start_year=2009,
            end_year=datetime.now(UTC).year,
            session_factory=session_factory,
        )
        logger.info("[bootstrap_pit] EDGAR backfill complete: %s", edgar_result)

        # ... rest of phases unchanged ...

    except EdgarUnavailableError as e:
        logger.error("[bootstrap_pit] SEC EDGAR unavailable, aborting: %s", e)
        reset_engine_cache()
        engine = get_engine()
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "failed"
            job.error_message = f"SEC EDGAR unavailable: {e}"[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "error", "message": f"SEC EDGAR unavailable: {e}"}

    except Exception as e:
        # ... existing generic handler ...
```

**Step 2: Run existing worker tests (if any)**

Run: `uv run pytest api/tests/ -v -k "bootstrap_pit" --ignore=api/tests/services/test_xbrl_parser.py`
Expected: PASS (or no tests found — that's fine)

**Step 3: Run full API test suite**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(edgar): handle EdgarUnavailableError in bootstrap_pit_data"
```

---

### Task 8: Final integration test and cleanup

**Files:**
- All modified files from previous tasks

**Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All ~2621 tests PASS

**Step 2: Run full API test suite**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All ~1587+ tests PASS

**Step 3: Run linter**

Run: `uv run ruff check --fix . && uv run ruff format .`
Expected: No errors

**Step 4: Verify imports are clean**

Run: `uv run python -c "from margin_api.services.edgar.index_builder import build_full_index, EdgarUnavailableError, ConsecutiveFailureTracker; print('OK')"`
Expected: `OK`

Run: `uv run python -c "from margin_api.services.edgar.backfill import run_edgar_backfill, fetch_and_parse_filing; print('OK')"`
Expected: `OK`

**Step 5: Final commit if any lint fixes were applied**

```bash
git add -A
git commit -m "chore: lint fixes for EDGAR resilience changes"
```
