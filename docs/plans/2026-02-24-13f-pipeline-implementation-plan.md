# 13F Institutional Holdings Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete 13F institutional holdings pipeline from SEC EDGAR ingestion through scoring integration and a Smart Money analytics page.

**Architecture:** Parallel dedicated pipeline alongside the existing daily ingest chain. New ARQ tasks (`full_13f_ingest` → `compute_accumulation_signals`) share the same worker process, database, and job tracking infrastructure. Five new database tables, a CUSIP resolution service, seven API endpoints, and two frontend surfaces (asset detail panel + /smart-money page).

**Tech Stack:** SQLAlchemy 2.0, Alembic, ARQ, OpenFIGI API, FastAPI, Pydantic, Next.js 15, Vitest, Tailwind v4

**Design Doc:** `docs/plans/2026-02-24-13f-pipeline-design.md`

---

## Dependency Graph

```
Task 1 (DB models) ──→ Task 2 (migration) ──→ Task 3 (CUSIP resolver)
                                             ├─→ Task 4 (EDGAR refactor)
                                             ├─→ Task 5 (signal compute)
                                             │
Task 3 + 4 ──→ Task 6 (13f_ingest worker)
Task 5 + 6 ──→ Task 7 (accumulation worker)
Task 7 ──→ Task 8 (backfill CLI)
Task 7 ──→ Task 9 (v4 scoring wire)
                                             │
Task 2 ──→ Task 10 (API schemas)
Task 10 ──→ Task 11 (holdings endpoints)
Task 10 ──→ Task 12 (managers endpoints)
Task 11 + 12 ──→ Task 13 (analytics endpoints)
                                             │
Task 11 ──→ Task 14 (frontend API helpers)
Task 14 ──→ Task 15 (institutional panel)
Task 14 ──→ Task 16 (conviction engine wire)
Task 14 ──→ Task 17 (smart money - fund tracker)
Task 17 ──→ Task 18 (smart money - market signals)
Task 17 ──→ Task 19 (smart money - clone lab)
Task 15 ──→ Task 20 (subscription gating)
```

## Parallel Groups

- **Group A (independent):** Tasks 1-2
- **Group B (after 2):** Tasks 3, 4, 5, 10 (all independent of each other)
- **Group C (after B):** Tasks 6, 11, 12
- **Group D (after C):** Tasks 7, 8, 13, 14
- **Group E (after D):** Tasks 9, 15, 16, 17, 20
- **Group F (after E):** Tasks 18, 19

---

### Task 1: Database Models — Five New Tables + CUSIP Column

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_13f_models.py`

**Step 1: Write the failing test**

```python
# api/tests/test_13f_models.py
"""Tests for 13F institutional holdings models."""
from datetime import UTC, datetime, date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    Asset,
    Manager,
    SecurityMaster,
    FilingMetadata,
    InstitutionalHolding,
    AccumulationSignal,
)


@pytest.mark.asyncio
async def test_create_manager(db_session: AsyncSession):
    mgr = Manager(
        cik="0001067983",
        name="BERKSHIRE HATHAWAY INC",
        short_name="Berkshire Hathaway",
        tier="curated",
        active=True,
    )
    db_session.add(mgr)
    await db_session.commit()

    result = await db_session.execute(select(Manager).where(Manager.cik == "0001067983"))
    row = result.scalar_one()
    assert row.name == "BERKSHIRE HATHAWAY INC"
    assert row.tier == "curated"
    assert row.active is True


@pytest.mark.asyncio
async def test_create_security_master(db_session: AsyncSession):
    sec = SecurityMaster(
        cusip="037833100",
        ticker="AAPL",
        issuer_name="APPLE INC",
        security_name="COM",
        resolution_method="openfigi",
    )
    db_session.add(sec)
    await db_session.commit()

    result = await db_session.execute(
        select(SecurityMaster).where(SecurityMaster.cusip == "037833100")
    )
    row = result.scalar_one()
    assert row.ticker == "AAPL"
    assert row.resolution_method == "openfigi"


@pytest.mark.asyncio
async def test_create_filing_metadata(db_session: AsyncSession):
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    db_session.add(mgr)
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        total_value=312_800_000,
        total_holdings=42,
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()
    assert filing.id is not None


@pytest.mark.asyncio
async def test_create_institutional_holding(db_session: AsyncSession):
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    sec = SecurityMaster(cusip="037833100", issuer_name="APPLE INC", resolution_method="openfigi")
    db_session.add_all([mgr, sec])
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()

    holding = InstitutionalHolding(
        filing_id=filing.id,
        manager_id=mgr.id,
        security_master_id=sec.id,
        cusip="037833100",
        period_of_report=date(2025, 12, 31),
        shares_held=915_560_382,
        value_thousands=142_300_000,
        put_call="NONE",
        investment_discretion="SOLE",
        voting_authority_sole=915_560_382,
        voting_authority_shared=0,
        voting_authority_none=0,
    )
    db_session.add(holding)
    await db_session.commit()
    assert holding.id is not None


@pytest.mark.asyncio
async def test_create_accumulation_signal(db_session: AsyncSession):
    asset = Asset(ticker="AAPL", name="Apple Inc")
    db_session.add(asset)
    await db_session.commit()

    signal = AccumulationSignal(
        asset_id=asset.id,
        period_of_report=date(2025, 12, 31),
        curated_holders=4,
        total_holders=47,
        curated_new_positions=1,
        total_new_positions=12,
        curated_net_shares=12_000_000,
        total_net_shares=34_500_000,
        signal_score=78.5,
    )
    db_session.add(signal)
    await db_session.commit()
    assert signal.id is not None


@pytest.mark.asyncio
async def test_asset_cusip_column(db_session: AsyncSession):
    asset = Asset(ticker="AAPL", name="Apple Inc", cusip="037833100")
    db_session.add(asset)
    await db_session.commit()

    result = await db_session.execute(select(Asset).where(Asset.cusip == "037833100"))
    row = result.scalar_one()
    assert row.ticker == "AAPL"


@pytest.mark.asyncio
async def test_filing_amendment_self_reference(db_session: AsyncSession):
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    db_session.add(mgr)
    await db_session.commit()

    original = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(original)
    await db_session.commit()

    amendment = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000015",
        filing_type="13F-HR/A",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 20),
        is_amendment=True,
        supersedes_id=original.id,
    )
    db_session.add(amendment)
    await db_session.commit()
    assert amendment.supersedes_id == original.id
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_13f_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Manager' from 'margin_api.db.models'`

**Step 3: Write the models**

Add to `api/src/margin_api/db/models.py` after the existing model definitions:

```python
class Manager(Base):
    """Institutional fund manager tracked for 13F filings."""

    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="top_aum")
    aum_latest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    first_filing_date: Mapped[date | None] = mapped_column(nullable=True)
    last_filing_date: Mapped[date | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSONVariant, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    filings: Mapped[list[FilingMetadata]] = relationship(back_populates="manager")


class SecurityMaster(Base):
    """CUSIP resolution cache — maps CUSIPs to tickers."""

    __tablename__ = "security_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    cusip: Mapped[str] = mapped_column(String(9), unique=True, index=True)
    ticker: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    figi: Mapped[str | None] = mapped_column(String(12), nullable=True)
    issuer_name: Mapped[str] = mapped_column(Text)
    security_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True, index=True
    )
    resolution_method: Mapped[str] = mapped_column(String(20), default="unresolved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    asset: Mapped[Asset | None] = relationship()


class FilingMetadata(Base):
    """One row per 13F filing from SEC EDGAR."""

    __tablename__ = "filing_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), index=True)
    accession_number: Mapped[str] = mapped_column(String(25), unique=True)
    filing_type: Mapped[str] = mapped_column(String(15))
    period_of_report: Mapped[date] = mapped_column(index=True)
    filed_date: Mapped[date] = mapped_column()
    total_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_holdings: Mapped[int | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_amendment: Mapped[bool] = mapped_column(default=False)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("filing_metadata.id"), nullable=True
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    manager: Mapped[Manager] = relationship(back_populates="filings")
    holdings: Mapped[list[InstitutionalHolding]] = relationship(back_populates="filing")

    __table_args__ = (
        Index("ix_filing_manager_period", "manager_id", "period_of_report"),
    )


class InstitutionalHolding(Base):
    """One row per position per 13F filing."""

    __tablename__ = "institutional_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filing_metadata.id"), index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), index=True)
    security_master_id: Mapped[int] = mapped_column(
        ForeignKey("security_master.id"), index=True
    )
    cusip: Mapped[str] = mapped_column(String(9))
    period_of_report: Mapped[date] = mapped_column()
    shares_held: Mapped[int] = mapped_column(BigInteger)
    value_thousands: Mapped[int] = mapped_column(BigInteger)
    put_call: Mapped[str] = mapped_column(String(10), default="NONE")
    investment_discretion: Mapped[str | None] = mapped_column(String(10), nullable=True)
    voting_authority_sole: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voting_authority_shared: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voting_authority_none: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    filing: Mapped[FilingMetadata] = relationship(back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("filing_id", "cusip", "put_call", name="uq_holding_filing_cusip_putcall"),
        Index("ix_holding_cusip_period", "cusip", "period_of_report"),
        Index("ix_holding_manager_period", "manager_id", "period_of_report"),
        Index("ix_holding_secmaster_period", "security_master_id", "period_of_report"),
    )


class AccumulationSignal(Base):
    """Precomputed per-asset institutional accumulation signal."""

    __tablename__ = "accumulation_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_of_report: Mapped[date] = mapped_column()
    curated_holders: Mapped[int] = mapped_column(default=0)
    total_holders: Mapped[int] = mapped_column(default=0)
    curated_new_positions: Mapped[int] = mapped_column(default=0)
    total_new_positions: Mapped[int] = mapped_column(default=0)
    curated_net_shares: Mapped[int] = mapped_column(BigInteger, default=0)
    total_net_shares: Mapped[int] = mapped_column(BigInteger, default=0)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        UniqueConstraint("asset_id", "period_of_report", name="uq_accumulation_asset_period"),
    )
```

Also add to the `Asset` model:

```python
cusip: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)
```

Also add the `date` import at the top of the file:

```python
from datetime import UTC, date, datetime
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_13f_models.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_13f_models.py
git commit -m "feat(api): add 13F database models — managers, security_master, filing_metadata, institutional_holdings, accumulation_signals"
```

---

### Task 2: Alembic Migration

**Files:**
- Create: `api/alembic/versions/<auto>_add_13f_tables.py`

**Step 1: Generate the migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add 13F institutional holdings tables"`

**Step 2: Review the generated migration**

Verify it creates all 5 tables (`managers`, `security_master`, `filing_metadata`, `institutional_holdings`, `accumulation_signals`) and adds the `cusip` column to `assets`. Edit if needed to:
- Use idempotent checks (`inspector = sa.inspect(connection)` / `inspector.has_table()`)
- Declare `jsonb_variant` inline for the `metadata` column on `managers`
- Ensure all indexes and unique constraints are present in the `upgrade()`
- Ensure `downgrade()` drops tables in reverse dependency order

**Step 3: Test the migration**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies cleanly. Run: `uv run alembic downgrade -1` then `uv run alembic upgrade head` to verify reversibility.

**Step 4: Verify no multiple heads**

Run: `cd api && uv run alembic heads`
Expected: Single head

**Step 5: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat(api): add alembic migration for 13F tables"
```

---

### Task 3: CUSIP Resolution Service

**Files:**
- Create: `engine/src/margin_engine/services/cusip_resolver.py`
- Test: `engine/tests/test_cusip_resolver.py`

**Step 1: Write the failing test**

```python
# engine/tests/test_cusip_resolver.py
"""Tests for CUSIP resolution via OpenFIGI + name matching."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from margin_engine.services.cusip_resolver import CUSIPResolver, ResolvedSecurity


class TestCUSIPResolver:
    def setup_method(self):
        self.resolver = CUSIPResolver()

    def test_cache_hit(self):
        """Already-resolved CUSIPs return from cache."""
        self.resolver._cache["037833100"] = ResolvedSecurity(
            cusip="037833100", ticker="AAPL", figi="BBG000B9XRY4",
            issuer_name="APPLE INC", resolution_method="openfigi",
        )
        result = self.resolver.resolve_from_cache("037833100")
        assert result is not None
        assert result.ticker == "AAPL"

    def test_cache_miss(self):
        """Unknown CUSIPs return None from cache."""
        result = self.resolver.resolve_from_cache("999999999")
        assert result is None

    def test_parse_openfigi_response(self):
        """OpenFIGI API response is parsed correctly."""
        response_data = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]}
        ]
        results = self.resolver._parse_openfigi_response(
            response_data,
            [{"cusip": "037833100", "issuer_name": "APPLE INC"}],
        )
        assert len(results) == 1
        assert results[0].ticker == "AAPL"
        assert results[0].resolution_method == "openfigi"

    def test_parse_openfigi_unresolved(self):
        """Unresolvable CUSIPs come back with empty data."""
        response_data = [{"warning": "No identifier found."}]
        results = self.resolver._parse_openfigi_response(
            response_data,
            [{"cusip": "999999999", "issuer_name": "UNKNOWN CORP"}],
        )
        assert len(results) == 1
        assert results[0].ticker is None
        assert results[0].resolution_method == "unresolved"

    def test_fuzzy_name_match(self):
        """Fuzzy name matching finds close matches."""
        known_assets = {"APPLE INC": "AAPL", "MICROSOFT CORP": "MSFT"}
        result = self.resolver._fuzzy_name_match("APPLE INC", known_assets)
        assert result == "AAPL"

    def test_fuzzy_name_match_partial(self):
        """Partial name matches work (substring both ways)."""
        known_assets = {"APPLE INC": "AAPL"}
        result = self.resolver._fuzzy_name_match("APPLE", known_assets)
        assert result == "AAPL"

    def test_fuzzy_name_match_no_match(self):
        known_assets = {"APPLE INC": "AAPL"}
        result = self.resolver._fuzzy_name_match("BERKSHIRE HATHAWAY", known_assets)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_batch_calls_openfigi(self):
        """Batch resolution calls OpenFIGI for uncached CUSIPs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]}
        ]
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            results = await self.resolver.resolve_batch(
                [{"cusip": "037833100", "issuer_name": "APPLE INC"}]
            )
        assert len(results) == 1
        assert results[0].ticker == "AAPL"
        # Should be cached now
        assert "037833100" in self.resolver._cache
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_cusip_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.services.cusip_resolver'`

**Step 3: Write the implementation**

