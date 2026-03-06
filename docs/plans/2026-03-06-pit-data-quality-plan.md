# PIT Data Quality Improvement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich PIT backtest data with real GICS sectors, volume/market-cap metrics, corrected delisting detection, and filter diagnostics to produce a meaningful backtest.

**Architecture:** Two phases. Phase 1 adds schema columns, SIC→GICS mapping, and fixes universe assembly (delisting threshold, batch queries, computed metrics). Phase 2 adds filter failure diagnostics to the backtest audit trail, re-enables the liquidity filter, and re-runs the backtest.

**Tech Stack:** SQLAlchemy 2.0, asyncpg, Alembic, SEC EDGAR API, pytest-asyncio

---

### Task 1: Alembic Migration — SIC Sector Map Table + New Columns

**Files:**
- Create: `api/alembic/versions/<auto>_add_sic_sector_map_and_columns.py`
- Modify: `api/src/margin_api/db/models.py:1058-1132`

**Step 1: Add ORM model for `sic_sector_map` and new columns**

In `api/src/margin_api/db/models.py`, add after the `PITUniverseMembership` class (around line 1132):

```python
class SICSectorMap(Base):
    """Static mapping from SIC codes to GICS sectors."""

    __tablename__ = "sic_sector_map"

    sic_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    gics_sector: Mapped[str] = mapped_column(String(50))
    sic_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

Add `sic_code` column to `PITFinancialSnapshot` (after `fiscal_quarter`, around line 1075):

```python
    sic_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Add `sic_code` and `avg_daily_volume` columns to `PITUniverseMembership` (after `market_cap`, around line 1124):

```python
    sic_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_daily_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
```

**Step 2: Generate the migration**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic revision --autogenerate -m "add sic_sector_map and columns"`

**Step 3: Edit migration — add SIC→GICS seed data**

Add a `data_upgrades()` call at the end of the `upgrade()` function that bulk-inserts the SIC→GICS mapping. Use `op.bulk_insert()` with the table reference. The mapping covers ~80 SIC range groups:

```python
sic_sector_map = sa.table(
    "sic_sector_map",
    sa.column("sic_code", sa.Integer),
    sa.column("gics_sector", sa.String),
    sa.column("sic_description", sa.String),
)

