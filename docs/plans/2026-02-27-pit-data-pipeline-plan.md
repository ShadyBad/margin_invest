# PIT Data Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace synthetic backtesting data with real point-in-time financial data from SEC EDGAR XBRL filings and yfinance daily prices.

**Architecture:** Three new DB tables (`pit_financial_snapshots`, `pit_daily_prices`, `pit_universe_membership`), an EDGAR XBRL parser, a price backfill CLI, a `DatabasePITProvider` implementing the engine's `PointInTimeProvider` protocol, and API wiring to replace `get_default_replay_result()` with real orchestrator runs.

**Tech Stack:** lxml (XBRL parsing), yfinance (price backfill), SQLAlchemy 2.0 async, asyncpg, Alembic, ARQ workers

**Design doc:** `docs/plans/2026-02-27-pit-data-pipeline-design.md`

---

## Task Overview

| # | Task | Dependencies | Parallel Group |
|---|------|-------------|----------------|
| 1 | Alembic migration for PIT tables | None | A |
| 2 | EDGAR index builder | T1 | B |
| 3 | XBRL parser + tag mapping | None | B |
| 4 | EDGAR backfill CLI (wire index + parser + DB) | T1, T2, T3 | C |
| 5 | Price backfill CLI | T1 | B |
| 6 | Universe assembly service | T1, T4, T5 | D |
| 7 | AsyncPointInTimeProvider protocol in engine | None | A |
| 8 | DatabasePITProvider implementation | T1, T7 | C |
| 9 | PIT correctness tests | T8 | D |
| 10 | API wiring — replace synthetic with real | T8, T9 | E |
| 11 | Precompute + shadow portfolio workers | T10 | E |
| 12 | Incremental daily update pipeline | T4, T5, T6 | F |

---

### Task 1: Alembic Migration for PIT Tables

**Files:**
- Create: `api/alembic/versions/XXXX_add_pit_tables.py`
- Modify: `api/src/margin_api/db/models.py`

**Step 1: Add ORM models to models.py**

Add after the existing `ShadowPortfolioSnapshot` class (around line 747). Use the existing `JSONVariant` pattern from line 29.

```python
class PITFinancialSnapshot(Base):
    __tablename__ = "pit_financial_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), index=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    filing_date: Mapped[date] = mapped_column(index=True)
    period_end: Mapped[date] = mapped_column()
    form_type: Mapped[str] = mapped_column(String(10))
    accession_number: Mapped[str] = mapped_column(String(30), unique=True)
    income_statement: Mapped[dict | None] = mapped_column(JSONVariant)
    balance_sheet: Mapped[dict | None] = mapped_column(JSONVariant)
    cash_flow: Mapped[dict | None] = mapped_column(JSONVariant)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    fiscal_quarter: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_pit_fin_ticker_filing", "ticker", "filing_date"),
    )


class PITDailyPrice(Base):
    __tablename__ = "pit_daily_prices"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[date] = mapped_column(primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20), default="yfinance")


class PITUniverseMembership(Base):
    __tablename__ = "pit_universe_membership"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    cik: Mapped[str] = mapped_column(String(10))
    quarter_date: Mapped[date] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    market_cap: Mapped[float | None] = mapped_column(Float)
    last_filing_date: Mapped[date | None] = mapped_column()
    delist_detected_at: Mapped[date | None] = mapped_column()
    last_known_price: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("ticker", "quarter_date", name="uq_pit_universe_ticker_quarter"),
        Index("ix_pit_universe_quarter", "quarter_date"),
    )
```

Also add `pit_data_version` column to `BacktestRun`:

```python
pit_data_version: Mapped[str | None] = mapped_column(String(64))
```

**Step 2: Generate and review Alembic migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add PIT tables for backtesting"`

Verify the migration creates 3 tables + 1 column. Check for idempotent guards.

**Step 3: Run migration locally**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies successfully.

**Step 4: Verify with tests**