```python
# engine/src/margin_engine/services/cusip_resolver.py
"""CUSIP resolution via OpenFIGI API + fuzzy name matching."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
OPENFIGI_BATCH_SIZE = 100


@dataclass
class ResolvedSecurity:
    cusip: str
    ticker: str | None
    figi: str | None
    issuer_name: str
    resolution_method: str  # 'openfigi', 'name_match', 'manual', 'unresolved'


class CUSIPResolver:
    """Resolves CUSIPs to tickers via OpenFIGI with local cache."""

    def __init__(self, openfigi_api_key: str | None = None) -> None:
        self._cache: dict[str, ResolvedSecurity] = {}
        self._api_key = openfigi_api_key

    def resolve_from_cache(self, cusip: str) -> ResolvedSecurity | None:
        return self._cache.get(cusip)

    def seed_cache(self, entries: list[ResolvedSecurity]) -> None:
        for entry in entries:
            self._cache[entry.cusip] = entry

    async def resolve_batch(
        self,
        holdings: list[dict],
        known_assets: dict[str, str] | None = None,
    ) -> list[ResolvedSecurity]:
        """Resolve a batch of holdings. Each holding needs 'cusip' and 'issuer_name'.

        Args:
            holdings: List of dicts with 'cusip' and 'issuer_name' keys.
            known_assets: Optional mapping of issuer_name -> ticker for fuzzy matching.

        Returns:
            List of ResolvedSecurity for every input holding.
        """
        results: list[ResolvedSecurity] = []
        uncached: list[dict] = []
        uncached_indices: list[int] = []

        # Step 1: Check cache
        for i, h in enumerate(holdings):
            cached = self._cache.get(h["cusip"])
            if cached:
                results.append(cached)
            else:
                results.append(None)  # type: ignore[arg-type]
                uncached.append(h)
                uncached_indices.append(i)

        if not uncached:
            return results

        # Step 2: Call OpenFIGI in batches
        openfigi_results = await self._call_openfigi(uncached)

        # Step 3: Fuzzy name match for unresolved
        for j, resolved in enumerate(openfigi_results):
            if resolved.ticker is None and known_assets:
                matched = self._fuzzy_name_match(resolved.issuer_name, known_assets)
                if matched:
                    resolved.ticker = matched
                    resolved.resolution_method = "name_match"
            # Cache and place into results
            self._cache[resolved.cusip] = resolved
            results[uncached_indices[j]] = resolved

        return results

    async def _call_openfigi(self, holdings: list[dict]) -> list[ResolvedSecurity]:
        """Call OpenFIGI batch endpoint."""
        all_results: list[ResolvedSecurity] = []
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-OPENFIGI-APIKEY"] = self._api_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            for batch_start in range(0, len(holdings), OPENFIGI_BATCH_SIZE):
                batch = holdings[batch_start : batch_start + OPENFIGI_BATCH_SIZE]
                payload = [
                    {"idType": "ID_CUSIP", "idValue": h["cusip"]} for h in batch
                ]
                try:
                    resp = await client.post(OPENFIGI_URL, json=payload, headers=headers)
                    resp.raise_for_status()
                    parsed = self._parse_openfigi_response(resp.json(), batch)
                    all_results.extend(parsed)
                except httpx.HTTPError as e:
                    logger.warning("OpenFIGI batch failed: %s", e)
                    # Fall back to unresolved for this batch
                    for h in batch:
                        all_results.append(
                            ResolvedSecurity(
                                cusip=h["cusip"],
                                ticker=None,
                                figi=None,
                                issuer_name=h["issuer_name"],
                                resolution_method="unresolved",
                            )
                        )
        return all_results

    def _parse_openfigi_response(
        self, response_data: list[dict], batch: list[dict]
    ) -> list[ResolvedSecurity]:
        results: list[ResolvedSecurity] = []
        for i, item in enumerate(response_data):
            h = batch[i]
            if "data" in item and item["data"]:
                entry = item["data"][0]
                results.append(
                    ResolvedSecurity(
                        cusip=h["cusip"],
                        ticker=entry.get("ticker"),
                        figi=entry.get("figi"),
                        issuer_name=h["issuer_name"],
                        resolution_method="openfigi",
                    )
                )
            else:
                results.append(
                    ResolvedSecurity(
                        cusip=h["cusip"],
                        ticker=None,
                        figi=None,
                        issuer_name=h["issuer_name"],
                        resolution_method="unresolved",
                    )
                )
        return results

    def _fuzzy_name_match(
        self, issuer_name: str, known_assets: dict[str, str]
    ) -> str | None:
        """Case-insensitive substring match, both directions."""
        issuer_upper = issuer_name.upper().strip()
        for name, ticker in known_assets.items():
            name_upper = name.upper().strip()
            if issuer_upper in name_upper or name_upper in issuer_upper:
                return ticker
        return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_cusip_resolver.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/services/cusip_resolver.py engine/tests/test_cusip_resolver.py
git commit -m "feat(engine): add CUSIP resolution service with OpenFIGI + fuzzy name matching"
```

---

### Task 4: Refactor EDGAR Provider for Fund-Centric 13F Ingestion

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/edgar_provider.py`
- Test: `engine/tests/test_edgar_13f.py`

**Step 1: Write the failing test**

```python
# engine/tests/test_edgar_13f.py
"""Tests for fund-centric 13F ingestion via EDGAR."""
import pytest
from unittest.mock import patch, MagicMock

from margin_engine.ingestion.providers.edgar_provider import EDGARProvider


SAMPLE_INFOTABLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>142300000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>915560382</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <putCall/>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>915560382</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>MICROSOFT CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>594918104</cusip>
    <value>89400000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>200000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <putCall/>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>200000000</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
</informationTable>"""

SAMPLE_SUBMISSIONS_JSON = {
    "cik": "0001067983",
    "name": "BERKSHIRE HATHAWAY INC",
    "filings": {
        "recent": {
            "accessionNumber": ["0001067983-26-000012", "0001067983-25-000050"],
            "form": ["13F-HR", "13F-HR"],
            "filingDate": ["2026-02-14", "2025-11-14"],
            "reportDate": ["2025-12-31", "2025-09-30"],
            "primaryDocument": ["doc.xml", "doc.xml"],
        }
    },
}


class TestParseFullInfotable:
    def test_parse_all_holdings(self):
        """Parse ALL holdings from infotable, not just target company."""
        provider = EDGARProvider(user_agent="test agent")
        holdings = provider.parse_full_infotable(
            SAMPLE_INFOTABLE_XML,
            fund_name="Berkshire Hathaway",
            fund_cik="0001067983",
            filing_date="2026-02-14",
            report_date="2025-12-31",
        )
        assert len(holdings) == 2
        assert holdings[0]["cusip"] == "037833100"
        assert holdings[0]["issuer_name"] == "APPLE INC"
        assert holdings[0]["shares"] == 915560382
        assert holdings[0]["value_thousands"] == 142300000
        assert holdings[0]["investment_discretion"] == "SOLE"
        assert holdings[0]["voting_sole"] == 915560382
        assert holdings[1]["cusip"] == "594918104"
        assert holdings[1]["issuer_name"] == "MICROSOFT CORP"

    def test_parse_put_call(self):
        """Empty putCall tag results in 'NONE'."""
        provider = EDGARProvider(user_agent="test agent")
        holdings = provider.parse_full_infotable(
            SAMPLE_INFOTABLE_XML,
            fund_name="Test",
            fund_cik="0000000001",
            filing_date="2026-01-01",
            report_date="2025-12-31",
        )
        assert holdings[0]["put_call"] == "NONE"


class TestFetchFundFilingIndex:
    def test_extract_filing_list(self):
        """Extract 13F filing list from submissions JSON."""
        provider = EDGARProvider(user_agent="test agent")
        filings = provider.extract_13f_filings(SAMPLE_SUBMISSIONS_JSON)
        assert len(filings) == 2
        assert filings[0]["accession_number"] == "0001067983-26-000012"
        assert filings[0]["filing_type"] == "13F-HR"
        assert filings[0]["period_of_report"] == "2025-12-31"
        assert filings[0]["filed_date"] == "2026-02-14"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_edgar_13f.py -v`
Expected: FAIL — `AttributeError: 'EDGARProvider' object has no attribute 'parse_full_infotable'`

**Step 3: Add fund-centric methods to EDGARProvider**

Add two new public methods to the existing `EDGARProvider` class:

```python
def parse_full_infotable(
    self,
    xml_text: str,
    fund_name: str,
    fund_cik: str,
    filing_date: str,
    report_date: str,
) -> list[dict]:
    """Parse ALL holdings from a 13F infotable XML (not filtered by target company)."""
    cleaned = re.sub(r'\s+xmlns="[^"]+"', "", xml_text, count=1)
    root = ET.fromstring(cleaned)
    holdings = []
    for entry in root.findall(".//infoTable"):
        put_call_text = (entry.findtext("putCall") or "").strip().upper()
        holdings.append({
            "fund_name": fund_name,
            "fund_cik": fund_cik,
            "issuer_name": (entry.findtext("nameOfIssuer") or "").strip(),
            "title_of_class": (entry.findtext("titleOfClass") or "").strip(),
            "cusip": (entry.findtext("cusip") or "").strip(),
            "value_thousands": int(entry.findtext("value") or 0),
            "shares": int(entry.findtext(".//sshPrnamt") or 0),
            "share_type": (entry.findtext(".//sshPrnamtType") or "SH").strip(),
            "put_call": put_call_text if put_call_text in ("PUT", "CALL") else "NONE",
            "investment_discretion": (entry.findtext("investmentDiscretion") or "").strip(),
            "voting_sole": int(entry.findtext(".//votingAuthority/Sole") or 0),
            "voting_shared": int(entry.findtext(".//votingAuthority/Shared") or 0),
            "voting_none": int(entry.findtext(".//votingAuthority/None") or 0),
            "filing_date": filing_date,
            "report_date": report_date,
        })
    return holdings

def extract_13f_filings(self, submissions: dict) -> list[dict]:
    """Extract 13F filing entries from an EDGAR submissions JSON response."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])

    filings = []
    for i, form in enumerate(forms):
        if form in ("13F-HR", "13F-HR/A"):
            filings.append({
                "accession_number": accessions[i],
                "filing_type": form,
                "filed_date": filing_dates[i],
                "period_of_report": report_dates[i],
                "is_amendment": form == "13F-HR/A",
            })
    return filings
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_edgar_13f.py -v`
Expected: All 3 tests PASS

**Step 5: Run existing EDGAR tests to confirm no regression**

Run: `uv run pytest engine/tests/ -k edgar -v`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/edgar_provider.py engine/tests/test_edgar_13f.py
git commit -m "feat(engine): add fund-centric 13F parsing methods to EDGARProvider"
```