# SIC range → GICS mapping (one row per SIC code seen in data)
# Generate entries for each SIC code in range
sic_ranges = [
    # Agriculture, Forestry, Fishing (0100-0999) → Consumer Staples
    (100, 999, "Consumer Staples", "Agriculture/Forestry/Fishing"),
    # Mining (1000-1499) → Materials (except 1300s = Energy)
    (1000, 1299, "Materials", "Mining"),
    (1300, 1399, "Energy", "Oil & Gas Extraction"),
    (1400, 1499, "Materials", "Mining & Quarrying"),
    # Construction (1500-1799) → Industrials
    (1500, 1799, "Industrials", "Construction"),
    # Manufacturing — Food/Tobacco (2000-2111) → Consumer Staples
    (2000, 2111, "Consumer Staples", "Food/Tobacco Manufacturing"),
    # Manufacturing — Textiles/Apparel/Furniture (2200-2599) → Consumer Discretionary
    (2200, 2599, "Consumer Discretionary", "Textiles/Apparel/Furniture"),
    # Manufacturing — Paper/Chemicals (2600-2899) → Materials
    (2600, 2899, "Materials", "Paper/Chemicals"),
    # Manufacturing — Rubber/Plastics/Stone/Metals (2900-3499) → Materials or Industrials
    (2900, 3299, "Materials", "Rubber/Plastics/Stone/Metals"),
    (3300, 3499, "Industrials", "Primary Metals/Fabricated Metals"),
    # Manufacturing — Industrial Machinery (3500-3599) → Industrials
    (3500, 3599, "Industrials", "Industrial Machinery"),
    # Manufacturing — Computer/Electronic (3600-3699) → Information Technology
    (3600, 3699, "Information Technology", "Electronic Equipment"),
    # Manufacturing — Transportation Equipment (3700-3799) → Industrials or Consumer Disc
    (3700, 3719, "Industrials", "Transportation Equipment"),
    (3720, 3729, "Industrials", "Aircraft"),
    (3730, 3799, "Industrials", "Ship/Railroad/Other Transport"),
    # Manufacturing — Instruments (3800-3899) → Health Care or Technology
    (3800, 3841, "Health Care", "Medical Instruments"),
    (3842, 3851, "Health Care", "Medical Devices/Ophthalmic"),
    (3852, 3899, "Information Technology", "Instruments"),
    # Manufacturing — Misc (3900-3999) → Consumer Discretionary
    (3900, 3999, "Consumer Discretionary", "Misc Manufacturing"),
    # Transportation (4000-4799) → Industrials
    (4000, 4799, "Industrials", "Transportation"),
    # Communications (4800-4899) → Communication Services
    (4800, 4899, "Communication Services", "Communications"),
    # Utilities (4900-4999) → Utilities
    (4900, 4999, "Utilities", "Electric/Gas/Sanitary Services"),
    # Wholesale Trade (5000-5199) → Industrials
    (5000, 5199, "Industrials", "Wholesale Trade"),
    # Retail Trade (5200-5999) → Consumer Discretionary (except grocery/drug)
    (5200, 5399, "Consumer Discretionary", "Retail - General"),
    (5400, 5499, "Consumer Staples", "Retail - Grocery"),
    (5500, 5599, "Consumer Discretionary", "Retail - Auto/Gas"),
    (5600, 5699, "Consumer Discretionary", "Retail - Apparel"),
    (5700, 5799, "Consumer Discretionary", "Retail - Home"),
    (5800, 5899, "Consumer Discretionary", "Retail - Eating/Drinking"),
    (5900, 5999, "Consumer Staples", "Retail - Drug/Other"),
    # Finance, Insurance, Real Estate (6000-6799)
    (6000, 6199, "Financials", "Banking/Credit"),
    (6200, 6299, "Financials", "Security/Commodity Brokers"),
    (6300, 6499, "Financials", "Insurance"),
    (6500, 6553, "Real Estate", "Real Estate"),
    (6600, 6799, "Financials", "Other Finance"),
    # Services — Hotels/Personal/Business (7000-7399) → Consumer Discretionary
    (7000, 7099, "Consumer Discretionary", "Hotels/Lodging"),
    (7100, 7199, "Consumer Discretionary", "Laundry/Personal Services"),
    (7200, 7299, "Consumer Discretionary", "Personal Services"),
    (7300, 7399, "Industrials", "Business Services"),
    # Services — Computer/Software (7370-7379) → Technology
    # NOTE: this range overrides the 7300-7399 above — handle in code by
    # inserting specific codes AFTER range codes (last write wins)
    # Services — Auto Repair/Entertainment (7500-7999) → Consumer Discretionary
    (7400, 7499, "Industrials", "Misc Business Services"),
    (7500, 7599, "Consumer Discretionary", "Auto Repair"),
    (7600, 7699, "Consumer Discretionary", "Misc Repair"),
    (7700, 7799, "Consumer Discretionary", "Recreation"),
    (7800, 7999, "Communication Services", "Amusement/Recreation"),
    # Health Services (8000-8099) → Health Care
    (8000, 8099, "Health Care", "Health Services"),
    # Legal/Educational/Social/Engineering Services
    (8100, 8199, "Industrials", "Legal Services"),
    (8200, 8299, "Consumer Discretionary", "Educational Services"),
    (8300, 8399, "Health Care", "Social Services"),
    (8400, 8499, "Industrials", "Museums/Membership Orgs"),
    (8700, 8799, "Industrials", "Engineering/Management Services"),
    # Software override: 7370-7379 → Technology
    (7370, 7379, "Information Technology", "Computer Services/Software"),
    # Pharma: 2830-2836 → Health Care (override Materials range)
    (2830, 2836, "Health Care", "Pharmaceuticals"),
    # Biotech: 2835-2836 already covered above
    # Semiconductors: 3674 → Technology
    (3674, 3674, "Information Technology", "Semiconductors"),
    # Public admin (9000-9999) → Industrials (rare in SEC filings)
    (9000, 9999, "Industrials", "Public Administration"),
]

rows = []
seen = set()
for start, end, sector, desc in sic_ranges:
    for code in range(start, end + 1):
        if code not in seen:
            rows.append({"sic_code": code, "gics_sector": sector, "sic_description": desc})
            seen.add(code)
        else:
            # Override: later range wins (e.g., 7370-7379 overrides 7300-7399)
            for i, r in enumerate(rows):
                if r["sic_code"] == code:
                    rows[i] = {"sic_code": code, "gics_sector": sector, "sic_description": desc}
                    break

op.bulk_insert(sic_sector_map, rows)
```

**Step 4: Add idempotent column checks to migration**

Wrap column adds with `inspector.has_table()` / column-exists checks per project convention.

**Step 5: Run migration locally**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic upgrade head`