Run: `uv run pytest api/tests/ -v -k "test_" --co -q | head -20`
Expected: Existing tests still collected (no import errors from new models).

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/*pit*
git commit -m "feat(api): add PIT tables for backtesting data pipeline"
```

---

### Task 2: EDGAR Index Builder

**Files:**
- Create: `api/src/margin_api/services/edgar/index_builder.py`
- Create: `api/src/margin_api/services/edgar/__init__.py`
- Test: `api/tests/services/test_edgar_index_builder.py`

**Context:** The SEC full-index at `https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}/company.idx` lists all filings for a quarter. We parse these to find 10-K/10-Q accession numbers.

CIK → ticker mapping comes from `https://www.sec.gov/files/company_tickers.json`.

**Step 1: Write failing tests**

```python
"""Tests for EDGAR index builder."""
import pytest
from margin_api.services.edgar.index_builder import (
    parse_company_idx,
    EdgarIndexEntry,
    load_cik_ticker_map,
)


def test_parse_company_idx_extracts_10k():
    """Parse a company.idx snippet and extract 10-K filing entries."""
    raw = (
        "Company Name|Form Type|CIK|Date Filed|Filename\n"
        "---\n"
        "APPLE INC|10-K|0000320193|2024-11-01|edgar/data/320193/0000320193-24-000123.txt\n"
        "APPLE INC|8-K|0000320193|2024-10-15|edgar/data/320193/0000320193-24-000100.txt\n"
        "MICROSOFT CORP|10-Q|0000789019|2024-10-30|edgar/data/789019/0000789019-24-000456.txt\n"
    )
    entries = parse_company_idx(raw, form_types={"10-K", "10-Q"})
    assert len(entries) == 2
    assert entries[0].cik == "0000320193"
    assert entries[0].form_type == "10-K"
    assert entries[0].accession_number == "0000320193-24-000123"
    assert entries[1].form_type == "10-Q"


def test_parse_company_idx_skips_non_target_forms():
    raw = (
        "Company Name|Form Type|CIK|Date Filed|Filename\n"
        "---\n"
        "FOO INC|8-K|0001234567|2024-01-01|edgar/data/1234567/0001234567-24-000001.txt\n"
    )
    entries = parse_company_idx(raw, form_types={"10-K", "10-Q"})
    assert len(entries) == 0


def test_edgar_index_entry_fields():
    entry = EdgarIndexEntry(
        company_name="APPLE INC",
        form_type="10-K",
        cik="0000320193",
        date_filed="2024-11-01",
        accession_number="0000320193-24-000123",
        filename="edgar/data/320193/0000320193-24-000123.txt",
    )
    assert entry.cik_int == 320193
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py -v`
Expected: FAIL — module not found.

**Step 3: Implement index builder**

Create `api/src/margin_api/services/edgar/__init__.py` (empty).

Create `api/src/margin_api/services/edgar/index_builder.py`:

```python
"""EDGAR full-index parser for finding 10-K/10-Q filings."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

SEC_BASE = "https://www.sec.gov"
FULL_INDEX_URL = f"{SEC_BASE}/Archives/edgar/full-index/{{year}}/QTR{{quarter}}/company.idx"
COMPANY_TICKERS_URL = f"{SEC_BASE}/files/company_tickers.json"
USER_AGENT = "MarginInvest admin@margininvest.com"
FORM_TYPES = {"10-K", "10-Q", "10-K/A", "10-Q/A"}


@dataclass
class EdgarIndexEntry:
    """A single filing entry from the EDGAR full-index."""

    company_name: str
    form_type: str
    cik: str
    date_filed: str  # YYYY-MM-DD
    accession_number: str
    filename: str

    @property
    def cik_int(self) -> int:
        return int(self.cik)


def parse_company_idx(
    raw: str,
    form_types: set[str] | None = None,
) -> list[EdgarIndexEntry]:
    """Parse a company.idx file and return entries matching form_types."""
    if form_types is None:
        form_types = FORM_TYPES

    entries: list[EdgarIndexEntry] = []
    in_data = False
    for line in raw.splitlines():
        if line.startswith("---"):
            in_data = True
            continue
        if not in_data:
            continue
        parts = line.split("|")
        if len(parts) < 5:
            continue
        company_name, form_type, cik, date_filed, filename = (
            parts[0].strip(),
            parts[1].strip(),
            parts[2].strip(),
            parts[3].strip(),
            parts[4].strip(),
        )
        if form_type not in form_types:
            continue

        # Extract accession number from filename
        # e.g. "edgar/data/320193/0000320193-24-000123.txt"
        match = re.search(r"(\d{10}-\d{2}-\d{6})", filename)
        accession = match.group(1) if match else filename.rsplit("/", 1)[-1].replace(".txt", "")

        entries.append(
            EdgarIndexEntry(
                company_name=company_name,
                form_type=form_type,
                cik=cik,
                date_filed=date_filed,
                accession_number=accession,
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
    """Download and parse a single quarter's company.idx."""
    url = FULL_INDEX_URL.format(year=year, quarter=quarter)
    resp = await client.get(url)
    resp.raise_for_status()
    return parse_company_idx(resp.text, form_types)


async def load_cik_ticker_map(client: httpx.AsyncClient) -> dict[int, str]:
    """Load CIK → ticker mapping from SEC company_tickers.json."""
    resp = await client.get(COMPANY_TICKERS_URL)
    resp.raise_for_status()
    data = resp.json()
    mapping: dict[int, str] = {}
    for entry in data.values():
        cik = entry.get("cik_str")
        ticker = entry.get("ticker", "").upper()
        if cik and ticker:
            mapping[int(cik)] = ticker
    return mapping


async def build_full_index(
    start_year: int = 2009,
    end_year: int = 2026,
    form_types: set[str] | None = None,
) -> tuple[list[EdgarIndexEntry], dict[int, str]]:
    """Build complete filing index for the given year range.

    Returns (entries, cik_to_ticker_map).
    """
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        cik_map = await load_cik_ticker_map(client)
        all_entries: list[EdgarIndexEntry] = []
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                try:
                    entries = await fetch_quarter_index(client, year, quarter, form_types)
                    all_entries.extend(entries)
                    logger.info(f"Indexed {year} Q{quarter}: {len(entries)} filings")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        logger.info(f"No index for {year} Q{quarter} (future quarter)")
                        break
                    raise
        return all_entries, cik_map
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/services/test_edgar_index_builder.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/ api/tests/services/test_edgar_index_builder.py
git commit -m "feat(api): add EDGAR full-index parser for PIT filing discovery"
```

---

### Task 3: XBRL Parser + Tag Mapping

**Files:**
- Create: `api/src/margin_api/services/edgar/xbrl_parser.py`
- Test: `api/tests/services/test_xbrl_parser.py`

**Context:** XBRL filings use US-GAAP taxonomy tags. We need to extract ~16 financial fields with fallback tag chains.

**Step 1: Write failing tests**

```python
"""Tests for XBRL parser and tag extraction."""
import pytest
from margin_api.services.edgar.xbrl_parser import (
    extract_financials,
    XBRLFinancials,
    GAAP_TAG_MAP,
)


SAMPLE_XBRL = """<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:Revenues contextRef="FY2024" decimals="-6" unitRef="USD">391035000000</us-gaap:Revenues>
  <us-gaap:NetIncomeLoss contextRef="FY2024" decimals="-6" unitRef="USD">93736000000</us-gaap:NetIncomeLoss>
  <us-gaap:Assets contextRef="FY2024_instant" decimals="-6" unitRef="USD">352583000000</us-gaap:Assets>
  <us-gaap:Liabilities contextRef="FY2024_instant" decimals="-6" unitRef="USD">290437000000</us-gaap:Liabilities>
  <us-gaap:StockholdersEquity contextRef="FY2024_instant" decimals="-6" unitRef="USD">62146000000</us-gaap:StockholdersEquity>
  <us-gaap:NetCashProvidedByOperatingActivities contextRef="FY2024" decimals="-6" unitRef="USD">118254000000</us-gaap:NetCashProvidedByOperatingActivities>
  <us-gaap:PaymentsToAcquirePropertyPlantAndEquipment contextRef="FY2024" decimals="-6" unitRef="USD">9959000000</us-gaap:PaymentsToAcquirePropertyPlantAndEquipment>
  <us-gaap:CommonStockSharesOutstanding contextRef="FY2024_instant" decimals="0" unitRef="shares">15115823000</us-gaap:CommonStockSharesOutstanding>
</xbrl>"""


def test_extract_financials_basic():
    result = extract_financials(SAMPLE_XBRL)
    assert result is not None
    assert result.income_statement["revenue"] == 391035000000
    assert result.income_statement["net_income"] == 93736000000
    assert result.balance_sheet["total_assets"] == 352583000000
    assert result.balance_sheet["total_liabilities"] == 290437000000
    assert result.cash_flow["operating_cash_flow"] == 118254000000
    assert result.shares_outstanding == 15115823000


def test_extract_financials_fallback_tag():
    """When primary tag missing, fallback should work."""
    xbrl = """<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="FY2024" decimals="-6" unitRef="USD">50000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
</xbrl>"""
    result = extract_financials(xbrl)
    assert result.income_statement["revenue"] == 50000000000


def test_extract_financials_empty_xbrl():
    xbrl = '<?xml version="1.0"?><xbrl xmlns="http://www.xbrl.org/2003/instance"></xbrl>'
    result = extract_financials(xbrl)
    assert result.income_statement["revenue"] is None
    assert result.balance_sheet["total_assets"] is None


def test_gaap_tag_map_has_required_fields():
    required = {"revenue", "net_income", "total_assets", "total_liabilities",
                 "operating_cash_flow", "capex", "shares_outstanding"}
    assert required.issubset(set(GAAP_TAG_MAP.keys()))
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_xbrl_parser.py -v`
Expected: FAIL — module not found.

**Step 3: Implement XBRL parser**

```python
"""XBRL instance document parser for extracting US-GAAP financial data."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from lxml import etree

logger = logging.getLogger(__name__)

# Namespace patterns for US-GAAP tags across taxonomy years
_GAAP_NS_PATTERN = re.compile(r"http://fasb\.org/us-gaap/\d{4}")

# Map: our field name → list of US-GAAP tag local names (primary first, then fallbacks)
GAAP_TAG_MAP: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfRevenue",
    ],
    "gross_profit": ["GrossProfit"],
    "sga_expense": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "ebit": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ],
    "interest_expense": ["InterestExpense", "InterestExpenseDebt"],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "total_liabilities": ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "short_term_debt": [
        "ShortTermBorrowings",
        "DebtCurrent",
    ],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "operating_cash_flow": [
        "NetCashProvidedByOperatingActivities",
        "CashFlowsFromOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PurchaseOfPropertyPlantAndEquipment",
    ],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "share_repurchases": ["PaymentsForRepurchaseOfCommonStock"],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "EntityCommonStockSharesOutstanding",
    ],
    "pp_and_e": ["PropertyPlantAndEquipmentNet"],
    "depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
    ],
    "tax_provision": ["IncomeTaxExpenseBenefit"],
    "receivables": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
    ],
}


@dataclass
class XBRLFinancials:
    """Extracted financial data from an XBRL filing."""

    income_statement: dict[str, float | None] = field(default_factory=dict)
    balance_sheet: dict[str, float | None] = field(default_factory=dict)
    cash_flow: dict[str, float | None] = field(default_factory=dict)
    shares_outstanding: int | None = None


# Classification of fields into statement categories
_INCOME_FIELDS = {
    "revenue", "cost_of_revenue", "gross_profit", "sga_expense", "rd_expense",
    "ebit", "interest_expense", "net_income", "depreciation", "tax_provision",
}
_BALANCE_FIELDS = {
    "total_assets", "current_assets", "cash_and_equivalents", "total_liabilities",
    "current_liabilities", "long_term_debt", "short_term_debt", "total_equity",
    "retained_earnings", "pp_and_e", "receivables",
}
_CASHFLOW_FIELDS = {
    "operating_cash_flow", "capex", "dividends_paid", "share_repurchases",
}


def extract_financials(xbrl_content: str) -> XBRLFinancials:
    """Parse XBRL content and extract financial data using US-GAAP tag mapping."""
    try:
        root = etree.fromstring(xbrl_content.encode("utf-8"))
    except etree.XMLSyntaxError:
        logger.warning("Failed to parse XBRL content")
        return XBRLFinancials()

    # Build lookup: local_name → value (first occurrence wins for simplicity)
    tag_values: dict[str, float] = {}
    for elem in root.iter():
        ns = elem.tag.split("}")[0].lstrip("{") if "}" in elem.tag else ""
        if not _GAAP_NS_PATTERN.match(ns):
            continue
        local = elem.tag.split("}")[-1]
        if local in tag_values:
            continue
        if elem.text and elem.text.strip():
            try:
                tag_values[local] = float(elem.text.strip())
            except ValueError:
                continue

    result = XBRLFinancials()

    for field_name, tag_chain in GAAP_TAG_MAP.items():
        value: float | None = None
        for tag in tag_chain:
            if tag in tag_values:
                value = tag_values[tag]
                break

        if field_name == "shares_outstanding":
            result.shares_outstanding = int(value) if value is not None else None
        elif field_name in _INCOME_FIELDS:
            result.income_statement[field_name] = value
        elif field_name in _BALANCE_FIELDS:
            result.balance_sheet[field_name] = value
        elif field_name in _CASHFLOW_FIELDS:
            result.cash_flow[field_name] = value

    return result
```

**Step 4: Add lxml dependency if not present**

Run: `uv add lxml --package margin-api` (lxml is already in engine deps but may not be in api)

**Step 5: Run tests**

Run: `uv run pytest api/tests/services/test_xbrl_parser.py -v`
Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add api/src/margin_api/services/edgar/xbrl_parser.py api/tests/services/test_xbrl_parser.py
git commit -m "feat(api): add XBRL parser with US-GAAP tag mapping for PIT data"
```

---

### Task 4: EDGAR Backfill CLI

**Files:**
- Create: `api/src/margin_api/services/edgar/backfill.py`
- Modify: `api/src/margin_api/cli.py` (add `edgar-backfill` subcommand)
- Test: `api/tests/services/test_edgar_backfill.py`

**Context:** Wires index builder + XBRL parser + DB insertion. Downloads filings from EDGAR archives, parses XBRL, inserts into `pit_financial_snapshots`. Checkpointed and resumable.

**Step 1: Write failing test for the backfill service**

```python
"""Tests for EDGAR backfill service."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from margin_api.services.edgar.backfill import (
    fetch_and_parse_filing,
    insert_pit_snapshot,
)
from margin_api.services.edgar.index_builder import EdgarIndexEntry
from margin_api.services.edgar.xbrl_parser import XBRLFinancials


@pytest.fixture
def sample_entry():
    return EdgarIndexEntry(
        company_name="APPLE INC",
        form_type="10-K",
        cik="0000320193",
        date_filed="2024-11-01",
        accession_number="0000320193-24-000123",
        filename="edgar/data/320193/0000320193-24-000123.txt",
    )


@pytest.fixture
def sample_financials():
    return XBRLFinancials(
        income_statement={"revenue": 391035000000, "net_income": 93736000000},
        balance_sheet={"total_assets": 352583000000},
        cash_flow={"operating_cash_flow": 118254000000},
        shares_outstanding=15115823000,
    )


def test_insert_pit_snapshot_builds_correct_row(sample_entry, sample_financials):
    """Verify the row dict built for DB insertion has all required fields."""
    from margin_api.services.edgar.backfill import _build_snapshot_row

    row = _build_snapshot_row(
        entry=sample_entry,
        financials=sample_financials,
        ticker="AAPL",
        fiscal_year=2024,
        fiscal_quarter=None,
    )
    assert row["cik"] == "0000320193"
    assert row["ticker"] == "AAPL"
    assert row["accession_number"] == "0000320193-24-000123"
    assert row["form_type"] == "10-K"
    assert row["fiscal_quarter"] is None
    assert row["income_statement"]["revenue"] == 391035000000
```

**Step 2: Run to verify failure**

Run: `uv run pytest api/tests/services/test_edgar_backfill.py -v`

**Step 3: Implement backfill service**

Create `api/src/margin_api/services/edgar/backfill.py`:

```python
"""EDGAR backfill service — fetches, parses, and stores XBRL filings."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PITFinancialSnapshot
from margin_api.services.edgar.index_builder import EdgarIndexEntry, USER_AGENT
from margin_api.services.edgar.xbrl_parser import XBRLFinancials, extract_financials

logger = logging.getLogger(__name__)

SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
RATE_LIMIT_DELAY = 0.2  # 5 req/sec


def _build_snapshot_row(
    entry: EdgarIndexEntry,
    financials: XBRLFinancials,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: int | None,
) -> dict:
    """Build a dict suitable for DB insertion."""
    return {
        "cik": entry.cik,
        "ticker": ticker,
        "filing_date": date.fromisoformat(entry.date_filed),
        "period_end": _infer_period_end(entry.date_filed, entry.form_type, fiscal_year, fiscal_quarter),
        "form_type": entry.form_type,
        "accession_number": entry.accession_number,
        "income_statement": financials.income_statement,
        "balance_sheet": financials.balance_sheet,
        "cash_flow": financials.cash_flow,
        "shares_outstanding": financials.shares_outstanding,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
    }


def _infer_period_end(
    date_filed: str, form_type: str, fiscal_year: int, fiscal_quarter: int | None
) -> date:
    """Infer period_end from filing metadata. Approximate if exact date unknown."""
    filed = date.fromisoformat(date_filed)
    if fiscal_quarter is not None:
        month = fiscal_quarter * 3
        return date(fiscal_year, month, 28)
    # Annual filing: fiscal year end, approximate as Dec 31
    return date(fiscal_year, 12, 31)


async def fetch_and_parse_filing(
    client: httpx.AsyncClient,
    entry: EdgarIndexEntry,
) -> XBRLFinancials | None:
    """Download a filing from EDGAR and parse its XBRL content."""
    cik_num = entry.cik_int
    accession_clean = entry.accession_number.replace("-", "")
    index_url = f"{SEC_ARCHIVES}/{cik_num}/{accession_clean}/"

    try:
        # Fetch filing index to find the XBRL file
        resp = await client.get(index_url)
        resp.raise_for_status()
        index_html = resp.text

        # Look for R*.xml or *_htm.xml (inline XBRL) or *.xml files
        xml_files = re.findall(r'href="([^"]+\.xml)"', index_html)
        # Prefer the primary instance document (usually the largest .xml)
        xbrl_file = None
        for f in xml_files:
            lower = f.lower()
            if "r1.xml" in lower or "r2.xml" in lower:
                continue  # Skip report XML
            if "_htm.xml" in lower or lower.endswith(".xml"):
                xbrl_file = f
                break

        if not xbrl_file:
            logger.debug(f"No XBRL file found for {entry.accession_number}")
            return None

        # Fetch the XBRL document
        if xbrl_file.startswith("http"):
            xbrl_url = xbrl_file
        else:
            xbrl_url = f"{index_url}{xbrl_file}"

        await asyncio.sleep(RATE_LIMIT_DELAY)
        resp = await client.get(xbrl_url)
        resp.raise_for_status()
        return extract_financials(resp.text)

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {entry.accession_number}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Error parsing {entry.accession_number}: {e}")
        return None


async def insert_pit_snapshot(
    session: AsyncSession,
    entry: EdgarIndexEntry,
    financials: XBRLFinancials,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: int | None = None,
) -> bool:
    """Insert a parsed filing into pit_financial_snapshots. Returns True if inserted."""
    row = _build_snapshot_row(entry, financials, ticker, fiscal_year, fiscal_quarter)
    stmt = pg_insert(PITFinancialSnapshot).values(**row)
    stmt = stmt.on_conflict_do_nothing(index_elements=["accession_number"])
    result = await session.execute(stmt)
    return result.rowcount > 0
```

**Step 4: Add CLI subcommand to `cli.py`**

Add an `edgar-backfill` subparser that calls `build_full_index()` then iterates entries, fetching and inserting. Use checkpointing (save last processed accession to a file).

Pattern: follow the existing `seed` / `backfill-13f` CLI patterns already in `cli.py`.

**Step 5: Run tests**

Run: `uv run pytest api/tests/services/test_edgar_backfill.py -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add api/src/margin_api/services/edgar/backfill.py api/tests/services/test_edgar_backfill.py api/src/margin_api/cli.py
git commit -m "feat(api): add EDGAR backfill service and CLI for PIT financial snapshots"
```

---

### Task 5: Price Backfill CLI

**Files:**
- Create: `api/src/margin_api/services/edgar/price_backfill.py`
- Modify: `api/src/margin_api/cli.py` (add `price-backfill` subcommand)
- Test: `api/tests/services/test_price_backfill.py`

**Context:** Uses yfinance `download()` for bulk daily price history. Inserts into `pit_daily_prices`.

**Step 1: Write failing tests**

```python
"""Tests for price backfill service."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
import pandas as pd

from margin_api.services.edgar.price_backfill import (
    build_price_rows,
)


def test_build_price_rows_from_dataframe():
    """Convert a yfinance DataFrame into price row dicts."""
    dates = pd.date_range("2024-01-02", periods=3, freq="B")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [104.0, 105.0, 106.0],
            "Adj Close": [103.0, 104.0, 105.0],
            "Volume": [1000000, 1100000, 1200000],
        },
        index=dates,
    )
    rows = build_price_rows("AAPL", df)
    assert len(rows) == 3
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["close"] == 104.0
    assert rows[0]["date"] == date(2024, 1, 2)


def test_build_price_rows_skips_nan():
    dates = pd.date_range("2024-01-02", periods=2, freq="B")
    df = pd.DataFrame(
        {
            "Open": [100.0, float("nan")],
            "High": [105.0, float("nan")],
            "Low": [99.0, float("nan")],
            "Close": [104.0, float("nan")],
            "Adj Close": [103.0, float("nan")],
            "Volume": [1000000, 0],
        },
        index=dates,
    )
    rows = build_price_rows("AAPL", df)
    assert len(rows) == 1  # NaN row skipped
```

**Step 2: Run to verify failure**

Run: `uv run pytest api/tests/services/test_price_backfill.py -v`

**Step 3: Implement price backfill**

```python
"""Price backfill service — bulk download daily prices via yfinance."""
from __future__ import annotations

import logging
import math
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)


def build_price_rows(ticker: str, df: pd.DataFrame) -> list[dict]:
    """Convert a yfinance OHLCV DataFrame into row dicts for pit_daily_prices."""
    rows: list[dict] = []
    for idx, row in df.iterrows():
        close = row.get("Close")
        if close is None or (isinstance(close, float) and math.isnan(close)):
            continue
        rows.append({
            "ticker": ticker,
            "date": idx.date() if hasattr(idx, "date") else idx,
            "open": float(row.get("Open", 0)),
            "high": float(row.get("High", 0)),
            "low": float(row.get("Low", 0)),
            "close": float(close),
            "adj_close": float(row.get("Adj Close", close)),
            "volume": int(row.get("Volume", 0)),
            "source": "yfinance",
        })
    return rows


async def backfill_prices_for_tickers(
    tickers: list[str],
    start_date: str = "2009-01-01",
    end_date: str | None = None,
    batch_size: int = 500,
    session_factory=None,
) -> dict[str, int]:
    """Download and insert daily prices for a list of tickers.

    Returns {ticker: rows_inserted} summary.
    """
    import yfinance as yf
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from margin_api.db.models import PITDailyPrice

    if end_date is None:
        end_date = date.today().isoformat()

    summary: dict[str, int] = {}

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        logger.info(f"Downloading prices for batch {i // batch_size + 1} ({len(batch)} tickers)")

        try:
            data = yf.download(
                batch,
                start=start_date,
                end=end_date,
                group_by="ticker" if len(batch) > 1 else "column",
                threads=True,
                progress=False,
            )
        except Exception as e:
            logger.error(f"yfinance download failed for batch: {e}")
            continue

        if data.empty:
            continue

        async with session_factory() as session:
            for ticker in batch:
                try:
                    if len(batch) > 1:
                        ticker_df = data[ticker].dropna(how="all")
                    else:
                        ticker_df = data.dropna(how="all")

                    rows = build_price_rows(ticker, ticker_df)
                    if not rows:
                        continue

                    # Bulk upsert
                    stmt = pg_insert(PITDailyPrice).values(rows)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["ticker", "date"]
                    )
                    await session.execute(stmt)
                    summary[ticker] = len(rows)
                except Exception as e:
                    logger.warning(f"Failed to process prices for {ticker}: {e}")
                    continue

            await session.commit()

    return summary
```

**Step 4: Add `price-backfill` CLI subcommand** (pattern: follow existing CLI structure in `cli.py`)

**Step 5: Run tests**

Run: `uv run pytest api/tests/services/test_price_backfill.py -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add api/src/margin_api/services/edgar/price_backfill.py api/tests/services/test_price_backfill.py api/src/margin_api/cli.py
git commit -m "feat(api): add yfinance daily price backfill for PIT backtesting"
```

---

### Task 6: Universe Assembly Service

**Files:**
- Create: `api/src/margin_api/services/edgar/universe_assembly.py`
- Test: `api/tests/services/test_universe_assembly.py`

**Context:** Scans `pit_financial_snapshots` by quarter to build `pit_universe_membership`. Detects delistings when a CIK stops filing for 2+ consecutive quarters.

**Step 1: Write failing tests**

```python
"""Tests for universe assembly service."""
import pytest
from datetime import date

from margin_api.services.edgar.universe_assembly import (
    detect_delistings,
    build_quarterly_membership,
)


def test_detect_delistings_two_missing_quarters():
    """A ticker missing 2+ consecutive quarters is marked delisted."""
    filing_quarters = {
        "AAPL": [date(2020, 3, 31), date(2020, 6, 30), date(2020, 9, 30), date(2020, 12, 31)],
        "GONE": [date(2020, 3, 31), date(2020, 6, 30)],  # Stops filing after Q2
    }
    all_quarters = [date(2020, 3, 31), date(2020, 6, 30), date(2020, 9, 30), date(2020, 12, 31)]
    result = detect_delistings(filing_quarters, all_quarters)
    assert "GONE" in result
    assert result["GONE"] == date(2020, 12, 31)  # Detected after 2 missing quarters
    assert "AAPL" not in result


def test_build_quarterly_membership():
    """Build membership rows for a single quarter."""
    active_tickers = {"AAPL": ("0000320193", date(2020, 9, 30), 2.5e12)}
    rows = build_quarterly_membership(date(2020, 9, 30), active_tickers, delistings={})
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["is_active"] is True
    assert rows[0]["market_cap"] == 2.5e12
```

**Step 2: Run to verify failure, then implement, then run to verify pass**

The service queries `pit_financial_snapshots` grouped by quarter to find active filers, then builds `pit_universe_membership` rows.

**Step 3: Commit**

```bash
git add api/src/margin_api/services/edgar/universe_assembly.py api/tests/services/test_universe_assembly.py
git commit -m "feat(api): add universe assembly with delisting detection for PIT data"
```

---

### Task 7: AsyncPointInTimeProvider Protocol in Engine

**Files:**
- Modify: `engine/src/margin_engine/backtesting/pit_provider.py`
- Modify: `engine/src/margin_engine/backtesting/__init__.py`
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py`
- Test: `engine/tests/backtesting/test_async_pit_provider.py`

**Step 1: Write failing test**

```python
"""Tests for async PIT provider protocol."""
import asyncio
import pytest
from datetime import date

from margin_engine.backtesting.pit_provider import AsyncPointInTimeProvider


class FakeAsyncProvider:
    """Test implementation of AsyncPointInTimeProvider."""

    async def get_universe(self, as_of_date):
        return []

    async def get_snapshot(self, ticker, as_of_date):
        return None

    async def get_price(self, ticker, as_of_date):
        return 100.0

    async def get_delisting(self, ticker):
        return None


def test_fake_async_provider_satisfies_protocol():
    provider = FakeAsyncProvider()
    assert isinstance(provider, AsyncPointInTimeProvider)


@pytest.mark.asyncio
async def test_fake_async_provider_get_price():
    provider = FakeAsyncProvider()
    price = await provider.get_price("AAPL", date(2024, 1, 1))
    assert price == 100.0
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/backtesting/test_async_pit_provider.py -v`

**Step 3: Add AsyncPointInTimeProvider to pit_provider.py**

Add after the existing `PointInTimeProvider` (around line 79):

```python
@runtime_checkable
class AsyncPointInTimeProvider(Protocol):
    """Async variant of PointInTimeProvider for database-backed providers."""

    async def get_universe(self, as_of_date: date) -> list[PITSnapshot]:
        """Return all tradeable stocks at the given date."""
        ...

    async def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        """Return point-in-time data for a specific ticker."""
        ...

    async def get_price(self, ticker: str, as_of_date: date) -> float | None:
        """Return closing price for a ticker at the given date."""
        ...

    async def get_delisting(self, ticker: str) -> DelistingEvent | None:
        """Return delisting event for a ticker, or None if still listed."""
        ...
```

**Step 4: Add async run path to ReplayOrchestrator**

Add `async def run_async(self)` to `replay_orchestrator.py` that mirrors `run()` but awaits provider calls. The constructor should accept `PointInTimeProvider | AsyncPointInTimeProvider`.

**Step 5: Export in `__init__.py`**

Add `AsyncPointInTimeProvider` to the imports and `__all__` list.

**Step 6: Run all backtesting tests**

Run: `uv run pytest engine/tests/backtesting/ -v`
Expected: All existing + new tests PASS.

**Step 7: Commit**

```bash
git add engine/src/margin_engine/backtesting/pit_provider.py engine/src/margin_engine/backtesting/replay_orchestrator.py engine/src/margin_engine/backtesting/__init__.py engine/tests/backtesting/test_async_pit_provider.py
git commit -m "feat(engine): add AsyncPointInTimeProvider protocol and async replay path"
```

---

### Task 8: DatabasePITProvider Implementation

**Files:**
- Create: `api/src/margin_api/services/pit_provider.py`
- Test: `api/tests/services/test_pit_provider.py`

**Context:** Implements `AsyncPointInTimeProvider` by querying `pit_financial_snapshots`, `pit_daily_prices`, and `pit_universe_membership`.

**Step 1: Write failing tests**

Tests should use the async test fixtures from `conftest.py`. Create test data directly in the test database (SQLite for tests). Verify:
- `get_snapshot()` returns most recent filing where `filing_date <= as_of_date`
- `get_snapshot()` does NOT return filings with `filing_date > as_of_date` (lookahead prevention)
- `get_universe()` returns active tickers for the nearest quarter
- `get_price()` returns exact date match or nearest prior trading day
- `get_delisting()` returns event for delisted tickers, None for active

**Step 2: Implement DatabasePITProvider**

```python
"""Database-backed PIT provider for real backtesting."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PITFinancialSnapshot, PITDailyPrice, PITUniverseMembership
from margin_engine.backtesting.pit_provider import (
    AsyncPointInTimeProvider,
    PITSnapshot,
    DelistingEvent,
    DelistingType,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.sector import GICSSector


class DatabasePITProvider:
    """AsyncPointInTimeProvider backed by PostgreSQL PIT tables."""

    def __init__(self, session: AsyncSession, min_market_cap: float = 100_000_000):
        self._session = session
        self._min_market_cap = min_market_cap

    async def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        # Fetch two most recent filings for YoY comparison
        stmt = (
            select(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.ticker == ticker)
            .where(PITFinancialSnapshot.filing_date <= as_of_date)
            .order_by(PITFinancialSnapshot.filing_date.desc())
            .limit(2)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return None

        current = rows[0]
        prior = rows[1] if len(rows) > 1 else None
        price = await self.get_price(ticker, as_of_date)
        if price is None:
            return None

        period = _build_period(current, prior)
        profile = _build_profile(ticker, current)

        return PITSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            profile=profile,
            period=period,
            price=price,
            filing_date=current.filing_date,
        )

    async def get_universe(self, as_of_date: date) -> list[PITSnapshot]:
        # Find nearest quarter <= as_of_date
        quarter_stmt = (
            select(func.max(PITUniverseMembership.quarter_date))
            .where(PITUniverseMembership.quarter_date <= as_of_date)
        )
        result = await self._session.execute(quarter_stmt)
        nearest_quarter = result.scalar_one_or_none()
        if nearest_quarter is None:
            return []

        # Get active tickers with sufficient market cap
        members_stmt = (
            select(PITUniverseMembership.ticker)
            .where(PITUniverseMembership.quarter_date == nearest_quarter)
            .where(PITUniverseMembership.is_active.is_(True))
            .where(PITUniverseMembership.market_cap >= self._min_market_cap)
        )
        result = await self._session.execute(members_stmt)
        tickers = [row[0] for row in result.all()]

        # Batch load snapshots
        snapshots = []
        for ticker in tickers:
            snap = await self.get_snapshot(ticker, as_of_date)
            if snap is not None:
                snapshots.append(snap)
        return snapshots

    async def get_price(self, ticker: str, as_of_date: date) -> float | None:
        stmt = (
            select(PITDailyPrice.close)
            .where(PITDailyPrice.ticker == ticker)
            .where(PITDailyPrice.date <= as_of_date)
            .order_by(PITDailyPrice.date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None

    async def get_delisting(self, ticker: str) -> DelistingEvent | None:
        stmt = (
            select(PITUniverseMembership)
            .where(PITUniverseMembership.ticker == ticker)
            .where(PITUniverseMembership.delist_detected_at.is_not(None))
            .order_by(PITUniverseMembership.quarter_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        return DelistingEvent(
            ticker=ticker,
            delist_date=row.delist_detected_at,
            delist_type=DelistingType.VOLUNTARY,  # default, refined later if data available
            last_price=row.last_known_price or 0.0,
        )
```

Include helper functions `_build_period()` and `_build_profile()` that convert DB row JSONB → engine Pydantic models (same pattern as `build_financial_period()` in `api/src/margin_api/services/scoring.py`).

**Step 3: Run tests**

Run: `uv run pytest api/tests/services/test_pit_provider.py -v`
Expected: PASS.

**Step 4: Commit**

```bash
git add api/src/margin_api/services/pit_provider.py api/tests/services/test_pit_provider.py
git commit -m "feat(api): add DatabasePITProvider for real PIT backtesting"
```

---

### Task 9: PIT Correctness Tests

**Files:**
- Create: `api/tests/services/test_pit_correctness.py`

**Context:** These are the critical tests that prove no lookahead bias, no survivorship bias, and correct price alignment.

**Step 1: Write correctness tests**

```python
"""PIT correctness tests — prove no lookahead bias or survivorship bias."""
import pytest
from datetime import date


class TestNoLookaheadBias:
    """Verify that data filed AFTER as_of_date is never returned."""

    async def test_filing_lag_respected(self, session):
        """A filing dated 2024-11-01 should NOT appear when querying as_of 2024-10-31."""
        # Insert filing with filing_date=2024-11-01
        # Query get_snapshot(ticker, date(2024, 10, 31))
        # Assert returns PRIOR quarter's filing, not this one
        ...

    async def test_future_filing_invisible(self, session):
        """Poison test: filing_date=2099-01-01 never appears."""
        # Insert poison filing
        # Query any date before 2099
        # Assert poison filing not returned
        ...


class TestSurvivorshipBias:
    """Verify delisted companies are excluded from post-delisting universes."""

    async def test_delisted_excluded_from_universe(self, session):
        """A company delisted in 2020 should not appear in 2021 universe."""
        ...

    async def test_delisted_included_before_delist(self, session):
        """A company delisted in 2020 SHOULD appear in 2019 universe."""
        ...


class TestPriceAlignment:
    """Verify correct price date handling."""

    async def test_exact_date_match(self, session):
        """get_price returns exact date when available."""
        ...

    async def test_weekend_returns_friday(self, session):
        """get_price on Saturday returns most recent prior trading day."""
        ...

    async def test_no_future_price(self, session):
        """get_price never returns a date after as_of_date."""
        ...
```

**Step 2: Implement all test bodies with real DB fixtures**

**Step 3: Run**

Run: `uv run pytest api/tests/services/test_pit_correctness.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add api/tests/services/test_pit_correctness.py
git commit -m "test(api): add PIT correctness tests for lookahead and survivorship bias"
```

---

### Task 10: API Wiring — Replace Synthetic with Real

**Files:**
- Modify: `api/src/margin_api/services/backtest.py`
- Modify: `api/src/margin_api/routes/backtest.py`
- Test: `api/tests/routes/test_backtest.py` (update existing tests)

**Context:** Replace `get_default_replay_result()` with a function that reads from `backtest_runs` table (pre-computed by worker). Wire `POST /backtest/replay` to instantiate `DatabasePITProvider` + `ReplayOrchestrator` and run real backtests.

**Step 1: Modify `services/backtest.py`**

- Keep `get_default_replay_result()` as a fallback for when no pre-computed result exists
- Add `get_precomputed_default(session) -> ReplayResult | None` that reads from `backtest_runs` WHERE `name = 'default'` AND `status = 'complete'` ORDER BY `created_at DESC`
- Add `run_real_backtest(session, config) -> ReplayResult` that instantiates `DatabasePITProvider` + `ReplayOrchestrator` and runs `run_async()`
- Modify `precompute_default_backtest()` to call `run_real_backtest()` instead of `get_default_replay_result()`

**Step 2: Modify routes**

- `GET /backtest/default`: Try `get_precomputed_default(session)` first, fall back to `get_default_replay_result()`
- `POST /backtest/replay`: Call `run_real_backtest(session, config)` — returns real results
- `GET /backtest/teaser/{ticker}` and `/portfolio-teaser`: Same pattern (precomputed or fallback)

**Step 3: Update existing route tests**

Existing tests may expect synthetic values. Update to accept either synthetic or real responses.

**Step 4: Run all backtest tests**

Run: `uv run pytest api/tests/routes/test_backtest.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add api/src/margin_api/services/backtest.py api/src/margin_api/routes/backtest.py api/tests/routes/test_backtest.py
git commit -m "feat(api): wire backtest endpoints to real PIT data with synthetic fallback"
```

---

### Task 11: Precompute + Shadow Portfolio Workers

**Files:**
- Modify: `api/src/margin_api/workers.py`

**Context:** Add ARQ worker jobs:
1. `precompute_default_backtest` — weekly cron, runs full 2009–present backtest, stores in `backtest_runs`
2. `snapshot_shadow_portfolio` — daily cron, records current scored portfolio as immutable snapshot in `shadow_portfolio_snapshots`

**Step 1: Add worker functions**

Follow existing worker patterns in `workers.py`. The `precompute_default_backtest` worker:
- Creates a DB session
- Instantiates `DatabasePITProvider`
- Creates `ReplayOrchestrator` with default `ReplayConfig(start_date=date(2009, 1, 1))`
- Calls `run_async()`
- Serializes `ReplayResult` to `backtest_runs` row

The `snapshot_shadow_portfolio` worker:
- Queries latest published V4Scores
- Builds portfolio positions
- Inserts into `shadow_portfolio_snapshots`

**Step 2: Register in cron schedule**

```python
cron_jobs = [
    # ... existing crons ...
    cron(precompute_default_backtest, weekday="sun", hour=3, minute=0),
    cron(snapshot_shadow_portfolio, hour=22, minute=30),
]
```

**Step 3: Write tests for worker functions**

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/workers/test_backtest_workers.py
git commit -m "feat(worker): add precompute and shadow portfolio cron jobs for PIT backtesting"
```

---

### Task 12: Incremental Daily Update Pipeline

**Files:**
- Create: `api/src/margin_api/services/edgar/daily_update.py`
- Modify: `api/src/margin_api/workers.py` (add daily EDGAR check)

**Context:** After initial backfill, keep PIT tables current:
1. Daily EDGAR check: fetch today's filings from EDGAR recent index, parse new 10-K/10-Q
2. Daily price append: download yesterday's prices, insert into `pit_daily_prices`
3. Quarterly universe refresh: after each quarter end, rebuild `pit_universe_membership`

**Step 1: Implement daily update service**

```python
"""Daily incremental updates for PIT data."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

from margin_api.services.edgar.index_builder import (
    USER_AGENT,
    EdgarIndexEntry,
    load_cik_ticker_map,
)
from margin_api.services.edgar.backfill import fetch_and_parse_filing, insert_pit_snapshot

logger = logging.getLogger(__name__)

RECENT_FILINGS_URL = "https://efts.sec.gov/LATEST/search-index?q=%2210-K%22+OR+%2210-Q%22&dateRange=custom&startdt={start}&enddt={end}"


async def check_new_filings(session_factory, lookback_days: int = 1):
    """Check EDGAR for new 10-K/10-Q filings since yesterday."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    # Use EDGAR EFTS API or full-index for the current quarter
    # Parse new filings and insert into pit_financial_snapshots
    ...


async def append_daily_prices(session_factory, tickers: list[str]):
    """Download and insert yesterday's closing prices."""
    from margin_api.services.edgar.price_backfill import backfill_prices_for_tickers
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    await backfill_prices_for_tickers(
        tickers, start_date=yesterday, end_date=today, session_factory=session_factory
    )
```

**Step 2: Add worker and cron**

```python
async def daily_pit_update(ctx):
    """Daily PIT data update — new EDGAR filings + price append."""
    ...

# In cron_jobs:
cron(daily_pit_update, hour=23, minute=0),
```

**Step 3: Write tests and commit**

```bash
git add api/src/margin_api/services/edgar/daily_update.py api/src/margin_api/workers.py
git commit -m "feat(worker): add daily PIT data update pipeline for EDGAR + prices"
```

---

## Validation Checkpoints

Run these after completing each group:

| After Tasks | Validation Command | Expected |
|---|---|---|
| T1 | `uv run alembic upgrade head && uv run pytest api/tests/ -v` | Migration applies, all tests pass |
| T2, T3 | `uv run pytest api/tests/services/test_edgar_*.py api/tests/services/test_xbrl_parser.py -v` | Index + parser tests pass |
| T4, T5 | `uv run python -m margin_api.cli edgar-backfill --help && uv run python -m margin_api.cli price-backfill --help` | CLI commands registered |
| T7 | `uv run pytest engine/tests/backtesting/ -v` | All engine tests pass including new async tests |
| T8, T9 | `uv run pytest api/tests/services/test_pit_provider.py api/tests/services/test_pit_correctness.py -v` | PIT correctness proven |
| T10, T11 | `uv run pytest api/tests/ -v` | All API tests pass, endpoints return real data when available |
| All | `uv run pytest -v` | Full suite green |
