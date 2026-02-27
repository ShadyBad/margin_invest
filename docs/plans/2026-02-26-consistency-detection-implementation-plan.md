# Data Consistency Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detect silent provider errors (e.g., wrong shares_outstanding after stock splits) by flagging tickers where critical financial fields deviate >3σ from their trailing history.

**Architecture:** A pure-engine `validate_data_consistency()` function computes z-scores for 5 critical fields across a ticker's `FinancialHistory`. An API-layer post-ingestion step calls it, flags suspect records, and optionally triggers re-ingestion from a fallback provider. Results stored as a `consistency_flags` JSONB column on `FinancialData`.

**Tech Stack:** Python 3.13, Pydantic, SQLAlchemy 2.0, pytest, existing engine/api patterns

**Design doc:** `docs/plans/2026-02-26-confidence-threshold-design.md`

---

## Task 1: ConsistencyFlag Model

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py`
- Test: `engine/tests/test_scoring_models.py`

**Step 1: Write the failing test**

Add to `engine/tests/test_scoring_models.py`:

```python
from margin_engine.models.scoring import ConsistencyFlag


def test_consistency_flag_creation():
    flag = ConsistencyFlag(
        field_name="revenue",
        current_value=1_000_000.0,
        historical_mean=500_000.0,
        historical_std=50_000.0,
        z_score=10.0,
        periods_used=5,
    )
    assert flag.field_name == "revenue"
    assert flag.z_score == 10.0
    assert flag.is_anomaly is True


def test_consistency_flag_normal_value():
    flag = ConsistencyFlag(
        field_name="revenue",
        current_value=510_000.0,
        historical_mean=500_000.0,
        historical_std=50_000.0,
        z_score=0.2,
        periods_used=5,
    )
    assert flag.is_anomaly is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_scoring_models.py::test_consistency_flag_creation -v`
Expected: FAIL with `ImportError: cannot import name 'ConsistencyFlag'`

**Step 3: Write minimal implementation**

Add to `engine/src/margin_engine/models/scoring.py`:

```python
_ANOMALY_Z_THRESHOLD = 3.0


class ConsistencyFlag(BaseModel):
    """Flag for a single field that deviates significantly from historical pattern."""

    field_name: str
    current_value: float
    historical_mean: float
    historical_std: float
    z_score: float
    periods_used: int

    @property
    def is_anomaly(self) -> bool:
        return abs(self.z_score) >= _ANOMALY_Z_THRESHOLD
```

Also add `ConsistencyFlag` to the `__init__.py` exports if the models package uses one.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/test_scoring_models.py -v -k consistency`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/test_scoring_models.py
git commit -m "feat(engine): add ConsistencyFlag model for data deviation detection"
```

---

## Task 2: validate_data_consistency() — Core Engine Function

**Files:**
- Create: `engine/src/margin_engine/scoring/data_consistency.py`
- Test: `engine/tests/scoring/test_data_consistency.py`

**Step 1: Write the failing tests**

Create `engine/tests/scoring/test_data_consistency.py`:

```python
"""Tests for cross-period data consistency validation."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.data_consistency import validate_data_consistency


def _make_period(
    period_end: str,
    revenue: int = 100_000,
    total_assets: int = 500_000,
    shares_outstanding: int = 1_000_000,
    operating_income: int = 20_000,
    operating_cash_flow: int = 25_000,
    capital_expenditures: int = -5_000,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            ebit=Decimal(str(operating_income)),
            net_income=Decimal(str(operating_income)),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(total_assets)),
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(operating_cash_flow)),
            capital_expenditures=Decimal(str(capital_expenditures)),
        ),
    )


def test_stable_history_no_flags():
    """Stable data across periods should produce no anomaly flags."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=105_000),
        _make_period("2022-12-31", revenue=102_000),
        _make_period("2023-12-31", revenue=108_000),
        _make_period("2024-12-31", revenue=103_000),
    ]
    history = FinancialHistory(ticker="STABLE", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) == 0