**Step 6: Verify no multiple heads**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic heads`
Expected: single head

**Step 7: Commit**

```bash
git add api/alembic/versions/ api/src/margin_api/db/models.py
git commit -m "feat(api): add sic_sector_map table and sic_code/avg_daily_volume columns"
```

---

### Task 2: Extend CIK→Ticker Map to Include SIC Codes

**Files:**
- Modify: `api/src/margin_api/services/edgar/index_builder.py:178-198`
- Test: `api/tests/services/test_edgar_index_builder.py`

**Step 1: Write failing test for SIC code in CIK map**

In `api/tests/services/test_edgar_index_builder.py`, add:

```python
class TestLoadCikTickerMapWithSic:
    """Tests for load_cik_ticker_sic_map using company_tickers_exchange.json."""

    @pytest.mark.asyncio
    async def test_returns_ticker_and_sic(self, httpx_mock):
        """SIC codes are returned alongside tickers."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers_exchange.json",
            json={
                "fields": ["cik", "name", "ticker", "exchange", "sic"],
                "data": [
                    [320193, "Apple Inc.", "AAPL", "Nasdaq", "3571"],
                    [789019, "Microsoft Corp", "MSFT", "Nasdaq", "7372"],
                ],
            },
        )
        from margin_api.services.edgar.index_builder import load_cik_ticker_sic_map

        result = await load_cik_ticker_sic_map(httpx.AsyncClient())
        assert result[320193] == ("AAPL", 3571)
        assert result[789019] == ("MSFT", 7372)

    @pytest.mark.asyncio
    async def test_missing_sic_defaults_to_none(self, httpx_mock):
        """Entries without SIC codes get None."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers_exchange.json",
            json={
                "fields": ["cik", "name", "ticker", "exchange", "sic"],
                "data": [
                    [12345, "No SIC Corp", "NOSIC", "NYSE", ""],
                ],
            },
        )
        from margin_api.services.edgar.index_builder import load_cik_ticker_sic_map

        result = await load_cik_ticker_sic_map(httpx.AsyncClient())
        assert result[12345] == ("NOSIC", None)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_edgar_index_builder.py::TestLoadCikTickerMapWithSic -v`
Expected: ImportError — `load_cik_ticker_sic_map` doesn't exist

**Step 3: Implement `load_cik_ticker_sic_map`**

In `api/src/margin_api/services/edgar/index_builder.py`, add after `load_cik_ticker_map()`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_edgar_index_builder.py::TestLoadCikTickerMapWithSic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/index_builder.py api/tests/services/test_edgar_index_builder.py
git commit -m "feat(api): add load_cik_ticker_sic_map for SIC code retrieval"
```

---

### Task 3: SIC→GICS Lookup Helper

**Files:**
- Create: `api/src/margin_api/services/sic_mapper.py`
- Test: `api/tests/services/test_sic_mapper.py`

**Step 1: Write failing test**

Create `api/tests/services/test_sic_mapper.py`:

```python
"""Tests for SIC→GICS sector mapping."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import SICSectorMap
from margin_engine.models.financial import GICSSector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        # Seed test data
        sess.add_all([
            SICSectorMap(sic_code=3571, gics_sector="Information Technology", sic_description="Computers"),
            SICSectorMap(sic_code=2830, gics_sector="Health Care", sic_description="Pharmaceuticals"),
            SICSectorMap(sic_code=6020, gics_sector="Financials", sic_description="Banking"),
        ])
        await sess.commit()
        yield sess


class TestSICMapper:
    @pytest.mark.asyncio
    async def test_known_sic_code(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(3571) == GICSSector.TECHNOLOGY

    @pytest.mark.asyncio
    async def test_unknown_sic_falls_back_to_industrials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(9999) == GICSSector.INDUSTRIALS

    @pytest.mark.asyncio
    async def test_none_sic_falls_back_to_industrials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(None) == GICSSector.INDUSTRIALS

    @pytest.mark.asyncio
    async def test_pharma_maps_to_healthcare(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(2830) == GICSSector.HEALTHCARE

    @pytest.mark.asyncio
    async def test_financials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(6020) == GICSSector.FINANCIALS
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_sic_mapper.py -v`
Expected: ImportError

**Step 3: Implement SICMapper**

Create `api/src/margin_api/services/sic_mapper.py`:

```python
"""SIC code to GICS sector mapping."""

from __future__ import annotations

from margin_engine.models.financial import GICSSector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import SICSectorMap

# Map GICS sector string values to enum members
_SECTOR_LOOKUP: dict[str, GICSSector] = {s.value: s for s in GICSSector}


class SICMapper:
    """In-memory cache of SIC→GICS mappings loaded from the database."""

    def __init__(self, mapping: dict[int, GICSSector]) -> None:
        self._mapping = mapping

    @classmethod
    async def load(cls, session: AsyncSession) -> SICMapper:
        """Load all SIC→GICS mappings from sic_sector_map table."""
        result = await session.execute(select(SICSectorMap))
        rows = result.scalars().all()

        mapping: dict[int, GICSSector] = {}
        for row in rows:
            sector = _SECTOR_LOOKUP.get(row.gics_sector)
            if sector is not None:
                mapping[row.sic_code] = sector

        return cls(mapping)

    def to_gics(self, sic_code: int | None) -> GICSSector:
        """Map a SIC code to a GICS sector. Falls back to INDUSTRIALS."""
        if sic_code is None:
            return GICSSector.INDUSTRIALS
        return self._mapping.get(sic_code, GICSSector.INDUSTRIALS)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_sic_mapper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/sic_mapper.py api/tests/services/test_sic_mapper.py
git commit -m "feat(api): add SICMapper for SIC→GICS sector lookup"
```

---

### Task 4: Fix Delisting Detection Threshold

**Files:**
- Modify: `api/src/margin_api/services/edgar/universe_assembly.py:64-97`
- Test: `api/tests/services/test_edgar_backfill.py` (or wherever `detect_delistings` is tested)

**Step 1: Find and update existing delisting tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest -v -k "delist" --collect-only 2>&1 | head -20`

Check existing tests. Update them to expect 8-quarter threshold instead of 2.

**Step 2: Write test for annual filers not being delisted**

Add to the relevant test file:

```python
def test_annual_filer_not_delisted_with_8q_threshold():
    """Annual filers that miss 3-4 quarters between 10-Ks should NOT be marked delisted."""
    from margin_api.services.edgar.universe_assembly import detect_delistings

    quarters = [date(2020, m, d) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]
    quarters += [date(2021, m, d) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]

    # Annual filer: files only in Q4 (10-K)
    filing_quarters = {"ANNUAL": [date(2020, 12, 31), date(2021, 12, 31)]}

    delistings = detect_delistings(filing_quarters, quarters)
    assert "ANNUAL" not in delistings


def test_truly_delisted_after_8_quarters():
    """A ticker missing 8+ consecutive quarters should be delisted."""
    from margin_api.services.edgar.universe_assembly import detect_delistings

    quarters = [date(2019 + y, m, d)
                for y in range(4) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]

    # Filed in Q1 2019 only
    filing_quarters = {"GONE": [date(2019, 3, 31)]}

    delistings = detect_delistings(filing_quarters, quarters)
    assert "GONE" in delistings
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -k "annual_filer_not_delisted" -v`
Expected: FAIL (current threshold is 2, so annual filer gets delisted)

**Step 4: Change threshold from 2 to 8**

In `api/src/margin_api/services/edgar/universe_assembly.py:64-97`, change:

```python
def detect_delistings(
    filing_quarters: dict[str, list[date]],
    all_quarters: list[date],
    consecutive_miss_threshold: int = 8,
) -> dict[str, date]:
    """Detect tickers that stopped filing for N+ consecutive quarters.

    Args:
        filing_quarters: {ticker: [quarter_dates_they_filed]}
        all_quarters: sorted list of all quarter end dates
        consecutive_miss_threshold: Number of consecutive quarters without
            a filing before marking as delisted. Default 8 (2 years) to
            accommodate annual-only filers who naturally miss 3 quarters.

    Returns:
        {ticker: delist_detected_date} for tickers exceeding the threshold.
    """
    if len(all_quarters) < 2:
        return {}

    delistings: dict[str, date] = {}

    for ticker, filed_quarters in filing_quarters.items():
        filed_set = set(filed_quarters)
        consecutive_misses = 0

        for q in all_quarters:
            if q in filed_set:
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                if consecutive_misses >= consecutive_miss_threshold:
                    delistings[ticker] = q
                    break

    return delistings
```

Update the module docstring at the top to say "8+ consecutive quarters" instead of "2+".

**Step 5: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -k "delist" -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/services/edgar/universe_assembly.py api/tests/
git commit -m "fix(api): change delisting threshold from 2 to 8 consecutive quarters"
```

---

### Task 5: Batch `fill_last_known_prices()` and Compute Market Cap / Volume

