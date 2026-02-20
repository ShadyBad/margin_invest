# Card Data Integrity Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure dashboard cards faithfully display values from the authoritative Score DB record, with an audit endpoint to verify correctness.

**Architecture:** Audit-first approach — build a diagnostic endpoint that compares card values vs DB values vs engine-derived values, then fix confirmed failure modes (JS falsy fallback, missing traceability), then add regression tests.

**Tech Stack:** Python/FastAPI (API), TypeScript/Next.js (frontend), SQLAlchemy (ORM), pytest + httpx (tests)

---

### Task 1: Add `score_id` to PickSummary schema

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py:10-41`
- Test: `api/tests/test_dashboard.py`

**Step 1: Write the failing test**

Add this test to `api/tests/test_dashboard.py` inside `TestDashboardPicks`:

```python
async def test_pick_includes_score_id(self, client):
    """Each pick must include score_id for traceability."""
    response = await client.get("/api/v1/dashboard")
    data = response.json()
    for pick in data["picks"]:
        assert "score_id" in pick
        assert isinstance(pick["score_id"], int)
        assert pick["score_id"] > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardPicks::test_pick_includes_score_id -v`
Expected: FAIL — `score_id` not in response

**Step 3: Add `score_id` to PickSummary schema**

In `api/src/margin_api/schemas/dashboard.py`, add to `PickSummary`:

```python
class PickSummary(BaseModel):
    """Summary of a high-conviction pick for the dashboard."""

    score_id: int  # DB primary key for traceability
    ticker: str
    # ... rest unchanged
```

**Step 4: Populate `score_id` in `_pick_summary_from_row()`**

In `api/src/margin_api/routes/dashboard.py:45`, add `score_id=s.id` to the PickSummary constructor:

```python
return PickSummary(
    score_id=s.id,
    ticker=row.ticker,
    # ... rest unchanged
)
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardPicks::test_pick_includes_score_id -v`
Expected: PASS

**Step 6: Run full dashboard test suite to check for regressions**

Run: `uv run pytest api/tests/test_dashboard.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/src/margin_api/routes/dashboard.py api/tests/test_dashboard.py
git commit -m "feat(api): add score_id to PickSummary for traceability"
```

---

### Task 2: Build audit endpoint

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py`
- Create: `api/tests/test_dashboard_audit.py`

**Step 1: Write the failing test**

Create `api/tests/test_dashboard_audit.py`:

```python
"""Tests for dashboard audit endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
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
async def audit_session(async_engine):
    """Seed DB with a score where conviction_level matches raw_score thresholds."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL", name="Apple Inc.",
            sector="Information Technology", market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        score = Score(
            asset_id=aapl.id,
            composite_percentile=99.5,
            composite_raw_score=82.0,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=98.0,
            value_percentile=95.0,
            momentum_percentile=97.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def mismatched_session(async_engine):
    """Seed DB with a score where conviction_level DOES NOT match raw_score thresholds.

    raw_score=60.0 should produce conviction_level='none' (< 65 threshold),
    but we store 'high' to simulate a mismatch.
    """
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL", name="Apple Inc.",
            sector="Information Technology", market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        score = Score(
            asset_id=aapl.id,
            composite_percentile=90.0,
            composite_raw_score=60.0,
            conviction_level="high",  # WRONG: 60.0 < 65 threshold → should be "none"
            signal="buy",             # WRONG: none conviction → should be "no_action"
            quality_percentile=80.0,
            value_percentile=85.0,
            momentum_percentile=75.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def audit_client(audit_session):
    app = create_app()

    async def override_get_db():
        async with audit_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def mismatched_client(mismatched_session):
    app = create_app()

    async def override_get_db():
        async with mismatched_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestDashboardAudit:
    async def test_audit_returns_entries(self, audit_client):
        """Audit endpoint returns one entry per card with db_values and derived_values."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["ticker"] == "AAPL"
        assert "db_values" in entry
        assert "derived_values" in entry
        assert "mismatches" in entry

    async def test_audit_no_mismatches_when_consistent(self, audit_client):
        """When DB conviction matches raw_score thresholds, no mismatches."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        entry = data["entries"][0]
        assert entry["mismatches"] == []

    async def test_audit_detects_conviction_mismatch(self, mismatched_client):
        """When stored conviction_level doesn't match raw_score thresholds, flag it."""
        response = await mismatched_client.get("/api/v1/dashboard/audit")
        data = response.json()
        entry = data["entries"][0]
        assert len(entry["mismatches"]) > 0
        mismatch_fields = [m["field"] for m in entry["mismatches"]]
        assert "conviction_level" in mismatch_fields

    async def test_audit_db_values_match_raw_columns(self, audit_client):
        """db_values should contain raw DB column values."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        db = data["entries"][0]["db_values"]
        assert db["composite_raw_score"] == 82.0
        assert db["conviction_level"] == "exceptional"
        assert db["signal"] == "buy"
        assert db["quality_percentile"] == 98.0

    async def test_audit_derived_values_use_engine_thresholds(self, audit_client):
        """derived_values should recompute conviction from raw_score using engine thresholds."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        derived = data["entries"][0]["derived_values"]
        # raw_score=82.0 >= 79 → exceptional
        assert derived["conviction_level"] == "exceptional"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_dashboard_audit.py -v`
