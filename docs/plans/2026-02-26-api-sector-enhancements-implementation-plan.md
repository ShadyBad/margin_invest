# API Sector Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire four data fields into the API that the frontend UX components already consume: `market_cap` on ScoreResponse, `sector_pass_rate` on FilterResultResponse, sector distribution stats (P10/P50/P90) per sub-factor, and a sector champion for the FailedComparison component.

**Architecture:** No new DB tables. Sector filter pass rates and sector distribution stats are precomputed during the V4 scoring pipeline and stored in V4Score.detail JSONB. Market cap comes from the existing Asset model. Sector champion is a runtime query only for eliminated tickers. The V4 pipeline currently does NOT populate V4Score.detail — Task 1 fixes that first, then subsequent tasks add sector data to it.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, pytest + pytest-asyncio + aiosqlite (in-memory SQLite tests)

**Design doc:** `docs/plans/2026-02-26-api-sector-enhancements-design.md`

---

### Task 1: Populate V4Score.detail JSONB in the V4 Scoring Pipeline

Currently `run_scoring_v4()` in `cli.py` creates V4Score objects without setting the `detail` field (lines 1498-1526). The V2 `run_scoring()` stores `composite.model_dump(mode="json")` at line 638. We need to build an equivalent detail blob for V4 so that downstream tasks can add sector data to it.

**Files:**
- Modify: `api/src/margin_api/cli.py:1486-1530`
- Test: `api/tests/test_v4_detail_blob.py` (new)

**Step 1: Write the failing test**

Create `api/tests/test_v4_detail_blob.py`:

```python
"""Tests for V4Score.detail JSONB population during scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score


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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_v4_detail_contains_filters_and_factors(session_factory):
    """V4Score.detail should contain filters_passed, quality, value, momentum."""
    async with session_factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )
        session.add(asset)
        await session.flush()

        # Simulate what run_scoring_v4 should produce
        detail = {
            "ticker": "AAPL",
            "composite_percentile": 85.0,
            "composite_raw_score": 0.78,
            "conviction_level": "high",
            "signal": "buy",
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [
                    {"name": "gross_profitability", "raw_value": 0.45, "percentile_rank": 80.0}
                ],
                "average_percentile": 80.0,
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 90.0,
            },
            "filters_passed": [
                {"name": "beneish_m_score", "passed": True, "value": -2.5, "threshold": -1.78}
            ],
            "data_coverage": 0.95,
        }
        v4 = V4Score(
            asset_id=asset.id,
            opportunity_type="deep_value",
            conviction="high",
            rules_conviction="high",
            style="value",
            timing_signal="buy",
            max_position_pct=5.0,
            regime="normal",
            composite_score=0.78,
            ml_override="none",
            detail=detail,
        )
        session.add(v4)
        await session.commit()

        # Verify detail was persisted
        from sqlalchemy import select
        result = await session.execute(select(V4Score).where(V4Score.asset_id == asset.id))
        saved = result.scalar_one()
        assert saved.detail is not None
        assert "filters_passed" in saved.detail
        assert "quality" in saved.detail
        assert saved.detail["quality"]["sub_scores"][0]["name"] == "gross_profitability"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_v4_detail_blob.py -v`
Expected: PASS (this test just verifies the model accepts detail — the real test is the integration)

**Step 3: Build the V4Score detail JSONB in `run_scoring_v4()`**

In `api/src/margin_api/cli.py`, after line 1487 (`results = score_universe_v4(...)`) and before the persist loop (line 1494), build a detail dict for each ticker from the raw scoring data. Add a helper function `_build_v4_detail()` and a dict `raw_results_by_ticker` populated during pass 1.

The key changes:
1. During the per-ticker loop (lines 1123-1326), also call `compute_raw_factor_scores()` and stash the `RawScoringResult` in a dict keyed by ticker.
2. After `rank_and_compute_composites()` runs (this already happens inside `score_universe_v4` for the v3 engine path, but the V4 pipeline uses a different path), capture the scored data.
3. When persisting (lines 1494-1529), build the detail JSONB from raw results and the V4ResultWithML, then set `score.detail = detail`.

The simplest approach: after the V4 pipeline runs and produces `results`, build the detail dict from data we already have (the `RawScoringResult` objects from `compute_raw_factor_scores` plus the V4ResultWithML fields).

Modify `run_scoring_v4()` to:
- After building `ticker_data_list` (line 1322), also build raw scoring results by calling `compute_raw_factor_scores()` for each ticker
- Run `rank_and_compute_composites()` on those raw results to get sector-ranked factor breakdowns
- Store the resulting `CompositeScore` objects in a dict by ticker
- When persisting V4Score, set `detail = composite.model_dump(mode="json")` (same as V2)