---

### Task 5: Accumulation Signal Computation

**Files:**
- Create: `engine/src/margin_engine/services/accumulation.py`
- Test: `engine/tests/test_accumulation.py`

**Step 1: Write the failing test**

```python
# engine/tests/test_accumulation.py
"""Tests for institutional accumulation signal computation."""
from datetime import date

from margin_engine.services.accumulation import (
    compute_quarter_signals,
    HoldingSummary,
    QuarterSignal,
)


def _make_summary(
    cusip: str = "037833100",
    ticker: str = "AAPL",
    asset_id: int = 1,
    period: date = date(2025, 12, 31),
    manager_id: int = 1,
    tier: str = "curated",
    shares: int = 1000,
    prev_shares: int | None = None,
) -> HoldingSummary:
    return HoldingSummary(
        cusip=cusip,
        ticker=ticker,
        asset_id=asset_id,
        period_of_report=period,
        manager_id=manager_id,
        tier=tier,
        shares_held=shares,
        prev_shares=prev_shares,
    )


class TestComputeQuarterSignals:
    def test_single_curated_new_position(self):
        """A curated fund with no previous shares = new position."""
        summaries = [_make_summary(prev_shares=None)]
        signals = compute_quarter_signals(summaries)
        assert len(signals) == 1
        s = signals[0]
        assert s.asset_id == 1
        assert s.curated_holders == 1
        assert s.total_holders == 1
        assert s.curated_new_positions == 1
        assert s.total_new_positions == 1
        assert s.curated_net_shares == 1000
        assert s.total_net_shares == 1000

    def test_existing_position_increased(self):
        """An increase in shares is accumulation, not a new position."""
        summaries = [_make_summary(shares=1500, prev_shares=1000)]
        signals = compute_quarter_signals(summaries)
        s = signals[0]
        assert s.curated_new_positions == 0
        assert s.curated_net_shares == 500

    def test_mixed_tiers(self):
        """Curated and top_aum funds tracked separately."""
        summaries = [
            _make_summary(manager_id=1, tier="curated", shares=1000, prev_shares=None),
            _make_summary(manager_id=2, tier="top_aum", shares=2000, prev_shares=1000),
            _make_summary(manager_id=3, tier="top_aum", shares=500, prev_shares=None),
        ]
        signals = compute_quarter_signals(summaries)
        s = signals[0]
        assert s.curated_holders == 1
        assert s.total_holders == 3
        assert s.curated_new_positions == 1
        assert s.total_new_positions == 2
        assert s.curated_net_shares == 1000
        assert s.total_net_shares == 2500

    def test_multiple_assets(self):
        """Signals are computed per-asset."""
        summaries = [
            _make_summary(asset_id=1, ticker="AAPL", cusip="037833100"),
            _make_summary(asset_id=2, ticker="MSFT", cusip="594918104"),
        ]
        signals = compute_quarter_signals(summaries)
        assert len(signals) == 2
        tickers = {s.asset_id for s in signals}
        assert tickers == {1, 2}

    def test_position_decreased(self):
        """Decreases produce negative net shares."""
        summaries = [_make_summary(shares=500, prev_shares=1000)]
        signals = compute_quarter_signals(summaries)
        s = signals[0]
        assert s.curated_net_shares == -500

    def test_empty_input(self):
        signals = compute_quarter_signals([])
        assert signals == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_accumulation.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
# engine/src/margin_engine/services/accumulation.py
"""Compute institutional accumulation signals from 13F holdings."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass
class HoldingSummary:
    """Input: one manager's holding of one asset for one quarter."""
    cusip: str
    ticker: str | None
    asset_id: int
    period_of_report: date
    manager_id: int
    tier: str  # 'curated' or 'top_aum'
    shares_held: int
    prev_shares: int | None  # None = new position


@dataclass
class QuarterSignal:
    """Output: aggregated signal for one asset for one quarter."""
    asset_id: int
    period_of_report: date
    curated_holders: int
    total_holders: int
    curated_new_positions: int
    total_new_positions: int
    curated_net_shares: int
    total_net_shares: int
    signal_score: float = 0.0  # populated later by percentile ranking


def compute_quarter_signals(summaries: list[HoldingSummary]) -> list[QuarterSignal]:
    """Aggregate holdings into per-asset accumulation signals."""
    if not summaries:
        return []

    # Group by asset_id
    by_asset: dict[int, list[HoldingSummary]] = defaultdict(list)
    for s in summaries:
        by_asset[s.asset_id].append(s)

    signals: list[QuarterSignal] = []
    for asset_id, holdings in by_asset.items():
        curated_holders = 0
        total_holders = 0
        curated_new = 0
        total_new = 0
        curated_net = 0
        total_net = 0

        for h in holdings:
            total_holders += 1
            is_new = h.prev_shares is None
            net = h.shares_held if is_new else h.shares_held - h.prev_shares

            if is_new:
                total_new += 1
            total_net += net

            if h.tier == "curated":
                curated_holders += 1
                curated_net += net
                if is_new:
                    curated_new += 1

        signals.append(
            QuarterSignal(
                asset_id=asset_id,
                period_of_report=holdings[0].period_of_report,
                curated_holders=curated_holders,
                total_holders=total_holders,
                curated_new_positions=curated_new,
                total_new_positions=total_new,
                curated_net_shares=curated_net,
                total_net_shares=total_net,
            )
        )
    return signals
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_accumulation.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/services/accumulation.py engine/tests/test_accumulation.py
git commit -m "feat(engine): add accumulation signal computation for 13F holdings"
```

---

### Task 6: `full_13f_ingest` ARQ Worker Task

**Files:**
- Create: `api/src/margin_api/services/thirteenf_ingest.py`
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_13f_ingest.py`

**Step 1: Write the failing test**

```python
# api/tests/test_13f_ingest.py
"""Tests for 13F ingestion service."""
from datetime import date, datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Manager, FilingMetadata, InstitutionalHolding, SecurityMaster
from margin_api.services.thirteenf_ingest import ThirteenFIngestService


@pytest.mark.asyncio
async def test_upsert_managers(db_session: AsyncSession):
    """Seed managers from a list of fund dicts."""
    service = ThirteenFIngestService(db_session)
    funds = [
        {"cik": "0001067983", "name": "BERKSHIRE HATHAWAY INC", "short_name": "Berkshire Hathaway", "tier": "curated"},
        {"cik": "0001061768", "name": "BAUPOST GROUP LLC", "short_name": "Baupost Group", "tier": "curated"},
    ]
    await service.upsert_managers(funds)
    result = await db_session.execute(select(Manager))
    managers = result.scalars().all()
    assert len(managers) == 2
    assert managers[0].cik == "0001067983"