**Files:**
- Modify: `api/src/margin_api/services/edgar/universe_assembly.py:137-313`
- Test: `api/tests/services/test_edgar_backfill.py` (existing universe assembly tests)

**Step 1: Write tests for market_cap and avg_daily_volume computation**

Add to the relevant test file (alongside existing universe assembly tests):

```python
@pytest.mark.asyncio
async def test_market_cap_computed_during_assembly(session):
    """market_cap = shares_outstanding × close_price at quarter date."""
    # Insert a filing with shares_outstanding
    session.add(PITFinancialSnapshot(
        cik="12345", ticker="TEST", filing_date=date(2020, 2, 15),
        period_end=date(2019, 12, 31), form_type="10-K",
        accession_number="0001-20-000001",
        income_statement={}, balance_sheet={}, cash_flow={},
        shares_outstanding=1_000_000, fiscal_year=2019,
    ))
    # Insert a price near the quarter date
    session.add(PITDailyPrice(
        ticker="TEST", date=date(2019, 12, 31),
        open=50.0, high=51.0, low=49.0, close=50.0, adj_close=50.0,
        volume=100_000, source="yfinance",
    ))
    await session.commit()

    result = await assemble_universe(session)

    # Check the membership row has market_cap = 1M × $50 = $50M
    stmt = select(PITUniverseMembership).where(
        PITUniverseMembership.ticker == "TEST",
        PITUniverseMembership.quarter_date == date(2019, 12, 31),
    )
    row = (await session.execute(stmt)).scalar_one()
    assert row.market_cap == pytest.approx(50_000_000.0, rel=0.01)
```

**Step 2: Implement batch market_cap and avg_daily_volume in `assemble_universe()`**

After the existing per-quarter loop that builds membership rows, add batch queries using window functions to compute market_cap and avg_daily_volume. Then update rows via batch UPDATE.

The key queries:

**Market cap batch** — for each (ticker, quarter_date), get latest `shares_outstanding` from filings and latest `close` from prices:

```python
# Batch compute market_cap: shares_outstanding × close_price
# Get latest shares_outstanding per ticker at each quarter
# Get latest close price per ticker at each quarter
# Multiply and update pit_universe_memberships.market_cap
```

**Avg daily volume batch** — trailing 60-day average of `close × volume`:

```python
# For each (ticker, quarter_date), compute AVG(close * volume)
# over the 60 most recent trading days before quarter_date
```

**Step 3: Replace N+1 `fill_last_known_prices()`**

Replace the per-ticker loop (lines 260-313) with a batch query:

```python
async def fill_last_known_prices(session: AsyncSession) -> int:
    """Fill last_known_price for delisted tickers using batch window query."""
    from sqlalchemy import func as sa_func

    # Find all delisted memberships missing last_known_price
    stmt = select(
        PITUniverseMembership.ticker,
        PITUniverseMembership.delist_detected_at,
    ).where(
        PITUniverseMembership.delist_detected_at.isnot(None),
        PITUniverseMembership.last_known_price.is_(None),
    ).distinct()
    result = await session.execute(stmt)
    delisted = result.all()

    if not delisted:
        return 0

    # Build {ticker: delist_date} for batch query
    delist_dates: dict[str, date] = {}
    for ticker, delist_date in delisted:
        if ticker not in delist_dates or delist_date < delist_dates[ticker]:
            delist_dates[ticker] = delist_date

    tickers = list(delist_dates.keys())

    # Batch: get latest price before delist date per ticker
    price_rn = (
        sa_func.row_number()
        .over(partition_by=PITDailyPrice.ticker, order_by=PITDailyPrice.date.desc())
        .label("rn")
    )
    price_sub = (
        select(PITDailyPrice.ticker, PITDailyPrice.close, price_rn)
        .where(PITDailyPrice.ticker.in_(tickers))
        .subquery()
    )
    price_stmt = select(price_sub.c.ticker, price_sub.c.close).where(price_sub.c.rn == 1)
    price_result = await session.execute(price_stmt)
    last_prices: dict[str, float] = {row.ticker: float(row.close) for row in price_result.all()}

    # Batch update
    updated = 0
    for ticker, price in last_prices.items():
        stmt_upd = (
            update(PITUniverseMembership)
            .where(
                PITUniverseMembership.ticker == ticker,
                PITUniverseMembership.delist_detected_at.isnot(None),
                PITUniverseMembership.last_known_price.is_(None),
            )
            .values(last_known_price=price)
        )
        result = await session.execute(stmt_upd)
        updated += result.rowcount

    await session.commit()
    logger.info("[universe-assembly] Filled last_known_price for %d delisted tickers", updated)
    return updated
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_edgar_backfill.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/universe_assembly.py api/tests/
git commit -m "feat(api): batch compute market_cap/volume, fix fill_last_known_prices N+1"
```