```python
# After building ticker_data_list (around line 1328):
# --- Build factor breakdowns for detail JSONB ---
from margin_api.services.scoring import compute_raw_factor_scores, rank_and_compute_composites

raw_scoring_results: list[RawScoringResult] = []
raw_by_ticker: dict[str, int] = {}  # ticker -> index in raw_scoring_results

for idx, td in enumerate(ticker_data_list):
    # We already have history, latest_period, profile, price_bars from the loop
    # Reconstruct price_bars_raw and earnings_raw from stored data
    # ... (use the data already gathered in the per-ticker loop)
    pass

# Then in the persist loop:
score.detail = composites_by_ticker[v4r.ticker].model_dump(mode="json")
```

**Important**: The per-ticker loop already builds `history`, `profile`, `bars`, `earnings_entries`. We need to stash these so they're available after the loop. Add parallel dicts:

```python
ticker_histories: dict[str, FinancialHistory] = {}
ticker_profiles: dict[str, AssetProfile] = {}
ticker_bars_raw: dict[str, list[dict]] = {}
ticker_earnings_raw: dict[str, list[dict]] = {}
```

Populate them inside the loop, then after the loop:

```python
from margin_api.services.scoring import compute_raw_factor_scores, rank_and_compute_composites, RawScoringResult

raw_results: list[RawScoringResult] = []
for td in ticker_data_list:
    t = td.ticker
    if t in ticker_profiles:
        raw = compute_raw_factor_scores(
            ticker=t,
            period=td.latest_period,
            profile=ticker_profiles[t],
            price_bars_raw=ticker_bars_raw.get(t, []),
            earnings_raw=ticker_earnings_raw.get(t, []),
            history=td.history,
        )
        raw_results.append(raw)

composites = rank_and_compute_composites(raw_results)
composites_by_ticker = {c.ticker: c for c in composites}
```

Then in the persist loop (line 1498):

```python
detail = composites_by_ticker[v4r.ticker].model_dump(mode="json") if v4r.ticker in composites_by_ticker else None
score = V4Score(
    ...existing fields...,
    detail=detail,
)
```

**Step 4: Run all tests**

Run: `uv run pytest api/tests/ -v -x`
Expected: All existing tests pass + new test passes

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py api/tests/test_v4_detail_blob.py
git commit -m "feat(api): populate V4Score.detail JSONB with factor breakdowns"
```

---

### Task 2: Add `market_cap` to ScoreResponse

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:76-138` (ScoreResponse)
- Modify: `api/src/margin_api/routes/scores.py:194-281` (_v4_score_response_from_row)
- Test: `api/tests/test_market_cap_response.py` (new)

**Step 1: Write the failing test**

Create `api/tests/test_market_cap_response.py`:

```python
"""Tests for market_cap on ScoreResponse."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail(ticker: str = "AAPL") -> dict:
    return {
        "ticker": ticker,
        "composite_percentile": 85.0,
        "composite_raw_score": 0.78,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 80.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 70.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 90.0},
        "filters_passed": [],
        "data_coverage": 0.95,
    }


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
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        v4 = V4Score(
            asset_id=aapl.id,
            opportunity_type="compounder",
            conviction="high",
            rules_conviction="high",
            style="blend",
            timing_signal="buy",
            max_position_pct=5.0,
            regime="normal",
            composite_score=0.78,
            ml_override="none",
            detail=_v4_detail("AAPL"),
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_score_response_includes_market_cap(client):
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert "market_cap" in data
    assert data["market_cap"] == 3500000000000.0


@pytest.mark.asyncio
async def test_market_cap_none_when_zero(client):
    """market_cap=0 in DB should still return as number."""
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    # At least field exists
    assert "market_cap" in resp.json()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_market_cap_response.py -v`
