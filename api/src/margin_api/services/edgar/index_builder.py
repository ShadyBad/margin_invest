"""EDGAR full-index parser and CIK-to-ticker mapper.

Parses SEC EDGAR company.idx files to discover 10-K/10-Q filings and maps
CIK numbers to tickers using the SEC company_tickers.json endpoint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

SEC_BASE = "https://www.sec.gov"
USER_AGENT = "MarginInvest admin@margininvest.com"
FORM_TYPES: set[str] = {"10-K", "10-Q", "10-K/A", "10-Q/A"}

_ACCESSION_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")


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
    """Parse pipe-delimited company.idx content into EdgarIndexEntry objects.

    The company.idx format has a header line, a dashes separator, then data lines:
        CIK|Company Name|Form Type|Date Filed|Filename
        --------------------------------------------------
        320193|APPLE INC|10-K|2024-11-01|edgar/data/320193/...

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
        line = line.strip()
        if not line:
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        cik = parts[0].strip()
        company_name = parts[1].strip()
        form_type = parts[2].strip()
        date_filed = parts[3].strip()
        filename = parts[4].strip()

        if form_type not in target_forms:
            continue

        # Extract accession number from filename
        match = _ACCESSION_RE.search(filename)
        accession_number = match.group(1) if match else ""

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
    resp = await client.get(url)
    resp.raise_for_status()
    return parse_company_idx(resp.text, form_types=form_types)


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


async def build_full_index(
    start_year: int,
    end_year: int,
    form_types: set[str] | None = None,
) -> tuple[list[EdgarIndexEntry], dict[int, str]]:
    """Build a complete EDGAR filing index across multiple years.

    Creates an httpx.AsyncClient with the required User-Agent header and
    iterates over all year/quarter combinations to build the index.

    Args:
        start_year: First year to include (inclusive).
        end_year: Last year to include (inclusive).
        form_types: Set of form types to filter. Defaults to FORM_TYPES.

    Returns:
        Tuple of (all_entries, cik_ticker_map).
    """
    all_entries: list[EdgarIndexEntry] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0),
    ) as client:
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                entries = await fetch_quarter_index(
                    client, year, quarter, form_types=form_types
                )
                all_entries.extend(entries)

        cik_map = await load_cik_ticker_map(client)

    return all_entries, cik_map