@pytest.mark.asyncio
async def test_upsert_managers_idempotent(db_session: AsyncSession):
    """Upserting same managers twice doesn't create duplicates."""
    service = ThirteenFIngestService(db_session)
    funds = [{"cik": "0001067983", "name": "BERKSHIRE", "short_name": "Berkshire", "tier": "curated"}]
    await service.upsert_managers(funds)
    await service.upsert_managers(funds)
    result = await db_session.execute(select(Manager))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_skip_already_ingested_filing(db_session: AsyncSession):
    """Filings with known accession numbers are skipped."""
    service = ThirteenFIngestService(db_session)
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    db_session.add(mgr)
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()

    is_new = await service.is_filing_new("0001067983-26-000012")
    assert is_new is False


@pytest.mark.asyncio
async def test_new_filing_detected(db_session: AsyncSession):
    service = ThirteenFIngestService(db_session)
    is_new = await service.is_filing_new("0001067983-26-999999")
    assert is_new is True


@pytest.mark.asyncio
async def test_store_holdings(db_session: AsyncSession):
    """Parsed holdings are stored correctly."""
    service = ThirteenFIngestService(db_session)
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    sec = SecurityMaster(cusip="037833100", issuer_name="APPLE INC", resolution_method="openfigi")
    db_session.add_all([mgr, sec])
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()

    parsed_holdings = [
        {
            "cusip": "037833100",
            "issuer_name": "APPLE INC",
            "shares": 915560382,
            "value_thousands": 142300000,
            "put_call": "NONE",
            "investment_discretion": "SOLE",
            "voting_sole": 915560382,
            "voting_shared": 0,
            "voting_none": 0,
        }
    ]
    count = await service.store_holdings(filing, mgr, parsed_holdings)
    assert count == 1

    result = await db_session.execute(select(InstitutionalHolding))
    holding = result.scalar_one()
    assert holding.shares_held == 915560382
    assert holding.cusip == "037833100"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_13f_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the service**

```python
# api/src/margin_api/services/thirteenf_ingest.py
"""13F filing ingestion service — fetches, parses, stores institutional holdings."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)

logger = logging.getLogger(__name__)


class ThirteenFIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_managers(self, funds: list[dict]) -> list[Manager]:
        """Insert or update manager records."""
        managers: list[Manager] = []
        for f in funds:
            result = await self._session.execute(
                select(Manager).where(Manager.cik == f["cik"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = f["name"]
                existing.short_name = f.get("short_name")
                existing.tier = f.get("tier", "top_aum")
                managers.append(existing)
            else:
                mgr = Manager(
                    cik=f["cik"],
                    name=f["name"],
                    short_name=f.get("short_name"),
                    tier=f.get("tier", "top_aum"),
                )
                self._session.add(mgr)
                managers.append(mgr)
        await self._session.commit()
        return managers

    async def is_filing_new(self, accession_number: str) -> bool:
        result = await self._session.execute(
            select(FilingMetadata.id).where(
                FilingMetadata.accession_number == accession_number
            )
        )
        return result.scalar_one_or_none() is None

    async def get_or_create_security(self, cusip: str, issuer_name: str) -> SecurityMaster:
        result = await self._session.execute(
            select(SecurityMaster).where(SecurityMaster.cusip == cusip)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        sec = SecurityMaster(
            cusip=cusip,
            issuer_name=issuer_name,
            resolution_method="unresolved",
        )
        self._session.add(sec)
        await self._session.flush()
        return sec

    async def store_holdings(
        self,
        filing: FilingMetadata,
        manager: Manager,
        parsed_holdings: list[dict],
    ) -> int:
        """Store parsed holdings for a filing. Returns count inserted."""
        count = 0
        for h in parsed_holdings:
            sec = await self.get_or_create_security(h["cusip"], h["issuer_name"])
            holding = InstitutionalHolding(
                filing_id=filing.id,
                manager_id=manager.id,
                security_master_id=sec.id,
                cusip=h["cusip"],
                period_of_report=filing.period_of_report,
                shares_held=h["shares"],
                value_thousands=h["value_thousands"],
                put_call=h.get("put_call", "NONE"),
                investment_discretion=h.get("investment_discretion"),
                voting_authority_sole=h.get("voting_sole"),
                voting_authority_shared=h.get("voting_shared"),
                voting_authority_none=h.get("voting_none"),
            )
            self._session.add(holding)
            count += 1
        await self._session.commit()
        return count

    async def handle_amendment(
        self, manager: Manager, period_of_report: date, new_accession: str
    ) -> int | None:
        """Find original filing for amendment. Returns original filing id or None."""
        result = await self._session.execute(
            select(FilingMetadata)
            .where(
                FilingMetadata.manager_id == manager.id,
                FilingMetadata.period_of_report == period_of_report,
                FilingMetadata.is_amendment == False,  # noqa: E712
            )
            .order_by(FilingMetadata.filed_date.desc())
            .limit(1)
        )
        original = result.scalar_one_or_none()
        return original.id if original else None
```

**Step 4: Wire into workers.py**

Add to `api/src/margin_api/workers.py`:

1. Import the new models: add `Manager, FilingMetadata, InstitutionalHolding, SecurityMaster` to the model imports
2. Add the `full_13f_ingest` function following the existing pattern (create `JobRun`, try/except, chain to next)
3. Register in `WorkerSettings.functions` and add cron: `cron(full_13f_ingest, hour=22, minute=0)`

The worker function body should:
- Create a `JobRun` with `job_type="13f_ingest"`
- Instantiate `ThirteenFIngestService` with a DB session
- Call `upsert_managers()` with the curated fund list
- For each manager, fetch submissions from EDGAR, extract 13F filings, skip already-ingested
- For new filings, fetch infotable XML, parse with `EDGARProvider.parse_full_infotable()`, store holdings
- Chain to `compute_accumulation_signals`

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_13f_ingest.py -v`
Expected: All 5 tests PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/services/thirteenf_ingest.py api/tests/test_13f_ingest.py api/src/margin_api/workers.py
git commit -m "feat(api): add 13F ingestion service and ARQ worker task"
```

---

### Task 7: `compute_accumulation_signals` ARQ Worker Task

**Files:**
- Create: `api/src/margin_api/services/accumulation_service.py`
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_accumulation_service.py`

**Step 1: Write the failing test**

```python
# api/tests/test_accumulation_service.py
"""Tests for accumulation signal computation service (DB layer)."""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    AccumulationSignal, Asset, InstitutionalHolding,
    FilingMetadata, Manager, SecurityMaster,
)
from margin_api.services.accumulation_service import AccumulationService


@pytest.fixture
async def seeded_data(db_session: AsyncSession):
    """Seed two quarters of holdings for one asset by one curated fund."""
    asset = Asset(ticker="AAPL", name="Apple Inc", cusip="037833100")
    mgr = Manager(cik="0001067983", name="BERKSHIRE", short_name="Berkshire", tier="curated")
    sec = SecurityMaster(cusip="037833100", issuer_name="APPLE INC", resolution_method="openfigi",
                         ticker="AAPL")
    db_session.add_all([asset, mgr, sec])
    await db_session.commit()

    # Q3 filing
    f1 = FilingMetadata(
        manager_id=mgr.id, accession_number="acc-q3",
        filing_type="13F-HR", period_of_report=date(2025, 9, 30),
        filed_date=date(2025, 11, 14), is_amendment=False,
    )
    db_session.add(f1)
    await db_session.commit()
    db_session.add(InstitutionalHolding(
        filing_id=f1.id, manager_id=mgr.id, security_master_id=sec.id,
        cusip="037833100", period_of_report=date(2025, 9, 30),
        shares_held=900_000_000, value_thousands=130_000_000, put_call="NONE",
    ))
    # Q4 filing
    f2 = FilingMetadata(
        manager_id=mgr.id, accession_number="acc-q4",
        filing_type="13F-HR", period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14), is_amendment=False,
    )
    db_session.add(f2)
    await db_session.commit()
    db_session.add(InstitutionalHolding(
        filing_id=f2.id, manager_id=mgr.id, security_master_id=sec.id,
        cusip="037833100", period_of_report=date(2025, 12, 31),
        shares_held=915_000_000, value_thousands=142_000_000, put_call="NONE",
    ))
    await db_session.commit()
    return {"asset": asset, "sec": sec, "mgr": mgr}


