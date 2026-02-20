# Watchlist Picks Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace percentile-based conviction thresholds with absolute raw-score thresholds (79/72/65) and make Watchlist Picks expandable with the same detail panel as Top Picks.

**Architecture:** Engine conviction property switches from `composite_percentile` to `composite_raw_score` thresholds. API enriches `WatchlistItem` schema and sorts by raw score. Frontend replaces flat `WatchlistTable` with expandable `WatchlistPicksList` that triggers `AssetPanel` on click.

**Tech Stack:** Python/Pydantic (engine), FastAPI/SQLAlchemy (api), Next.js 15/React/Tailwind/Framer Motion (web)

---

### Task 1: Engine — Rename WATCHLIST to MEDIUM and update thresholds

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:16-20` (ConvictionLevel enum)
- Modify: `engine/src/margin_engine/models/scoring.py:141-152` (conviction_level property)
- Modify: `engine/src/margin_engine/models/scoring.py:155-158` (signal property WATCHLIST reference)
- Modify: `engine/src/margin_engine/models/scoring.py:183-198` (ScoringConfig thresholds)
- Test: `engine/tests/test_scoring_models.py`

**Step 1: Update existing conviction tests to use new thresholds**

Replace the entire `TestCompositeScore` class in `engine/tests/test_scoring_models.py` with tests that use `composite_raw_score` thresholds:

```python
class TestCompositeScore:
    def _make_score(self, **kwargs):
        defaults = dict(
            ticker="TEST",
            composite_percentile=50.0,
            composite_raw_score=50.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        defaults.update(kwargs)
        return CompositeScore(**defaults)

    def test_conviction_level_exceptional(self):
        score = self._make_score(composite_raw_score=80.0)
        assert score.conviction_level == ConvictionLevel.EXCEPTIONAL
        assert score.signal == Signal.BUY

    def test_conviction_level_exceptional_boundary(self):
        score = self._make_score(composite_raw_score=79.0)
        assert score.conviction_level == ConvictionLevel.EXCEPTIONAL

    def test_conviction_level_high(self):
        score = self._make_score(composite_raw_score=75.0)
        assert score.conviction_level == ConvictionLevel.HIGH
        assert score.signal == Signal.BUY

    def test_conviction_level_high_boundary(self):
        score = self._make_score(composite_raw_score=72.0)
        assert score.conviction_level == ConvictionLevel.HIGH

    def test_conviction_level_medium(self):
        score = self._make_score(composite_raw_score=67.0)
        assert score.conviction_level == ConvictionLevel.MEDIUM
        assert score.signal == Signal.WATCH

    def test_conviction_level_medium_boundary(self):
        score = self._make_score(composite_raw_score=65.0)
        assert score.conviction_level == ConvictionLevel.MEDIUM

    def test_conviction_level_none(self):
        score = self._make_score(composite_raw_score=64.9)
        assert score.conviction_level == ConvictionLevel.NONE
        assert score.signal == Signal.NO_ACTION

    def test_conviction_level_none_low(self):
        score = self._make_score(composite_raw_score=30.0)
        assert score.conviction_level == ConvictionLevel.NONE

    def test_turnaround_uses_same_thresholds(self):
        """No turnaround exception — same thresholds for all growth stages."""
        score = self._make_score(
            composite_raw_score=72.0,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert score.conviction_level == ConvictionLevel.HIGH

    def test_below_high_turnaround_is_medium(self):
        score = self._make_score(
            composite_raw_score=71.9,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert score.conviction_level == ConvictionLevel.MEDIUM
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestCompositeScore -v`
Expected: FAIL — `ConvictionLevel` has no `MEDIUM` member, property still uses percentile

**Step 3: Update the engine models**

In `engine/src/margin_engine/models/scoring.py`:

a) Rename enum member:
```python
class ConvictionLevel(StrEnum):
    EXCEPTIONAL = "exceptional"  # composite_raw_score >= 79
    HIGH = "high"               # composite_raw_score >= 72
    MEDIUM = "medium"           # composite_raw_score >= 65
    NONE = "none"               # < 65
```

b) Update `CompositeScore.conviction_level` property:
```python
@property
def conviction_level(self) -> ConvictionLevel:
    if self.composite_raw_score >= 79.0:
        return ConvictionLevel.EXCEPTIONAL
    if self.composite_raw_score >= 72.0:
        return ConvictionLevel.HIGH
    if self.composite_raw_score >= 65.0:
        return ConvictionLevel.MEDIUM
    return ConvictionLevel.NONE
```

c) Update `signal` property reference:
```python
if level == ConvictionLevel.MEDIUM:
    return Signal.WATCH
```

d) Update `ScoringConfig`:
```python
# Conviction thresholds (raw score) — absolute, universe-independent
exceptional_threshold: float = 79.0
high_threshold: float = 72.0
medium_threshold: float = 65.0  # renamed from watchlist_threshold
sell_threshold: float = 97.0
```

Remove `turnaround_threshold` field (no longer needed).

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestCompositeScore -v`
Expected: PASS

**Step 5: Update ScoringConfig tests**

In `engine/tests/test_scoring_models.py`, update `TestScoringConfig.test_default_weights` to check new threshold names:
```python
def test_default_thresholds(self):
    config = ScoringConfig()
    assert config.exceptional_threshold == 79.0
    assert config.high_threshold == 72.0
    assert config.medium_threshold == 65.0
```

**Step 6: Run full engine model tests**

Run: `uv run pytest engine/tests/test_scoring_models.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/test_scoring_models.py
git commit -m "feat(engine): replace percentile conviction thresholds with raw-score thresholds (79/72/65)"
```

---

### Task 2: Engine — Update all WATCHLIST references to MEDIUM

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py:55`
- Modify: `engine/src/margin_engine/scoring/v3_thresholds.py:70,117`
- Modify: `engine/src/margin_engine/scoring/v3_orchestrator.py:43,50`
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py:50`
- Modify: `engine/src/margin_engine/scoring/position_sizing.py:23`
- Modify: `engine/src/margin_engine/scoring/v3_position_sizing.py:17,23,29`
- Modify: `engine/src/margin_engine/scoring/dual_track.py:18`

**Step 1: Replace all `ConvictionLevel.WATCHLIST` with `ConvictionLevel.MEDIUM` across engine/src**

Use find-and-replace across all files listed above. Change:
- `ConvictionLevel.WATCHLIST` -> `ConvictionLevel.MEDIUM`
- `_WATCHLIST_CAP = 98.0` in `dual_track.py` -> `_MEDIUM_CAP = 98.0` (and update its usage)

**Step 2: Run the full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All 784+ tests pass (some threshold-dependent tests may need updating — fix any that reference old WATCHLIST enum values)

**Step 3: Fix any failing tests that reference WATCHLIST enum**

Search `engine/tests/` for `ConvictionLevel.WATCHLIST` or `"watchlist"` and update to `ConvictionLevel.MEDIUM` / `"medium"`.

**Step 4: Run engine tests again**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/
git commit -m "refactor(engine): rename WATCHLIST to MEDIUM across scoring modules"
```

---

### Task 3: API — Enrich WatchlistItem schema

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py:43-49`
- Test: `api/tests/test_schemas.py` (or `api/tests/test_dashboard.py`)

**Step 1: Write test for enriched WatchlistItem schema**

Add to `api/tests/test_schemas.py` (or create inline):

```python
def test_watchlist_item_enriched_fields():
    from margin_api.schemas.dashboard import WatchlistItem
    item = WatchlistItem(
        ticker="MSFT",
        name="Microsoft Corp",
        composite_raw_score=67.5,
        conviction_level="medium",
        sector="Information Technology",
        actual_price=420.50,
        price_upside=0.15,
        opportunity_type="compounder",
    )
    assert item.composite_raw_score == 67.5
    assert item.sector == "Information Technology"
    assert item.actual_price == 420.50
    assert item.price_upside == 0.15
    assert item.opportunity_type == "compounder"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_schemas.py::test_watchlist_item_enriched_fields -v`
Expected: FAIL — `composite_raw_score` field doesn't exist

**Step 3: Update the WatchlistItem schema**

In `api/src/margin_api/schemas/dashboard.py`:

```python
class WatchlistItem(BaseModel):
    """Summary of a watchlist item for the dashboard."""

    ticker: str
    name: str
    composite_raw_score: float
    conviction_level: str
    sector: str | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    opportunity_type: str | None = None
```

Remove the old `composite_percentile` field.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_schemas.py::test_watchlist_item_enriched_fields -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/tests/test_schemas.py
git commit -m "feat(api): enrich WatchlistItem schema with score, sector, price fields"
```

---

### Task 4: API — Update dashboard endpoint queries and watchlist construction

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py:104-135`
- Modify: `api/tests/test_dashboard.py`

**Step 1: Update dashboard tests for new conviction level string and enriched watchlist**

In `api/tests/test_dashboard.py`:

a) Update the seeded MSFT score's `conviction_level` from `"watchlist"` to `"medium"` in all fixtures (`seeded_session`, `universe_seeded_session`). Also add `composite_raw_score` to Score rows.

b) Update `TestDashboardWatchlist.test_watchlist_populated`:
```python
async def test_watchlist_populated(self, client):
    """Medium conviction scores appear in watchlist."""
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    watchlist = data["watchlist"]
    assert len(watchlist) == 1
    assert watchlist[0]["ticker"] == "MSFT"
    assert watchlist[0]["name"] == "Microsoft Corp"
    assert watchlist[0]["composite_raw_score"] == 67.0
    assert watchlist[0]["conviction_level"] == "medium"
    assert watchlist[0]["sector"] == "Information Technology"
```

c) Update `TestDashboardMixed.test_mixed_conviction_levels` assertion for watchlist count.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_dashboard.py -v --tb=short`
Expected: FAIL — endpoint still returns old watchlist format

**Step 3: Update the dashboard route**

In `api/src/margin_api/routes/dashboard.py`:

a) Update `_fetch_picks_and_watchlist` watchlist query:
```python
watchlist_result = await db.execute(
    base.where(Score.conviction_level.in_(["medium", "watchlist"]))
    .order_by(Score.composite_raw_score.desc())
)
```

Note: `.in_(["medium", "watchlist"])` handles both old and new DB values during transition.

b) Update picks query sort:
```python
picks_result = await db.execute(
    base.where(Score.conviction_level.in_(["exceptional", "high"]))
    .order_by(Score.composite_raw_score.desc())
)
```

c) Update watchlist row construction to build enriched `WatchlistItem`:
```python
watchlist = [
    WatchlistItem(
        ticker=row.ticker,
        name=row.asset_name,
        composite_raw_score=row.Score.composite_raw_score,
        conviction_level=row.Score.conviction_level,
        sector=getattr(row, "asset_sector", None),
        actual_price=getattr(row.Score, "actual_price", None),
        price_upside=(
            round((row.Score.margin_invest_value - row.Score.actual_price) / row.Score.actual_price, 4)
            if getattr(row.Score, "margin_invest_value", None)
            and getattr(row.Score, "actual_price", None)
            and not getattr(row.Score, "price_target_invalid_reason", None)
            else None
        ),
        opportunity_type=getattr(row.Score, "opportunity_type", None),
    )
    for row in watchlist_result.all()
]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_dashboard.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/dashboard.py api/tests/test_dashboard.py
git commit -m "feat(api): update dashboard to sort by raw_score and enrich watchlist items"
```

---

### Task 5: API — Update remaining WATCHLIST string references

**Files:**
- Modify: `api/src/margin_api/services/metrics.py:138`
- Modify: `api/src/margin_api/cli.py:461`
- Modify: `api/src/margin_api/schemas/scores.py:77`

**Step 1: Update all remaining "watchlist" string references**

a) `api/src/margin_api/services/metrics.py:138` — update dict key:
```python
{"exceptional": 8.0, "high": 5.0, "moderate": 3.0, "medium": 2.0}
```

b) `api/src/margin_api/cli.py:461` — update conviction level list:
```python
for level in ("exceptional", "high", "medium", "none"):
```

c) `api/src/margin_api/schemas/scores.py:77` — update comment:
```python
conviction_level: str  # "exceptional", "high", "medium", "none"
```

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: ALL PASS (fix any that still reference `"watchlist"` string in assertions)

**Step 3: Commit**

```bash
git add api/src/
git commit -m "refactor(api): rename watchlist to medium in remaining references"
```

---

### Task 6: Frontend — Update TypeScript types

**Files:**
- Modify: `web/src/lib/api/types.ts:141-146`

**Step 1: Update `WatchlistItem` type**

```typescript
export interface WatchlistItem {
  ticker: string
  name: string
  composite_raw_score: number
  conviction_level: string
  sector?: string | null
  actual_price?: number | null
  price_upside?: number | null
  opportunity_type?: string | null
}
```

**Step 2: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): update WatchlistItem type with enriched fields"
```

