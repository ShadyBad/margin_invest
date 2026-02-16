# Data Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a deterministic, production-grade data pipeline that ingests the full US equity universe (~5000 tickers) with completeness tracking, progressive failure handling, live price polling, and universe-aware API/web integration.

**Architecture:** Universe-as-Config (YAML in git + DB snapshots). ARQ + Redis background job queue for ingestion/scoring/backtesting. Live price polling via Redis for recommended candidates. All API responses include universe metadata and freshness tiers.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 + asyncpg/aiosqlite, ARQ, Redis, yfinance, Pydantic, Next.js 15, TypeScript, vitest

**Design Doc:** `docs/plans/2026-02-15-data-pipeline-design.md`

---

## Phase 1: Database Schema Changes

Foundation tables and columns that everything else depends on.

### Task 1: Add `universe_snapshots` table

**Files:**
- Modify: `api/src/margin_api/db/models.py` (after line 15, before Asset class at line 18)
- Test: `api/tests/test_universe_models.py`

**Step 1: Write the failing test**

```python
# api/tests/test_universe_models.py
"""Tests for universe_snapshots model."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import UniverseSnapshot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestUniverseSnapshot:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, session):
        snapshot = UniverseSnapshot(
            version="2026.02.15",
            config_hash="abc123" * 10 + "abcd",
            ticker_count=4847,
            tickers=["AAPL", "MSFT", "NVDA"],
            exclusion_rules={"sectors": ["Financial Services"]},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        assert snapshot.id is not None
        assert snapshot.version == "2026.02.15"
        assert snapshot.ticker_count == 4847
        assert snapshot.is_active is True
        assert "AAPL" in snapshot.tickers
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'UniverseSnapshot'`

**Step 3: Write minimal implementation**

Add to `api/src/margin_api/db/models.py` after the imports, before the Asset class:

```python
class UniverseSnapshot(Base):
    __tablename__ = "universe_snapshots"

    id = Column(Integer, primary_key=True)
    version = Column(String, nullable=False)
    config_hash = Column(String(64), nullable=False)
    ticker_count = Column(Integer, nullable=False)
    tickers = Column(JSONVariant, nullable=False)
    exclusion_rules = Column(JSONVariant, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime(timezone=True), nullable=False)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_universe_models.py -v`
Expected: PASS

**Step 5: Run full test suite to check for regressions**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: All 294+ tests pass

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_universe_models.py
git commit -m "feat: add universe_snapshots table"
```

---

### Task 2: Add `ingestion_runs` and `ingestion_ticker_status` tables

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_universe_models.py` (extend)

**Step 1: Write the failing test**

Append to `api/tests/test_universe_models.py`:

```python
from margin_api.db.models import IngestionRun, IngestionTickerStatus


class TestIngestionRun:
    @pytest.mark.asyncio
    async def test_create_run_with_snapshot(self, session):
        snapshot = UniverseSnapshot(
            version="2026.02.15",
            config_hash="a" * 64,
            ticker_count=100,
            tickers=["AAPL"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=100,
            tickers_succeeded=0,
            tickers_failed=0,
            tickers_skipped=0,
            failed_tickers=[],
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        assert run.id is not None
        assert run.snapshot_id == snapshot.id
        assert run.status == "running"


class TestIngestionTickerStatus:
    @pytest.mark.asyncio
    async def test_create_ticker_status(self, session):
        snapshot = UniverseSnapshot(
            version="v1",
            config_hash="b" * 64,
            ticker_count=1,
            tickers=["AAPL"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=1,
            tickers_succeeded=0,
            tickers_failed=0,
            tickers_skipped=0,
            failed_tickers=[],
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()

        ticker_status = IngestionTickerStatus(
            run_id=run.id,
            ticker="AAPL",
            status="succeeded",
            data_fetched={"fundamentals": True, "prices": True, "earnings": True},
            duration_ms=1234,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(ticker_status)
        await session.commit()
        await session.refresh(ticker_status)
        assert ticker_status.id is not None
        assert ticker_status.data_fetched["fundamentals"] is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_models.py::TestIngestionRun -v`
Expected: FAIL — `ImportError: cannot import name 'IngestionRun'`

**Step 3: Write minimal implementation**

Add to `api/src/margin_api/db/models.py`:

```python
class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("universe_snapshots.id"), nullable=False)
    run_type = Column(String, nullable=False)  # "full" | "subset"
    tickers_requested = Column(Integer, nullable=False)
    tickers_succeeded = Column(Integer, nullable=False, default=0)
    tickers_failed = Column(Integer, nullable=False, default=0)
    tickers_skipped = Column(Integer, nullable=False, default=0)
    failed_tickers = Column(JSONVariant, nullable=False, default=list)
    status = Column(String, nullable=False)  # running | completed | failed | cancelled
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    snapshot = relationship("UniverseSnapshot")
    ticker_statuses = relationship("IngestionTickerStatus", back_populates="run")


class IngestionTickerStatus(Base):
    __tablename__ = "ingestion_ticker_status"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("ingestion_runs.id"), nullable=False)
    ticker = Column(String, nullable=False)
    status = Column(String, nullable=False)  # pending | ingesting | succeeded | failed
    error_message = Column(Text, nullable=True)
    data_fetched = Column(JSONVariant, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    run = relationship("IngestionRun", back_populates="ticker_statuses")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_universe_models.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_universe_models.py
git commit -m "feat: add ingestion_runs and ingestion_ticker_status tables"
```

---

### Task 3: Add `job_runs` table

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_universe_models.py` (extend)

**Step 1: Write the failing test**

Append to `api/tests/test_universe_models.py`:

```python
from margin_api.db.models import JobRun