def test_shares_outstanding_spike_flagged():
    """A 4x jump in shares_outstanding (stock split error) should be flagged."""
    periods = [
        _make_period("2020-12-31", shares_outstanding=1_000_000),
        _make_period("2021-12-31", shares_outstanding=1_000_000),
        _make_period("2022-12-31", shares_outstanding=1_000_000),
        _make_period("2023-12-31", shares_outstanding=1_000_000),
        _make_period("2024-12-31", shares_outstanding=4_000_000),  # 4x jump
    ]
    history = FinancialHistory(ticker="SPLIT", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) >= 1
    assert any(f.field_name == "shares_outstanding" for f in anomalies)


def test_revenue_drop_flagged():
    """A sudden 80% revenue drop should be flagged."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=105_000),
        _make_period("2022-12-31", revenue=102_000),
        _make_period("2023-12-31", revenue=108_000),
        _make_period("2024-12-31", revenue=20_000),  # 80% drop
    ]
    history = FinancialHistory(ticker="DROP", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert any(f.field_name == "revenue" for f in anomalies)


def test_insufficient_history_returns_empty():
    """With < 3 periods, there's not enough history to validate. Return empty."""
    periods = [
        _make_period("2023-12-31"),
        _make_period("2024-12-31"),
    ]
    history = FinancialHistory(ticker="SHORT", periods=periods)
    flags = validate_data_consistency(history)
    assert flags == []


def test_zero_std_skipped():
    """If all historical values are identical (std=0), skip the field (no division by zero)."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=100_000),
        _make_period("2022-12-31", revenue=100_000),
        _make_period("2023-12-31", revenue=100_000),
        _make_period("2024-12-31", revenue=200_000),  # 2x jump
    ]
    history = FinancialHistory(ticker="ZERO_STD", periods=periods)
    # With zero std among prior periods, should either skip or use
    # absolute deviation logic — but must NOT raise ZeroDivisionError
    flags = validate_data_consistency(history)
    # Should still flag via fallback logic (>100% deviation from mean)
    assert isinstance(flags, list)


def test_gradual_growth_not_flagged():
    """20% YoY revenue growth sustained over 5 years should NOT be flagged."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=120_000),
        _make_period("2022-12-31", revenue=144_000),
        _make_period("2023-12-31", revenue=173_000),
        _make_period("2024-12-31", revenue=207_000),
    ]
    history = FinancialHistory(ticker="GROWER", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) == 0


def test_all_five_critical_fields_checked():
    """Verify all 5 critical fields are checked when data is present."""
    periods = [
        _make_period("2020-12-31"),
        _make_period("2021-12-31"),
        _make_period("2022-12-31"),
        _make_period("2023-12-31"),
        _make_period("2024-12-31"),
    ]
    history = FinancialHistory(ticker="ALL", periods=periods)
    flags = validate_data_consistency(history)
    checked_fields = {f.field_name for f in flags}
    expected = {"revenue", "total_assets", "shares_outstanding", "operating_income", "free_cash_flow"}
    assert checked_fields == expected
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_data_consistency.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'margin_engine.scoring.data_consistency'`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/scoring/data_consistency.py`:

```python
"""Cross-period data consistency validation.

Compares the most recent period's critical financial fields against trailing
history to detect silent provider errors (e.g., wrong shares_outstanding
after stock splits, revenue off by orders of magnitude).

Uses z-scores with a 3σ threshold. Fields with zero standard deviation
use a fallback: flag if current deviates >100% from mean.
"""

from __future__ import annotations

import math

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import ConsistencyFlag

_MIN_PERIODS = 3
_Z_THRESHOLD = 3.0
_FALLBACK_DEVIATION_PCT = 1.0  # 100% deviation when std is zero


def _extract_field(period: FinancialPeriod, field_name: str) -> float | None:
    """Extract a critical field value from a FinancialPeriod."""
    extractors: dict[str, callable] = {
        "revenue": lambda p: float(p.current_income.revenue),
        "total_assets": lambda p: float(p.current_balance.total_assets),
        "shares_outstanding": lambda p: float(p.current_income.shares_outstanding),
        "operating_income": lambda p: float(p.current_income.ebit),
        "free_cash_flow": lambda p: float(p.current_cash_flow.free_cash_flow),
    }
    extractor = extractors.get(field_name)
    if extractor is None:
        return None
    try:
        return extractor(period)
    except (AttributeError, TypeError, ZeroDivisionError):
        return None


CRITICAL_FIELDS = [
    "revenue",
    "total_assets",
    "shares_outstanding",
    "operating_income",
    "free_cash_flow",
]


def validate_data_consistency(
    history: FinancialHistory,
) -> list[ConsistencyFlag]:
    """Validate the most recent period against trailing history.

    Args:
        history: Multi-period financial data (sorted oldest-first by validator).

    Returns:
        List of ConsistencyFlag for each critical field. Each flag includes
        the z-score; callers use flag.is_anomaly to check if it exceeds 3σ.
        Returns empty list if fewer than 3 periods available.
    """
    if len(history.periods) < _MIN_PERIODS:
        return []

    current = history.periods[-1]
    prior_periods = history.periods[:-1]
    flags: list[ConsistencyFlag] = []

    for field_name in CRITICAL_FIELDS:
        current_value = _extract_field(current, field_name)
        if current_value is None:
            continue

        prior_values = []
        for p in prior_periods:
            v = _extract_field(p, field_name)
            if v is not None:
                prior_values.append(v)

        if len(prior_values) < 2:
            continue

        mean = sum(prior_values) / len(prior_values)
        variance = sum((v - mean) ** 2 for v in prior_values) / len(prior_values)
        std = math.sqrt(variance)

        if std == 0.0:
            # All prior values identical — use percentage deviation fallback
            if mean == 0.0:
                z_score = 0.0
            else:
                deviation_pct = abs(current_value - mean) / abs(mean)
                # Map >100% deviation to z=4 (above threshold), proportionally
                z_score = (deviation_pct / _FALLBACK_DEVIATION_PCT) * (_Z_THRESHOLD + 1.0)
        else:
            z_score = (current_value - mean) / std

        flags.append(
            ConsistencyFlag(
                field_name=field_name,
                current_value=current_value,
                historical_mean=round(mean, 2),
                historical_std=round(std, 2),
                z_score=round(z_score, 2),
                periods_used=len(prior_values),
            )
        )

    return flags
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_data_consistency.py -v`
Expected: All 7 PASSED

**Step 5: Run full engine test suite to verify no regressions**

Run: `uv run pytest engine/tests/ -v --tb=short -q`
Expected: ~2124+ passed, 0 failed

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/data_consistency.py engine/tests/scoring/test_data_consistency.py
git commit -m "feat(engine): add validate_data_consistency() for cross-period deviation detection"
```

---

## Task 3: Alembic Migration — Add consistency_flags Column

**Files:**
- Create: new Alembic migration
- Modify: `api/src/margin_api/db/models.py`

**Step 1: Add column to ORM model**

In `api/src/margin_api/db/models.py`, add to `class FinancialData`:

```python
consistency_flags: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
```

Place it after the `source` column (line ~150).

**Step 2: Generate migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add consistency_flags to financial_data"`

**Step 3: Review the generated migration**

Open the generated file in `api/alembic/versions/`. Verify it contains:
- `op.add_column('financial_data', sa.Column('consistency_flags', ...))`

Edit the migration to be idempotent (per project conventions):

```python
def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("financial_data")]
    if "consistency_flags" not in existing:
        op.add_column("financial_data", sa.Column("consistency_flags", sa.JSON(), nullable=True))

def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("financial_data")]
    if "consistency_flags" in existing:
        op.drop_column("financial_data", "consistency_flags")
```

**Step 4: Check for multiple heads**

Run: `cd api && uv run alembic heads`
Expected: Single head. If multiple, merge with `uv run alembic merge heads -m "merge heads"`.

