# Score History Graph Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the score history graph to display the raw composite score (matching the header badge) instead of the universe percentile rank.

**Architecture:** Add a `score` field to the `ScoreHistoryPoint` API schema (populated from `composite_raw_score`), add it to the frontend type, and remap the chart/table data to use it. The existing `composite_percentile` and `composite_raw_score` fields remain untouched for backward compatibility.

**Tech Stack:** Python/Pydantic (API schema), FastAPI (route), TypeScript/React (frontend types + components), Vitest + pytest (tests)

---

### Task 1: Add `score` field to API schema and route

**Files:**
- Modify: `api/src/margin_api/schemas/score_history.py:10-23`
- Modify: `api/src/margin_api/routes/scores.py:401-418`

**Step 1: Add `score` field to the Pydantic schema**

In `api/src/margin_api/schemas/score_history.py`, add `score: float` as the first field after `scored_at`:

```python
class ScoreHistoryPoint(BaseModel):
    scored_at: datetime
    score: float
    composite_percentile: float
    composite_raw_score: float | None = None
    quality_percentile: float | None = None
    value_percentile: float | None = None
    momentum_percentile: float | None = None
    composite_tier: str
    signal: str
    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    delta: float | None = None
```

**Step 2: Populate `score` in the route handler**

In `api/src/margin_api/routes/scores.py`, inside the `points.append(ScoreHistoryPoint(...))` call (~line 402), add:

```python
score=row.composite_raw_score,
```

as the first kwarg after `scored_at=scored_at,`.

**Step 3: Run existing API tests to verify no regressions**

Run: `uv run pytest api/tests/test_score_history.py -v`
Expected: All 7 tests PASS (the new field has a value from the model default of 0.0)

**Step 4: Commit**

```bash
git add api/src/margin_api/schemas/score_history.py api/src/margin_api/routes/scores.py
git commit -m "feat(api): add score field to ScoreHistoryPoint schema"
```

---

### Task 2: Add API test asserting `score` field matches `composite_raw_score`

**Files:**
- Modify: `api/tests/test_score_history.py:44-62` (fixture — add `composite_raw_score`)
- Modify: `api/tests/test_score_history.py` (new test method)

**Step 1: Update the test fixture to set explicit `composite_raw_score` values**

In `api/tests/test_score_history.py`, inside the `for i in range(5):` loop (~line 46), add `composite_raw_score` to the `Score(...)` constructor:

```python
score = Score(
    asset_id=aapl.id,
    composite_percentile=80.0 + i * 2,
    composite_raw_score=70.0 + i * 3,  # Different from percentile to catch mixups
    conviction_level="high",
    signal="buy",
    quality_percentile=85.0 + i,
    value_percentile=80.0 + i,
    momentum_percentile=82.0 + i,
    data_coverage=1.0,
    scored_at=base_time + timedelta(days=i * 7),
    margin_invest_value=200.0,
    buy_price=150.0,
    sell_price=250.0,
    actual_price=185.0,
    score_detail={},
)
```

**Step 2: Write the test**

Add to the `TestScoreHistory` class:

```python
async def test_score_field_matches_composite_raw_score(self, history_client):
    resp = await history_client.get("/api/v1/scores/AAPL/history")
    points = resp.json()["points"]
    for i, point in enumerate(points):
        expected_raw = 70.0 + i * 3
        assert point["score"] == pytest.approx(expected_raw)
        assert point["score"] == point["composite_raw_score"]
```

**Step 3: Run the test to verify it passes**

Run: `uv run pytest api/tests/test_score_history.py::TestScoreHistory::test_score_field_matches_composite_raw_score -v`
Expected: PASS

**Step 4: Commit**

```bash
git add api/tests/test_score_history.py
git commit -m "test(api): assert score field matches composite_raw_score in history"
```

---

### Task 3: Add `score` to frontend `ScoreHistoryPoint` type

**Files:**
- Modify: `web/src/lib/api/types.ts:219-233`

**Step 1: Add `score` field to the TypeScript interface**

In `web/src/lib/api/types.ts`, add `score: number` after `scored_at`:

```typescript
export interface ScoreHistoryPoint {
  scored_at: string
  score: number
  composite_percentile: number
  composite_raw_score: number | null
  quality_percentile: number | null
  value_percentile: number | null
  momentum_percentile: number | null
  composite_tier: string
  signal: string
  margin_invest_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  delta: number | null
}
```

**Step 2: Run type check to verify no errors**

Run: `cd web && npx tsc --noEmit`
Expected: No errors (the field is non-optional, but we only construct these from API responses)

**Step 3: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): add score field to ScoreHistoryPoint type"
```

---

### Task 4: Remap graph and table data to use `score` instead of `composite_percentile`

**Files:**
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx:112,133`

**Step 1: Update `scoreHistory` useMemo (line 112)**

Change:
```typescript
score: p.composite_percentile,
```
To:
```typescript
score: p.score ?? p.composite_raw_score ?? 0,
```

**Step 2: Update `scoreChartData` useMemo (line 133)**

Change:
```typescript
score: p.composite_percentile,
```
To:
```typescript
score: p.score ?? p.composite_raw_score ?? 0,
```

**Step 3: Run frontend tests**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/dashboard/panel/asset-panel.tsx
git commit -m "fix(web): display raw score instead of percentile in score history graph"
```

---

### Task 5: Update frontend test mock data to include `score` field

**Files:**
- Modify: `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx:177-178,222-223`

**Step 1: Add `score` to mock history points**

In the two `mockHistory` objects inside `asset-panel.test.tsx`, add `score` to each point. The existing mocks have `composite_raw_score: 75` and `composite_raw_score: 77` — add matching `score` fields:

First mock (~line 177-178):
```typescript
{ scored_at: "2026-01-01T00:00:00Z", score: 75, composite_percentile: 80, composite_raw_score: 75, ... },
{ scored_at: "2026-01-08T00:00:00Z", score: 77, composite_percentile: 82, composite_raw_score: 77, ... },
```

Second mock (~line 222-223): same pattern.

**Step 2: Run all panel tests to verify**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx
git commit -m "test(web): add score field to mock history data in asset-panel tests"
```

---

### Task 6: Final verification — run full test suites

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/test_score_history.py -v`
Expected: All 8 tests PASS (7 existing + 1 new)

**Step 2: Run all frontend panel tests**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/`
Expected: All tests PASS

**Step 3: Verify no TypeScript errors**

Run: `cd web && npx tsc --noEmit`
Expected: Clean exit