---

### Task 7: Frontend — Update ConvictionBadge with medium style

**Files:**
- Modify: `web/src/components/ui/conviction-badge.tsx`

**Step 1: Add `medium` style and capitalize display text**

```tsx
interface ConvictionBadgeProps {
  level: string
  className?: string
}

const badgeStyles: Record<string, string> = {
  exceptional: "bg-accent text-white border-accent",
  high: "bg-accent/10 text-accent-hover border-accent/20",
  medium: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  watchlist: "bg-amber-500/10 text-amber-600 border-amber-500/20",  // backward compat
  none: "bg-bg-primary text-text-secondary border-border-primary",
}

const displayNames: Record<string, string> = {
  exceptional: "Exceptional",
  high: "High",
  medium: "Medium",
  watchlist: "Medium",  // backward compat
  none: "None",
}

export function ConvictionBadge({ level, className = "" }: ConvictionBadgeProps) {
  const style = badgeStyles[level] || badgeStyles.none
  const sizeClass = level === "exceptional" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs"
  return (
    <span className={`inline-flex items-center rounded-sm font-medium border ${sizeClass} ${style} ${className}`}>
      {displayNames[level] || level}
    </span>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/ui/conviction-badge.tsx
git commit -m "feat(web): add medium conviction badge style with capitalized labels"
```

