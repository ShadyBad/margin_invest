"""EDGAR backfill service: downloads XBRL filings and inserts into pit_financial_snapshots.

Wires the EDGAR index builder and XBRL parser together with database insertion.
Supports checkpointing for resumable backfills and rate-limited SEC access.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from margin_api.db.models import PITFinancialSnapshot
from margin_api.services.edgar.index_builder import (
    EdgarIndexEntry,
    USER_AGENT,
    build_full_index,
)
from margin_api.services.edgar.xbrl_parser import XBRLFinancials, extract_financials

logger = logging.getLogger(__name__)


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
) -> dict[str, Any]:
    """Build a dict suitable for DB insertion into pit_financial_snapshots.

    Args:
        entry: EDGAR index entry with filing metadata.
        financials: Parsed XBRL financial data.
        ticker: Stock ticker symbol.
        fiscal_year: The fiscal year of the filing.
        fiscal_quarter: The fiscal quarter (None for annual 10-K filings).

    Returns:
        Dict with all columns for pit_financial_snapshots.
    """
    filing_date = date.fromisoformat(entry.date_filed)
    period_end = _infer_period_end(filing_date, entry.form_type, fiscal_year, fiscal_quarter)

    return {
        "cik": entry.cik,
        "ticker": ticker,
        "filing_date": filing_date,
        "period_end": period_end,
        "form_type": entry.form_type,
        "accession_number": entry.accession_number,
        "income_statement": financials.income_statement or None,
        "balance_sheet": financials.balance_sheet or None,
        "cash_flow": financials.cash_flow or None,
        "shares_outstanding": financials.shares_outstanding,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
    }


# ---------------------------------------------------------------------------
# Filing download + parse
# ---------------------------------------------------------------------------

# Match XBRL instance files, skip R*.xml report files
_XBRL_FILE_RE = re.compile(r'href="([^"]+\.xml)"', re.IGNORECASE)


async def fetch_and_parse_filing(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
) -> XBRLFinancials | None:
    """Download an XBRL filing from SEC EDGAR and parse it.

    Fetches the filing index page, finds the XBRL instance document,
    downloads it, and extracts financials.

    Args:
        client: An httpx.AsyncClient with User-Agent header set.
        entry: EDGAR index entry with filing metadata.

    Returns:
        XBRLFinancials if successfully parsed, None on any error.
    """
    try:
        cik_int = entry.cik_int
        accession_clean = entry.accession_number.replace("-", "")

        index_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/"
        )

        # Rate limit: 5 req/sec max
        await asyncio.sleep(0.2)

        resp = await client.get(index_url)
        resp.raise_for_status()

        # Find XBRL file links (*.xml but skip R*.xml report files)
        matches = _XBRL_FILE_RE.findall(resp.text)
        xbrl_file = None
        for match in matches:
            filename = match.rsplit("/", 1)[-1]
            # Skip R*.xml (report files like R1.xml, R2.xml, etc.)
            if filename.startswith("R") and filename[1:2].isdigit():
                continue
            # Skip non-XBRL-instance files
            if filename.lower().endswith(".xml"):
                xbrl_file = match
                break

        if not xbrl_file:
            logger.warning("No XBRL file found for accession %s", entry.accession_number)
            return None

        # Build full URL if relative
        if xbrl_file.startswith("http"):
            xbrl_url = xbrl_file
        elif xbrl_file.startswith("/"):
            xbrl_url = f"https://www.sec.gov{xbrl_file}"
        else:
            xbrl_url = f"{index_url}{xbrl_file}"

        await asyncio.sleep(0.2)

        xbrl_resp = await client.get(xbrl_url)
        xbrl_resp.raise_for_status()

        return extract_financials(xbrl_resp.text)

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

    Returns:
        True if the row was inserted, False if it already existed.
    """
    row = _build_snapshot_row(entry, financials, ticker, fiscal_year, fiscal_quarter)
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
) -> dict[str, int]:
    """Run a full EDGAR backfill: index -> filter -> fetch -> parse -> insert.

    Args:
        start_year: First year to include (inclusive).
        end_year: Last year to include (inclusive).
        session_factory: Async SQLAlchemy session factory.
        checkpoint_file: Path to checkpoint file for resumable backfills.
        dry_run: If True, only build the index without fetching/parsing.

    Returns:
        Summary dict with keys: total, inserted, skipped, failed.
    """
    logger.info(
        "[edgar-backfill] Building index for %d-%d...", start_year, end_year
    )

    all_entries, cik_map = await build_full_index(start_year, end_year)
    logger.info(
        "[edgar-backfill] Index built: %d entries, %d CIK mappings",
        len(all_entries),
        len(cik_map),
    )

    # Filter to entries with a known ticker
    entries_with_ticker = [
        (entry, cik_map[entry.cik_int])
        for entry in all_entries
        if entry.cik_int in cik_map
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

    # Query existing accession numbers to skip
    async with session_factory() as session:
        result = await session.execute(
            select(PITFinancialSnapshot.accession_number)
        )
        existing_accessions = {row[0] for row in result.all()}

    logger.info(
        "[edgar-backfill] %d filings already in DB", len(existing_accessions)
    )

    # Filter out already-processed entries
    entries_to_process = [
        (entry, ticker)
        for entry, ticker in entries_with_ticker
        if entry.accession_number not in existing_accessions
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
    inserted = 0
    skipped = len(existing_accessions)
    failed = 0

    logger.info("[edgar-backfill] Processing %d filings...", total)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0),
    ) as client:
        for i, (entry, ticker) in enumerate(entries_to_process, 1):
            fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

            financials = await fetch_and_parse_filing(client, entry)
            if financials is None:
                failed += 1
            else:
                async with session_factory() as session:
                    was_inserted = await insert_pit_snapshot(
                        session,
                        entry,
                        financials,
                        ticker,
                        fiscal_year,
                        fiscal_quarter,
                    )
                    await session.commit()
                    if was_inserted:
                        inserted += 1
                    else:
                        skipped += 1

            # Checkpoint every 100 filings
            if checkpoint_file and i % 100 == 0:
                Path(checkpoint_file).write_text(entry.accession_number)
                logger.info(
                    "[edgar-backfill] Checkpoint saved at %s", entry.accession_number
                )

            # Log progress every 100 filings
            if i % 100 == 0 or i == total:
                logger.info(
                    "[edgar-backfill] Processed %d/%d filings "
                    "(%d inserted, %d skipped, %d failed)",
                    i,
                    total,
                    inserted,
                    skipped,
                    failed,
                )

    return {
        "total": total,
        "inserted": inserted,
        "skipped": skipped,
        "failed": failed,
    }
