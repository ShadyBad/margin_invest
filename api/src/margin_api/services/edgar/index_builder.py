"""EDGAR full-index parser and CIK-to-ticker mapper.

Parses SEC EDGAR company.idx files to discover 10-K/10-Q filings and maps
CIK numbers to tickers using the SEC company_tickers.json endpoint.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

SEC_BASE = "https://www.sec.gov"
USER_AGENT = "MarginInvest admin@margininvest.com"
FORM_TYPES: set[str] = {"10-K", "10-Q", "10-K/A", "10-Q/A"}

logger = logging.getLogger(__name__)
EDGAR_TIMEOUT = float(os.environ.get("MARGIN_EDGAR_TIMEOUT", "60"))

_ACCESSION_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")

# Regex to parse SEC EDGAR company.idx fixed-width data lines.
# The format uses a 62-char company name column, followed by form type, CIK,
# date (YYYY-MM-DD), and filename (always starts with "edgar/").
# Data values are right-aligned and can overflow header column boundaries,
# so regex is more reliable than pure fixed-width slicing.
_IDX_LINE_RE = re.compile(
    r"^(.{62})"  # Company Name — always 62 chars wide
    r"(\S+(?:\s+\S+)*?)\s+"  # Form Type — e.g. "10-K", "10-K/A", "NT 10-Q"
    r"(\d+)\s+"  # CIK — integer
    r"(\d{4}-\d{2}-\d{2})\s+"  # Date Filed — YYYY-MM-DD
    r"(edgar/.+?)\s*$"  # Filename — always starts with "edgar/"
)


@dataclass(frozen=True, slots=True)
class EdgarIndexEntry:
    """A single filing entry from a company.idx file."""

    company_name: str
    form_type: str
    cik: str
    date_filed: str
    accession_number: str
    filename: str

    @property
    def cik_int(self) -> int:
        """CIK as integer, stripping any leading zeros."""
        return int(self.cik)


def parse_company_idx(
    raw: str,
    form_types: set[str] | None = None,
) -> list[EdgarIndexEntry]:
    """Parse SEC EDGAR company.idx fixed-width content into EdgarIndexEntry objects.

    The SEC EDGAR company.idx format has metadata headers, a column header line,
    a dashes separator, then fixed-width data lines::

        Company Name                                                  Form Type   CIK         Date Filed  File Name
        -------------------------------------------------------------------------------------------
        APPLE INC                                                     10-K             320193      2024-11-01  edgar/data/320193/...

    Args:
        raw: Raw text content of a company.idx file.
        form_types: Set of form types to include. Defaults to FORM_TYPES
            (10-K, 10-Q, 10-K/A, 10-Q/A).

    Returns:
        List of EdgarIndexEntry for matching filings.
    """
    if not raw or not raw.strip():
        return []

    target_forms = form_types if form_types is not None else FORM_TYPES
    entries: list[EdgarIndexEntry] = []

    # Find the separator line (all dashes) to know where data begins
    lines = raw.strip().splitlines()
    data_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("---"):
            data_start = i + 1
            break

    if data_start < 0 or data_start >= len(lines):
        return []

    for line in lines[data_start:]:
        if not line.strip():
            continue

        match = _IDX_LINE_RE.match(line)
        if not match:
            continue

        company_name = match.group(1).strip()
        form_type = match.group(2).strip()
        cik = match.group(3).strip()
        date_filed = match.group(4).strip()
        filename = match.group(5).strip()

        if form_type not in target_forms:
            continue

        # Extract accession number from filename
        acc_match = _ACCESSION_RE.search(filename)
        accession_number = acc_match.group(1) if acc_match else ""

        entries.append(
            EdgarIndexEntry(
                company_name=company_name,
                form_type=form_type,
                cik=cik,
                date_filed=date_filed,
                accession_number=accession_number,
                filename=filename,
            )
        )

    return entries


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
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

    Args:
        client: An httpx.AsyncClient (should have User-Agent set).
        year: Filing year (e.g. 2024).
        quarter: Quarter number (1-4).
        form_types: Set of form types to filter. Defaults to FORM_TYPES.

    Returns:
        List of EdgarIndexEntry for the quarter.
    """
    url = f"{SEC_BASE}/Archives/edgar/full-index/{year}/QTR{quarter}/company.idx"
    logger.debug("Fetching quarter index: %s", url)
    resp = await client.get(url)
    resp.raise_for_status()
    return parse_company_idx(resp.text, form_types=form_types)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