---

### Task 8: Frontend — Create WatchlistPicksList component

**Files:**
- Create: `web/src/components/dashboard/watchlist-picks-list.tsx`
- Modify: `web/src/components/dashboard/index.ts`

**Step 1: Create the WatchlistPicksList component**

```tsx
"use client"

import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ConvictionBadge } from "@/components/ui"
import { AssetPanel } from "./panel"
import { PanelErrorBoundary } from "./panel/panel-error-boundary"
import { getScore, getMetrics } from "@/lib/api/scores"
import { ApiError } from "@/lib/api/client"
import { getSectorColor } from "@/lib/sector-colors"
import type { WatchlistItem, ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"

interface WatchlistPicksListProps {
  items: WatchlistItem[]
  className?: string
}

function WatchlistRow({ item }: { item: WatchlistItem }) {
  const [expanded, setExpanded] = useState(false)
  const [scoreData, setScoreData] = useState<ScoreResponse | null>(null)
  const [metricsData, setMetricsData] = useState<InstitutionalMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDetails = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [scoreResult, metricsResult] = await Promise.allSettled([
        getScore(item.ticker, ["price_history", "signal_history"]),
        getMetrics(item.ticker),
      ])

      if (scoreResult.status === "fulfilled") {
        setScoreData(scoreResult.value)
      } else {
        const err = scoreResult.reason
        const requestId = err instanceof ApiError ? err.requestId : undefined
        if (requestId) console.error(`[${requestId}] Score fetch failed:`, err)
        setError("Unable to load details")
        return
      }

      if (metricsResult.status === "fulfilled") {
        setMetricsData(metricsResult.value)
      } else {
        setMetricsData(null)
      }
    } finally {
      setLoading(false)
    }
  }, [item.ticker])

  const handleClick = useCallback(async () => {
    if (expanded) {
      setExpanded(false)
      return
    }
    setExpanded(true)
    if (!scoreData) {
      await fetchDetails()
    }
  }, [expanded, scoreData, fetchDetails])

  const sectorColor = getSectorColor(item.sector)

  return (
    <>
      <div
        className="flex items-center gap-4 px-5 py-3.5 cursor-pointer transition-colors hover:bg-bg-primary/50 border-b border-border-primary last:border-b-0"
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            handleClick()
          }
        }}
        aria-expanded={expanded}
        data-testid={`watchlist-row-${item.ticker}`}
      >
        {/* Sector dot */}
        <span
          className="h-2 w-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: sectorColor }}
        />

        {/* Ticker + name */}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-bold text-text-primary">{item.ticker}</span>
          <span className="text-sm text-text-secondary ml-2 truncate">{item.name}</span>
        </div>

        {/* Conviction badge */}
        <ConvictionBadge level={item.conviction_level} />

        {/* Score */}
        <span className="text-sm font-mono text-text-primary w-8 text-right">
          {Math.round(item.composite_raw_score)}
        </span>

        {/* Price + upside */}
        <div className="text-sm text-right w-28 flex-shrink-0">
          {item.actual_price != null && (
            <span className="text-text-secondary">
              ${item.actual_price.toFixed(2)}
            </span>
          )}
          {item.price_upside != null && (
            <span className={`ml-1.5 ${item.price_upside >= 0 ? "text-bullish" : "text-bearish"}`}>
              {item.price_upside >= 0 ? "+" : ""}
              {(item.price_upside * 100).toFixed(1)}%
            </span>
          )}
        </div>

        {/* Chevron */}
        <motion.svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-text-tertiary flex-shrink-0"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </motion.svg>
      </div>

      {/* Loading state */}
      {expanded && loading && (
        <div className="px-5 py-4 flex items-center justify-center border-b border-border-primary">
          <div className="animate-spin h-5 w-5 border-2 border-accent border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-text-secondary">Loading details...</span>
        </div>
      )}

      {/* Error state */}
      {expanded && error && (
        <div className="px-5 py-4 border-b border-border-primary">
          <div className="text-center">
            <p className="text-sm text-text-secondary mb-2">{error}</p>
            <button
              type="button"
              className="text-xs text-accent hover:text-accent/80 underline underline-offset-2"
              onClick={(e) => {
                e.stopPropagation()
                setScoreData(null)
                fetchDetails()
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* AssetPanel overlay */}
      {scoreData && (
        <PanelErrorBoundary onDismiss={() => setExpanded(false)}>
          <AssetPanel
            isOpen={expanded && !loading}
            onClose={() => setExpanded(false)}
            ticker={item.ticker}
            scoredResult={scoreData}
            metrics={metricsData}
          />
        </PanelErrorBoundary>
      )}
    </>
  )
}

export function WatchlistPicksList({ items, className = "" }: WatchlistPicksListProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-text-secondary" data-testid="watchlist-empty">
        No Watchlist Picks available
      </p>
    )
  }

  return (
    <div
      className={`bg-bg-elevated border border-border-primary rounded-sm overflow-hidden ${className}`}
      data-testid="watchlist-picks-list"
    >
      {items.map((item) => (
        <WatchlistRow key={item.ticker} item={item} />
      ))}
    </div>
  )
}
```