class TestJobRun:
    @pytest.mark.asyncio
    async def test_create_job_run(self, session):
        job = JobRun(
            job_type="full_ingest",
            status="queued",
            progress=0.0,
            triggered_by="cli",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        assert job.id is not None
        assert job.job_type == "full_ingest"
        assert job.progress == 0.0

    @pytest.mark.asyncio
    async def test_chained_job(self, session):
        parent = JobRun(
            job_type="full_ingest",
            status="completed",
            progress=1.0,
            triggered_by="schedule",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(parent)
        await session.flush()

        child = JobRun(
            job_type="full_score",
            status="queued",
            progress=0.0,
            triggered_by="chained",
            parent_job_id=parent.id,
            started_at=datetime.now(UTC),
        )
        session.add(child)
        await session.commit()
        await session.refresh(child)
        assert child.parent_job_id == parent.id
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_models.py::TestJobRun -v`
Expected: FAIL — `ImportError`

**Step 3: Write minimal implementation**

Add to `api/src/margin_api/db/models.py`:

```python
class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # queued | running | completed | failed | cancelled
    progress = Column(Float, nullable=False, default=0.0)
    progress_detail = Column(String, nullable=True)
    triggered_by = Column(String, nullable=False)  # schedule | cli | chained
    parent_job_id = Column(Integer, ForeignKey("job_runs.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_universe_models.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_universe_models.py
git commit -m "feat: add job_runs table"
```

---

### Task 4: Add failure tracking columns to `assets` table

**Files:**
- Modify: `api/src/margin_api/db/models.py` (Asset class, lines 18-40)
- Test: `api/tests/test_universe_models.py` (extend)

**Step 1: Write the failing test**

```python
from margin_api.db.models import Asset


class TestAssetFailureTracking:
    @pytest.mark.asyncio
    async def test_default_ingestion_status(self, session):
        asset = Asset(ticker="AAPL", name="Apple Inc", sector="Information Technology")
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        assert asset.ingestion_status == "active"
        assert asset.consecutive_failures == 0
        assert asset.last_failure_reason is None
        assert asset.quarantined_at is None
        assert asset.last_retry_at is None

    @pytest.mark.asyncio
    async def test_quarantine_asset(self, session):
        asset = Asset(
            ticker="XYZW",
            name="XYZ Corp",
            sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=3,
            last_failure_reason="No financial data available",
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        assert asset.ingestion_status == "quarantined"
        assert asset.consecutive_failures == 3
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_models.py::TestAssetFailureTracking -v`
Expected: FAIL — `TypeError: 'ingestion_status' is an invalid keyword argument`

**Step 3: Add columns to Asset class**

In `api/src/margin_api/db/models.py`, add to the Asset class (after `updated_at`):

```python
    ingestion_status = Column(String, nullable=False, default="active")
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_failure_reason = Column(Text, nullable=True)
    quarantined_at = Column(DateTime(timezone=True), nullable=True)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_universe_models.py -v`
Expected: All PASS

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: All existing tests still pass (new columns have defaults, so no breakage)

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_universe_models.py
git commit -m "feat: add failure tracking columns to assets table"
```

---

## Phase 2: Universe Config System

### Task 5: Universe YAML loader and validator

**Files:**
- Create: `engine/src/margin_engine/universe/__init__.py`
- Create: `engine/src/margin_engine/universe/config.py`
- Test: `engine/tests/test_universe_config.py`

**Step 1: Write the failing test**

```python
# engine/tests/test_universe_config.py
"""Tests for universe config loading and validation."""
from __future__ import annotations

import hashlib
from pathlib import Path
from textwrap import dedent

import pytest

from margin_engine.universe.config import UniverseConfig, load_universe_config


class TestLoadUniverseConfig:
    def test_load_valid_yaml(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text(dedent("""\
            version: "2026.02.15"
            description: "Test universe"
            source: "manual"
            generated_at: "2026-02-15T12:00:00Z"
            exclusions:
              sectors:
                - "Financial Services"
                - "Real Estate"
              min_market_cap: 300000000
              min_avg_volume: 1000000
            tickers:
              - AAPL
              - MSFT
              - NVDA
        """))
        config = load_universe_config(config_file)
        assert config.version == "2026.02.15"
        assert config.ticker_count == 3
        assert "AAPL" in config.tickers
        assert "Financial Services" in config.exclusions.sectors

    def test_config_hash_deterministic(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        content = "version: '1'\ntickers:\n  - AAPL\n"
        config_file.write_text(content)
        c1 = load_universe_config(config_file)
        c2 = load_universe_config(config_file)
        assert c1.config_hash == c2.config_hash
        assert len(c1.config_hash) == 64  # SHA-256 hex

    def test_empty_tickers_raises(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: '1'\ntickers: []\n")
        with pytest.raises(ValueError, match="tickers"):
            load_universe_config(config_file)

    def test_missing_version_raises(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("tickers:\n  - AAPL\n")
        with pytest.raises(ValueError, match="version"):
            load_universe_config(config_file)

    def test_duplicate_tickers_deduplicated(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: '1'\ntickers:\n  - AAPL\n  - AAPL\n  - MSFT\n")
        config = load_universe_config(config_file)
        assert config.ticker_count == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_universe_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.universe'`

**Step 3: Write implementation**

Create `engine/src/margin_engine/universe/__init__.py`:
```python
"""Universe definition and management."""
```

Create `engine/src/margin_engine/universe/config.py`:
```python
"""Universe configuration loading and validation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExclusionRules:
    sectors: list[str] = field(default_factory=list)
    min_market_cap: int = 0
    min_avg_volume: int = 0


@dataclass(frozen=True)
class UniverseConfig:
    version: str
    tickers: list[str]
    ticker_count: int
    config_hash: str
    description: str = ""
    source: str = ""
    generated_at: str = ""
    exclusions: ExclusionRules = field(default_factory=ExclusionRules)


def load_universe_config(path: Path) -> UniverseConfig:
    """Load and validate a universe YAML config file."""
    raw = path.read_text()
    data = yaml.safe_load(raw)

    if not data or "version" not in data:
        raise ValueError("Universe config must include 'version' field")

    tickers_raw = data.get("tickers", [])
    if not tickers_raw:
        raise ValueError("Universe config must include non-empty 'tickers' list")

    # Deduplicate, preserve order, uppercase
    seen: set[str] = set()
    tickers: list[str] = []
    for t in tickers_raw:
        upper = str(t).upper().strip()
        if upper not in seen:
            seen.add(upper)
            tickers.append(upper)

    config_hash = hashlib.sha256(raw.encode()).hexdigest()

    exclusions_data = data.get("exclusions", {})
    exclusions = ExclusionRules(
        sectors=exclusions_data.get("sectors", []),
        min_market_cap=exclusions_data.get("min_market_cap", 0),
        min_avg_volume=exclusions_data.get("min_avg_volume", 0),
    )

    return UniverseConfig(
        version=str(data["version"]),
        tickers=tickers,
        ticker_count=len(tickers),
        config_hash=config_hash,
        description=data.get("description", ""),
        source=data.get("source", ""),
        generated_at=data.get("generated_at", ""),
        exclusions=exclusions,
    )
```

**Step 4: Add pyyaml dependency**

Run: `uv add pyyaml --package margin-engine`

**Step 5: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_universe_config.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/universe/ engine/tests/test_universe_config.py engine/pyproject.toml
git commit -m "feat: add universe YAML config loader with validation"
```

---

### Task 6: Universe screener (yfinance discovery)

**Files:**
- Create: `engine/src/margin_engine/universe/screener.py`
- Test: `engine/tests/test_universe_screener.py`

**Step 1: Write the failing test**

```python
# engine/tests/test_universe_screener.py
"""Tests for universe screener — yfinance-based ticker discovery."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from margin_engine.universe.screener import (
    filter_universe,
    generate_universe_yaml,
)


class TestFilterUniverse:
    def test_excludes_financial_services(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "JPM", "sector": "Financial Services", "market_cap": 5e11, "avg_volume_dollar": 2e9},
        ]
        excluded_sectors = ["Financial Services", "Real Estate"]
        result = filter_universe(tickers, excluded_sectors=excluded_sectors)
        assert len(result) == 1
        assert result[0] == "AAPL"

    def test_excludes_below_market_cap(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "TINY", "sector": "Technology", "market_cap": 1e8, "avg_volume_dollar": 5e6},
        ]
        result = filter_universe(tickers, min_market_cap=300_000_000)
        assert result == ["AAPL"]

    def test_excludes_below_volume(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "ILLIQ", "sector": "Technology", "market_cap": 1e9, "avg_volume_dollar": 500_000},
        ]
        result = filter_universe(tickers, min_avg_volume=1_000_000)
        assert result == ["AAPL"]


class TestGenerateUniverseYaml:
    def test_generates_valid_yaml(self):
        tickers = ["AAPL", "MSFT", "NVDA"]
        yaml_str = generate_universe_yaml(
            tickers=tickers,
            excluded_sectors=["Financial Services", "Real Estate"],
            min_market_cap=300_000_000,
            min_avg_volume=1_000_000,
        )
        assert "version:" in yaml_str
        assert "AAPL" in yaml_str
        assert "MSFT" in yaml_str
        assert "Financial Services" in yaml_str
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_universe_screener.py -v`
Expected: FAIL — `ImportError`

**Step 3: Write implementation**

Create `engine/src/margin_engine/universe/screener.py`:

```python
"""Universe screener — discover US equities via yfinance."""
from __future__ import annotations

from datetime import UTC, datetime


def filter_universe(
    tickers: list[dict],
    *,
    excluded_sectors: list[str] | None = None,
    min_market_cap: int = 0,
    min_avg_volume: int = 0,
) -> list[str]:
    """Filter raw ticker data by sector, market cap, and volume thresholds."""
    excluded = set(excluded_sectors or [])
    result: list[str] = []
    for t in tickers:
        if t.get("sector", "") in excluded:
            continue
        if t.get("market_cap", 0) < min_market_cap:
            continue
        if t.get("avg_volume_dollar", 0) < min_avg_volume:
            continue
        result.append(t["ticker"])
    return sorted(result)


def generate_universe_yaml(
    *,
    tickers: list[str],
    excluded_sectors: list[str],
    min_market_cap: int,
    min_avg_volume: int,
) -> str:
    """Generate a universe.yaml string from filtered tickers."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(UTC).strftime("%Y.%m.%d")

    lines = [
        f'version: "{today}"',
        f'description: "US equities, excluding financials and REITs"',
        f'source: "yfinance_screener"',
        f'generated_at: "{now}"',
        "",
        "exclusions:",
        "  sectors:",
    ]
    for sector in excluded_sectors:
        lines.append(f'    - "{sector}"')
    lines.append(f"  min_market_cap: {min_market_cap}")
    lines.append(f"  min_avg_volume: {min_avg_volume}")
    lines.append("")
    lines.append("tickers:")
    for ticker in sorted(tickers):
        lines.append(f"  - {ticker}")
    lines.append("")
    return "\n".join(lines)
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/test_universe_screener.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/universe/screener.py engine/tests/test_universe_screener.py
git commit -m "feat: add universe screener with filtering and YAML generation"
```

---

### Task 7: Universe CLI commands (refresh, activate, status)

**Files:**
- Modify: `api/src/margin_api/cli.py` (add universe subcommands)
- Test: `api/tests/test_cli_universe.py`

**Step 1: Write the failing test**

```python
# api/tests/test_cli_universe.py
"""Tests for universe CLI commands."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import UniverseSnapshot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestActivateUniverse:
    @pytest.mark.asyncio
    async def test_activate_creates_snapshot(self, session, tmp_path):
        from margin_api.services.universe import activate_universe

        config_file = tmp_path / "universe.yaml"
        config_file.write_text(dedent("""\
            version: "2026.02.15"
            description: "Test"
            tickers:
              - AAPL
              - MSFT
        """))
        snapshot = await activate_universe(session, config_file)
        assert snapshot.version == "2026.02.15"
        assert snapshot.ticker_count == 2
        assert snapshot.is_active is True

    @pytest.mark.asyncio
    async def test_activate_deactivates_previous(self, session, tmp_path):
        from margin_api.services.universe import activate_universe

        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: 'v1'\ntickers:\n  - AAPL\n")
        s1 = await activate_universe(session, config_file)

        config_file.write_text("version: 'v2'\ntickers:\n  - MSFT\n")
        s2 = await activate_universe(session, config_file)

        await session.refresh(s1)
        assert s1.is_active is False
        assert s2.is_active is True


class TestGetActiveSnapshot:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_snapshot(self, session):
        from margin_api.services.universe import get_active_snapshot

        result = await get_active_snapshot(session)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_active_snapshot(self, session):
        from margin_api.services.universe import activate_universe, get_active_snapshot

        # Create a snapshot via activation
        snapshot = UniverseSnapshot(
            version="v1",
            config_hash="a" * 64,
            ticker_count=1,
            tickers=["AAPL"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.commit()

        result = await get_active_snapshot(session)
        assert result is not None
        assert result.version == "v1"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_cli_universe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.universe'`

**Step 3: Write implementation**

Create `api/src/margin_api/services/__init__.py` (if missing):
```python
"""Service layer modules."""
```

Create `api/src/margin_api/services/universe.py`:

```python
"""Universe management service."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from margin_engine.universe.config import load_universe_config
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import UniverseSnapshot


async def activate_universe(session: AsyncSession, config_path: Path) -> UniverseSnapshot:
    """Load universe config from YAML, deactivate previous, create active snapshot."""
    config = load_universe_config(config_path)

    # Deactivate all existing snapshots
    await session.execute(
        update(UniverseSnapshot).where(UniverseSnapshot.is_active.is_(True)).values(is_active=False)
    )

    snapshot = UniverseSnapshot(
        version=config.version,
        config_hash=config.config_hash,
        ticker_count=config.ticker_count,
        tickers=config.tickers,
        exclusion_rules={
            "sectors": config.exclusions.sectors,
            "min_market_cap": config.exclusions.min_market_cap,
            "min_avg_volume": config.exclusions.min_avg_volume,
        },
        is_active=True,
        activated_at=datetime.now(UTC),
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def get_active_snapshot(session: AsyncSession) -> UniverseSnapshot | None:
    """Return the currently active universe snapshot, or None."""
    result = await session.execute(
        select(UniverseSnapshot).where(UniverseSnapshot.is_active.is_(True))
    )
    return result.scalar_one_or_none()
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_cli_universe.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/ api/tests/test_cli_universe.py
git commit -m "feat: add universe service (activate, get_active_snapshot)"
```

---

### Task 8: Create initial universe.yaml seed file

**Files:**
- Create: `engine/universe.yaml`

**Step 1: Create the file**

Create `engine/universe.yaml` with the current ~50 tickers as the initial seed. This will be expanded via `universe refresh` later.

```yaml
version: "2026.02.15"
description: "US equities, excluding financials and REITs — initial seed"
source: "manual"
generated_at: "2026-02-15T00:00:00Z"

exclusions:
  sectors:
    - "Financial Services"
    - "Real Estate"
  min_market_cap: 300000000
  min_avg_volume: 1000000

tickers:
  - AAPL
  - ABBV
  - AMD
  - AMZN
  - AMT
  - APD
  - AVGO
  - BAC
  - CAT
  - CMCSA
  - COST
  - CRM
  - CVX
  - DIS
  - DUK
  - GE
  - GOOGL
  - GS
  - HD
  - HON
  - JNJ
  - JPM
  - KO
  - LIN
  - LLY
  - MA
  - MCD
  - META
  - MRK
  - MSFT
  - NEE
  - NFLX
  - NKE
  - NVDA
  - ORCL
  - PEP
  - PG
  - PLD
  - RTX
  - SBUX
  - SHW
  - SO
  - TJX
  - TSLA
  - UNH
  - UNP
  - V
  - WMT
  - XOM
```

**Step 2: Verify it loads**

Run: `uv run python -c "from margin_engine.universe.config import load_universe_config; from pathlib import Path; c = load_universe_config(Path('engine/universe.yaml')); print(f'{c.ticker_count} tickers, version {c.version}')"`
Expected: `49 tickers, version 2026.02.15`

**Step 3: Commit**

```bash
git add engine/universe.yaml
git commit -m "feat: add initial universe.yaml seed config"
```

---

## Phase 3: Ingestion Refactor

### Task 9: Universe-aware ingestion service

**Files:**
- Create: `api/src/margin_api/services/ingestion.py`
- Test: `api/tests/test_ingestion_service.py`

This task implements the core ingestion orchestration that respects universe snapshots, tracks per-ticker status, and implements the progressive failure policy. It replaces the current `run_seed` function in `cli.py`.

**Step 1: Write the failing test**

```python
# api/tests/test_ingestion_service.py
"""Tests for the ingestion service."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, IngestionRun, IngestionTickerStatus, UniverseSnapshot
from margin_api.services.ingestion import (
    classify_error,
    should_ingest_ticker,
    update_failure_status,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestClassifyError:
    def test_timeout_is_transient(self):
        assert classify_error(TimeoutError("connection timed out")) == "transient"

    def test_connection_error_is_transient(self):
        assert classify_error(ConnectionError("refused")) == "transient"

    def test_value_error_is_data_unavailable(self):
        assert classify_error(ValueError("No financial data")) == "data_unavailable"

    def test_key_error_is_data_unavailable(self):
        assert classify_error(KeyError("missing_field")) == "data_unavailable"

    def test_ticker_not_found_is_permanent(self):
        assert classify_error(ValueError("Ticker not found")) == "permanent"

    def test_delisted_is_permanent(self):
        assert classify_error(ValueError("delisted")) == "permanent"


class TestShouldIngestTicker:
    def test_active_ticker_should_ingest(self):
        assert should_ingest_ticker("active", 0, None) is True

    def test_permanently_skipped_should_not_ingest(self):
        assert should_ingest_ticker("permanently_skipped", 6, None) is False

    def test_quarantined_within_7_days_should_not_ingest(self):
        recent = datetime.now(UTC)
        assert should_ingest_ticker("quarantined", 3, recent) is False

    def test_quarantined_after_7_days_should_ingest(self):
        from datetime import timedelta
        old = datetime.now(UTC) - timedelta(days=8)
        assert should_ingest_ticker("quarantined", 3, old) is True


class TestUpdateFailureStatus:
    @pytest.mark.asyncio
    async def test_data_unavailable_increments_failures(self, session):
        asset = Asset(ticker="XYZW", name="XYZ Corp", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 1
        assert asset.ingestion_status == "active"

    @pytest.mark.asyncio
    async def test_three_failures_quarantines(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            consecutive_failures=2,
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 3
        assert asset.ingestion_status == "quarantined"
        assert asset.quarantined_at is not None

    @pytest.mark.asyncio
    async def test_six_failures_permanently_skips(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=5,
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 6
        assert asset.ingestion_status == "permanently_skipped"

    @pytest.mark.asyncio
    async def test_permanent_error_skips_immediately(self, session):
        asset = Asset(ticker="DEAD", name="Dead Corp", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "permanent", "Ticker delisted")
        await session.refresh(asset)
        assert asset.ingestion_status == "permanently_skipped"

    @pytest.mark.asyncio
    async def test_transient_does_not_increment(self, session):
        asset = Asset(ticker="AAPL", name="Apple", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "transient", "Timeout")
        await session.refresh(asset)
        assert asset.consecutive_failures == 0
        assert asset.ingestion_status == "active"

    @pytest.mark.asyncio
    async def test_success_resets_failures(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=4,
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "success", None)
        await session.refresh(asset)
        assert asset.consecutive_failures == 0
        assert asset.ingestion_status == "active"
        assert asset.quarantined_at is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ingestion_service.py -v`
Expected: FAIL — `ImportError`

**Step 3: Write implementation**

Create `api/src/margin_api/services/ingestion.py`:

```python
"""Ingestion service — universe-aware data pipeline orchestration."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset

_PERMANENT_KEYWORDS = {"not found", "delisted", "merged", "acquired", "no longer listed"}
_QUARANTINE_THRESHOLD = 3
_PERMANENT_THRESHOLD = 6


def classify_error(error: Exception) -> str:
    """Classify an ingestion error as transient, data_unavailable, or permanent."""
    msg = str(error).lower()

    if any(kw in msg for kw in _PERMANENT_KEYWORDS):
        return "permanent"

    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return "transient"

    # Rate limit errors
    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return "transient"

    if "503" in msg or "502" in msg or "500" in msg:
        return "transient"

    return "data_unavailable"


def should_ingest_ticker(
    ingestion_status: str,
    consecutive_failures: int,
    last_retry_at: datetime | None,
) -> bool:
    """Determine whether a ticker should be ingested in the current run."""
    if ingestion_status == "permanently_skipped":
        return False

    if ingestion_status == "quarantined":
        if last_retry_at is None:
            return True
        return datetime.now(UTC) - last_retry_at > timedelta(days=7)

    return True


async def update_failure_status(
    session: AsyncSession,
    asset: Asset,
    error_type: str,
    error_message: str | None,
) -> None:
    """Update asset failure tracking based on error classification."""
    if error_type == "success":
        asset.consecutive_failures = 0
        asset.ingestion_status = "active"
        asset.last_failure_reason = None
        asset.quarantined_at = None
        asset.last_retry_at = None
        await session.commit()
        return

    if error_type == "transient":
        asset.last_failure_reason = error_message
        await session.commit()
        return

    if error_type == "permanent":
        asset.ingestion_status = "permanently_skipped"
        asset.last_failure_reason = error_message
        await session.commit()
        return

    # data_unavailable
    asset.consecutive_failures += 1
    asset.last_failure_reason = error_message

    if asset.consecutive_failures >= _PERMANENT_THRESHOLD:
        asset.ingestion_status = "permanently_skipped"
    elif asset.consecutive_failures >= _QUARANTINE_THRESHOLD:
        asset.ingestion_status = "quarantined"
        if asset.quarantined_at is None:
            asset.quarantined_at = datetime.now(UTC)
        asset.last_retry_at = datetime.now(UTC)

    await session.commit()
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_ingestion_service.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/ingestion.py api/tests/test_ingestion_service.py
git commit -m "feat: add ingestion service with progressive failure policy"
```

---

### Task 10: Refactor CLI — unified `ingest` command with universe enforcement

**Files:**
- Modify: `api/src/margin_api/cli.py`
- Test: `api/tests/test_cli_ingest.py`

This task modifies the CLI to replace `seed` with `ingest`, enforce universe snapshots, and add universe subcommands. The existing `seed` command should remain as an alias for backward compatibility during transition but print a deprecation warning.

**Step 1: Write the failing test**

```python
# api/tests/test_cli_ingest.py
"""Tests for the ingest CLI command enforcement logic."""
from __future__ import annotations

import pytest


class TestIngestEnforcement:
    def test_ingest_requires_active_snapshot(self):
        """Verify that ingest refuses to run without an active snapshot."""
        from margin_api.cli import validate_ingest_preconditions

        with pytest.raises(SystemExit, match="No active universe snapshot"):
            validate_ingest_preconditions(active_snapshot=None, tickers_override=None)

    def test_ingest_with_tickers_override_skips_snapshot_check(self):
        """Explicit --tickers flag bypasses snapshot requirement."""
        from margin_api.cli import validate_ingest_preconditions

        # Should not raise
        validate_ingest_preconditions(active_snapshot=None, tickers_override=["AAPL", "MSFT"])

    def test_ingest_determines_full_run_type(self):
        """No --tickers flag = full run type."""
        from margin_api.cli import determine_run_type

        assert determine_run_type(tickers_override=None) == "full"

    def test_ingest_determines_subset_run_type(self):
        """--tickers flag = subset run type."""
        from margin_api.cli import determine_run_type

        assert determine_run_type(tickers_override=["AAPL"]) == "subset"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_cli_ingest.py -v`
Expected: FAIL — `ImportError`

**Step 3: Add functions to cli.py**

Add to `api/src/margin_api/cli.py`:

```python
def validate_ingest_preconditions(
    active_snapshot: object | None,
    tickers_override: list[str] | None,
) -> None:
    """Validate that ingestion preconditions are met."""
    if tickers_override:
        return  # Explicit subset bypasses snapshot check
    if active_snapshot is None:
        raise SystemExit(
            "No active universe snapshot. Run 'universe activate' first.\n"
            "Or use --tickers to ingest a specific subset."
        )


def determine_run_type(tickers_override: list[str] | None) -> str:
    """Determine whether this is a 'full' or 'subset' run."""
    return "subset" if tickers_override else "full"
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_cli_ingest.py -v`
Expected: All PASS

**Step 5: Run full API suite**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add api/src/margin_api/cli.py api/tests/test_cli_ingest.py
git commit -m "feat: add ingest CLI enforcement logic"
```

---

## Phase 4: API Updates (Universe-Aware)

### Task 11: Universe status endpoint and Pydantic models

**Files:**
- Create: `api/src/margin_api/routes/universe.py`
- Create: `api/src/margin_api/schemas/universe.py`
- Test: `api/tests/test_universe_routes.py`

**Step 1: Write failing test**

```python
# api/tests/test_universe_routes.py
"""Tests for universe API endpoints."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, UniverseSnapshot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestUniverseStatusSchema:
    def test_universe_status_model(self):
        from margin_api.schemas.universe import UniverseStatusResponse

        status = UniverseStatusResponse(
            universe_version="2026.02.15",
            universe_size=4847,
            assets_ingested=4812,
            assets_scored=4790,
            assets_fresh=4780,
            assets_stale=10,
            assets_expired=0,
            assets_quarantined=8,
            assets_permanently_skipped=3,
            ingestion_coverage=0.993,
            scoring_coverage=0.988,
            last_ingestion_run=datetime.now(UTC),
            last_scoring_run=datetime.now(UTC),
            is_complete=True,
        )
        assert status.is_complete is True
        assert status.ingestion_coverage == 0.993


class TestUniverseSummarySchema:
    def test_universe_summary_model(self):
        from margin_api.schemas.universe import UniverseSummary

        summary = UniverseSummary(
            version="2026.02.15",
            size=4847,
            scoring_coverage=0.988,
            is_complete=True,
            last_scoring_run=datetime.now(UTC),
        )
        data = summary.model_dump()
        assert data["version"] == "2026.02.15"
        assert data["is_complete"] is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_routes.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

Create `api/src/margin_api/schemas/__init__.py`:
```python
"""Pydantic response schemas."""
```

Create `api/src/margin_api/schemas/universe.py`:

```python
"""Universe-related Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UniverseSummary(BaseModel):
    """Lightweight universe metadata included in dashboard/score responses."""
    version: str
    size: int
    scoring_coverage: float
    is_complete: bool
    last_scoring_run: datetime | None


class UniverseStatusResponse(BaseModel):
    """Full universe status for the /universe/status endpoint."""
    universe_version: str
    universe_size: int
    assets_ingested: int
    assets_scored: int
    assets_fresh: int
    assets_stale: int
    assets_expired: int
    assets_quarantined: int
    assets_permanently_skipped: int
    ingestion_coverage: float
    scoring_coverage: float
    last_ingestion_run: datetime | None
    last_scoring_run: datetime | None
    is_complete: bool


class Warning(BaseModel):
    """Structured warning for incomplete universe coverage."""
    code: str
    message: str
    severity: str  # "warning" | "error"
```

Create `api/src/margin_api/routes/universe.py`:

```python
"""Universe status API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.session import get_session
from margin_api.schemas.universe import UniverseStatusResponse
from margin_api.services.universe import get_active_snapshot

router = APIRouter(prefix="/api/v1", tags=["universe"])


@router.get("/universe/status", response_model=UniverseStatusResponse)
async def get_universe_status(session: AsyncSession = Depends(get_session)):
    """Return full universe completeness status."""
    snapshot = await get_active_snapshot(session)
    if snapshot is None:
        return UniverseStatusResponse(
            universe_version="none",
            universe_size=0,
            assets_ingested=0,
            assets_scored=0,
            assets_fresh=0,
            assets_stale=0,
            assets_expired=0,
            assets_quarantined=0,
            assets_permanently_skipped=0,
            ingestion_coverage=0.0,
            scoring_coverage=0.0,
            last_ingestion_run=None,
            last_scoring_run=None,
            is_complete=False,
        )
    # Full implementation will query actual DB counts
    # For now, return snapshot metadata
    return UniverseStatusResponse(
        universe_version=snapshot.version,
        universe_size=snapshot.ticker_count,
        assets_ingested=0,
        assets_scored=0,
        assets_fresh=0,
        assets_stale=0,
        assets_expired=0,
        assets_quarantined=0,
        assets_permanently_skipped=0,
        ingestion_coverage=0.0,
        scoring_coverage=0.0,
        last_ingestion_run=None,
        last_scoring_run=None,
        is_complete=False,
    )
```

**Step 4: Register router in app.py**

Add to `api/src/margin_api/app.py` imports and router registration:

```python
from margin_api.routes.universe import router as universe_router
# ...
app.include_router(universe_router)
```

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_universe_routes.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/ api/src/margin_api/routes/universe.py api/src/margin_api/app.py api/tests/test_universe_routes.py
git commit -m "feat: add universe status endpoint and schemas"
```

---

### Task 12: Add freshness computation to score responses

**Files:**
- Create: `api/src/margin_api/services/freshness.py`
- Test: `api/tests/test_freshness.py`

**Step 1: Write failing test**

```python
# api/tests/test_freshness.py
"""Tests for data freshness computation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from margin_api.services.freshness import compute_freshness


class TestComputeFreshness:
    def test_fresh_within_18_hours(self):
        scored_at = datetime.now(UTC) - timedelta(hours=1)
        assert compute_freshness(scored_at) == "fresh"

    def test_stale_between_18h_and_3d(self):
        scored_at = datetime.now(UTC) - timedelta(hours=24)
        assert compute_freshness(scored_at) == "stale"

    def test_stale_at_2_days(self):
        scored_at = datetime.now(UTC) - timedelta(days=2)
        assert compute_freshness(scored_at) == "stale"

    def test_expired_after_3_days(self):
        scored_at = datetime.now(UTC) - timedelta(days=4)
        assert compute_freshness(scored_at) == "expired"

    def test_exactly_18_hours_is_stale(self):
        scored_at = datetime.now(UTC) - timedelta(hours=18)
        assert compute_freshness(scored_at) == "stale"

    def test_exactly_3_days_is_expired(self):
        scored_at = datetime.now(UTC) - timedelta(days=3)
        assert compute_freshness(scored_at) == "expired"

    def test_none_scored_at_is_expired(self):
        assert compute_freshness(None) == "expired"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_freshness.py -v`
Expected: FAIL

**Step 3: Write implementation**

Create `api/src/margin_api/services/freshness.py`:

```python
"""Data freshness tier computation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

FRESH_THRESHOLD = timedelta(hours=18)
STALE_THRESHOLD = timedelta(days=3)


def compute_freshness(scored_at: datetime | None) -> str:
    """Compute freshness tier from scored_at timestamp.

    Returns: "fresh" | "stale" | "expired"
    """
    if scored_at is None:
        return "expired"

    age = datetime.now(UTC) - scored_at

    if age < FRESH_THRESHOLD:
        return "fresh"
    if age < STALE_THRESHOLD:
        return "stale"
    return "expired"
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_freshness.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/freshness.py api/tests/test_freshness.py
git commit -m "feat: add data freshness tier computation"
```

---

### Task 13: Modify dashboard endpoint to include universe metadata

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py`
- Modify: existing dashboard response model
- Test: verify existing tests still pass, add new test for universe field

This task adds the `universe` and `warnings` fields to the DashboardResponse. The implementation should compute universe metadata from DB queries and include warnings when coverage is below thresholds.

**Step 1: Update DashboardResponse schema**

Add `universe` and `warnings` fields to the dashboard response model. Check existing response model location and extend it.

**Step 2: Update dashboard route**

In `api/src/margin_api/routes/dashboard.py`, after computing picks and watchlist, query the universe status and attach it to the response.

**Step 3: Run all API tests to verify no regression**

Run: `uv run pytest api/tests/ -v --tb=short`

**Step 4: Commit**

```bash
git commit -m "feat: add universe metadata and warnings to dashboard response"
```

---

## Phase 5: Web App Updates

### Task 14: Update TypeScript types

**Files:**
- Modify: `web/src/lib/api/types.ts`

Add `UniverseSummary`, `Warning`, `data_freshness`, `price_source`, `price_updated_at`, and `ingestion_status` fields to the existing types.

```typescript
// Add to types.ts

export interface UniverseSummary {
  version: string
  size: number
  scoring_coverage: number
  is_complete: boolean
  last_scoring_run: string | null
}

export interface Warning {
  code: string
  message: string
  severity: "warning" | "error"
}

// Extend DashboardResponse
export interface DashboardResponse {
  picks: PickSummary[]
  watchlist: WatchlistItem[]
  last_updated: string
  total_scored: number
  universe: UniverseSummary      // NEW
  warnings?: Warning[]           // NEW
}

// Extend PickSummary
export interface PickSummary {
  // ... existing fields ...
  data_freshness: "fresh" | "stale" | "expired"        // NEW
  scored_at: string                                      // NEW
  price_source: "live" | "daily_close"                   // NEW
  price_updated_at: string | null                        // NEW
  ingestion_status: "complete" | "processing" | "failed" | "pending"  // NEW
}
```

**Step 1: Update types.ts with new interfaces and extended fields**

**Step 2: Run web tests to verify no regressions**

Run: `cd web && pnpm test:run`

**Step 3: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): add universe, freshness, and live price types"
```

---

### Task 15: Ingestion status banner component

**Files:**
- Create: `web/src/components/dashboard/ingestion-banner.tsx`
- Test: `web/src/components/dashboard/__tests__/ingestion-banner.test.tsx`

**Step 1: Write failing test**

```typescript
// web/src/components/dashboard/__tests__/ingestion-banner.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { IngestionBanner } from "../ingestion-banner"

describe("IngestionBanner", () => {
  it("renders nothing when universe is complete", () => {
    const { container } = render(
      <IngestionBanner
        universe={{ version: "v1", size: 5000, scoring_coverage: 0.98, is_complete: true, last_scoring_run: null }}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders warning when coverage between 50-95%", () => {
    render(
      <IngestionBanner
        universe={{ version: "v1", size: 5000, scoring_coverage: 0.72, is_complete: false, last_scoring_run: null }}
      />
    )
    expect(screen.getByText(/72%/)).toBeInTheDocument()
    expect(screen.getByText(/Rankings may shift/)).toBeInTheDocument()
  })

  it("renders error when coverage below 50%", () => {
    render(
      <IngestionBanner
        universe={{ version: "v1", size: 5000, scoring_coverage: 0.30, is_complete: false, last_scoring_run: null }}
      />
    )
    expect(screen.getByText(/too low/i)).toBeInTheDocument()
  })
})
```

**Step 2: Write implementation**

```tsx
// web/src/components/dashboard/ingestion-banner.tsx
"use client"

import type { UniverseSummary } from "@/lib/api/types"

interface IngestionBannerProps {
  universe: UniverseSummary
  warnings?: { code: string; message: string; severity: string }[]
}

export function IngestionBanner({ universe, warnings }: IngestionBannerProps) {
  if (universe.is_complete) return null

  const coverage = Math.round(universe.scoring_coverage * 100)
  const isLow = universe.scoring_coverage < 0.5

  return (
    <div
      className={`rounded-sm px-4 py-3 mb-6 text-sm ${
        isLow
          ? "bg-bearish/10 border border-bearish/30 text-bearish"
          : "bg-accent/10 border border-accent/30 text-accent"
      }`}
      role="alert"
    >
      {isLow
        ? `Universe coverage too low for reliable rankings. Ingestion in progress.`
        : `Data ingestion in progress — ${coverage}% of universe scored. Rankings may shift.`}
    </div>
  )
}
```

**Step 3: Run tests**

Run: `cd web && pnpm test:run`

**Step 4: Commit**

```bash
git add web/src/components/dashboard/ingestion-banner.tsx web/src/components/dashboard/__tests__/ingestion-banner.test.tsx
git commit -m "feat(web): add ingestion status banner component"
```

---

### Task 16: Integrate banner into dashboard page

**Files:**
- Modify: `web/src/app/dashboard/page.tsx`

Add the `IngestionBanner` component after the title section, passing `data.universe` and `data.warnings`.

**Step 1: Import and add banner**

**Step 2: Run tests**

**Step 3: Commit**

```bash
git commit -m "feat(web): integrate ingestion banner into dashboard"
```

---

### Task 17: Add freshness indicators to stock cards

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`

Add a freshness badge when `pick.data_freshness === "stale"` — shows "Updated Xh ago" with muted styling. Skip rendering for expired picks (handled at the grid level).

**Step 1: Update StockCard to show freshness badge**

**Step 2: Add live price indicator (green dot when `price_source === "live"`)**

**Step 3: Run tests**

**Step 4: Commit**

```bash
git commit -m "feat(web): add freshness badge and live price indicator to stock cards"
```

---

## Phase 6: ARQ Job Queue

### Task 18: ARQ worker setup and job tracking

**Files:**
- Create: `api/src/margin_api/workers.py`
- Test: `api/tests/test_workers.py`

**Step 1: Write failing test**

Test that the worker settings are properly configured and that job functions exist.

```python
# api/tests/test_workers.py
"""Tests for ARQ worker configuration."""
from __future__ import annotations

from margin_api.workers import WorkerSettings


class TestWorkerSettings:
    def test_has_redis_settings(self):
        assert WorkerSettings.redis_settings is not None

    def test_has_functions(self):
        assert len(WorkerSettings.functions) >= 3  # ingest, score, backtest

    def test_has_cron_jobs(self):
        assert len(WorkerSettings.cron_jobs) >= 2  # daily ingest, live price poll
```

**Step 2: Write implementation**

```python
# api/src/margin_api/workers.py
"""ARQ worker configuration and job definitions."""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings


async def full_ingest(ctx: dict) -> dict:
    """Ingest full universe from active snapshot."""
    # Implementation in subsequent task
    return {"status": "not_implemented"}


async def full_score(ctx: dict) -> dict:
    """Score all ingested assets."""
    return {"status": "not_implemented"}


async def backtest_validate(ctx: dict) -> dict:
    """Run automatic backtest validation."""
    return {"status": "not_implemented"}


async def live_price_poll(ctx: dict) -> dict:
    """Poll live prices for recommended candidates."""
    return {"status": "not_implemented"}


async def retry_quarantined(ctx: dict) -> dict:
    """Retry quarantined tickers weekly."""
    return {"status": "not_implemented"}


class WorkerSettings:
    redis_settings = RedisSettings(host="localhost", port=6379)
    functions = [full_ingest, full_score, backtest_validate, live_price_poll, retry_quarantined]
    cron_jobs = [
        cron(full_ingest, hour=16, minute=30),  # 4:30 PM (configure TZ in production)
        cron(
            live_price_poll,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            run_at_startup=False,
        ),
        cron(retry_quarantined, weekday=6, hour=0),  # Sunday midnight
    ]
```

**Step 3: Run tests**

Run: `uv run pytest api/tests/test_workers.py -v`

**Step 4: Add redis dependency if not present**

Run: `uv add redis --package margin-api`

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "feat: add ARQ worker configuration with cron jobs"
```

---

### Task 19: Jobs API endpoint

**Files:**
- Create: `api/src/margin_api/routes/jobs.py`
- Test: `api/tests/test_jobs_routes.py`

Implement `GET /api/v1/jobs/latest` to return pipeline health status.

**Step 1: Write test, step 2: implement, step 3: register router, step 4: commit**

---

### Task 20: Ingestion runs API endpoint

**Files:**
- Create: `api/src/margin_api/routes/ingestion.py`

Implement `GET /api/v1/ingestion/runs` with pagination.

---

## Phase 7: Live Price Polling

### Task 21: Redis-backed live price service

**Files:**
- Create: `api/src/margin_api/services/live_prices.py`
- Test: `api/tests/test_live_prices.py`

Implement reading/writing live prices from Redis, with fallback to DB stored price.

---

### Task 22: Live price poll ARQ task

Wire `live_price_poll` worker function to use the live price service + yfinance batch fetch.

---

### Task 23: Integrate live prices into score API responses

Modify `api/src/margin_api/routes/scores.py` to check Redis for live prices and include `price_source` and `price_updated_at` fields.

---

## Phase 8: Automatic Backtesting

### Task 24: Chained backtest validation job

Wire `backtest_validate` worker to run after `full_score` completes. Store results with `universe_version` and `methodology_health`.

---

### Task 25: Update backtesting page to read-only

Modify `web/src/app/backtesting/page.tsx` to display latest automatic validation results instead of user-triggered backtests.

---

## Phase 9: Integration & Smoke Testing

### Task 26: End-to-end integration test

Create a test that:
1. Loads `engine/universe.yaml`
2. Activates the snapshot
3. Runs ingestion for 3 tickers (subset mode)
4. Runs scoring
5. Verifies dashboard API returns universe metadata
6. Verifies freshness is computed correctly

### Task 27: Verify all existing tests pass

Run: `uv run pytest -v` (all tests)
Run: `cd web && pnpm test:run` (all frontend tests)

Verify zero regressions across the full test suite.

---

## Execution Notes

- **Redis must be running** for ARQ tests and live price tests. Use `docker compose up -d redis`.
- **Database migrations**: After schema changes, run `uv run alembic revision --autogenerate -m "add pipeline tables"` followed by `uv run alembic upgrade head`.
- **Existing tests**: The 784 engine tests and 294 API tests must continue passing after every task.
- **TDD discipline**: Write the failing test FIRST. Never write implementation before seeing the test fail.
- **Commits**: One commit per task. Each commit should leave the codebase in a passing state.