---

### Task 6: Wire SIC Codes into Universe Assembly

**Files:**
- Modify: `api/src/margin_api/services/edgar/universe_assembly.py:137-257`
- Modify: `api/src/margin_api/services/edgar/backfill.py` (passes CIK map to assembly)
- Modify: `api/src/margin_api/workers.py` (bootstrap_pit_data calls)

**Step 1: Update `assemble_universe()` signature to accept SIC map**

```python
async def assemble_universe(
    session: AsyncSession,
    cik_sic_map: dict[int, int | None] | None = None,
) -> dict[str, int]:
```

When `cik_sic_map` is provided, look up each ticker's CIK → SIC code and store it on the membership row.

**Step 2: Update `build_quarterly_membership()` to include `sic_code`**

Add `sic_code` to the row dict.

**Step 3: Update backfill.py and workers.py to pass CIK→SIC map**

The `bootstrap_pit_data` worker already calls `build_full_index()` which returns a CIK map. Switch it to use `load_cik_ticker_sic_map()` and pass SIC data through to `assemble_universe()`.

**Step 4: Run existing tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_edgar_backfill.py -v`
Expected: PASS (existing tests pass None for cik_sic_map, backward compatible)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/edgar/ api/src/margin_api/workers.py api/tests/
git commit -m "feat(api): wire SIC codes through universe assembly pipeline"
```

---

### Task 7: Update PIT Provider — Real Sectors, Volume, History

**Files:**
- Modify: `api/src/margin_api/services/pit_provider.py:376-392`
- Modify: `api/src/margin_api/services/pit_provider.py:94-120` (get_universe)
- Test: `api/tests/services/test_pit_provider.py`

**Step 1: Write tests for real sector lookup**

Add to `api/tests/services/test_pit_provider.py`:

```python
@pytest.mark.asyncio
async def test_profile_uses_sic_sector(session):
    """_build_profile should use SIC→GICS mapping instead of hardcoded TECHNOLOGY."""
    # Seed SIC sector map
    from margin_api.db.models import SICSectorMap
    session.add(SICSectorMap(sic_code=2830, gics_sector="Health Care"))
    # Seed snapshot with sic_code
    session.add(PITFinancialSnapshot(
        cik="12345", ticker="PFE", filing_date=date(2020, 2, 15),
        period_end=date(2019, 12, 31), form_type="10-K",
        accession_number="0001-20-000001",
        income_statement=_make_income_statement(),
        balance_sheet=_make_balance_sheet(),
        cash_flow=_make_cash_flow(),
        shares_outstanding=5_000_000, fiscal_year=2019, sic_code=2830,
    ))
    session.add(PITDailyPrice(
        ticker="PFE", date=date(2020, 3, 1),
        open=35.0, high=36.0, low=34.0, close=35.0, adj_close=35.0,
        volume=1_000_000, source="yfinance",
    ))
    await session.commit()

    provider = DatabasePITProvider(session)
    snapshot = await provider.get_snapshot("PFE", date(2020, 3, 15))
    assert snapshot is not None
    assert snapshot.profile.sector == GICSSector.HEALTHCARE
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_pit_provider.py::test_profile_uses_sic_sector -v`
Expected: FAIL (still returns TECHNOLOGY)

**Step 3: Update `DatabasePITProvider` to load SIC mapper**

```python
class DatabasePITProvider:
    def __init__(self, session: AsyncSession, min_market_cap: float = 100_000_000):
        self._session = session
        self._min_market_cap = min_market_cap
        self._sic_mapper: SICMapper | None = None

    async def _get_sic_mapper(self) -> SICMapper:
        if self._sic_mapper is None:
            from margin_api.services.sic_mapper import SICMapper
            self._sic_mapper = await SICMapper.load(self._session)
        return self._sic_mapper
```

**Step 4: Update `_build_profile` to accept SIC mapper and use real sector**

Change from module-level function to method (or pass mapper):