Expected: FAIL — 404 on `/api/v1/dashboard/audit`

**Step 3: Implement the audit endpoint**

Add to `api/src/margin_api/routes/dashboard.py` (before the existing `get_dashboard` route):

```python
def _derive_conviction_level(raw_score: float) -> str:
    """Re-derive conviction_level from raw_score using engine thresholds."""
    if raw_score >= 79.0:
        return "exceptional"
    if raw_score >= 72.0:
        return "high"
    if raw_score >= 65.0:
        return "medium"
    return "none"


def _derive_signal(conviction_level: str, actual_price=None, buy_price=None, sell_price=None) -> str:
    """Re-derive signal from conviction_level and price targets."""
    if conviction_level == "medium":
        return "watch"
    if conviction_level == "none":
        return "no_action"
    if actual_price is not None and sell_price is not None and buy_price is not None:
        if actual_price > sell_price * 1.15:
            return "urgent_sell"
        if actual_price > sell_price:
            return "sell"
        if actual_price <= buy_price:
            return "buy"
        return "hold"
    return "buy"


@router.get("/dashboard/audit")
async def audit_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Audit dashboard card values against DB and engine-derived values.

    Returns per-card comparison: DB columns vs engine-derived conviction/signal,
    with a list of mismatches.
    """
    latest = _latest_score_subquery()
    base = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
        .order_by(Score.composite_raw_score.desc())
    )

    result = await db.execute(base)
    entries = []
    for row in result.all():
        s = row.Score

        db_values = {
            "score_id": s.id,
            "composite_raw_score": s.composite_raw_score,
            "composite_percentile": s.composite_percentile,
            "conviction_level": s.conviction_level,
            "signal": s.signal,
            "quality_percentile": s.quality_percentile,
            "value_percentile": s.value_percentile,
            "momentum_percentile": s.momentum_percentile,
            "actual_price": getattr(s, "actual_price", None),
            "buy_price": getattr(s, "buy_price", None),
            "sell_price": getattr(s, "sell_price", None),
            "margin_invest_value": getattr(s, "margin_invest_value", None),
            "scored_at": s.scored_at.isoformat() if s.scored_at else None,
        }

        derived_conviction = _derive_conviction_level(s.composite_raw_score)
        derived_signal = _derive_signal(
            derived_conviction,
            actual_price=getattr(s, "actual_price", None),
            buy_price=getattr(s, "buy_price", None),
            sell_price=getattr(s, "sell_price", None),
        )

        derived_values = {
            "conviction_level": derived_conviction,
            "signal": derived_signal,
        }

        mismatches = []
        if s.conviction_level != derived_conviction:
            mismatches.append({
                "field": "conviction_level",
                "db_value": s.conviction_level,
                "derived_value": derived_conviction,
            })
        if s.signal != derived_signal:
            mismatches.append({
                "field": "signal",
                "db_value": s.signal,
                "derived_value": derived_signal,
            })

        entries.append({
            "ticker": row.ticker,
            "name": row.asset_name,
            "db_values": db_values,
            "derived_values": derived_values,
            "mismatches": mismatches,
        })

    return {"entries": entries, "total": len(entries)}
```