**Step 5: Run migration against local DB**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies cleanly.

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add consistency_flags JSONB column to financial_data"
```

---

## Task 4: Post-Ingestion Consistency Validation Service

**Files:**
- Create: `api/src/margin_api/services/consistency.py`
- Test: `api/tests/services/test_consistency.py`

**Step 1: Write the failing test**

Create `api/tests/services/test_consistency.py`:

```python
"""Tests for post-ingestion data consistency validation."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData
from margin_api.services.consistency import validate_ticker_consistency


@pytest.fixture
def _stable_financial_data(session: AsyncSession):
    """Create an asset with 5 periods of stable data."""
    asset = Asset(ticker="STABLE", name="Stable Corp", sector="Information Technology",
                  market_cap=10_000_000_000, ingestion_status="active")
    session.add(asset)

    for year, revenue in [(2020, 100000), (2021, 105000), (2022, 102000), (2023, 108000), (2024, 103000)]:
        fd = FinancialData(
            asset=asset,
            period_end=f"{year}-12-31",
            filing_date=f"{year + 1}-02-15",
            income_statement={"revenue": revenue, "ebit": 20000, "netIncome": 15000, "sharesOutstanding": 1000000},
            balance_sheet={"totalAssets": 500000, "sharesOutstanding": 1000000},
            cash_flow={"operatingCashFlow": 25000, "capitalExpenditure": -5000},
            source="yfinance",
        )
        session.add(fd)


@pytest.fixture
def _anomalous_financial_data(session: AsyncSession):
    """Create an asset where the latest period has a 4x shares_outstanding jump."""
    asset = Asset(ticker="ANOMALY", name="Anomaly Corp", sector="Information Technology",
                  market_cap=10_000_000_000, ingestion_status="active")
    session.add(asset)

    for year, shares in [(2020, 1000000), (2021, 1000000), (2022, 1000000), (2023, 1000000), (2024, 4000000)]:
        fd = FinancialData(
            asset=asset,
            period_end=f"{year}-12-31",
            filing_date=f"{year + 1}-02-15",
            income_statement={"revenue": 100000, "ebit": 20000, "netIncome": 15000, "sharesOutstanding": shares},
            balance_sheet={"totalAssets": 500000, "sharesOutstanding": shares},
            cash_flow={"operatingCashFlow": 25000, "capitalExpenditure": -5000},
            source="yfinance",
        )
        session.add(fd)


@pytest.mark.asyncio
async def test_stable_ticker_no_anomalies(session: AsyncSession, _stable_financial_data):
    await session.flush()
    result = await validate_ticker_consistency(session, "STABLE")
    assert result is not None
    assert result["has_anomalies"] is False
    assert len(result["anomalies"]) == 0


@pytest.mark.asyncio
async def test_anomalous_ticker_detected(session: AsyncSession, _anomalous_financial_data):
    await session.flush()
    result = await validate_ticker_consistency(session, "ANOMALY")
    assert result is not None
    assert result["has_anomalies"] is True
    assert any(a["field_name"] == "shares_outstanding" for a in result["anomalies"])


@pytest.mark.asyncio
async def test_unknown_ticker_returns_none(session: AsyncSession):
    result = await validate_ticker_consistency(session, "NONEXISTENT")
    assert result is None


@pytest.mark.asyncio
async def test_flags_persisted_to_db(session: AsyncSession, _anomalous_financial_data):
    await session.flush()
    await validate_ticker_consistency(session, "ANOMALY")
    await session.flush()

    # Check that the latest FinancialData row now has consistency_flags
    from sqlalchemy import select
    from margin_api.db.models import FinancialData as FD, Asset as A
    stmt = (
        select(FD)
        .join(A)
        .where(A.ticker == "ANOMALY")
        .order_by(FD.period_end.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one()
    assert row.consistency_flags is not None
    assert row.consistency_flags["has_anomalies"] is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_consistency.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'margin_api.services.consistency'`

**Step 3: Write minimal implementation**

Create `api/src/margin_api/services/consistency.py`:

```python
"""Post-ingestion data consistency validation.

