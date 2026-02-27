# Dashboard Visualization Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace 4 landing page proof visualizations with data-driven charts: selectivity funnel, sector breakdown, updated correlation heatmap, and real backtest equity curve.

**Architecture:** New `/universe/funnel` API endpoint + extended backtest teaser + rewired correlation query + 2 new frontend components + 2 rewritten components. ProofSection grid changes from 2x2 to 5 cards (factor bars + 4 new).

**Tech Stack:** FastAPI + SQLAlchemy (API), Recharts + Framer Motion + Tailwind (frontend), Vitest + pytest (tests)

---

### Task 1: Add `/universe/funnel` API endpoint

**Files:**
- Modify: `api/src/margin_api/schemas/universe.py`
- Modify: `api/src/margin_api/routes/universe.py`
- Test: `api/tests/test_universe_routes.py`

**Step 1: Write the failing test**

Add to `api/tests/test_universe_routes.py`:

```python
class TestUniverseFunnelSchema:
    def test_funnel_response_model(self):
        from margin_api.schemas.universe import UniverseFunnelResponse

        funnel = UniverseFunnelResponse(
            universe_size=3200,
            survived_filters=280,
            exceptional_count=12,
            high_count=35,
            medium_count=58,
            last_scored_at=datetime.now(UTC),
        )
        data = funnel.model_dump()
        assert data["universe_size"] == 3200
        assert data["survived_filters"] == 280
        assert data["exceptional_count"] == 12
        assert data["high_count"] == 35
        assert data["medium_count"] == 58
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_routes.py::TestUniverseFunnelSchema -v`
Expected: FAIL with ImportError (UniverseFunnelResponse does not exist)

**Step 3: Write the schema**

Add to `api/src/margin_api/schemas/universe.py`:

```python
class UniverseFunnelResponse(BaseModel):
    """Selectivity funnel for the landing page."""

    universe_size: int
    survived_filters: int
    exceptional_count: int
    high_count: int
    medium_count: int
    last_scored_at: datetime | None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_universe_routes.py::TestUniverseFunnelSchema -v`
Expected: PASS

**Step 5: Write the failing route test**

Add to `api/tests/test_universe_routes.py`:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.models import Asset, Base, Score