**Step 2: Update the barrel export**

In `web/src/components/dashboard/index.ts`, replace:
```
export { WatchlistTable } from "./watchlist-table"
```
with:
```
export { WatchlistPicksList } from "./watchlist-picks-list"
```

**Step 3: Commit**

```bash
git add web/src/components/dashboard/watchlist-picks-list.tsx web/src/components/dashboard/index.ts
git commit -m "feat(web): create expandable WatchlistPicksList component"
```

---

### Task 9: Frontend — Update dashboard page to use WatchlistPicksList

**Files:**
- Modify: `web/src/app/dashboard/page.tsx`

**Step 1: Swap component import and usage**

In `web/src/app/dashboard/page.tsx`:

a) Update import:
```tsx
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction } from "@/components/dashboard"
```

b) Update the watchlist section (replace the existing block at approximately lines 83-90):
```tsx
{(data?.watchlist?.length ?? 0) > 0 && (
  <section>
    <h2 className="text-lg font-semibold text-text-primary mb-4">
      Watchlist Picks
    </h2>
    <WatchlistPicksList items={data!.watchlist} />
  </section>
)}
```

**Step 2: Verify the old WatchlistTable is no longer imported anywhere**

Search for `WatchlistTable` in `web/src/` — it should have zero imports. If clean, delete `web/src/components/dashboard/watchlist-table.tsx`.

**Step 3: Commit**

```bash
git add web/src/app/dashboard/page.tsx
git rm web/src/components/dashboard/watchlist-table.tsx
git commit -m "feat(web): replace WatchlistTable with WatchlistPicksList on dashboard"
```

---

### Task 10: Verify end-to-end

**Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ALL PASS

**Step 2: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: ALL PASS

**Step 3: Fix any remaining test failures**

Any test referencing `"watchlist"` conviction string or `composite_percentile` in watchlist items will need updating. Common patterns:
- `conviction_level="watchlist"` -> `conviction_level="medium"`
- `watchlist[0]["composite_percentile"]` -> `watchlist[0]["composite_raw_score"]`
- `ConvictionLevel.WATCHLIST` -> `ConvictionLevel.MEDIUM`

**Step 4: Run both suites clean**

Run: `uv run pytest engine/tests/ api/tests/ -v --tb=short`
Expected: ALL PASS

**Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: update remaining test references from watchlist to medium"
```