```python
def _build_profile(ticker: str, row, price: float, sic_mapper: SICMapper | None = None) -> AssetProfile:
    shares = row.shares_outstanding or 0
    market_cap = Decimal(str(shares)) * Decimal(str(price))
    sic_code = getattr(row, "sic_code", None)

    if sic_mapper and sic_code is not None:
        sector = sic_mapper.to_gics(sic_code)
    else:
        sector = GICSSector.INDUSTRIALS  # Changed from TECHNOLOGY

    return AssetProfile(
        ticker=ticker,
        name=ticker,
        sector=sector,
        market_cap=market_cap,
        shares_outstanding=shares,
    )
```

**Step 5: Update `get_universe()` to re-enable `is_active` filter**

In `get_universe()`, restore the `is_active` filter:

```python
members_stmt = select(PITUniverseMembership.ticker.distinct()).where(
    PITUniverseMembership.quarter_date == nearest_quarter,
    PITUniverseMembership.is_active.is_(True),
)
```

Remove the comment about skipping is_active.

**Step 6: Populate `avg_daily_volume` and `years_of_history` on profile**

In the batch-build section of `get_universe()`, read `avg_daily_volume` from membership rows and compute `years_of_history` from earliest filing date.

**Step 7: Run all pit_provider tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_pit_provider.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add api/src/margin_api/services/pit_provider.py api/src/margin_api/services/sic_mapper.py api/tests/
git commit -m "feat(api): use real GICS sectors, volume, history in PIT provider"
```

---

### Task 8: Add `get_prices()` Batch Method

**Files:**
- Modify: `engine/src/margin_engine/backtesting/pit_provider.py:82-96`
- Modify: `api/src/margin_api/services/pit_provider.py`
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:470-479`
- Test: `api/tests/services/test_pit_provider.py`

**Step 1: Add `get_prices()` to both protocols**

In `engine/src/margin_engine/backtesting/pit_provider.py`, add to both `PointInTimeProvider` and `AsyncPointInTimeProvider`:

```python
    def get_prices(self, tickers: list[str], as_of_date: date) -> dict[str, float]:
        """Return closing prices for multiple tickers. Batch optimization."""
        ...
```

(Async version uses `async def`.)

**Step 2: Implement in `DatabasePITProvider`**

Already have the batch price query pattern from `get_universe()`. Extract into `get_prices()`:

```python
async def get_prices(self, tickers: list[str], as_of_date: date) -> dict[str, float]:
    """Batch price lookup using window functions."""
    from sqlalchemy import func as sa_func

    price_rn = (
        sa_func.row_number()
        .over(partition_by=PITDailyPrice.ticker, order_by=PITDailyPrice.date.desc())
        .label("prn")
    )
    price_sub = (
        select(PITDailyPrice.ticker, PITDailyPrice.close, price_rn)
        .where(PITDailyPrice.ticker.in_(tickers), PITDailyPrice.date <= as_of_date)
        .subquery()
    )
    stmt = select(price_sub.c.ticker, price_sub.c.close).where(price_sub.c.prn == 1)
    result = await self._session.execute(stmt)
    return {row.ticker: float(row.close) for row in result.all()}
```

**Step 3: Update `ReplayOrchestrator.run_async()` to use batch prices**

Replace lines 472-478:

```python
            # 6. Calculate portfolio value change (batch price lookup)
            if i > 0 and prev_holdings:
                holding_tickers = [h.ticker for h in prev_holdings]
                prices = await self._provider.get_prices(holding_tickers, rebal_date)
                total_return = 0.0
                for h in prev_holdings:
                    current_price = prices.get(h.ticker)
                    if current_price and h.entry_price > 0:
                        stock_return = (current_price / h.entry_price) - 1.0
                        total_return += h.weight * stock_return
                portfolio_value *= 1.0 + total_return
```

Also update the sync `run()` path (lines 231-238) similarly.

**Step 4: Update `InMemoryPITProvider` to implement `get_prices()`**

Check if `InMemoryPITProvider` exists and add the method (calls `get_price()` per ticker as fallback).

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_pit_provider.py engine/tests/backtesting/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/ api/src/margin_api/services/pit_provider.py api/tests/
git commit -m "perf: add batch get_prices() to PIT provider and orchestrator"
```

---

### Task 9: Filter Failure Diagnostics (Phase 2)

**Files:**
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:59-75` (RebalanceAuditRecord)
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:180-201` (sync filter loop)
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:421-442` (async filter loop)
- Test: `engine/tests/backtesting/` (existing orchestrator tests)

**Step 1: Add `filter_failure_breakdown` to `RebalanceAuditRecord`**