**Important:** The audit route MUST be registered BEFORE the `/dashboard` route in the same router, because `/dashboard/audit` needs to match before the generic `/dashboard` pattern. In this codebase both use `@router.get(...)` with the `prefix="/api/v1"` — so `"/dashboard/audit"` must appear above `"/dashboard"` in the file.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_dashboard_audit.py -v`
Expected: All 5 tests PASS

**Step 5: Run full API test suite to check for regressions**

Run: `uv run pytest api/tests/ -v`
Expected: All tests PASS (no regressions)

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/dashboard.py api/tests/test_dashboard_audit.py
git commit -m "feat(api): add /dashboard/audit endpoint for data-integrity verification"
```

---

### Task 3: Fix JS falsy fallback on score display

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx:188`

**Step 1: Identify the line**

In `web/src/components/dashboard/stock-card.tsx` line 188:

```tsx
// BEFORE (broken — treats score=0 as falsy, falls through to percentile):
value={pick.score || pick.composite_percentile}
```

**Step 2: Fix with nullish coalescing**

```tsx
// AFTER (only falls through on null/undefined, not on 0):
value={pick.score ?? pick.composite_percentile}
```

**Step 3: Search for other instances of the same pattern**

Search all `.tsx` and `.ts` files for `pick.score ||` or `\.score ||` — fix any other instances with `??`.

Check `web/src/app/dashboard/page.tsx` which also computes portfolio conviction:
```tsx
// In page.tsx, look for: pick.score || pick.composite_percentile
// Fix the same way: pick.score ?? pick.composite_percentile
```

**Step 4: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/app/dashboard/page.tsx
git commit -m "fix(web): use nullish coalescing for score display to handle score=0"
```

---

### Task 4: Add `score_id` to frontend types

**Files:**
- Modify: `web/src/lib/api/types.ts:109-139`

**Step 1: Add `score_id` to PickSummary interface**

In `web/src/lib/api/types.ts`, add `score_id` to `PickSummary`:

```typescript
export interface PickSummary {
  score_id: number              // DB primary key for traceability
  ticker: string
  name: string
  // ... rest unchanged
}
```