@pytest.mark.asyncio
async def test_compute_signals_for_quarter(db_session: AsyncSession, seeded_data):
    service = AccumulationService(db_session)
    count = await service.compute_signals(period_of_report=date(2025, 12, 31))
    assert count == 1

    result = await db_session.execute(
        select(AccumulationSignal).where(
            AccumulationSignal.period_of_report == date(2025, 12, 31)
        )
    )
    signal = result.scalar_one()
    assert signal.curated_holders == 1
    assert signal.total_holders == 1
    assert signal.curated_new_positions == 0  # existed in Q3
    assert signal.curated_net_shares == 15_000_000  # 915M - 900M


@pytest.mark.asyncio
async def test_compute_signals_idempotent(db_session: AsyncSession, seeded_data):
    """Running twice updates rather than duplicates."""
    service = AccumulationService(db_session)
    await service.compute_signals(period_of_report=date(2025, 12, 31))
    await service.compute_signals(period_of_report=date(2025, 12, 31))
    result = await db_session.execute(
        select(AccumulationSignal).where(
            AccumulationSignal.period_of_report == date(2025, 12, 31)
        )
    )
    assert len(result.scalars().all()) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_accumulation_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the service**

The `AccumulationService` queries `institutional_holdings` joined to `security_master` (for `asset_id`) and `managers` (for `tier`), computes quarter-over-quarter deltas, and upserts `AccumulationSignal` rows. Use the engine's `compute_quarter_signals()` for the pure computation, wrapping it with DB reads and writes.

**Step 4: Add `compute_accumulation_signals` to workers.py**

Follow the same pattern as existing workers: create `JobRun`, call the service, update status. Find all distinct `period_of_report` values that have holdings but no (or outdated) signals.

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_accumulation_service.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/services/accumulation_service.py api/tests/test_accumulation_service.py api/src/margin_api/workers.py
git commit -m "feat(api): add accumulation signal computation service and worker task"
```

---

### Task 8: Backfill CLI Command

**Files:**
- Modify: `api/src/margin_api/cli.py`
- Test: `api/tests/test_cli_backfill.py`

**Step 1: Write a test** that verifies the CLI command registers and validates arguments.

**Step 2: Run to verify failure.**

**Step 3: Add a `backfill-13f` CLI command** to the existing Click/Typer CLI in `cli.py`. It should:
- Accept `--start-year` (default 2013) and `--max-managers` (default 300)
- Instantiate `ThirteenFIngestService` with a DB session
- Seed managers (curated list + top AUM discovery from EDGAR)
- For each manager, iterate all quarters from start_year to present
- For each quarter, check if filing exists, fetch if not, parse, store
- After all holdings ingested, run `AccumulationService.compute_signals()` for all quarters
- Log progress: `"[142/300] Berkshire Hathaway: 40 quarters ingested"`

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py api/tests/test_cli_backfill.py
git commit -m "feat(api): add backfill-13f CLI command for historical 13F ingestion"
```

---

### Task 9: Wire `institutional_accumulation` into V4 Scoring

**Files:**
- Modify: scoring service (find exact path in `api/src/margin_api/` or `engine/` where v4 scoring reads factor values)
- Test: add test case verifying real signal is read instead of hardcoded 50.0

**Step 1: Write a test** that seeds an `AccumulationSignal` row and verifies v4 scoring reads `signal_score` instead of returning 50.0.

**Step 2: Run to verify failure** (currently hardcoded at 50.0).

**Step 3: Modify the v4 scoring code** to:
- Query `AccumulationSignal` for the asset's latest `period_of_report`
- Use `signal_score` as `institutional_percentile`
- If no signal exists, set to `None` (excluded from composite, not faked)

**Step 4: Run tests** — both the new test and all existing scoring tests.

**Step 5: Commit**

```bash
git commit -m "feat(engine): wire institutional_accumulation to real 13F signals in v4 scoring"
```

---

### Task 10: API Schemas (Pydantic Response Models)

**Files:**
- Create: `api/src/margin_api/schemas/thirteenf.py`
- Test: `api/tests/test_13f_schemas.py`

**Step 1: Write the failing test**

```python
# api/tests/test_13f_schemas.py
"""Tests for 13F API response schemas."""
from datetime import date
from margin_api.schemas.thirteenf import (
    HolderResponse,
    HoldingsResponse,
    HoldingsSummary,
    ManagerResponse,
    ManagerPortfolioResponse,
    PortfolioHolding,
    OverlapResponse,
    NewPositionResponse,
)


def test_holdings_response_serialization():
    resp = HoldingsResponse(
        ticker="AAPL",
        period_of_report=date(2025, 12, 31),
        curated_holders=[
            HolderResponse(
                manager_name="Berkshire Hathaway",
                tier="curated",
                shares_held=915_560_382,
                value_millions=142.3,
                shares_changed=12_000_000,
                pct_portfolio=4.8,
                is_new_position=False,
                quarters_held=18,
            )
        ],
        other_holders=[],
        summary=HoldingsSummary(
            total_holders=47,
            curated_holders=4,
            net_shares_changed=34_500_000,
            signal_score=78.5,
        ),
    )
    data = resp.model_dump()
    assert data["ticker"] == "AAPL"
    assert data["curated_holders"][0]["manager_name"] == "Berkshire Hathaway"
    assert data["summary"]["signal_score"] == 78.5


def test_manager_response():
    resp = ManagerResponse(
        id=1,
        name="Berkshire Hathaway",
        tier="curated",
        aum_millions=312_800.0,
        total_holdings=42,
        top_positions=["AAPL", "BAC", "KO"],
        last_filing=date(2026, 2, 14),
        period_of_report=date(2025, 12, 31),
    )
    assert resp.model_dump()["tier"] == "curated"
```

**Step 2: Run to verify failure.**

**Step 3: Write schemas** following the existing pattern in `schemas/backtest.py`:

```python
# api/src/margin_api/schemas/thirteenf.py
from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field


class HolderResponse(BaseModel):
    manager_name: str
    tier: str
    shares_held: int
    value_millions: float
    shares_changed: int
    pct_portfolio: float | None = None
    is_new_position: bool = False
    quarters_held: int | None = None


class HoldingsSummary(BaseModel):
    total_holders: int
    curated_holders: int
    net_shares_changed: int
    signal_score: float


class HoldingsResponse(BaseModel):
    ticker: str
    period_of_report: date
    curated_holders: list[HolderResponse]
    other_holders: list[HolderResponse]
    summary: HoldingsSummary


class HoldingsHistoryQuarter(BaseModel):
    period: str
    curated_holders: int
    total_holders: int
    total_shares: int
    net_change: int


class HoldingsHistoryResponse(BaseModel):
    ticker: str
    quarters: list[HoldingsHistoryQuarter]


class ManagerResponse(BaseModel):
    id: int
    name: str
    tier: str
    aum_millions: float | None = None
    total_holdings: int
    top_positions: list[str]
    last_filing: date | None = None
    period_of_report: date | None = None


class PortfolioHolding(BaseModel):
    ticker: str | None = None
    cusip: str
    shares_held: int
    value_millions: float
    pct_portfolio: float
    shares_changed: int
    is_new_position: bool = False


class ChangesSummary(BaseModel):
    new_positions: list[str]
    exited_positions: list[str]
    increased: int
    decreased: int
    unchanged: int


class ManagerPortfolioResponse(BaseModel):
    manager: str
    period_of_report: date
    aum_millions: float | None = None
    holdings: list[PortfolioHolding]
    changes_summary: ChangesSummary


class OverlapEntry(BaseModel):
    ticker: str
    holder_count: int
    curated_count: int


class CrowdedTrade(BaseModel):
    ticker: str
    new_position_count: int
    pct_funds_adding: float


class OverlapResponse(BaseModel):
    period_of_report: date
    most_held: list[OverlapEntry]
    crowded_trades: list[CrowdedTrade]


class NewPositionEntry(BaseModel):
    ticker: str
    managers: list[str]
    total_new_funds: int
    curated_new_funds: int
    total_value_millions: float


class NewPositionResponse(BaseModel):
    period_of_report: date
    new_positions: list[NewPositionEntry]


class ClonePerformance(BaseModel):
    return_1y: float | None = None
    cagr_3y: float | None = None
    max_drawdown: float | None = None
    sharpe: float | None = None


class ClonePosition(BaseModel):
    ticker: str
    target_weight: float


class CloneResponse(BaseModel):
    manager: str
    strategy: str
    period_of_report: date
    positions: list[ClonePosition]
    historical_performance: ClonePerformance | None = None
```

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/thirteenf.py api/tests/test_13f_schemas.py
git commit -m "feat(api): add 13F Pydantic response schemas"
```

---

### Task 11: Asset Detail 13F Endpoints

**Files:**
- Create: `api/src/margin_api/routes/thirteenf.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/test_13f_routes.py`

**Step 1: Write failing tests** for `GET /api/v1/13f/holdings/{ticker}` and `GET /api/v1/13f/holdings/{ticker}/history`. Seed DB with managers, filings, holdings, and security_master entries. Verify response structure matches schemas.

**Step 2: Run to verify failure.**

**Step 3: Implement routes** following the backtest route pattern:

```python
# api/src/margin_api/routes/thirteenf.py
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.session import get_db
from margin_api.schemas.thirteenf import HoldingsResponse, HoldingsHistoryResponse