async def load_cik_ticker_map(client: httpx.AsyncClient) -> dict[int, str]:
    """Download the SEC company_tickers.json and return a CIK -> ticker mapping.

    Args:
        client: An httpx.AsyncClient (should have User-Agent set).

    Returns:
        Dictionary mapping CIK integers to ticker strings.
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


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=32, jitter=2),
    reraise=True,
)
async def load_cik_ticker_sic_map(client: httpx.AsyncClient) -> dict[int, tuple[str, int | None]]:
    """Download SEC company_tickers_exchange.json and return CIK -> (ticker, sic_code).

    Uses the exchange endpoint which includes SIC codes alongside tickers.

    Returns:
        Dictionary mapping CIK integers to (ticker, sic_code) tuples.
        SIC code is None if not available.
    """
    url = f"{SEC_BASE}/files/company_tickers_exchange.json"
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    fields = data.get("fields", [])
    rows = data.get("data", [])

    # Find column indices
    cik_idx = fields.index("cik")
    ticker_idx = fields.index("ticker")
    sic_idx = fields.index("sic") if "sic" in fields else None

    result: dict[int, tuple[str, int | None]] = {}
    for row in rows:
        cik = int(row[cik_idx])
        ticker = str(row[ticker_idx]).upper()
        sic_code = None
        if sic_idx is not None:
            raw_sic = row[sic_idx]
            if raw_sic and str(raw_sic).strip():
                try:
                    sic_code = int(raw_sic)
                except (ValueError, TypeError):
                    pass
        result[cik] = (ticker, sic_code)

    return result


# ---------------------------------------------------------------------------
# Per-quarter index caching helpers
# ---------------------------------------------------------------------------


def _is_cache_fresh(fetched_at: datetime, year: int, quarter: int) -> bool:
    """Determine whether a cached quarter index is still fresh.

    Past quarters (before the current quarter) are always fresh because
    SEC EDGAR data for completed quarters never changes.
    The current quarter expires after 24 hours since new filings may appear.

    Args:
        fetched_at: When the cache entry was fetched (tz-aware UTC).
        year: The year of the cached quarter.
        quarter: The quarter number (1-4) of the cached quarter.

    Returns:
        True if the cache is still fresh, False if it should be re-fetched.
    """
    now = datetime.now(UTC)
    current_year = now.year
    current_quarter = (now.month - 1) // 3 + 1

    # Past quarters (year < current year, or same year but earlier quarter)
    if year < current_year or (year == current_year and quarter < current_quarter):
        return True

    # Current or future quarter: fresh if fetched within last 24 hours
    return (now - fetched_at) < timedelta(hours=24)


async def _get_cached_quarter(
    session: AsyncSession,
    year: int,
    quarter: int,
) -> list[EdgarIndexEntry] | None:
    """Retrieve cached quarter index entries if available and fresh.

    Args:
        session: Async SQLAlchemy session.
        year: Filing year.
        quarter: Quarter number (1-4).

    Returns:
        List of EdgarIndexEntry if cache hit and fresh, None otherwise.
    """
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

    return [EdgarIndexEntry(**entry) for entry in row.entries_json]


async def _cache_quarter(
    session: AsyncSession,
    year: int,
    quarter: int,
    entries: list[EdgarIndexEntry],
) -> None:
    """Cache quarter index entries (delete-then-insert for SQLite compat).

    Args:
        session: Async SQLAlchemy session.
        year: Filing year.
        quarter: Quarter number (1-4).
        entries: List of EdgarIndexEntry to cache.
    """
    from margin_api.db.models import EdgarIndexCache

    cache_key = f"index:{year}:{quarter}"

    # Delete existing entry (upsert alternative that works with SQLite)
    existing = await session.execute(
        select(EdgarIndexCache).where(EdgarIndexCache.cache_key == cache_key)
    )
    old = existing.scalar_one_or_none()
    if old:
        await session.delete(old)
        await session.flush()

    row = EdgarIndexCache(
        year=year,
        quarter=quarter,
        cache_key=cache_key,
        entries_json=[asdict(e) for e in entries],
        entry_count=len(entries),
    )
    session.add(row)
    await session.commit()


async def _get_cached_cik_map(session: AsyncSession) -> dict[int, str] | None:
    """Retrieve cached CIK-to-ticker map if available and fresh.

    Uses 24-hour expiry (always treated as "current" for freshness).

    Args:
        session: Async SQLAlchemy session.

    Returns:
        Dict mapping CIK ints to ticker strings, or None if cache miss/stale.
    """
    from margin_api.db.models import EdgarIndexCache

    cache_key = "cik_ticker_map"
    result = await session.execute(
        select(EdgarIndexCache).where(EdgarIndexCache.cache_key == cache_key)
    )
    row = result.scalar_one_or_none()

    if row is None:
        return None

    # CIK map always uses 24h freshness (like current quarter)
    now = datetime.now(UTC)
    if (now - row.fetched_at) >= timedelta(hours=24):
        return None

    # JSON keys are strings — convert back to int
    return {int(k): v for k, v in row.entries_json.items()}


async def _cache_cik_map(session: AsyncSession, cik_map: dict[int, str]) -> None:
    """Cache CIK-to-ticker map (delete-then-insert for SQLite compat).

    Args:
        session: Async SQLAlchemy session.
        cik_map: Dict mapping CIK ints to ticker strings.
    """
    from margin_api.db.models import EdgarIndexCache

    cache_key = "cik_ticker_map"

    # Delete existing entry
    existing = await session.execute(
        select(EdgarIndexCache).where(EdgarIndexCache.cache_key == cache_key)
    )
    old = existing.scalar_one_or_none()
    if old:
        await session.delete(old)
        await session.flush()

    row = EdgarIndexCache(
        year=0,
        quarter=0,
        cache_key=cache_key,
        entries_json={str(k): v for k, v in cik_map.items()},
        entry_count=len(cik_map),
    )
    session.add(row)
    await session.commit()


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


async def build_full_index(
    start_year: int,
    end_year: int,
    form_types: set[str] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> tuple[list[EdgarIndexEntry], dict[int, str]]:
    """Build a complete EDGAR filing index across multiple years.

    Creates an httpx.AsyncClient with the required User-Agent header and
    iterates over all year/quarter combinations to build the index.
    When a session_factory is provided, uses per-quarter caching to avoid
    re-downloading data from SEC EDGAR for quarters that haven't changed.

    Args:
        start_year: First year to include (inclusive).
        end_year: Last year to include (inclusive).
        form_types: Set of form types to filter. Defaults to FORM_TYPES.
        session_factory: Optional async session factory for DB caching.
            When provided, cached quarter data is used when fresh.

    Returns:
        Tuple of (all_entries, cik_ticker_map).
    """
    all_entries: list[EdgarIndexEntry] = []
    tracker = ConsecutiveFailureTracker(threshold=3)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_TIMEOUT),
    ) as client:
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                # Try cache first if session_factory is available
                if session_factory is not None:
                    async with session_factory() as session:
                        cached = await _get_cached_quarter(session, year, quarter)
                    if cached is not None:
                        logger.debug(
                            "Cache hit for %d-Q%d (%d entries)", year, quarter, len(cached)
                        )
                        all_entries.extend(cached)
                        tracker.record_success()
                        continue

                try:
                    entries = await fetch_quarter_index(
                        client, year, quarter, form_types=form_types
                    )
                    all_entries.extend(entries)
                    tracker.record_success()
                except (
                    httpx.ReadTimeout,
                    httpx.ConnectTimeout,
                    httpx.HTTPStatusError,
                ) as exc:
                    logger.warning(
                        "Failed to fetch index for %d-Q%d after retries: %s",
                        year,
                        quarter,
                        exc,
                    )
                    tracker.record_failure()  # May raise EdgarUnavailableError
                    continue

                # Cache the fetched entries
                if session_factory is not None:
                    try:
                        async with session_factory() as session:
                            await _cache_quarter(session, year, quarter, entries)
                        logger.debug("Cached %d-Q%d (%d entries)", year, quarter, len(entries))
                    except Exception:
                        logger.warning(
                            "Failed to cache quarter index %d-Q%d",
                            year,
                            quarter,
                            exc_info=True,
                        )

        # Try CIK map cache
        cik_map: dict[int, str] | None = None
        if session_factory is not None:
            async with session_factory() as session:
                cik_map = await _get_cached_cik_map(session)
            if cik_map is not None:
                logger.debug("Cache hit for CIK ticker map (%d entries)", len(cik_map))

        if cik_map is None:
            cik_map = await load_cik_ticker_map(client)
            # Cache the CIK map
            if session_factory is not None:
                try:
                    async with session_factory() as session:
                        await _cache_cik_map(session, cik_map)
                    logger.debug("Cached CIK ticker map (%d entries)", len(cik_map))
                except Exception:
                    logger.warning("Failed to cache CIK ticker map", exc_info=True)

    return all_entries, cik_map