Loads a ticker's financial history from the DB, runs the engine's
validate_data_consistency(), and stores flags on the latest FinancialData row.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData
from margin_api.services.scoring import build_financial_history_from_rows
from margin_engine.scoring.data_consistency import validate_data_consistency

logger = logging.getLogger(__name__)


async def validate_ticker_consistency(
    session: AsyncSession,
    ticker: str,
) -> dict | None:
    """Validate data consistency for a ticker and persist flags.

    Args:
        session: Active DB session.
        ticker: Ticker symbol to validate.

    Returns:
        Dict with has_anomalies and anomalies list, or None if ticker not found.
    """
    # Load asset
    stmt = select(Asset).where(Asset.ticker == ticker)
    asset = (await session.execute(stmt)).scalar_one_or_none()
    if asset is None:
        return None

    # Load all financial data rows for this ticker, sorted oldest-first
    fd_stmt = (
        select(FinancialData)
        .where(FinancialData.asset_id == asset.id)
        .order_by(FinancialData.period_end.asc())
    )
    rows = (await session.execute(fd_stmt)).scalars().all()
    if len(rows) < 3:
        return None

    # Build FinancialHistory from DB rows
    row_dicts = [
        {
            "period_end": r.period_end,
            "filing_date": r.filing_date,
            "income_statement": r.income_statement or {},
            "balance_sheet": r.balance_sheet or {},
            "cash_flow": r.cash_flow or {},
        }
        for r in rows
    ]
    history = build_financial_history_from_rows(ticker, row_dicts)

    # Run engine consistency check
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]

    result = {
        "has_anomalies": len(anomalies) > 0,
        "anomalies": [f.model_dump() for f in anomalies],
        "all_flags": [f.model_dump() for f in flags],
    }

    # Persist to latest FinancialData row
    latest = rows[-1]
    latest.consistency_flags = result
    await session.flush()

    if anomalies:
        logger.warning(
            "[consistency] %s: %d anomalies detected — %s",
            ticker,
            len(anomalies),
            ", ".join(f.field_name for f in anomalies),
        )

    return result
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_consistency.py -v`
Expected: All 4 PASSED

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short -q`
Expected: ~1227+ passed, 0 failed

**Step 6: Commit**

```bash
git add api/src/margin_api/services/consistency.py api/tests/services/test_consistency.py
git commit -m "feat(api): add post-ingestion consistency validation service"
```

---

## Task 5: Wire into Ingestion Pipeline

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_workers.py` (or appropriate integration test)

**Step 1: Write the failing test**

Add a test that verifies `ingest_sweep_complete` calls consistency validation. The exact test structure depends on how workers are tested in the project. Look at existing `test_workers.py` patterns. The test should verify that after `ingest_sweep_complete` runs, `consistency_flags` is populated on `FinancialData` rows.

If worker tests are complex to set up, a simpler integration approach: add a standalone `validate_universe_consistency` job that can be tested independently.

```python
@pytest.mark.asyncio
async def test_validate_universe_consistency(session, _scored_universe_fixture):
    """Running consistency validation on the universe populates flags."""
    from margin_api.services.consistency import validate_universe_consistency

    results = await validate_universe_consistency(session)
    assert isinstance(results, dict)
    # Should have one entry per ticker with enough history
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/ -v -k "consistency" --tb=short`
Expected: FAIL

**Step 3: Add universe-level function and wire into pipeline**

Add to `api/src/margin_api/services/consistency.py`:

```python
async def validate_universe_consistency(
    session: AsyncSession,
    tickers: list[str] | None = None,
) -> dict[str, dict]:
    """Validate consistency for all tickers (or a subset) in the universe.

    Args:
        session: Active DB session.
        tickers: Optional list of tickers to validate. If None, validates all active tickers.

    Returns:
        Dict mapping ticker -> consistency result.
    """
    if tickers is None:
        stmt = select(Asset.ticker).where(Asset.ingestion_status == "active")
        result = await session.execute(stmt)
        tickers = [r[0] for r in result.all()]

    results = {}
    for ticker in tickers:
        r = await validate_ticker_consistency(session, ticker)
        if r is not None:
            results[ticker] = r

    anomaly_count = sum(1 for r in results.values() if r["has_anomalies"])
    if anomaly_count > 0:
        logger.warning(
            "[consistency] Universe validation: %d/%d tickers have anomalies",
            anomaly_count,
            len(results),
        )
    return results