router = APIRouter(prefix="/api/v1/13f", tags=["13f"])

@router.get("/holdings/{ticker}", response_model=HoldingsResponse)
async def get_holdings(
    ticker: str = Path(pattern=r"^[A-Z0-9.]{1,10}$"),
    db: AsyncSession = Depends(get_db),
) -> HoldingsResponse:
    ...

@router.get("/holdings/{ticker}/history", response_model=HoldingsHistoryResponse)
async def get_holdings_history(
    ticker: str = Path(pattern=r"^[A-Z0-9.]{1,10}$"),
    limit: int = Query(default=10, le=40),
    db: AsyncSession = Depends(get_db),
) -> HoldingsHistoryResponse:
    ...
```

Register in `app.py`:
```python
from margin_api.routes.thirteenf import router as thirteenf_router
app.include_router(thirteenf_router)
```

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/thirteenf.py api/src/margin_api/app.py api/tests/test_13f_routes.py
git commit -m "feat(api): add 13F holdings endpoints for asset detail"
```

---

### Task 12: Manager Endpoints

**Files:**
- Modify: `api/src/margin_api/routes/thirteenf.py`
- Test: `api/tests/test_13f_manager_routes.py`

**Step 1: Write failing tests** for `GET /api/v1/13f/managers` and `GET /api/v1/13f/managers/{manager_id}/portfolio`.

**Step 2: Run to verify failure.**

**Step 3: Add endpoints:**

```python
@router.get("/managers", response_model=list[ManagerResponse])
async def list_managers(
    tier: str | None = Query(None, pattern="^(curated|top_aum)$"),
    db: AsyncSession = Depends(get_db),
) -> list[ManagerResponse]:
    ...

@router.get("/managers/{manager_id}/portfolio", response_model=ManagerPortfolioResponse)
async def get_manager_portfolio(
    manager_id: int,
    period: date | None = Query(None, description="Quarter end date, defaults to latest"),
    db: AsyncSession = Depends(get_db),
) -> ManagerPortfolioResponse:
    ...
```

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/thirteenf.py api/tests/test_13f_manager_routes.py
git commit -m "feat(api): add 13F manager listing and portfolio endpoints"
```

---

### Task 13: Analytics Endpoints

**Files:**
- Modify: `api/src/margin_api/routes/thirteenf.py`
- Test: `api/tests/test_13f_analytics_routes.py`

**Step 1: Write failing tests** for `/analytics/overlap`, `/analytics/new-positions`, and `/analytics/clone/{manager_id}`.

**Step 2: Run to verify failure.**

**Step 3: Implement the three analytics endpoints.** The overlap and new-positions queries aggregate across `institutional_holdings` joined to `security_master` and `managers`. The clone endpoint computes equal-weight portfolio from a manager's top N holdings and calculates historical performance using price data from `financial_data`.

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/thirteenf.py api/tests/test_13f_analytics_routes.py
git commit -m "feat(api): add 13F analytics endpoints — overlap, new positions, clone"
```

---

### Task 14: Frontend API Helpers

**Files:**
- Create: `web/src/lib/api/thirteenf.ts`
- Test: `web/src/lib/api/__tests__/thirteenf.test.ts`

**Step 1: Write the failing test**

```typescript
// web/src/lib/api/__tests__/thirteenf.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest"
import { getHoldings, getHoldingsHistory, getManagers, getManagerPortfolio } from "../thirteenf"

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("13F API helpers", () => {
  beforeEach(() => { mockFetch.mockReset() })

  it("getHoldings calls correct URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ticker: "AAPL", curated_holders: [], other_holders: [], summary: {} }),
    })
    await getHoldings("AAPL")
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/13f/holdings/AAPL"),
      expect.any(Object),
    )
  })

  it("getManagers calls correct URL", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] })
    await getManagers()
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/13f/managers"),
      expect.any(Object),
    )
  })
})
```

**Step 2: Run to verify failure.**

Run: `cd web && npx vitest run src/lib/api/__tests__/thirteenf.test.ts`

**Step 3: Write the API helpers**

```typescript
// web/src/lib/api/thirteenf.ts
import { apiFetch } from "./client"

export interface HoldingsResponse { /* match schema */ }
export interface HoldingsHistoryResponse { /* match schema */ }
export interface ManagerResponse { /* match schema */ }
export interface ManagerPortfolioResponse { /* match schema */ }
export interface OverlapResponse { /* match schema */ }
export interface NewPositionResponse { /* match schema */ }
export interface CloneResponse { /* match schema */ }

export function getHoldings(ticker: string) {
  return apiFetch<HoldingsResponse>(`/api/v1/13f/holdings/${ticker.toUpperCase()}`)
}

export function getHoldingsHistory(ticker: string, limit = 10) {
  return apiFetch<HoldingsHistoryResponse>(`/api/v1/13f/holdings/${ticker.toUpperCase()}/history?limit=${limit}`)
}

export function getManagers(tier?: string) {
  const params = tier ? `?tier=${tier}` : ""
  return apiFetch<ManagerResponse[]>(`/api/v1/13f/managers${params}`)
}

export function getManagerPortfolio(managerId: number, period?: string) {
  const params = period ? `?period=${period}` : ""
  return apiFetch<ManagerPortfolioResponse>(`/api/v1/13f/managers/${managerId}/portfolio${params}`)
}

export function getOverlap() {
  return apiFetch<OverlapResponse>("/api/v1/13f/analytics/overlap")
}

export function getNewPositions() {
  return apiFetch<NewPositionResponse>("/api/v1/13f/analytics/new-positions")
}

export function getClonePortfolio(managerId: number, strategy = "equal_weight_top_20") {
  return apiFetch<CloneResponse>(`/api/v1/13f/analytics/clone/${managerId}?strategy=${strategy}`)
}
```

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add web/src/lib/api/thirteenf.ts web/src/lib/api/__tests__/thirteenf.test.ts
git commit -m "feat(web): add 13F API client helpers"
```

---

### Task 15: Institutional Positioning Panel (Asset Detail)

**Files:**
- Create: `web/src/components/asset-detail/institutional-positioning.tsx`
- Create: `web/src/components/asset-detail/__tests__/institutional-positioning.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` (add panel)

**Step 1: Write the failing test**

Test that the component renders holder summary, curated fund rows, and the trend sparkline. Test the free-tier teaser state (blurred content + CTA). Mock `useSubscriptionTier`.

**Step 2: Run to verify failure.**

**Step 3: Build the component**

`"use client"` component that:
- Accepts `ticker` prop
- Fetches `getHoldings(ticker)` and `getHoldingsHistory(ticker)` in `useEffect`
- Renders header: "Institutional Positioning — Q4 2025" with filing lag badge
- Summary bar: holder counts, net accumulation
- Curated holders table (fund name, shares, change delta with green/red color, % portfolio, quarters held)
- Sparkline chart for holder trend (reuse Recharts `AreaChart` or `LineChart`)
- Expandable "All Tracked Holders" section
- Loading: skeleton cards
- Empty: "No institutional holdings data available"

Add to `asset-detail-view.tsx` after the scoring pillars section.

**Step 4: Run tests.**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/institutional-positioning.test.tsx`

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/institutional-positioning.tsx web/src/components/asset-detail/__tests__/institutional-positioning.test.tsx web/src/components/asset-detail/asset-detail-view.tsx
git commit -m "feat(web): add Institutional Positioning panel to asset detail"
```

---

### Task 16: Wire ConvictionEngine `institutionalAccumulation` Prop

**Files:**
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`
- Modify: `web/src/lib/api/scores.ts` (or types.ts — add institutional_accumulation to score response type)
- Test: update existing conviction engine tests