Expected: FAIL — `"market_cap" not in data` (field doesn't exist on ScoreResponse yet)

**Step 3: Add `market_cap` to ScoreResponse and populate it**

In `api/src/margin_api/schemas/scores.py`, add after line 135 (`institutional_accumulation`):

```python
    # Market cap from Asset table
    market_cap: float | None = None
```

In `api/src/margin_api/routes/scores.py`, in the `get_score()` function (around line 517 where sector is populated), add:

```python
    # Populate market_cap from Asset
    asset_market_cap = row.asset_market_cap if hasattr(row, "asset_market_cap") else None
    if asset_market_cap is not None:
        response.market_cap = float(asset_market_cap)
```

Also modify the V4 query (line 463-474) to include `Asset.market_cap`:

```python
    v4_query = (
        select(
            V4Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
            Asset.market_cap.label("asset_market_cap"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
```

Do the same for the V2 fallback query (line 497-506).

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_market_cap_response.py api/tests/test_scores.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/routes/scores.py api/tests/test_market_cap_response.py
git commit -m "feat(api): add market_cap field to ScoreResponse"
```

---

### Task 3: Precompute `sector_filter_pass_rates` in V4 Pipeline

After all tickers are scored, group filter results by (sector, filter_name) and compute pass rates. Store in V4Score.detail JSONB as `sector_filter_pass_rates`.

**Files:**
- Modify: `api/src/margin_api/cli.py:1486-1530` (run_scoring_v4 persist loop)
- Test: `api/tests/test_sector_pass_rates.py` (new)

**Depends on:** Task 1 (V4Score.detail must be populated)

**Step 1: Write the failing test**

Create `api/tests/test_sector_pass_rates.py`:

```python
"""Tests for sector_filter_pass_rates precomputation."""

from __future__ import annotations

import pytest

from margin_api.services.sector_stats import compute_sector_filter_pass_rates


@pytest.mark.parametrize(
    "filter_data, expected",
    [
        # Two tickers in same sector, both pass beneish
        (
            [
                ("Tech", [{"name": "beneish_m_score", "passed": True}]),
                ("Tech", [{"name": "beneish_m_score", "passed": True}]),
            ],
            {"Tech": {"beneish_m_score": 1.0}},
        ),
        # One pass, one fail -> 0.5
        (
            [
                ("Tech", [{"name": "beneish_m_score", "passed": True}]),
                ("Tech", [{"name": "beneish_m_score", "passed": False}]),
            ],
            {"Tech": {"beneish_m_score": 0.5}},
        ),
        # Different sectors don't mix
        (
            [
                ("Tech", [{"name": "z_score", "passed": True}]),
                ("Health", [{"name": "z_score", "passed": False}]),
            ],
            {"Tech": {"z_score": 1.0}, "Health": {"z_score": 0.0}},
        ),
        # Empty input
        ([], {}),
    ],
)
def test_compute_sector_filter_pass_rates(filter_data, expected):
    result = compute_sector_filter_pass_rates(filter_data)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_sector_pass_rates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.sector_stats'`

**Step 3: Implement `sector_stats.py` service**

Create `api/src/margin_api/services/sector_stats.py`:

```python
"""Sector statistics computation for V4 scoring pipeline."""

from __future__ import annotations

from collections import defaultdict


def compute_sector_filter_pass_rates(
    filter_data: list[tuple[str, list[dict]]],
) -> dict[str, dict[str, float]]:
    """Compute pass rate for each (sector, filter_name) pair.

    Args:
        filter_data: List of (sector, filters_passed_list) tuples.
            Each filters_passed_list is a list of dicts with 'name' and 'passed' keys.

    Returns:
        Nested dict: sector -> filter_name -> pass_rate (0.0-1.0)
    """
    # (sector, filter_name) -> [passed_bool, ...]
    counts: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for sector, filters in filter_data:
        for f in filters:
            key = (sector, f["name"])
            counts[key].append(bool(f.get("passed", False)))

    result: dict[str, dict[str, float]] = {}
    for (sector, filter_name), passed_list in counts.items():
        if sector not in result:
            result[sector] = {}
        result[sector][filter_name] = sum(passed_list) / len(passed_list)

    return result
```

**Step 4: Wire into `run_scoring_v4()` persist loop**

In `cli.py`, after running `rank_and_compute_composites()` and before the persist loop:

```python
# Compute sector filter pass rates
from margin_api.services.sector_stats import compute_sector_filter_pass_rates

filter_data_for_rates: list[tuple[str, list[dict]]] = []
for c in composites:
    ticker_sector = None
    for td in ticker_data_list:
        if td.ticker == c.ticker:
            ticker_sector = td.profile.sector.value
            break
    if ticker_sector:
        filters_list = [
            {"name": f.name, "passed": f.passed}
            for f in c.filters_passed
        ]
        filter_data_for_rates.append((ticker_sector, filters_list))

sector_pass_rates = compute_sector_filter_pass_rates(filter_data_for_rates)
```

Then in the persist loop, inject into detail:

```python
if detail and ticker_sector:
    detail["sector_filter_pass_rates"] = sector_pass_rates
```

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_sector_pass_rates.py api/tests/ -v -x`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/services/sector_stats.py api/tests/test_sector_pass_rates.py api/src/margin_api/cli.py
git commit -m "feat(api): precompute sector_filter_pass_rates in V4 pipeline"
```

---

### Task 4: Add `sector_pass_rate` to FilterResultResponse

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:13-22` (FilterResultResponse)
- Modify: `api/src/margin_api/routes/scores.py:194-281` (_v4_score_response_from_row)
- Test: `api/tests/test_filter_sector_pass_rate.py` (new)

**Depends on:** Task 3

**Step 1: Write the failing test**

Create `api/tests/test_filter_sector_pass_rate.py`:

```python
"""Tests for sector_pass_rate on FilterResultResponse."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail_with_pass_rates(ticker: str = "TSLA") -> dict:
    return {
        "ticker": ticker,
        "composite_percentile": 60.0,
        "composite_raw_score": 0.55,
        "conviction_level": "medium",
        "signal": "watch",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 60.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 55.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 65.0},
        "filters_passed": [
            {"name": "beneish_m_score", "passed": False, "value": -1.42, "threshold": -1.78},
            {"name": "z_score", "passed": True, "value": 3.5, "threshold": 1.81},
        ],
        "data_coverage": 0.90,
        "sector_filter_pass_rates": {
            "Consumer Discretionary": {
                "beneish_m_score": 0.68,
                "z_score": 0.92,
            }
        },
    }


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
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        tsla = Asset(
            ticker="TSLA",
            name="Tesla Inc.",
            sector="Consumer Discretionary",
            market_cap=Decimal("800000000000"),
        )
        session.add(tsla)
        await session.flush()

        v4 = V4Score(
            asset_id=tsla.id,
            opportunity_type="momentum",
            conviction="medium",
            rules_conviction="medium",
            style="growth",
            timing_signal="watch",
            max_position_pct=3.0,
            regime="normal",
            composite_score=0.55,
            ml_override="none",
            detail=_v4_detail_with_pass_rates("TSLA"),
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_filter_result_includes_sector_pass_rate(client):
    resp = await client.get("/api/v1/scores/TSLA")
    assert resp.status_code == 200
    data = resp.json()
    filters = data["filters_passed"]
    assert len(filters) == 2

    beneish = next(f for f in filters if f["name"] == "beneish_m_score")
    assert beneish["sector_pass_rate"] == pytest.approx(0.68)

    z_score = next(f for f in filters if f["name"] == "z_score")
    assert z_score["sector_pass_rate"] == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_sector_pass_rate_none_when_no_data(client):
    """If sector_filter_pass_rates is missing from detail, sector_pass_rate should be None."""
    # The default _score_detail helper doesn't include sector_filter_pass_rates
    # so for tickers without it, the field should default to None
    pass  # Covered by existing tests that don't have the data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_filter_sector_pass_rate.py -v`
Expected: FAIL — `sector_pass_rate` not in filter response

**Step 3: Add `sector_pass_rate` to FilterResultResponse**

In `api/src/margin_api/schemas/scores.py`, add to FilterResultResponse (after line 22):

```python
    sector_pass_rate: float | None = None
```

In `api/src/margin_api/routes/scores.py`, in `_v4_score_response_from_row()`, after the filter verdict loop (line 233), add sector pass rate injection:

```python
    # Inject sector_pass_rate into filter results
    sector = row.asset_sector if hasattr(row, "asset_sector") else None
    pass_rates = detail.get("sector_filter_pass_rates", {})
    sector_rates = pass_rates.get(sector, {}) if sector else {}
    for f in detail.get("filters_passed", []):
        f.setdefault("sector_pass_rate", sector_rates.get(f.get("name")))
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_filter_sector_pass_rate.py api/tests/test_scores.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/routes/scores.py api/tests/test_filter_sector_pass_rate.py
git commit -m "feat(api): add sector_pass_rate to FilterResultResponse"
```

---

### Task 5: Precompute Sector Distribution (P10/P50/P90) per Sub-Factor

Capture sector distribution stats during `rank_and_compute_composites()` in `scoring.py`. Store in the detail JSONB.

**Files:**
- Modify: `api/src/margin_api/services/scoring.py:288-392` (rank_and_compute_composites)
- Modify: `api/src/margin_api/services/sector_stats.py`
- Test: `api/tests/test_sector_distribution.py` (new)

**Depends on:** Task 1

**Step 1: Write the failing test**

Create `api/tests/test_sector_distribution.py`:

```python
"""Tests for sector distribution (P10/P50/P90) computation."""

from __future__ import annotations

import pytest

from margin_api.services.sector_stats import compute_sector_distribution


@pytest.mark.parametrize(
    "raw_values, expected_p10, expected_p50, expected_p90",
    [
        # 10 values: sorted = [1..10], P10=1, P50=5.5, P90=9
        (list(range(1, 11)), 1.9, 5.5, 9.1),
        # 5 values
        ([10, 20, 30, 40, 50], 14.0, 30.0, 46.0),
        # Single value — all percentiles equal
        ([42.0], 42.0, 42.0, 42.0),
    ],
)
def test_compute_sector_distribution(raw_values, expected_p10, expected_p50, expected_p90):
    result = compute_sector_distribution(raw_values)
    assert result["p10"] == pytest.approx(expected_p10, abs=0.5)
    assert result["p50"] == pytest.approx(expected_p50, abs=0.5)
    assert result["p90"] == pytest.approx(expected_p90, abs=0.5)
    assert result["count"] == len(raw_values)


def test_compute_sector_distribution_empty():
    result = compute_sector_distribution([])
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_sector_distribution.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_sector_distribution'`

**Step 3: Implement `compute_sector_distribution`**

In `api/src/margin_api/services/sector_stats.py`, add:

```python
import statistics


def compute_sector_distribution(
    raw_values: list[float],
) -> dict[str, float] | None:
    """Compute P10, P50 (median), P90 and count for a list of raw values.

    Args:
        raw_values: Raw sub-factor values for all stocks in a sector.

    Returns:
        Dict with p10, p50, p90, count. None if empty.
    """
    if not raw_values:
        return None

    sorted_vals = sorted(raw_values)
    n = len(sorted_vals)

    if n == 1:
        v = sorted_vals[0]
        return {"p10": v, "p50": v, "p90": v, "count": 1}

    # Use linear interpolation for percentiles
    def _percentile(data: list[float], pct: float) -> float:
        k = (len(data) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[f]
        return data[f] + (k - f) * (data[c] - data[f])

    return {
        "p10": round(_percentile(sorted_vals, 10), 4),
        "p50": round(_percentile(sorted_vals, 50), 4),
        "p90": round(_percentile(sorted_vals, 90), 4),
        "count": n,
    }
```

**Step 4: Wire into `rank_and_compute_composites()`**

In `api/src/margin_api/services/scoring.py`, modify `rank_and_compute_composites()` to return sector distribution alongside composites. Add a new function or modify the return type:

Option: Add a separate function `compute_sector_distributions()` that takes raw_results and returns the distributions dict. This avoids modifying the existing function signature (which is used elsewhere).

```python
def compute_sector_distributions(
    raw_results: list[RawScoringResult],
) -> dict[str, dict[str, float]]:
    """Compute P10/P50/P90 per (sector, sub-factor) from raw scoring results.

    Returns:
        Dict mapping sub-factor name to {p10, p50, p90, count}.
        Keyed by factor name (not sector+factor) since each ticker
        stores their own sector's distribution.
    """
    from margin_api.services.sector_stats import compute_sector_distribution

    # Group raw values by (sector, factor_name)
    sector_values: dict[tuple[str, str], list[float]] = defaultdict(list)

    for result in raw_results:
        for list_attr in ("quality_scores", "value_scores", "momentum_scores"):
            for score in getattr(result, list_attr):
                key = (result.sector, score.name)
                sector_values[key].append(score.raw_value)

    # Compute distribution for each group
    distributions: dict[str, dict[str, dict]] = defaultdict(dict)
    for (sector, factor_name), values in sector_values.items():
        dist = compute_sector_distribution(values)
        if dist is not None:
            distributions[sector][factor_name] = dist

    return dict(distributions)
```

Then in `cli.py`, after `rank_and_compute_composites()` but before persist:

```python
from margin_api.services.scoring import compute_sector_distributions

sector_distributions = compute_sector_distributions(raw_results)
```

In the persist loop, inject into detail per-ticker (using that ticker's sector):

```python
if detail and ticker_sector:
    detail["sector_distribution"] = sector_distributions.get(ticker_sector, {})
```

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_sector_distribution.py api/tests/ -v -x`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/services/sector_stats.py api/src/margin_api/services/scoring.py api/tests/test_sector_distribution.py api/src/margin_api/cli.py
git commit -m "feat(api): precompute sector distribution (P10/P50/P90) per sub-factor"
```

---

### Task 6: Add Sector Distribution Fields to FactorScoreResponse

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:25-31` (FactorScoreResponse)
- Modify: `api/src/margin_api/routes/scores.py:194-281` (_v4_score_response_from_row)
- Test: `api/tests/test_factor_sector_distribution.py` (new)

**Depends on:** Task 5

**Step 1: Write the failing test**

Create `api/tests/test_factor_sector_distribution.py`:

```python
"""Tests for sector distribution fields on FactorScoreResponse."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail_with_distribution() -> dict:
    return {
        "ticker": "AAPL",
        "composite_percentile": 90.0,
        "composite_raw_score": 0.85,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "gross_profitability", "raw_value": 0.45, "percentile_rank": 88.0},
                {"name": "roic_wacc_spread", "raw_value": 0.12, "percentile_rank": 75.0},
            ],
            "average_percentile": 81.5,
        },
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 85.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 92.0},
        "filters_passed": [],
        "data_coverage": 1.0,
        "sector_distribution": {
            "gross_profitability": {"p10": 0.15, "p50": 0.30, "p90": 0.50, "count": 120},
            "roic_wacc_spread": {"p10": -0.05, "p50": 0.05, "p90": 0.15, "count": 120},
        },
    }


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
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()
        v4 = V4Score(
            asset_id=aapl.id,
            opportunity_type="compounder",
            conviction="high",
            rules_conviction="high",
            style="blend",
            timing_signal="buy",
            max_position_pct=5.0,
            regime="normal",
            composite_score=0.85,
            ml_override="none",
            detail=_v4_detail_with_distribution(),
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_factor_scores_include_sector_distribution(client):
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()

    quality_subs = data["quality"]["sub_scores"]
    gp = next(s for s in quality_subs if s["name"] == "gross_profitability")
    assert gp["sector_p10"] == pytest.approx(0.15)
    assert gp["sector_p50"] == pytest.approx(0.30)
    assert gp["sector_p90"] == pytest.approx(0.50)
    assert gp["sector_count"] == 120

    roic = next(s for s in quality_subs if s["name"] == "roic_wacc_spread")
    assert roic["sector_p10"] == pytest.approx(-0.05)
    assert roic["sector_p50"] == pytest.approx(0.05)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_factor_sector_distribution.py -v`
Expected: FAIL — `sector_p10` not in sub_score dict

**Step 3: Add fields to FactorScoreResponse and populate**

In `api/src/margin_api/schemas/scores.py`, modify FactorScoreResponse (line 25-31):

```python
class FactorScoreResponse(BaseModel):
    """API representation of a single factor score."""

    name: str
    raw_value: float
    percentile_rank: float
    detail: str = ""
    sector_p10: float | None = None
    sector_p50: float | None = None
    sector_p90: float | None = None
    sector_count: int | None = None
```

In `api/src/margin_api/routes/scores.py`, in `_v4_score_response_from_row()`, after the factor average_percentile loop (line 240), add:

```python
    # Inject sector distribution into sub-factor scores
    sector_dist = detail.get("sector_distribution", {})
    for factor_key in ("quality", "value", "momentum"):
        factor = detail.get(factor_key)
        if factor and isinstance(factor, dict):
            for sub in factor.get("sub_scores", []):
                dist = sector_dist.get(sub.get("name"), {})
                if dist:
                    sub["sector_p10"] = dist.get("p10")
                    sub["sector_p50"] = dist.get("p50")
                    sub["sector_p90"] = dist.get("p90")
                    sub["sector_count"] = dist.get("count")
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_factor_sector_distribution.py api/tests/test_scores.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/routes/scores.py api/tests/test_factor_sector_distribution.py
git commit -m "feat(api): add sector P10/P50/P90/count to FactorScoreResponse"
```

---

### Task 7: Add Sector Champion to ScoreResponse (Runtime Query)

For eliminated tickers only, find the highest-scoring passing ticker in the same sector.

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py` (add SectorChampionResponse)
- Modify: `api/src/margin_api/routes/scores.py:451-565` (get_score endpoint)
- Test: `api/tests/test_sector_champion.py` (new)

**Step 1: Write the failing test**

Create `api/tests/test_sector_champion.py`:

```python
"""Tests for sector champion on ScoreResponse (eliminated tickers only)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _detail(ticker: str, filters_passed: list[dict], percentile: float = 80.0) -> dict:
    return {
        "ticker": ticker,
        "composite_percentile": percentile,
        "composite_raw_score": percentile / 100.0,
        "conviction_level": "high" if percentile > 70 else "none",
        "signal": "buy" if percentile > 70 else "no_action",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": percentile},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": percentile},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": percentile},
        "filters_passed": filters_passed,
        "data_coverage": 1.0,
    }


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
async def seeded_session(async_engine):
    """Seed: TSLA eliminated (2 failed filters), AAPL passing champion in same sector."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        tsla = Asset(
            ticker="TSLA", name="Tesla Inc.",
            sector="Consumer Discretionary", market_cap=Decimal("800000000000"),
        )
        aapl = Asset(
            ticker="AAPL", name="Apple Inc.",
            sector="Consumer Discretionary", market_cap=Decimal("3500000000000"),
        )
        msft = Asset(
            ticker="MSFT", name="Microsoft Corp",
            sector="Information Technology", market_cap=Decimal("3000000000000"),
        )
        session.add_all([tsla, aapl, msft])
        await session.flush()

        # TSLA: eliminated (2 failed filters)
        tsla_filters = [
            {"name": "beneish_m_score", "passed": False, "value": -1.42, "threshold": -1.78},
            {"name": "sloan_accrual_ratio", "passed": False, "value": 0.12, "threshold": 0.10},
            {"name": "z_score", "passed": True, "value": 3.5, "threshold": 1.81},
        ]
        tsla_v4 = V4Score(
            asset_id=tsla.id,
            opportunity_type="momentum", conviction="none", rules_conviction="none",
            style="growth", timing_signal="no_action", max_position_pct=0.0,
            regime="normal", composite_score=0.55, ml_override="none",
            detail=_detail("TSLA", tsla_filters, 55.0),
        )

        # AAPL: passing champion in same sector
        aapl_filters = [
            {"name": "beneish_m_score", "passed": True, "value": -2.91, "threshold": -1.78},
            {"name": "sloan_accrual_ratio", "passed": True, "value": -0.04, "threshold": 0.10},
            {"name": "z_score", "passed": True, "value": 5.1, "threshold": 1.81},
        ]
        aapl_v4 = V4Score(
            asset_id=aapl.id,
            opportunity_type="compounder", conviction="high", rules_conviction="high",
            style="blend", timing_signal="buy", max_position_pct=5.0,
            regime="normal", composite_score=0.88, ml_override="none",
            detail=_detail("AAPL", aapl_filters, 92.0),
        )

        # MSFT: passing but different sector (should not be champion for TSLA)
        msft_filters = [
            {"name": "beneish_m_score", "passed": True, "value": -3.1, "threshold": -1.78},
            {"name": "sloan_accrual_ratio", "passed": True, "value": -0.02, "threshold": 0.10},
            {"name": "z_score", "passed": True, "value": 6.0, "threshold": 1.81},
        ]
        msft_v4 = V4Score(
            asset_id=msft.id,
            opportunity_type="compounder", conviction="exceptional", rules_conviction="exceptional",
            style="blend", timing_signal="buy", max_position_pct=5.0,
            regime="normal", composite_score=0.95, ml_override="none",
            detail=_detail("MSFT", msft_filters, 98.0),
        )

        session.add_all([tsla_v4, aapl_v4, msft_v4])
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_eliminated_ticker_gets_sector_champion(client):
    resp = await client.get("/api/v1/scores/TSLA")
    assert resp.status_code == 200
    data = resp.json()

    champion = data.get("sector_champion")
    assert champion is not None
    assert champion["ticker"] == "AAPL"
    assert "filter_values" in champion
    assert "beneish_m_score" in champion["filter_values"]
    assert champion["filter_values"]["beneish_m_score"] == pytest.approx(-2.91)


@pytest.mark.asyncio
async def test_passing_ticker_has_no_sector_champion(client):
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("sector_champion") is None


@pytest.mark.asyncio
async def test_different_sector_not_used_as_champion(client):
    """MSFT (Tech) should not be TSLA's champion (Consumer Discretionary)."""
    resp = await client.get("/api/v1/scores/TSLA")
    data = resp.json()
    champion = data.get("sector_champion")
    assert champion is not None
    assert champion["ticker"] != "MSFT"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_sector_champion.py -v`
Expected: FAIL — `sector_champion` not in response

**Step 3: Add SectorChampionResponse and wire into ScoreResponse**

In `api/src/margin_api/schemas/scores.py`, add before ScoreResponse:

```python
class SectorChampionResponse(BaseModel):
    """Sector champion data for FailedComparison component."""

    ticker: str
    filter_values: dict[str, float | None]
```

Add to ScoreResponse (after `institutional_accumulation`):

```python
    # Sector champion (only populated for eliminated tickers)
    sector_champion: SectorChampionResponse | None = None
```

In `api/src/margin_api/routes/scores.py`, in `get_score()`, after the sector survivor counting block (around line 565), add the champion query:

```python
    # Sector champion: only for eliminated tickers
    from margin_api.schemas.scores import SectorChampionResponse

    filters = response.filters_passed or []
    has_failed_filters = any(not f.passed for f in filters)

    if has_failed_filters and sector:
        # Find highest-scoring passing ticker in same sector
        champion_q = (
            select(V4Score, Asset.ticker.label("champ_ticker"))
            .join(Asset, V4Score.asset_id == Asset.id)
            .where(
                Asset.sector == sector,
                Asset.ticker != ticker,
            )
            .order_by(V4Score.composite_score.desc())
            .limit(10)  # Check top 10 to find one that passed all filters
        )
        champ_result = await db.execute(champion_q)
        champ_rows = champ_result.all()

        for champ_row in champ_rows:
            champ_v4 = champ_row[0]
            champ_ticker = champ_row.champ_ticker
            champ_detail = champ_v4.detail or {}
            champ_filters = champ_detail.get("filters_passed", [])
            if champ_filters and all(f.get("passed") for f in champ_filters):
                # Extract filter values as dict
                filter_values = {
                    f["name"]: f.get("value")
                    for f in champ_filters
                }
                response.sector_champion = SectorChampionResponse(
                    ticker=champ_ticker,
                    filter_values=filter_values,
                )
                break
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_sector_champion.py api/tests/test_scores.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/routes/scores.py api/tests/test_sector_champion.py
git commit -m "feat(api): add sector champion to ScoreResponse for eliminated tickers"
```

---

### Task 8: Integration Test — Full Pipeline End-to-End

Verify that all four enhancements work together on a realistic scenario.

**Files:**
- Test: `api/tests/test_sector_enhancements_integration.py` (new)

**Step 1: Write the integration test**

Create `api/tests/test_sector_enhancements_integration.py`:

```python
"""Integration test: all four sector enhancements together."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _full_detail(ticker: str, filters: list[dict], percentile: float, sector: str) -> dict:
    return {
        "ticker": ticker,
        "composite_percentile": percentile,
        "composite_raw_score": percentile / 100.0,
        "conviction_level": "high" if percentile > 70 else "none",
        "signal": "buy" if percentile > 70 else "no_action",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "gross_profitability", "raw_value": 0.45, "percentile_rank": 88.0},
            ],
            "average_percentile": 88.0,
        },
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": percentile},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": percentile},
        "filters_passed": filters,
        "data_coverage": 1.0,
        "sector_filter_pass_rates": {
            sector: {"beneish_m_score": 0.72, "z_score": 0.91},
        },
        "sector_distribution": {
            "gross_profitability": {"p10": 0.12, "p50": 0.28, "p90": 0.48, "count": 85},
        },
    }


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
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        sector = "Consumer Discretionary"
        tsla = Asset(ticker="TSLA", name="Tesla", sector=sector, market_cap=Decimal("800000000000"))
        amzn = Asset(ticker="AMZN", name="Amazon", sector=sector, market_cap=Decimal("2000000000000"))
        session.add_all([tsla, amzn])
        await session.flush()

        tsla_filters = [
            {"name": "beneish_m_score", "passed": False, "value": -1.42, "threshold": -1.78},
            {"name": "z_score", "passed": True, "value": 3.5, "threshold": 1.81},
        ]
        amzn_filters = [
            {"name": "beneish_m_score", "passed": True, "value": -3.1, "threshold": -1.78},
            {"name": "z_score", "passed": True, "value": 4.8, "threshold": 1.81},
        ]

        session.add(V4Score(
            asset_id=tsla.id, opportunity_type="momentum", conviction="none",
            rules_conviction="none", style="growth", timing_signal="no_action",
            max_position_pct=0.0, regime="normal", composite_score=0.55, ml_override="none",
            detail=_full_detail("TSLA", tsla_filters, 55.0, sector),
        ))
        session.add(V4Score(
            asset_id=amzn.id, opportunity_type="compounder", conviction="high",
            rules_conviction="high", style="blend", timing_signal="buy",
            max_position_pct=5.0, regime="normal", composite_score=0.88, ml_override="none",
            detail=_full_detail("AMZN", amzn_filters, 88.0, sector),
        ))
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_all_enhancements_on_eliminated_ticker(client):
    """TSLA (eliminated) should have all 4 enhancements populated."""
    resp = await client.get("/api/v1/scores/TSLA")
    assert resp.status_code == 200
    data = resp.json()

    # Enhancement 1: market_cap
    assert data["market_cap"] == 800000000000.0

    # Enhancement 2: sector_pass_rate on filters
    beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
    assert beneish["sector_pass_rate"] == pytest.approx(0.72)

    # Enhancement 3: sector distribution on sub-factors
    gp = data["quality"]["sub_scores"][0]
    assert gp["sector_p10"] == pytest.approx(0.12)
    assert gp["sector_p50"] == pytest.approx(0.28)
    assert gp["sector_p90"] == pytest.approx(0.48)
    assert gp["sector_count"] == 85

    # Enhancement 4: sector champion
    champion = data["sector_champion"]
    assert champion is not None
    assert champion["ticker"] == "AMZN"


@pytest.mark.asyncio
async def test_all_enhancements_on_passing_ticker(client):
    """AMZN (passing) should have enhancements 1-3 but NOT champion."""
    resp = await client.get("/api/v1/scores/AMZN")
    assert resp.status_code == 200
    data = resp.json()

    # Enhancement 1: market_cap
    assert data["market_cap"] == 2000000000000.0

    # Enhancement 2: sector_pass_rate on filters
    beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
    assert beneish["sector_pass_rate"] == pytest.approx(0.72)

    # Enhancement 3: sector distribution
    gp = data["quality"]["sub_scores"][0]
    assert gp["sector_p10"] is not None

    # Enhancement 4: no champion for passing ticker
    assert data.get("sector_champion") is None
```

**Step 2: Run tests**

Run: `uv run pytest api/tests/test_sector_enhancements_integration.py -v`
Expected: All PASS

**Step 3: Run full test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All ~1091+ tests pass

**Step 4: Commit**

```bash
git add api/tests/test_sector_enhancements_integration.py
git commit -m "test(api): add integration test for all sector enhancements"
```

---

## Task Dependency Graph

```
Task 1 (V4Score.detail JSONB) ──┬── Task 2 (market_cap)
                                 ├── Task 3 (sector_filter_pass_rates) ── Task 4 (sector_pass_rate on FilterResult)
                                 ├── Task 5 (sector_distribution P10/P50/P90) ── Task 6 (FactorScoreResponse fields)
                                 └── Task 7 (sector champion)
                                                                            All ──→ Task 8 (integration test)
```

Tasks 2, 3, 5, and 7 can run in parallel after Task 1. Tasks 4 and 6 depend on 3 and 5 respectively. Task 8 depends on all others.
