"""EDGAR backfill service: downloads XBRL filings and inserts into pit_financial_snapshots.

Wires the EDGAR index builder and XBRL parser together with database insertion.
Supports checkpointing for resumable backfills and rate-limited SEC access.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from margin_api.db.models import EdgarNoXBRLCache, PITFinancialSnapshot
from margin_api.services.edgar.index_builder import (
    USER_AGENT,
    ConsecutiveFailureTracker,
    EdgarIndexEntry,
    EdgarUnavailableError,
    build_full_index,
)
from margin_api.services.edgar.xbrl_parser import XBRLFinancials, extract_financials

logger = logging.getLogger(__name__)

EDGAR_FILING_TIMEOUT = float(os.environ.get("MARGIN_EDGAR_TIMEOUT", "45"))


class NoXBRLAvailableError(Exception):
    """Raised when a filing has no XBRL file (expected for pre-2011 filings)."""


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and (
        exc.response.status_code == 429 or exc.response.status_code >= 500
    ):
        return True
    return False


# ---------------------------------------------------------------------------
# Period / fiscal inference helpers
# ---------------------------------------------------------------------------


def _infer_period_end(
    date_filed: date,
    form_type: str,
    fiscal_year: int,
    fiscal_quarter: int | None,
) -> date:
    """Infer the fiscal period end date from filing metadata.

    For quarterly filings: month = fiscal_quarter * 3, return date(fiscal_year, month, 28).
    For annual filings: return date(fiscal_year, 12, 31).
    """
    if form_type.startswith("10-K") or fiscal_quarter is None:
        return date(fiscal_year, 12, 31)

    month = fiscal_quarter * 3
    return date(fiscal_year, month, 28)


def _infer_fiscal_info(entry: EdgarIndexEntry) -> tuple[int, int | None]:
    """Infer fiscal_year and fiscal_quarter from form_type and date_filed.

    For 10-K/10-K/A: fiscal_year = year of date_filed (or year-1 if filed Jan-Mar),
    quarter = None.
    For 10-Q/10-Q/A: fiscal_year = year of date_filed,
    quarter inferred from filing month (months 1-4 -> Q1, 4-7 -> Q2, 7-10 -> Q3).
    """
    filed = date.fromisoformat(entry.date_filed)

    if entry.form_type.startswith("10-K"):
        # Annual filing — if filed early (Jan-Mar), it's for the prior year
        fiscal_year = filed.year if filed.month > 3 else filed.year - 1
        return fiscal_year, None

    # Quarterly filing (10-Q, 10-Q/A)
    # Filing month lags the quarter end by ~45 days, so:
    #   Filed months 1-5  → Q1 (period Jan-Mar, filed ~45 days after Mar 31)
    #   Filed months 5-8  → Q2 (period Apr-Jun, filed ~45 days after Jun 30)
    #   Filed months 8-11 → Q3 (period Jul-Sep, filed ~45 days after Sep 30)
    # (Q4 is reported on 10-K, not 10-Q)
    fiscal_year = filed.year
    month = filed.month

    if month <= 5:
        fiscal_quarter = 1
    elif month <= 8:
        fiscal_quarter = 2
    else:
        fiscal_quarter = 3

    return fiscal_year, fiscal_quarter


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------


def _build_snapshot_row(
    entry: EdgarIndexEntry,
    financials: XBRLFinancials,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: int | None,
    sic_code: int | None = None,
) -> dict[str, Any]:
    """Build a dict suitable for DB insertion into pit_financial_snapshots.

    Args:
        entry: EDGAR index entry with filing metadata.
        financials: Parsed XBRL financial data.
        ticker: Stock ticker symbol.
        fiscal_year: The fiscal year of the filing.
        fiscal_quarter: The fiscal quarter (None for annual 10-K filings).
        sic_code: Optional SIC industry code for this company.

    Returns:
        Dict with all columns for pit_financial_snapshots.
    """
    filing_date = date.fromisoformat(entry.date_filed)
    period_end = _infer_period_end(filing_date, entry.form_type, fiscal_year, fiscal_quarter)

    row: dict[str, Any] = {
        "cik": entry.cik,
        "ticker": ticker,
        "filing_date": filing_date,
        "period_end": period_end,
        "form_type": entry.form_type,
        "accession_number": entry.accession_number,
        "shares_outstanding": financials.shares_outstanding,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
    }
    # Omit empty/None JSONB values so INSERT uses SQL NULL (column default).
    # Python None passed to a JSONB column via pg_insert becomes JSON null
    # (not SQL NULL) because SQLAlchemy JSON defaults to none_as_null=False.
    if financials.income_statement:
        row["income_statement"] = financials.income_statement
    if financials.balance_sheet:
        row["balance_sheet"] = financials.balance_sheet
    if financials.cash_flow:
        row["cash_flow"] = financials.cash_flow
    if sic_code is not None:
        row["sic_code"] = sic_code
    return row


# ---------------------------------------------------------------------------
# Filing download + parse
# ---------------------------------------------------------------------------

# Match any .xml href in a filing index page
_XML_HREF_RE = re.compile(r'href="([^"]+\.xml)"', re.IGNORECASE)

# Linkbase suffixes and metadata files that are NOT XBRL instance documents
_LINKBASE_SUFFIXES = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")

# XBRL instance files always contain a date pattern like YYYYMMDD in their name
# (e.g., aapl-20230930.xml). Generic files like edgar.xml, primary_doc.xml don't.
_INSTANCE_DATE_RE = re.compile(r"\d{8}")


def _select_xbrl_file(index_html: str) -> str | None:
    """Pick the best XBRL instance file from a filing index page.

    Priority order:
    1. ``*_htm.xml`` — SEC's flattened XML from inline XBRL (post-~2019 filings)
    2. A plain ``.xml`` file that isn't a linkbase, report, or summary
    3. None if no suitable file found

    Returns the href string (may be relative or absolute path).
    """
    matches = _XML_HREF_RE.findall(index_html)

    htm_xml: str | None = None
    plain_xml: str | None = None

    for href in matches:
        filename = href.rsplit("/", 1)[-1].lower()

        # Skip R*.xml report files (R1.xml, R2.xml, ...)
        if filename.startswith("r") and len(filename) > 1 and filename[1].isdigit():
            continue

        # Skip FilingSummary.xml
        if filename == "filingsummary.xml":
            continue

        # Skip linkbase files
        if any(filename.endswith(suffix) for suffix in _LINKBASE_SUFFIXES):
            continue

        # Categorize
        if filename.endswith("_htm.xml"):
            htm_xml = href
        elif plain_xml is None and _INSTANCE_DATE_RE.search(filename):
            # Only accept plain XML if it contains a YYYYMMDD date pattern,
            # which distinguishes real XBRL instances (e.g., aapl-20230930.xml)
            # from generic metadata files (e.g., edgar.xml, primary_doc.xml).
            plain_xml = href

    # Prefer _htm.xml (modern iXBRL flattened), fall back to plain instance
    return htm_xml or plain_xml


class _RateLimiter:
    """Sequential rate limiter for SEC's 10 req/sec fair access policy.

    Uses a simple lock + interval to serialise all HTTP requests.
    When a 429 is received, a global cooldown pauses everything.
    """

    def __init__(self, rate: float = 2.0):
        self._interval = 1.0 / rate
        self._lock = asyncio.Lock()
        self._last = 0.0
        self._cooldown_seconds = 0.0

    async def cooldown(self, retry_after: float | None = None) -> None:
        """Pause all requests. Uses Retry-After header if available."""
        wait = retry_after if retry_after and retry_after > 0 else 15.0
        self._cooldown_seconds = wait
        logger.warning("[rate-limiter] 429 — pausing all requests for %.0fs", wait)
        await asyncio.sleep(wait)
        self._cooldown_seconds = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self._last + self._interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = asyncio.get_event_loop().time()


async def _do_get(
    client: httpx.AsyncClient,
    url: str,
    rate_limiter: _RateLimiter | None,
) -> httpx.Response:
    """GET with rate limiting and 429 cooldown."""
    if rate_limiter:
        await rate_limiter.acquire()
    else:
        await asyncio.sleep(0.5)

    resp = await client.get(url)

    if resp.status_code == 429:
        # Parse Retry-After header (seconds) if provided by SEC
        retry_after: float | None = None
        ra_header = resp.headers.get("Retry-After")
        if ra_header:
            try:
                retry_after = float(ra_header)
            except ValueError:
                retry_after = None
        if rate_limiter:
            await rate_limiter.cooldown(retry_after)
        else:
            await asyncio.sleep(retry_after or 15.0)
        resp.raise_for_status()  # Let tenacity retry

    resp.raise_for_status()
    return resp


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(8),
    wait=wait_exponential_jitter(initial=5, max=120, jitter=5),
    reraise=True,
)
async def _fetch_filing_with_retry(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
    rate_limiter: _RateLimiter | None = None,
) -> XBRLFinancials | None:
    """Inner retryable function — downloads and parses a single XBRL filing.

    Raises on transient errors (timeouts, 5xx, 429) so tenacity can retry.
    Non-retryable errors (other 4xx, parse errors) propagate immediately.
    """
    cik_int = entry.cik_int
    accession_clean = entry.accession_number.replace("-", "")

    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/"

    resp = await _do_get(client, index_url, rate_limiter)

    xbrl_file = _select_xbrl_file(resp.text)

    if not xbrl_file:
        logger.info(
            "No XBRL file found for accession %s (pre-XBRL era filing)",
            entry.accession_number,
        )
        raise NoXBRLAvailableError(entry.accession_number)

    # Build full URL if relative
    if xbrl_file.startswith("http"):
        xbrl_url = xbrl_file
    elif xbrl_file.startswith("/"):
        xbrl_url = f"https://www.sec.gov{xbrl_file}"
    else:
        xbrl_url = f"{index_url}{xbrl_file}"

    xbrl_resp = await _do_get(client, xbrl_url, rate_limiter)

    return extract_financials(xbrl_resp.text)


async def fetch_and_parse_filing(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
    rate_limiter: _RateLimiter | None = None,
) -> XBRLFinancials | None:
    """Download an XBRL filing from SEC EDGAR and parse it.

    Delegates to _fetch_filing_with_retry which handles transient errors
    (timeouts, 5xx) via tenacity. This outer function catches permanent
    failures and returns None.

    Args:
        client: An httpx.AsyncClient with User-Agent header set.
        entry: EDGAR index entry with filing metadata.
        rate_limiter: Optional rate limiter for SEC fair access compliance.

    Returns:
        XBRLFinancials if successfully parsed, None on any error.
    """
    try:
        return await _fetch_filing_with_retry(client, entry, rate_limiter)
    except NoXBRLAvailableError:
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %d fetching filing %s: %s",
            exc.response.status_code,
            entry.accession_number,
            exc,
        )
        return None
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        logger.warning(
            "Timeout fetching filing %s after retries exhausted",
            entry.accession_number,
        )
        return None
    except Exception:
        logger.warning(
            "Failed to fetch/parse filing %s",
            entry.accession_number,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# DB insertion
# ---------------------------------------------------------------------------


async def insert_pit_snapshot(
    session: AsyncSession,
    entry: EdgarIndexEntry,
    financials: XBRLFinancials,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: int | None = None,
    sic_code: int | None = None,
) -> bool:
    """Insert a parsed filing into pit_financial_snapshots.

    Uses INSERT ... ON CONFLICT DO NOTHING on accession_number.

    Args:
        session: Async SQLAlchemy session.
        entry: EDGAR index entry with filing metadata.
        financials: Parsed XBRL financial data.
        ticker: Stock ticker symbol.
        fiscal_year: The fiscal year of the filing.
        fiscal_quarter: The fiscal quarter (None for annual filings).
        sic_code: Optional SIC industry code for this company.

    Returns:
        True if the row was inserted, False if it already existed.
    """
    row = _build_snapshot_row(entry, financials, ticker, fiscal_year, fiscal_quarter, sic_code)
    stmt = pg_insert(PITFinancialSnapshot).values(**row)
    stmt = stmt.on_conflict_do_nothing(index_elements=["accession_number"])
    result = await session.execute(stmt)
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Main backfill orchestration
# ---------------------------------------------------------------------------


async def run_edgar_backfill(
    start_year: int,
    end_year: int,
    session_factory: async_sessionmaker[AsyncSession],
    checkpoint_file: str | None = None,
    dry_run: bool = False,
    concurrency: int = 1,
    cik_sic_map: dict[int, int | None] | None = None,
) -> dict[str, int]:
    """Run a full EDGAR backfill: index -> filter -> fetch -> parse -> insert.

    Args:
        start_year: First year to include (inclusive).
        end_year: Last year to include (inclusive).
        session_factory: Async SQLAlchemy session factory.
        checkpoint_file: Path to checkpoint file for resumable backfills.
        dry_run: If True, only build the index without fetching/parsing.
        concurrency: Number of concurrent filing downloads (default 1).
            Sequential processing avoids SEC EDGAR 429 rate limiting.
        cik_sic_map: Optional mapping from CIK (int) to SIC code (int | None).
            When provided, SIC codes are populated on snapshot rows.

    Returns:
        Summary dict with keys: total, inserted, skipped, failed.
    """
    logger.info("[edgar-backfill] Building index for %d-%d...", start_year, end_year)

    all_entries, cik_map = await build_full_index(
        start_year, end_year, session_factory=session_factory
    )
    logger.info(
        "[edgar-backfill] Index built: %d entries, %d CIK mappings",
        len(all_entries),
        len(cik_map),
    )

    # Filter to entries with a known ticker
    entries_with_ticker = [
        (entry, cik_map[entry.cik_int]) for entry in all_entries if entry.cik_int in cik_map
    ]
    logger.info(
        "[edgar-backfill] %d entries have known tickers (of %d total)",
        len(entries_with_ticker),
        len(all_entries),
    )

    if dry_run:
        logger.info("[edgar-backfill] Dry run — skipping fetch/parse/insert")
        return {
            "total": len(entries_with_ticker),
            "inserted": 0,
            "skipped": 0,
            "failed": 0,
        }

    # Query existing accession numbers to skip (both successful parses and known no-XBRL)
    async with session_factory() as session:
        result = await session.execute(select(PITFinancialSnapshot.accession_number))
        existing_accessions = {row[0] for row in result.all()}

        result = await session.execute(select(EdgarNoXBRLCache.accession_number))
        no_xbrl_accessions = {row[0] for row in result.all()}

    skip_accessions = existing_accessions | no_xbrl_accessions
    logger.info(
        "[edgar-backfill] %d filings already in DB, %d in no-XBRL cache",
        len(existing_accessions),
        len(no_xbrl_accessions),
    )

    # Filter out already-processed entries
    entries_to_process = [
        (entry, ticker)
        for entry, ticker in entries_with_ticker
        if entry.accession_number not in skip_accessions
    ]

    # Resume from checkpoint if available
    checkpoint_accession: str | None = None
    if checkpoint_file:
        cp_path = Path(checkpoint_file)
        if cp_path.exists():
            checkpoint_accession = cp_path.read_text().strip()
            logger.info(
                "[edgar-backfill] Resuming from checkpoint: %s",
                checkpoint_accession,
            )

    if checkpoint_accession:
        # Skip entries before the checkpoint
        skip = True
        filtered: list[tuple[EdgarIndexEntry, str]] = []
        for entry, ticker in entries_to_process:
            if skip:
                if entry.accession_number == checkpoint_accession:
                    skip = False
                continue
            filtered.append((entry, ticker))
        entries_to_process = filtered
        logger.info(
            "[edgar-backfill] %d entries remaining after checkpoint",
            len(entries_to_process),
        )

    total = len(entries_to_process)
    counters = {"inserted": 0, "skipped": len(existing_accessions), "failed": 0, "done": 0}
    lock = asyncio.Lock()

    logger.info("[edgar-backfill] Processing %d filings (concurrency=%d)...", total, concurrency)

    # Rate limiter: 2 req/sec — very conservative to avoid 429s from SEC
    # Each filing needs 2 requests (index page + XBRL file), so effective
    # rate is ~1 filing/sec with concurrency=1.
    rate_limiter = _RateLimiter(rate=2.0)
    semaphore = asyncio.Semaphore(concurrency)
    filing_tracker = ConsecutiveFailureTracker(threshold=10)

    async def _process_one(
        entry: EdgarIndexEntry,
        ticker: str,
        client: httpx.AsyncClient,
    ) -> None:
        async with semaphore:
            fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

            # Call inner function directly to distinguish no-XBRL (expected skip)
            # from actual errors (HTTP failures, parse errors, etc.)
            no_xbrl = False
            try:
                financials = await _fetch_filing_with_retry(client, entry, rate_limiter)
            except NoXBRLAvailableError:
                financials = None
                no_xbrl = True
            except Exception:
                logger.warning(
                    "Failed to fetch/parse filing %s", entry.accession_number, exc_info=True
                )
                financials = None

            async with lock:
                if financials is None:
                    if no_xbrl:
                        # No XBRL available — expected for pre-2011 filings, not a failure.
                        # Cache the result so future runs skip the HTTP request entirely.
                        async with session_factory() as session:
                            stmt = pg_insert(EdgarNoXBRLCache).values(
                                accession_number=entry.accession_number,
                            )
                            stmt = stmt.on_conflict_do_nothing(index_elements=["accession_number"])
                            await session.execute(stmt)
                            await session.commit()
                        counters["skipped"] += 1
                    else:
                        # Actual error — counts toward consecutive failure tracker
                        counters["failed"] += 1
                        filing_tracker.record_failure()  # May raise EdgarUnavailableError
                else:
                    filing_tracker.record_success()
                    # Look up SIC code for this entry's CIK
                    sic = None
                    if cik_sic_map:
                        sic = cik_sic_map.get(entry.cik_int)
                    async with session_factory() as session:
                        was_inserted = await insert_pit_snapshot(
                            session,
                            entry,
                            financials,
                            ticker,
                            fiscal_year,
                            fiscal_quarter,
                            sic_code=sic,
                        )
                        await session.commit()
                        if was_inserted:
                            counters["inserted"] += 1
                        else:
                            counters["skipped"] += 1

                counters["done"] += 1
                done = counters["done"]

            # Progress logging (outside lock)
            if done % 100 == 0 or done == total:
                logger.info(
                    "[edgar-backfill] Processed %d/%d filings (%d inserted, %d skipped, %d failed)",
                    done,
                    total,
                    counters["inserted"],
                    counters["skipped"],
                    counters["failed"],
                )

    # Process in chunks to allow checkpointing
    chunk_size = 500
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_FILING_TIMEOUT),
        limits=httpx.Limits(max_connections=concurrency + 2, max_keepalive_connections=concurrency),
    ) as client:
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
                filing_tracker._consecutive_failures = 0  # Reset for next chunk

            # Checkpoint at end of each chunk
            if checkpoint_file and chunk:
                last_entry = chunk[-1][0]
                Path(checkpoint_file).write_text(last_entry.accession_number)

    return {
        "total": total,
        "inserted": counters["inserted"],
        "skipped": counters["skipped"],
        "failed": counters["failed"],
    }


# ---------------------------------------------------------------------------
# Re-parse empty filings
# ---------------------------------------------------------------------------


async def reparse_empty_filings(
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int = 100,
) -> dict[str, int]:
    """Delete and re-fetch filings that have empty parsed data.

    Targets rows in pit_financial_snapshots where:
    - income_statement IS NULL or contains JSON null, OR
    - shares_outstanding IS NULL
    Only considers filings from 2011-01-01 onward (pre-2011 XBRL uses
    unsupported xbrl.us GAAP namespace).

    Also performs a one-time cleanup: deletes all pre-2011 snapshot rows.

    Returns:
        Summary dict with keys: total, reparsed, failed, still_empty.
    """
    from sqlalchemy import delete, func, or_

    # 0. One-time cleanup: delete pre-2011 snapshots (unsupported GAAP namespace)
    pre_2011_cutoff = date(2011, 1, 1)
    async with session_factory() as session:
        del_result = await session.execute(
            delete(PITFinancialSnapshot).where(
                PITFinancialSnapshot.filing_date < pre_2011_cutoff
            )
        )
        pre_2011_deleted = del_result.rowcount
        await session.commit()
    if pre_2011_deleted:
        logger.info("[edgar-reparse] Deleted %d pre-2011 snapshots", pre_2011_deleted)

    # 1. Find rows with missing/empty data (filing_date >= 2011)
    # Check both SQL NULL (IS NULL) and JSON null (jsonb_typeof = 'null')
    # because SQLAlchemy JSON(none_as_null=False) stores Python None as JSON null.
    async with session_factory() as session:
        stmt = select(
            PITFinancialSnapshot.accession_number,
            PITFinancialSnapshot.cik,
            PITFinancialSnapshot.ticker,
            PITFinancialSnapshot.filing_date,
            PITFinancialSnapshot.form_type,
            PITFinancialSnapshot.fiscal_year,
            PITFinancialSnapshot.fiscal_quarter,
            PITFinancialSnapshot.sic_code,
        ).where(
            PITFinancialSnapshot.filing_date >= pre_2011_cutoff,
            or_(
                PITFinancialSnapshot.income_statement.is_(None),
                func.jsonb_typeof(PITFinancialSnapshot.income_statement) == "null",
                PITFinancialSnapshot.shares_outstanding.is_(None),
            ),
        )
        result = await session.execute(stmt)
        empty_rows = result.all()

    total = len(empty_rows)
    logger.info("[edgar-reparse] Found %d filings with empty data", total)

    if total == 0:
        return {"total": 0, "reparsed": 0, "failed": 0, "still_empty": 0}

    # 2. Delete empty rows so ON CONFLICT DO NOTHING won't block re-insert
    async with session_factory() as session:
        accessions = [row.accession_number for row in empty_rows]
        for i in range(0, len(accessions), batch_size):
            batch = accessions[i : i + batch_size]
            await session.execute(
                delete(PITFinancialSnapshot).where(
                    PITFinancialSnapshot.accession_number.in_(batch)
                )
            )
        await session.commit()
    logger.info("[edgar-reparse] Deleted %d empty rows", total)

    # 3. Re-fetch and re-parse each filing
    rate_limiter = _RateLimiter(rate=2.0)
    counters = {"reparsed": 0, "failed": 0, "still_empty": 0, "done": 0}

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(EDGAR_FILING_TIMEOUT),
    ) as client:
        for row in empty_rows:
            cik_int = int(row.cik) if isinstance(row.cik, str) else row.cik
            accession_clean = row.accession_number.replace("-", "")
            entry = EdgarIndexEntry(
                company_name="",
                form_type=row.form_type,
                cik=str(row.cik),
                date_filed=row.filing_date.isoformat(),
                accession_number=row.accession_number,
                filename=f"edgar/data/{cik_int}/{accession_clean}.txt",
            )

            try:
                financials = await _fetch_filing_with_retry(client, entry, rate_limiter)
            except (NoXBRLAvailableError, Exception):
                financials = None

            if financials is None or not financials.income_statement:
                if financials and not financials.income_statement:
                    counters["still_empty"] += 1
                else:
                    counters["failed"] += 1
                continue

            async with session_factory() as session:
                was_inserted = await insert_pit_snapshot(
                    session,
                    entry,
                    financials,
                    row.ticker,
                    row.fiscal_year,
                    row.fiscal_quarter,
                    sic_code=row.sic_code,
                )
                await session.commit()
                if was_inserted:
                    counters["reparsed"] += 1

            counters["done"] += 1
            done = counters["done"]
            if done % 50 == 0 or done == total:
                logger.info(
                    "[edgar-reparse] Progress %d/%d (reparsed=%d, failed=%d, still_empty=%d)",
                    done,
                    total,
                    counters["reparsed"],
                    counters["failed"],
                    counters["still_empty"],
                )

    return {
        "total": total,
        "reparsed": counters["reparsed"],
        "failed": counters["failed"],
        "still_empty": counters["still_empty"],
    }