**Step 1: Write a failing test** that passes `institutionalAccumulation` data to `ConvictionEngine` and verifies the Smart Money Alignment section renders with fund names.

**Step 2: Run to verify failure.**

**Step 3: Wire the data:**
- Add `institutional_accumulation` field to the score response TypeScript type
- In `asset-detail-view.tsx`, extract the field from the score response and pass it as the `institutionalAccumulation` prop to `ConvictionEngine`
- Map API response shape to the component's expected interface: `{ percentile, newPositions: curated_new_positions, topFunds: notable_new_positions }`

**Step 4: Run tests** — both new and existing conviction engine tests.

**Step 5: Commit**

```bash
git commit -m "feat(web): wire ConvictionEngine institutionalAccumulation to score API"
```

---

### Task 17: Smart Money Page — Fund Tracker Tab

**Files:**
- Create: `web/src/app/smart-money/page.tsx`
- Create: `web/src/components/smart-money/fund-tracker.tsx`
- Create: `web/src/components/smart-money/tab-nav.tsx`
- Create: `web/src/components/smart-money/__tests__/fund-tracker.test.tsx`

**Step 1: Write the failing test**

Test that the Fund Tracker renders a table of managers with name, tier badge, AUM, holdings count, and top position pills. Test row expansion shows full portfolio with position change highlighting.

**Step 2: Run to verify failure.**

**Step 3: Build the page and components**

`/smart-money/page.tsx` — `"use client"` page with `AppShell`, header, and `TabNav` switching between three tab panels.

`tab-nav.tsx`:
```tsx
"use client"
interface TabNavProps {
  tabs: { id: string; label: string }[]
  activeTab: string
  onChange: (id: string) => void
}
export function TabNav({ tabs, activeTab, onChange }: TabNavProps) {
  return (
    <div className="flex gap-1 border-b border-white/[0.06] mb-6">
      {tabs.map((tab) => (
        <button key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "text-accent border-b-2 border-accent"
              : "text-text-tertiary hover:text-text-secondary"
          }`}>
          {tab.label}
        </button>
      ))}
    </div>
  )
}
```

`fund-tracker.tsx` — fetches `getManagers()`, renders sortable table. Row click expands inline to show `getManagerPortfolio(id)`.

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add web/src/app/smart-money/ web/src/components/smart-money/
git commit -m "feat(web): add Smart Money page with Fund Tracker tab"
```

---

### Task 18: Smart Money Page — Market Signals Tab

**Files:**
- Create: `web/src/components/smart-money/market-signals.tsx`
- Create: `web/src/components/smart-money/__tests__/market-signals.test.tsx`

**Step 1: Write failing test** — renders most crowded positions, new position alerts, biggest exits.

**Step 2: Run to verify failure.**

**Step 3: Build component** — fetches `getOverlap()` and `getNewPositions()`. Three sections: crowded positions table, new position cards (with fund name pills), exits list.

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add web/src/components/smart-money/market-signals.tsx web/src/components/smart-money/__tests__/
git commit -m "feat(web): add Market Signals tab to Smart Money page"
```

---

### Task 19: Smart Money Page — Clone Lab Tab

**Files:**
- Create: `web/src/components/smart-money/clone-lab.tsx`
- Create: `web/src/components/smart-money/__tests__/clone-lab.test.tsx`

**Step 1: Write failing test** — renders manager dropdown, strategy selector, portfolio table, performance chart, disclaimer.

**Step 2: Run to verify failure.**

**Step 3: Build component:**
- Manager dropdown populated from `getManagers()`
- Strategy selector: radio group with "Equal-weight top 10", "Equal-weight top 20", "Market-cap weighted"
- On selection change, fetch `getClonePortfolio(managerId, strategy)`
- Portfolio allocation table with ticker and target weight
- Historical performance via `EquityCurve` component (import from `@/components/backtesting/equity-curve`)
- Stats via `StatsSummary` component
- Disclaimer footer: `terminal-card p-3` with text about 45-day delay

**Step 4: Run tests.**

**Step 5: Commit**

```bash
git add web/src/components/smart-money/clone-lab.tsx web/src/components/smart-money/__tests__/
git commit -m "feat(web): add Clone Lab tab to Smart Money page"
```

---

### Task 20: Subscription Gating

**Files:**
- Create: `web/src/components/smart-money/institutional-gate.tsx`
- Create: `web/src/components/smart-money/__tests__/institutional-gate.test.tsx`
- Modify: `web/src/components/asset-detail/institutional-positioning.tsx` (add gating)
- Modify: `web/src/app/smart-money/page.tsx` (wrap with gate)

**Step 1: Write failing tests**

Test three states:
- `tier="institutional"` → children render normally
- `tier="portfolio"` → asset detail visible, smart money page shows teaser
- `tier="free"` → blurred content + upgrade CTA on both surfaces

**Step 2: Run to verify failure.**

**Step 3: Build the gate component** following the existing `ProGate` pattern:

```tsx
"use client"
import { useSubscriptionTier } from "@/lib/hooks/use-subscription-tier"

interface InstitutionalGateProps {
  children: React.ReactNode
  requiredTier: "portfolio" | "institutional"
  teaserMessage?: string
}

export function InstitutionalGate({ children, requiredTier, teaserMessage }: InstitutionalGateProps) {
  const { tier, loading } = useSubscriptionTier()
  // tier hierarchy: free < portfolio < institutional < operator
  const tierRank = { free: 0, analyst: 0, portfolio: 1, institutional: 2, operator: 3 }
  const userRank = tierRank[tier as keyof typeof tierRank] ?? 0
  const requiredRank = tierRank[requiredTier]

  if (loading || userRank >= requiredRank) {
    return <>{children}</>
  }

  return (
    <div className="relative">
      <div className="blur-[6px] select-none pointer-events-none">{children}</div>
      <div className="mt-3 flex items-center gap-3 bg-accent/[0.04] border border-accent/10 rounded-sm py-3 px-5">
        <span className="text-xs text-text-secondary">
          {teaserMessage || `Upgrade to ${requiredTier} to unlock this feature`}
        </span>
        <a href="/account" className="text-xs font-semibold text-accent hover:underline">
          Upgrade
        </a>
      </div>
    </div>
  )
}
```

**Step 4: Apply gating:**
- Wrap the curated holders table in `InstitutionalPositioning` with `<InstitutionalGate requiredTier="portfolio">`
- Wrap the Smart Money page content with `<InstitutionalGate requiredTier="institutional">`

**Step 5: Run all frontend tests.**

Run: `cd web && npx vitest run`

**Step 6: Commit**

```bash
git add web/src/components/smart-money/institutional-gate.tsx web/src/components/smart-money/__tests__/ web/src/components/asset-detail/institutional-positioning.tsx web/src/app/smart-money/page.tsx
git commit -m "feat(web): add subscription gating for 13F features"
```

---

## Final Verification

After all 20 tasks:

```bash
# All Python tests
uv run pytest api/tests/ engine/tests/ -v

# All frontend tests
cd web && npx vitest run

# Verify no alembic head issues
cd api && uv run alembic heads
```