**Step 2: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): add score_id to PickSummary type for traceability"
```

---

### Task 5: Data contract validation tests

**Files:**
- Modify: `api/tests/test_dashboard.py`

**Step 1: Write conviction derivation boundary tests**

Add a new test class to `api/tests/test_dashboard.py`:

```python
@pytest.mark.asyncio
class TestConvictionDerivation:
    """Verify that stored conviction_level matches engine threshold derivation."""

    async def test_score_zero_shows_zero_not_percentile(self, async_engine):
        """When composite_raw_score=0.0, the API returns score=0.0 (not composite_percentile)."""
        factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="TEST", name="Test Corp",
                sector="Information Technology", market_cap=Decimal("1000000000"),
            )
            session.add(asset)
            await session.flush()
            score = Score(
                asset_id=asset.id,
                composite_percentile=75.0,
                composite_raw_score=0.0,  # edge case: zero
                conviction_level="none",
                signal="no_action",
                quality_percentile=50.0,
                value_percentile=50.0,
                momentum_percentile=50.0,
                data_coverage=1.0,
                scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        app = create_app()

        async def override():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/dashboard")
            data = response.json()
            # With no high/exceptional picks, falls back to top-10
            picks = data["picks"]
            assert len(picks) == 1
            # The score field must be 0.0, NOT 75.0 (the percentile)
            assert picks[0]["score"] == 0.0

    async def test_conviction_boundary_79(self, async_engine):
        """raw_score=79.0 exactly → conviction_level='exceptional'."""
        factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="EDGE", name="Edge Case Corp",
                sector="Financials", market_cap=Decimal("500000000"),
            )
            session.add(asset)
            await session.flush()
            score = Score(
                asset_id=asset.id,
                composite_percentile=95.0,
                composite_raw_score=79.0,
                conviction_level="exceptional",
                signal="buy",
                quality_percentile=80.0, value_percentile=80.0, momentum_percentile=80.0,
                data_coverage=1.0, scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        app = create_app()

        async def override():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/dashboard")
            data = response.json()
            pick = data["picks"][0]
            assert pick["conviction_level"] == "exceptional"
            assert pick["score"] == 79.0

    async def test_conviction_boundary_78_9(self, async_engine):
        """raw_score=78.9 → conviction_level='high' (just below exceptional)."""
        factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="NEAR", name="Near Miss Corp",
                sector="Financials", market_cap=Decimal("500000000"),
            )
            session.add(asset)
            await session.flush()
            score = Score(
                asset_id=asset.id,
                composite_percentile=93.0,
                composite_raw_score=78.9,
                conviction_level="high",
                signal="buy",
                quality_percentile=78.0, value_percentile=78.0, momentum_percentile=78.0,
                data_coverage=1.0, scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        app = create_app()

        async def override():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/dashboard")
            data = response.json()
            pick = data["picks"][0]
            assert pick["conviction_level"] == "high"
            assert pick["score"] == 78.9
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_dashboard.py::TestConvictionDerivation -v`
Expected: All 3 tests PASS (these validate existing correct behavior, not new code)

**Step 3: Commit**

```bash
git add api/tests/test_dashboard.py
git commit -m "test(api): add data-contract validation tests for conviction boundaries"
```

---

### Task 6: Integration test — card values match DB values

**Files:**
- Modify: `api/tests/test_dashboard.py`

**Step 1: Write integration test that cross-checks dashboard response against known DB values**

Add to `api/tests/test_dashboard.py` inside `TestDashboardPicks`:

```python
async def test_pick_values_match_seeded_db_exactly(self, client):
    """Every card field must exactly match what was seeded into the DB.

    This is the core data-contract test: the API must not transform,
    recompute, or lose any field between DB and response.
    """
    response = await client.get("/api/v1/dashboard")
    data = response.json()
    aapl = next(p for p in data["picks"] if p["ticker"] == "AAPL")

    # These must exactly match the seeded values in the fixture
    assert aapl["score"] == 82.0                          # composite_raw_score
    assert aapl["composite_percentile"] == 99.5            # composite_percentile
    assert aapl["universe_percentile"] == 99.5             # same as composite_percentile
    assert aapl["conviction_level"] == "exceptional"       # conviction_level
    assert aapl["signal"] == "buy"                         # signal
    assert aapl["quality_percentile"] == 98.0              # quality_percentile
    assert aapl["value_percentile"] == 95.0                # value_percentile
    assert aapl["momentum_percentile"] == 97.0             # momentum_percentile
    assert aapl["name"] == "Apple Inc."
    assert aapl["sector"] == "Information Technology"
    assert aapl["score_id"] > 0                            # traceability
    assert aapl["scored_at"] is not None                   # timestamp
```

**Step 2: Run test**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardPicks::test_pick_values_match_seeded_db_exactly -v`
Expected: PASS

**Step 3: Commit**

```bash
git add api/tests/test_dashboard.py
git commit -m "test(api): add integration test verifying card values match DB exactly"
```

---

### Task 7: Final regression run

**Step 1: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All tests PASS

**Step 2: Run full engine test suite (sanity check)**

Run: `uv run pytest engine/tests/ -v`
Expected: All tests PASS (engine untouched, but verify no side effects)

**Step 3: Commit if any cleanup needed, then verify clean working tree**

```bash
git status
```