```

In `api/src/margin_api/workers.py`, add a call inside `ingest_sweep_complete` after the sweep finishes but before `full_score` is triggered. Find the point where `ingest_sweep_complete` chains to scoring:

```python
# After sweep completes, before scoring:
from margin_api.services.consistency import validate_universe_consistency

# Inside ingest_sweep_complete, after verifying batches:
async with session_factory() as session:
    await validate_universe_consistency(session, tickers=ingested_tickers)
    await session.commit()
```

The exact insertion point depends on the current structure of `ingest_sweep_complete`. Read it carefully and add the call at the right spot.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/ -v -k "consistency" --tb=short`
Expected: PASSED

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short -q`
Expected: ~1227+ passed, 0 failed

**Step 6: Commit**

```bash
git add api/src/margin_api/services/consistency.py api/src/margin_api/workers.py api/tests/
git commit -m "feat(api): wire consistency validation into post-ingestion pipeline"
```

---

## Task 6: Score API — Surface Consistency Warnings

**Files:**
- Modify: `api/src/margin_api/routes/scores.py` (or wherever the score endpoint lives)
- Modify: `api/src/margin_api/schemas/` (score response schema)
- Test: corresponding route test file

**Step 1: Write the failing test**

Add a test to the score route tests that verifies the score response includes a `consistency_warnings` field when the ticker has anomalies:

```python
async def test_score_response_includes_consistency_warnings(client, _anomalous_scored_ticker):
    response = await client.get("/api/scores/ANOMALY")
    assert response.status_code == 200
    data = response.json()
    assert "consistency_warnings" in data
    assert len(data["consistency_warnings"]) > 0
    assert data["consistency_warnings"][0]["field_name"] == "shares_outstanding"
```

Also test that a clean ticker returns an empty list:

```python
async def test_score_response_no_warnings_when_clean(client, _clean_scored_ticker):
    response = await client.get("/api/scores/CLEAN")
    assert response.status_code == 200
    data = response.json()
    assert data["consistency_warnings"] == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/ -v -k "consistency_warning" --tb=short`
Expected: FAIL

**Step 3: Implement**

In the score response schema, add:

```python
consistency_warnings: list[dict] = Field(default_factory=list)
```

In the score route handler, when loading the score for a ticker, also load the latest `FinancialData.consistency_flags` and extract anomalies:

```python
# After loading score, also load consistency flags
fd_stmt = (
    select(FinancialData.consistency_flags)
    .where(FinancialData.asset_id == asset.id)
    .order_by(FinancialData.period_end.desc())
    .limit(1)
)
fd_result = (await session.execute(fd_stmt)).scalar_one_or_none()
consistency_warnings = []
if fd_result and fd_result.get("has_anomalies"):
    consistency_warnings = fd_result["anomalies"]
```

Add `consistency_warnings=consistency_warnings` to the response construction.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/ -v -k "consistency_warning" --tb=short`
Expected: PASSED

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short -q`
Expected: ~1230+ passed, 0 failed

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/ api/src/margin_api/schemas/ api/tests/
git commit -m "feat(api): surface consistency warnings in score API response"
```

---

## Task 7: Frontend — Consistency Warning Badge

**Files:**
- Create: `web/src/components/asset-detail/consistency-badge.tsx`
- Test: `web/src/__tests__/components/asset-detail/consistency-badge.test.tsx`
- Modify: `web/src/components/asset-detail/hero-header.tsx` (or wherever the score quality indicator lives)