```python
class RebalanceAuditRecord(BaseModel):
    rebalance_date: date
    universe_size: int
    eliminated_count: int
    survivor_count: int
    selected_count: int
    top_holdings: list[dict]
    notable_events: list[str]
    filter_failure_breakdown: dict[str, int] = Field(default_factory=dict)
    factor_coverage: float
    available_factors: list[str]
    missing_factors: list[str]
    regime: MarketRegimeHistorical
    regime_state: RegimeState | None = Field(default=None)
```

**Step 2: Collect filter failure stats in both sync and async paths**

In both `run()` and `run_async()`, after the filter loop, add:

```python
            filter_failures: dict[str, int] = defaultdict(int)

            for snapshot in universe:
                try:
                    filter_result = run_elimination_filters(
                        period=snapshot.period,
                        profile=snapshot.profile,
                        config=self._filter_config,
                        disabled_filters=self._disabled_filters,
                    )
                    if filter_result.passed:
                        survivors.append(snapshot)
                    else:
                        eliminated_count += 1
                        for f in filter_result.failed_filters:
                            filter_failures[f.name] += 1
                        failed = [f.name for f in filter_result.failed_filters]
                        notable_events.append(f"{snapshot.ticker} eliminated — {', '.join(failed)}")
                except Exception:
                    logger.warning("Filter error for %s on %s", snapshot.ticker, rebal_date)
                    eliminated_count += 1
                    filter_failures["_error"] += 1
```

Then pass `filter_failure_breakdown=dict(filter_failures)` to the `RebalanceAuditRecord`.

Add logging:

```python
            if filter_failures:
                logger.info(
                    "[replay] %s: %d/%d eliminated — %s",
                    rebal_date, eliminated_count, len(universe),
                    ", ".join(f"{k}={v}" for k, v in sorted(filter_failures.items(), key=lambda x: -x[1])),
                )
```

**Step 3: Run engine tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest engine/tests/backtesting/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/
git commit -m "feat(engine): add filter failure breakdown to backtest audit records"
```

---

### Task 10: Re-enable Liquidity Filter & Final Backtest

**Files:**
- Modify: `api/src/margin_api/workers.py:2553`

**Step 1: Remove `disabled_filters={"liquidity"}`**

In `api/src/margin_api/workers.py`, remove the `disabled_filters` parameter from the `ReplayOrchestrator` constructor call:

```python
            orchestrator = ReplayOrchestrator(
                config=config,
                pit_provider=provider,
                factor_registry=registry,
                use_real_scoring=True,
            )
```

**Step 2: Run worker tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/workers/test_backtest_workers.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(api): re-enable liquidity filter in PIT backtest"
```

---

### Task 11: Clean Up Screenshots & Deploy

**Files:**
- Remove: `*.png` files in repo root and `web/` directory
- Remove: `runs/` directories

**Step 1: Remove accidentally committed artifacts**

```bash
cd /Users/brandon/repos/margin_invest
git rm -f faq-footer.png hero-elevation-desktop.png hero-section.png mobile-hero.png mobile-mid.png pipeline-section.png pipeline-steps.png pricing-section.png problem-section.png proof-section.png testimonials-section.png 2>/dev/null
git rm -f final-verify-after-close.png final-verify-cmdk-open.png final-verify-default.png final-verify-overlay-open.png price-target-band-date-verification.png search-01-navbar-default.png search-02-overlay-open.png verify-final-top-7px.png verify-navbar-default.png verify-search-overlay-open.png verify-top-7px.png 2>/dev/null
git rm -rf runs/ api/runs/ 2>/dev/null
```

Note: Only `git rm` files that are actually tracked. Check `git ls-files` first for each.

**Step 2: Commit cleanup**

```bash
git commit -m "chore: remove accidentally committed screenshots and run artifacts"
```

**Step 3: Push all changes**

```bash
git push origin main
```

**Step 4: Re-run universe assembly on production**

Trigger `bootstrap_pit_data` to re-run universe assembly with new SIC codes, market_cap, volume, and 8-quarter delisting threshold.

**Step 5: Trigger precompute backtest**

After universe assembly completes, trigger `precompute_default_backtest` and monitor via Railway logs. Verify:
- Filter failure breakdown appears in logs
- Universe size is reasonable (2,000-5,000 per date, not 15)
- Some tickers survive all filters (survivors > 0)
- Non-zero returns

**Step 6: Check calibration status**

```bash
curl -s "https://margininvest-production.up.railway.app/api/v1/backtest/calibration-status" | python3 -m json.tool
```

Verify `total_return`, `cagr`, `sharpe_ratio` are non-zero and more reasonable than before.