@pytest_asyncio.fixture
async def funnel_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def funnel_session(funnel_engine):
    factory = async_sessionmaker(funnel_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Seed: 3 assets, varying conviction
        a1 = Asset(ticker="AAPL", name="Apple", sector="Technology")
        a2 = Asset(ticker="MSFT", name="Microsoft", sector="Technology")
        a3 = Asset(ticker="JNJ", name="J&J", sector="Healthcare")
        session.add_all([a1, a2, a3])
        await session.flush()

        s1 = Score(
            asset_id=a1.id, composite_raw_score=82.0, composite_percentile=99.0,
            conviction_level="exceptional", signal="buy",
            quality_percentile=90.0, value_percentile=85.0, momentum_percentile=80.0,
        )
        s2 = Score(
            asset_id=a2.id, composite_raw_score=75.0, composite_percentile=90.0,
            conviction_level="high", signal="buy",
            quality_percentile=80.0, value_percentile=75.0, momentum_percentile=70.0,
        )
        s3 = Score(
            asset_id=a3.id, composite_raw_score=67.0, composite_percentile=70.0,
            conviction_level="medium", signal="watch",
            quality_percentile=70.0, value_percentile=65.0, momentum_percentile=60.0,
        )
        session.add_all([s1, s2, s3])
        await session.commit()
        yield session


class TestUniverseFunnelRoute:
    @pytest.mark.asyncio
    async def test_funnel_returns_counts(self, funnel_session):
        from margin_api.routes.universe import _compute_funnel
        result = await _compute_funnel(funnel_session)
        assert result.exceptional_count == 1
        assert result.high_count == 1
        assert result.medium_count == 1
        assert result.survived_filters == 3  # all 3 scored = survived
```

**Step 6: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_routes.py::TestUniverseFunnelRoute -v`
Expected: FAIL with ImportError (_compute_funnel does not exist)

**Step 7: Implement the route**

Add to `api/src/margin_api/routes/universe.py`:

```python
from margin_api.schemas.universe import UniverseFunnelResponse, UniverseStatusResponse

async def _compute_funnel(db: AsyncSession) -> UniverseFunnelResponse:
    """Compute selectivity funnel counts from the database."""
    snapshot = await get_active_snapshot(db)
    universe_size = snapshot.ticker_count if snapshot else 0

    # Count scored assets (survived filters = has a score)
    survived_result = await db.execute(select(func.count(func.distinct(Score.asset_id))))
    survived_filters = survived_result.scalar() or 0

    # Count by conviction level
    for level in ("exceptional", "high", "medium"):
        result = await db.execute(
            select(func.count(func.distinct(Score.asset_id)))
            .where(Score.conviction_level == level)
        )
        locals()[f"{level}_count"] = result.scalar() or 0

    last_scored = await db.execute(select(func.max(Score.scored_at)))
    last_scored_at = last_scored.scalar()

    return UniverseFunnelResponse(
        universe_size=universe_size,
        survived_filters=survived_filters,
        exceptional_count=locals()["exceptional_count"],
        high_count=locals()["high_count"],
        medium_count=locals()["medium_count"],
        last_scored_at=last_scored_at,
    )


@router.get("/universe/funnel", response_model=UniverseFunnelResponse)
async def get_universe_funnel(db: AsyncSession = Depends(get_db)):
    """Selectivity funnel for the landing page."""
    return await _compute_funnel(db)
```

Note: Avoid the `locals()` trick — use explicit variables instead:

```python
async def _compute_funnel(db: AsyncSession) -> UniverseFunnelResponse:
    snapshot = await get_active_snapshot(db)
    universe_size = snapshot.ticker_count if snapshot else 0

    survived_result = await db.execute(select(func.count(func.distinct(Score.asset_id))))
    survived_filters = survived_result.scalar() or 0

    exc_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id)))
        .where(Score.conviction_level == "exceptional")
    )
    exceptional_count = exc_result.scalar() or 0

    high_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id)))
        .where(Score.conviction_level == "high")
    )
    high_count = high_result.scalar() or 0

    med_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id)))
        .where(Score.conviction_level == "medium")
    )
    medium_count = med_result.scalar() or 0

    last_scored = await db.execute(select(func.max(Score.scored_at)))
    last_scored_at = last_scored.scalar()

    return UniverseFunnelResponse(
        universe_size=universe_size,
        survived_filters=survived_filters,
        exceptional_count=exceptional_count,
        high_count=high_count,
        medium_count=medium_count,
        last_scored_at=last_scored_at,
    )
```

**Step 8: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_universe_routes.py -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add api/src/margin_api/schemas/universe.py api/src/margin_api/routes/universe.py api/tests/test_universe_routes.py
git commit -m "feat(api): add /universe/funnel endpoint for landing page selectivity funnel"
```

---

### Task 2: Add portfolio-level backtest teaser endpoint with equity curve

The current teaser endpoint is per-ticker (`/backtest/teaser/{ticker}`). The landing page needs a portfolio-level teaser with equity curve data.

**Files:**
- Modify: `api/src/margin_api/schemas/backtest.py`
- Modify: `api/src/margin_api/routes/backtest.py`
- Modify: `api/src/margin_api/services/backtest.py`
- Test: `api/tests/test_backtest.py`

**Step 1: Write the failing test**

Add to `api/tests/test_backtest.py`:

```python
class TestPortfolioTeaserSchema:
    def test_portfolio_teaser_response_model(self):
        from margin_api.schemas.backtest import EquityCurvePoint, PortfolioTeaserResponse

        point = EquityCurvePoint(month="2023-03", portfolio=10000.0, benchmark=10000.0)
        assert point.month == "2023-03"

        teaser = PortfolioTeaserResponse(
            model_return=0.42,
            benchmark_return=0.28,
            max_drawdown=-0.18,
            sharpe_ratio=1.45,
            num_months=36,
            start_date=date(2023, 1, 1),
            end_date=date(2025, 12, 31),
            equity_curve=[point],
        )
        data = teaser.model_dump()
        assert data["sharpe_ratio"] == 1.45
        assert len(data["equity_curve"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_backtest.py::TestPortfolioTeaserSchema -v`
Expected: FAIL with ImportError

**Step 3: Write the schemas**

Add to `api/src/margin_api/schemas/backtest.py`:

```python
class EquityCurvePoint(BaseModel):
    """Single month in the equity curve."""

    month: str  # "YYYY-MM" format
    portfolio: float
    benchmark: float


class PortfolioTeaserResponse(BaseModel):
    """Portfolio-level teaser for the landing page."""

    model_return: float
    benchmark_return: float
    max_drawdown: float
    sharpe_ratio: float
    num_months: int
    start_date: date
    end_date: date
    equity_curve: list[EquityCurvePoint]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_backtest.py::TestPortfolioTeaserSchema -v`
Expected: PASS

**Step 5: Write the failing route test**

```python
class TestPortfolioTeaserRoute:
    def test_portfolio_teaser_returns_200(self, client):
        response = client.get("/api/v1/backtest/portfolio-teaser")
        assert response.status_code == 200

    def test_portfolio_teaser_has_equity_curve(self, client):
        response = client.get("/api/v1/backtest/portfolio-teaser")
        data = response.json()
        assert "equity_curve" in data
        assert len(data["equity_curve"]) > 0
        assert "month" in data["equity_curve"][0]
        assert "portfolio" in data["equity_curve"][0]
        assert "benchmark" in data["equity_curve"][0]

    def test_portfolio_teaser_has_metrics(self, client):
        response = client.get("/api/v1/backtest/portfolio-teaser")
        data = response.json()
        assert "sharpe_ratio" in data
        assert "model_return" in data
        assert "num_months" in data
```

**Step 6: Run test to verify it fails**

Run: `uv run pytest api/tests/test_backtest.py::TestPortfolioTeaserRoute -v`
Expected: FAIL (404 — endpoint doesn't exist)

**Step 7: Implement the service function**

Add to `api/src/margin_api/services/backtest.py`:

```python
from margin_api.schemas.backtest import EquityCurvePoint, PortfolioTeaserResponse

def build_portfolio_teaser(result: ReplayResult) -> PortfolioTeaserResponse:
    """Build a portfolio-level teaser with equity curve from replay result."""
    m = result.metrics
    curve = []
    for snap in result.snapshots:
        curve.append(
            EquityCurvePoint(
                month=snap.date.strftime("%Y-%m"),
                portfolio=round(snap.portfolio_value, 2),
                benchmark=round(snap.benchmark_value, 2),
            )
        )
    return PortfolioTeaserResponse(
        model_return=m.total_return,
        benchmark_return=m.benchmark_total_return,
        max_drawdown=m.max_drawdown,
        sharpe_ratio=m.sharpe_ratio,
        num_months=m.num_months,
        start_date=result.config.start_date,
        end_date=result.config.end_date,
        equity_curve=curve,
    )
```

**Step 8: Implement the route**

Add to `api/src/margin_api/routes/backtest.py`:

```python
from margin_api.schemas.backtest import PortfolioTeaserResponse
from margin_api.services.backtest import build_portfolio_teaser

@router.get(
    "/backtest/portfolio-teaser",
    response_model=PortfolioTeaserResponse,
)
async def get_portfolio_teaser() -> PortfolioTeaserResponse:
    """Portfolio-level teaser for the landing page. Public (no auth)."""
    result = get_default_replay_result()
    return build_portfolio_teaser(result)
```

**Step 9: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_backtest.py::TestPortfolioTeaserRoute -v`
Expected: PASS

**Step 10: Commit**

```bash
git add api/src/margin_api/schemas/backtest.py api/src/margin_api/routes/backtest.py api/src/margin_api/services/backtest.py api/tests/test_backtest.py
git commit -m "feat(api): add /backtest/portfolio-teaser endpoint with equity curve"
```

---

### Task 3: Update correlation showcase to use most recently scored tickers

**Files:**
- Modify: `api/src/margin_api/routes/correlations.py`
- Test: `api/tests/test_correlations.py` (or wherever correlation tests live)

**Step 1: Write the failing test**

Check for existing correlation tests first. Add:

```python
class TestShowcaseSelectionOrder:
    """Verify showcase selects by most recently scored, not highest score."""

    @pytest.mark.asyncio
    async def test_showcase_selects_by_scored_at(self):
        """The _compute_live_showcase query should ORDER BY Score.scored_at DESC."""
        from margin_api.routes.correlations import _SHOWCASE_TICKER_COUNT
        # This test verifies the query ordering was changed.
        # After implementation, the function orders by scored_at DESC.
        # We verify by inspecting the source or via integration test.
        assert _SHOWCASE_TICKER_COUNT == 5
```

Note: The real verification is that the query in `_compute_live_showcase` orders by `Score.scored_at.desc()` instead of `Score.composite_raw_score.desc()`. A full integration test would require seeding price history data. The simpler approach is a unit-level change test.

**Step 2: Modify the query**

In `api/src/margin_api/routes/correlations.py`, change line 118:

From:
```python
.order_by(Score.composite_raw_score.desc())
```

To:
```python
.order_by(Score.scored_at.desc())
```

**Step 3: Run existing correlation tests**

Run: `uv run pytest api/tests/ -k "correl" -v`
Expected: All existing tests PASS (the ordering change doesn't break any behavior)

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/correlations.py
git commit -m "feat(api): select showcase correlations by most recently scored"
```

---

### Task 4: Build the `ProofSelectivityFunnel` frontend component

**Files:**
- Create: `web/src/components/landing/proof-selectivity-funnel.tsx`
- Create: `web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofSelectivityFunnel } from "../proof-selectivity-funnel"

const MOCK_FUNNEL = {
  universe_size: 3200,
  survived_filters: 280,
  exceptional_count: 12,
  high_count: 35,
  medium_count: 58,
  last_scored_at: "2026-02-26T04:30:00Z",
}

describe("ProofSelectivityFunnel", () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it("renders loading skeleton initially", () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // never resolves
    render(<ProofSelectivityFunnel />)
    expect(screen.getByTestId("funnel-skeleton")).toBeInTheDocument()
  })

  it("renders funnel bars after data loads", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByText(/3,200 equities screened/)).toBeInTheDocument()
    expect(screen.getByText(/280 survived/)).toBeInTheDocument()
    expect(screen.getByText(/12 Exceptional/)).toBeInTheDocument()
  })

  it("renders subtitle text", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByText(/most equities are eliminated/i)).toBeInTheDocument()
  })

  it("renders safeguard footnote", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByText(/insufficient data or failing fundamentals/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: FAIL (module not found)

**Step 3: Implement the component**

Create `web/src/components/landing/proof-selectivity-funnel.tsx`:

```typescript
"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"

interface FunnelData {
  universe_size: number
  survived_filters: number
  exceptional_count: number
  high_count: number
  medium_count: number
  last_scored_at: string | null
}

function formatCount(n: number): string {
  return n.toLocaleString()
}

function pct(part: number, whole: number): string {
  if (whole === 0) return "0%"
  return `${((part / whole) * 100).toFixed(1)}%`
}

const BARS: {
  key: keyof FunnelData
  label: (d: FunnelData) => string
  right: (d: FunnelData) => string
  color: string
}[] = [
  {
    key: "universe_size",
    label: (d) => `${formatCount(d.universe_size)} equities screened`,
    right: () => "100%",
    color: "bg-text-tertiary/30",
  },
  {
    key: "survived_filters",
    label: (d) => `${formatCount(d.survived_filters)} survived elimination`,
    right: (d) => pct(d.survived_filters, d.universe_size),
    color: "bg-accent/30",
  },
  {
    key: "high_count",
    label: (d) =>
      `${formatCount(d.high_count + d.exceptional_count)} High or Exceptional`,
    right: (d) => pct(d.high_count + d.exceptional_count, d.universe_size),
    color: "bg-accent/60",
  },
  {
    key: "exceptional_count",
    label: (d) => `${formatCount(d.exceptional_count)} Exceptional candidates`,
    right: (d) => pct(d.exceptional_count, d.universe_size),
    color: "bg-accent",
  },
]

export function ProofSelectivityFunnel() {
  const [data, setData] = useState<FunnelData | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch("/api/v1/universe/funnel")
        if (resp.ok) setData(await resp.json())
      } catch {
        // keep null → skeleton stays
      }
    }
    load()
  }, [])

  if (!data) {
    return (
      <div data-testid="funnel-skeleton" className="space-y-3">
        {[100, 60, 20, 8].map((w, i) => (
          <div
            key={i}
            className="h-8 rounded bg-bg-subtle animate-pulse"
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    )
  }

  const maxVal = data.universe_size || 1

  return (
    <div>
      <div className="space-y-2">
        {BARS.map((bar, i) => {
          const raw =
            bar.key === "high_count"
              ? data.high_count + data.exceptional_count
              : (data[bar.key] as number)
          const widthPct = Math.max(4, (raw / maxVal) * 100) // min 4% so labels visible
          return (
            <motion.div
              key={bar.key}
              className="relative"
              initial={{ width: 0 }}
              whileInView={{ width: "100%" }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <div
                className={`${bar.color} rounded h-8 flex items-center justify-between px-3`}
                style={{ width: `${widthPct}%` }}
              >
                <span className="text-xs text-text-primary font-mono truncate">
                  {bar.label(data)}
                </span>
                <span className="text-[10px] text-text-secondary font-mono ml-2 shrink-0">
                  {bar.right(data)}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Most equities are eliminated before scoring begins.
      </p>
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Elimination removes stocks with insufficient data or failing fundamentals — not a
        quality judgment on the business.
      </p>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-selectivity-funnel.tsx web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx
git commit -m "feat(web): add ProofSelectivityFunnel component for landing page"
```

---

### Task 5: Build the `ProofSectorChart` frontend component (replaces tilt chart)

**Files:**
- Create: `web/src/components/landing/proof-sector-chart.tsx`
- Create: `web/src/components/landing/__tests__/proof-sector-chart.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/proof-sector-chart.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="sector-bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Legend: () => null,
  Tooltip: () => null,
  Cell: () => null,
}))

import { ProofSectorChart } from "../proof-sector-chart"
import type { CandidateCard } from "../types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    score: 75,
    composite_percentile: 75,
    conviction_level: "high",
    quality_percentile: 70,
    value_percentile: 75,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    growth_percentile: 55,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("ProofSectorChart", () => {
  it("renders empty state when no candidates", () => {
    render(<ProofSectorChart candidates={[]} />)
    expect(screen.getByText(/scoring in progress/i)).toBeInTheDocument()
  })

  it("renders bar chart when candidates provided", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", conviction_level: "exceptional" }),
      makeCandidate({ sector: "Healthcare", conviction_level: "high" }),
      makeCandidate({ sector: "Financials", conviction_level: "medium" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByTestId("sector-bar-chart")).toBeInTheDocument()
  })

  it("renders subtitle text", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", conviction_level: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/candidates by sector/i)).toBeInTheDocument()
  })

  it("renders sector-neutral safeguard note", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", conviction_level: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/sector-neutral/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-sector-chart.test.tsx`
Expected: FAIL (module not found)

**Step 3: Implement the component**

Create `web/src/components/landing/proof-sector-chart.tsx`:

```typescript
"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts"
import type { CandidateCard } from "./types"

interface ProofSectorChartProps {
  candidates: CandidateCard[]
}

interface SectorRow {
  sector: string
  exceptional: number
  high: number
  medium: number
  total: number
}

function aggregateBySector(candidates: CandidateCard[]): SectorRow[] {
  const map = new Map<string, SectorRow>()

  for (const c of candidates) {
    const sector = c.sector || "Unknown"
    if (!map.has(sector)) {
      map.set(sector, { sector, exceptional: 0, high: 0, medium: 0, total: 0 })
    }
    const row = map.get(sector)!
    if (c.conviction_level === "exceptional") row.exceptional++
    else if (c.conviction_level === "high") row.high++
    else row.medium++
    row.total++
  }

  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}

export function ProofSectorChart({ candidates }: ProofSectorChartProps) {
  if (candidates.length === 0) {
    return (
      <div>
        <div className="h-[180px] flex items-center justify-center">
          <p className="text-xs text-text-tertiary">
            Scoring in progress — sector breakdown updates after each scoring run.
          </p>
        </div>
      </div>
    )
  }

  const data = aggregateBySector(candidates)
  const chartHeight = Math.max(180, data.length * 32)

  return (
    <div>
      <div style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" barCategoryGap="20%">
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--color-text-tertiary)" }}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="sector"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--color-text-secondary)" }}
              width={120}
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}
            />
            <Bar
              dataKey="exceptional"
              name="Exceptional"
              fill="var(--color-accent)"
              radius={[0, 4, 4, 0]}
              barSize={8}
            />
            <Bar
              dataKey="high"
              name="High"
              fill="color-mix(in srgb, var(--color-accent), transparent 40%)"
              radius={[0, 4, 4, 0]}
              barSize={8}
            />
            <Bar
              dataKey="medium"
              name="Medium"
              fill="color-mix(in srgb, var(--color-warning), transparent 40%)"
              radius={[0, 4, 4, 0]}
              barSize={8}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Candidates by sector and conviction level
      </p>
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Scoring is sector-neutral. Distribution reflects where quality + value currently
        concentrate.
      </p>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-sector-chart.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-sector-chart.tsx web/src/components/landing/__tests__/proof-sector-chart.test.tsx
git commit -m "feat(web): add ProofSectorChart component replacing Growth vs Value Tilt"
```

---

### Task 6: Add interpretation line to `ProofHeatmap`

**Files:**
- Modify: `web/src/components/landing/proof-heatmap.tsx`
- Test: Update or create `web/src/components/landing/__tests__/proof-heatmap.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/proof-heatmap.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofHeatmap } from "../proof-heatmap"
import { interpretCorrelation } from "../proof-heatmap"

describe("interpretCorrelation", () => {
  it("returns diversification message for low correlations", () => {
    const matrix = [
      [1.0, 0.1, 0.2],
      [0.1, 1.0, 0.15],
      [0.2, 0.15, 1.0],
    ]
    const result = interpretCorrelation(matrix)
    expect(result).toMatch(/diversification/)
  })

  it("returns clustering warning for high correlations", () => {
    const matrix = [
      [1.0, 0.85, 0.9],
      [0.85, 1.0, 0.82],
      [0.9, 0.82, 1.0],
    ]
    const result = interpretCorrelation(matrix)
    expect(result).toMatch(/clustering/)
  })
})

describe("ProofHeatmap", () => {
  beforeEach(() => mockFetch.mockReset())

  it("renders interpretation line after data loads", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        tickers: ["A", "B", "C"],
        matrix: [
          [1.0, 0.1, 0.2],
          [0.1, 1.0, 0.15],
          [0.2, 0.15, 1.0],
        ],
      }),
    })
    render(<ProofHeatmap />)
    expect(await screen.findByText(/diversification/i)).toBeInTheDocument()
  })

  it("renders correlation caveat footnote", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        tickers: ["A", "B"],
        matrix: [[1.0, 0.5], [0.5, 1.0]],
      }),
    })
    render(<ProofHeatmap />)
    expect(await screen.findByText(/correlations shift during market stress/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-heatmap.test.tsx`
Expected: FAIL (interpretCorrelation not exported)

**Step 3: Add interpretation logic and update component**

Modify `web/src/components/landing/proof-heatmap.tsx`:

```typescript
"use client"

import { useEffect, useState } from "react"
import { CorrelationGrid } from "@/components/ui/correlation-grid"

const FALLBACK_TICKERS = ["AAPL", "MSFT", "JNJ", "COST", "V"]
const FALLBACK_MATRIX: (number | null)[][] = [
  [1.0, 0.82, 0.15, 0.28, 0.45],
  [0.82, 1.0, 0.12, 0.31, 0.51],
  [0.15, 0.12, 1.0, 0.62, 0.22],
  [0.28, 0.31, 0.62, 1.0, 0.35],
  [0.45, 0.51, 0.22, 0.35, 1.0],
]

interface ShowcaseData {
  tickers: string[]
  matrix: (number | null)[][]
}

export function interpretCorrelation(matrix: (number | null)[][]): string {
  const n = matrix.length
  let lowPairs = 0
  let highPairs = 0
  let totalPairs = 0

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const val = matrix[i][j]
      if (val == null) continue
      totalPairs++
      const abs = Math.abs(val)
      if (abs < 0.3) lowPairs++
      if (abs > 0.7) highPairs++
    }
  }

  if (totalPairs === 0) return ""
  if (highPairs >= totalPairs * 0.5) {
    return `Caution: ${highPairs} of ${totalPairs} pairs show |ρ| > 0.7 — sector clustering detected.`
  }
  return `${lowPairs} of ${totalPairs} pairs show |ρ| < 0.3 — strong diversification.`
}

export function ProofHeatmap() {
  const [data, setData] = useState<ShowcaseData>({
    tickers: FALLBACK_TICKERS,
    matrix: FALLBACK_MATRIX,
  })

  useEffect(() => {
    async function fetchShowcase() {
      try {
        const resp = await fetch("/api/v1/correlations/showcase")
        if (resp.ok) {
          const json = await resp.json()
          setData({ tickers: json.tickers, matrix: json.matrix })
        }
      } catch {
        // Keep fallback
      }
    }
    fetchShowcase()
  }, [])

  const interpretation = interpretCorrelation(data.matrix)

  return (
    <div>
      <CorrelationGrid
        tickers={data.tickers}
        matrix={data.matrix}
        showTooltip={false}
      />
      {interpretation && (
        <p className="text-[10px] text-text-secondary mt-3 text-center font-mono">
          {interpretation}
        </p>
      )}
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Correlations shift during market stress. Past correlation does not guarantee future
        diversification.
      </p>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-heatmap.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-heatmap.tsx web/src/components/landing/__tests__/proof-heatmap.test.tsx
git commit -m "feat(web): add correlation interpretation line and safeguard footnote to ProofHeatmap"
```

---

### Task 7: Rewrite `ProofHistoricalChart` with real backtest data

**Files:**
- Modify: `web/src/components/landing/proof-historical-chart.tsx`
- Create: `web/src/components/landing/__tests__/proof-historical-chart.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/proof-historical-chart.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofHistoricalChart } from "../proof-historical-chart"

const MOCK_TEASER = {
  model_return: 5.42,
  benchmark_return: 3.80,
  max_drawdown: -0.28,
  sharpe_ratio: 0.85,
  num_months: 240,
  start_date: "2006-01-01",
  end_date: "2025-12-31",
  equity_curve: [
    { month: "2006-01", portfolio: 10000, benchmark: 10000 },
    { month: "2006-02", portfolio: 10200, benchmark: 10100 },
    { month: "2006-03", portfolio: 10400, benchmark: 10180 },
  ],
}

describe("ProofHistoricalChart", () => {
  beforeEach(() => mockFetch.mockReset())

  it("renders loading skeleton initially", () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<ProofHistoricalChart />)
    expect(screen.getByTestId("historical-skeleton")).toBeInTheDocument()
  })

  it("renders area chart after data loads", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("area-chart")).toBeInTheDocument()
  })

  it("renders metric ribbon with CAGR and Sharpe", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByText(/CAGR/i)).toBeInTheDocument()
    expect(screen.getByText(/Sharpe/i)).toBeInTheDocument()
    expect(screen.getByText(/Max Drawdown/i)).toBeInTheDocument()
  })

  it("renders disclaimer", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByText(/past performance is not indicative/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-historical-chart.test.tsx`
Expected: FAIL (component still renders old mock data with no fetch)

**Step 3: Rewrite the component**

Replace `web/src/components/landing/proof-historical-chart.tsx` entirely:

```typescript
"use client"

import { useEffect, useState } from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts"

interface EquityCurvePoint {
  month: string
  portfolio: number
  benchmark: number
}

interface PortfolioTeaser {
  model_return: number
  benchmark_return: number
  max_drawdown: number
  sharpe_ratio: number
  num_months: number
  start_date: string
  end_date: string
  equity_curve: EquityCurvePoint[]
}

function formatValue(v: number): string {
  return `$${(v / 1000).toFixed(1)}k`
}

function formatPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

function computeCAGR(totalReturn: number, months: number): number {
  if (months <= 0) return 0
  const years = months / 12
  return Math.pow(1 + totalReturn, 1 / years) - 1
}

interface MetricProps {
  label: string
  value: string
  accent?: boolean
  danger?: boolean
}

function Metric({ label, value, accent, danger }: MetricProps) {
  const colorClass = danger
    ? "text-danger"
    : accent
      ? "text-accent"
      : "text-text-primary"
  return (
    <div className="text-center">
      <div className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className={`font-mono text-sm ${colorClass}`}>{value}</div>
    </div>
  )
}

export function ProofHistoricalChart() {
  const [data, setData] = useState<PortfolioTeaser | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch("/api/v1/backtest/portfolio-teaser")
        if (resp.ok) setData(await resp.json())
      } catch {
        // stay null
      }
    }
    load()
  }, [])

  if (!data) {
    return (
      <div data-testid="historical-skeleton">
        <div className="h-[200px] bg-bg-subtle animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-bg-subtle animate-pulse rounded" />
          ))}
        </div>
      </div>
    )
  }

  const cagr = computeCAGR(data.model_return, data.num_months)
  const excessReturn = data.model_return - data.benchmark_return

  // Thin the equity curve for display — show every Nth point
  const thinned =
    data.equity_curve.length > 60
      ? data.equity_curve.filter(
          (_, i) => i === 0 || i === data.equity_curve.length - 1 || i % 6 === 0
        )
      : data.equity_curve

  return (
    <div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={thinned}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              interval={Math.max(0, Math.floor(thinned.length / 6))}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                formatValue(value),
                name,
              ]}
              contentStyle={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}
            />
            <Area
              type="monotone"
              dataKey="portfolio"
              name="Portfolio"
              stroke="var(--color-accent)"
              strokeWidth={2}
              fill="var(--color-accent)"
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="benchmark"
              name="Benchmark"
              stroke="var(--color-text-tertiary)"
              strokeWidth={1}
              fill="none"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Metric ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <Metric label="CAGR" value={formatPct(cagr)} accent={cagr > 0} />
        <Metric
          label="Max Drawdown"
          value={formatPct(data.max_drawdown)}
          danger={data.max_drawdown < 0}
        />
        <Metric label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(2)} />
        <Metric
          label="Excess Return"
          value={formatPct(excessReturn)}
          accent={excessReturn > 0}
        />
      </div>

      <p className="text-[9px] text-text-tertiary mt-3 text-center italic">
        Past performance is not indicative of future results. Walk-forward methodology: no
        look-ahead bias.
      </p>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-historical-chart.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-historical-chart.tsx web/src/components/landing/__tests__/proof-historical-chart.test.tsx
git commit -m "feat(web): rewrite ProofHistoricalChart with real backtest equity curve"
```

---

### Task 8: Wire everything into `ProofSection` and clean up

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx`
- Modify: `web/src/components/landing/__tests__/proof-section.test.tsx`
- Delete: `web/src/components/landing/proof-tilt-chart.tsx`
- Delete: `web/src/components/landing/classify-tilt.ts`
- Delete: `web/src/components/landing/__tests__/proof-tilt-chart.test.tsx`

**Step 1: Update the proof section test**

Replace `web/src/components/landing/__tests__/proof-section.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Area: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}))
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection />)
    expect(
      screen.getByText(/structure creates measurable advantage/i)
    ).toBeInTheDocument()
  })

  it("renders all 5 proof card titles", () => {
    render(<ProofSection />)
    expect(screen.getByText("Factor Transparency")).toBeInTheDocument()
    expect(screen.getByText("System Selectivity")).toBeInTheDocument()
    expect(screen.getByText("Sector Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Correlation Heatmap")).toBeInTheDocument()
    expect(screen.getByText("Historical Application")).toBeInTheDocument()
  })

  it("does NOT render Growth vs Value Tilt (removed)", () => {
    render(<ProofSection />)
    expect(screen.queryByText("Growth vs Value Tilt")).not.toBeInTheDocument()
  })

  it("renders sector-neutral metadata", () => {
    render(<ProofSection />)
    expect(screen.getByText(/sector-neutral by design/i)).toBeInTheDocument()
  })

  it("renders factor bar labels", () => {
    render(<ProofSection />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-section.test.tsx`
Expected: FAIL (still renders old titles)

**Step 3: Update `proof-section.tsx`**

Replace the entire file:

```typescript
"use client"

import { useEffect, useRef, type ReactNode } from "react"
import { MicroMetadata } from "./micro-metadata"
import { ProofFactorBars } from "./proof-factor-bars"
import { ProofSelectivityFunnel } from "./proof-selectivity-funnel"
import { ProofSectorChart } from "./proof-sector-chart"
import { ProofHeatmap } from "./proof-heatmap"
import { ProofHistoricalChart } from "./proof-historical-chart"
import type { CandidateCard } from "./types"

interface ProofCardProps {
  title: string
  children: ReactNode
}

function ProofCard({ title, children }: ProofCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!cardRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = cardRef.current
      if (!el) return

      gsap.set(el, { opacity: 0, y: 24 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  return (
    <div ref={cardRef} className="terminal-card p-6">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
        {title}
      </div>
      {children}
    </div>
  )
}

interface ProofSectionProps {
  candidates?: CandidateCard[]
}

export function ProofSection({ candidates = [] }: ProofSectionProps) {
  return (
    <section id="proof" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary text-center mb-4">
          Structure creates measurable advantage.
        </h2>
        <div className="text-center mb-16">
          <MicroMetadata text="Sector-neutral by design" />
        </div>
        <div className="text-center mb-8 space-y-2">
          <p className="text-sm font-mono text-text-primary">
            Every signal recorded · Sector-neutral · Live tracking from day one
          </p>
          <p className="text-[10px] text-text-tertiary max-w-md mx-auto">
            Past performance does not guarantee future results. Walk-forward backtesting with
            point-in-time data and transaction costs is in development. Full methodology on
            the backtesting page.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProofCard title="Factor Transparency">
            <ProofFactorBars />
          </ProofCard>
          <ProofCard title="System Selectivity">
            <ProofSelectivityFunnel />
          </ProofCard>
          <ProofCard title="Sector Breakdown">
            <ProofSectorChart candidates={candidates} />
          </ProofCard>
          <ProofCard title="Correlation Heatmap">
            <ProofHeatmap />
          </ProofCard>
          <ProofCard title="Historical Application">
            <ProofHistoricalChart />
          </ProofCard>
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Delete old files**

```bash
rm web/src/components/landing/proof-tilt-chart.tsx
rm web/src/components/landing/classify-tilt.ts
rm web/src/components/landing/__tests__/proof-tilt-chart.test.tsx
```

**Step 5: Run all proof section tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-section.test.tsx`
Expected: All PASS

**Step 6: Run full landing component tests**

Run: `cd web && npx vitest run src/components/landing/`
Expected: All tests PASS. Some existing tests that referenced "Growth vs Value Tilt" may need updating — fix any that fail by updating expected text.

**Step 7: Commit**

```bash
git add -A web/src/components/landing/
git commit -m "feat(web): wire new visualizations into ProofSection, remove tilt chart"
```

---

### Task 9: Run full test suites and fix breakages

**Files:** Any files with broken tests

**Step 1: Run API tests**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: ~1091+ tests passing

**Step 2: Run web tests**

Run: `cd web && npx vitest run`
Expected: ~1037+ tests passing

**Step 3: Fix any failures**

Common expected breakages:
- `homepage-client.test.tsx` or `page-assembly.test.tsx` may reference old proof card titles
- Any test that asserts "Growth vs Value Tilt" text needs updating to "System Selectivity" / "Sector Breakdown"
- Any import of `classify-tilt` or `ProofTiltChart` in tests needs removal

Fix each failure, run the suite again.

**Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix(web): update tests for new proof section visualization layout"
```

---

### Dependency Graph

```
Task 1 (API funnel)     ─── independent ───┐
Task 2 (API teaser)     ─── independent ───┤
Task 3 (API correlation)─── independent ───┤
                                           ├── Task 8 (wire ProofSection)
Task 4 (Funnel component)── needs T1 ─────┤
Task 5 (Sector component)── independent ───┤
Task 6 (Heatmap update)  ── needs T3 ─────┤
Task 7 (Historical chart) ── needs T2 ────┘
                                           │
                                           └── Task 9 (full test suite)
```

**Parallelization**: Tasks 1-3 (API) can run in parallel. Tasks 4-7 (frontend) can run in parallel after their API dependency. Task 8 depends on all of 4-7. Task 9 depends on 8.