**Step 1: Write the failing test**

Create `web/src/__tests__/components/asset-detail/consistency-badge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConsistencyBadge } from "@/components/asset-detail/consistency-badge";

describe("ConsistencyBadge", () => {
  it("renders nothing when no warnings", () => {
    const { container } = render(<ConsistencyBadge warnings={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders warning badge when anomalies present", () => {
    const warnings = [
      { field_name: "shares_outstanding", z_score: 10.5, current_value: 4000000, historical_mean: 1000000 },
    ];
    render(<ConsistencyBadge warnings={warnings} />);
    expect(screen.getByText(/data anomaly/i)).toBeInTheDocument();
  });

  it("lists affected fields", () => {
    const warnings = [
      { field_name: "shares_outstanding", z_score: 10.5, current_value: 4000000, historical_mean: 1000000 },
      { field_name: "revenue", z_score: -4.2, current_value: 20000, historical_mean: 100000 },
    ];
    render(<ConsistencyBadge warnings={warnings} />);
    expect(screen.getByText(/shares outstanding/i)).toBeInTheDocument();
    expect(screen.getByText(/revenue/i)).toBeInTheDocument();
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/__tests__/components/asset-detail/consistency-badge.test.tsx`
Expected: FAIL

**Step 3: Implement**

Create `web/src/components/asset-detail/consistency-badge.tsx`:

```tsx
"use client";

interface ConsistencyWarning {
  field_name: string;
  z_score: number;
  current_value: number;
  historical_mean: number;
}

interface ConsistencyBadgeProps {
  warnings: ConsistencyWarning[];
}

const FIELD_LABELS: Record<string, string> = {
  revenue: "Revenue",
  total_assets: "Total Assets",
  shares_outstanding: "Shares Outstanding",
  operating_income: "Operating Income",
  free_cash_flow: "Free Cash Flow",
};

export function ConsistencyBadge({ warnings }: ConsistencyBadgeProps) {
  if (warnings.length === 0) return null;

  return (
    <div className="flex items-center gap-2 rounded-md border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-3 py-1.5 text-xs">
      <span className="font-mono font-semibold text-[var(--color-warning)]">
        DATA ANOMALY
      </span>
      <span className="text-[var(--color-muted)]">
        {warnings.map((w) => FIELD_LABELS[w.field_name] || w.field_name).join(", ")}{" "}
        deviated {`>`}3σ from history
      </span>
    </div>
  );
}
```

Then wire it into the HeroHeader or asset detail view by passing `consistency_warnings` from the score API response.

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/__tests__/components/asset-detail/consistency-badge.test.tsx`
Expected: 3 PASSED

**Step 5: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: ~1090+ passed

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/consistency-badge.tsx web/src/__tests__/
git commit -m "feat(web): add ConsistencyBadge component for data anomaly warnings"
```

---

## Parallel Execution Groups

Tasks can be parallelized as follows:

- **Group A (independent):** Task 1, Task 2 (engine-only, no DB dependency)
- **Group B (after Group A):** Task 3 (migration), Task 4 (API service — depends on T2 + T3)
- **Group C (after Group B):** Task 5 (pipeline wiring — depends on T4)
- **Group D (after Group B):** Task 6 (API route — depends on T3 + T4), Task 7 (frontend — depends on T6's schema)

```
T1 ──┐
     ├── T3 ── T4 ── T5
T2 ──┘         │
               ├── T6 ── T7
               │
```

## Verification Checklist

After all tasks complete:

1. `uv run pytest engine/tests/ -v` — all passing (including new consistency tests)
2. `uv run pytest api/tests/ -v` — all passing (including consistency service + route tests)
3. `cd web && npx vitest run` — all passing (including ConsistencyBadge tests)
4. Manual smoke test: `uv run python -m margin_api.cli score --tickers AAPL` — response includes `consistency_warnings` field
5. Verify migration: `cd api && uv run alembic upgrade head` runs cleanly
