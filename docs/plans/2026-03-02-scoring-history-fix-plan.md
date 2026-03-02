# Score Tracking Defensive Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the blank Score Tracking chart by replacing silent error swallowing with explicit loading/error/empty states and retry.

**Architecture:** The AssetPanel currently fetches score history and silently discards errors, producing a blank chart on any failure. We add an explicit status state machine (`idle → loading → loaded | error`) in AssetPanel, pass status down to ScoreChart and ScoreHistoryTable, and render distinct UI for each state.

**Tech Stack:** React 19, TypeScript, Vitest, @testing-library/react, Recharts

---

### Task 1: Add Status States to ScoreChart

**Files:**
- Modify: `web/src/components/dashboard/panel/score-chart.tsx:26-34` (ScoreChartProps)
- Modify: `web/src/components/dashboard/panel/score-chart.tsx:44-65` (component body)
- Test: `web/src/components/dashboard/panel/__tests__/score-chart.test.tsx`

**Step 1: Write failing tests for loading and error states**

Add these tests to the existing `score-chart.test.tsx`. The existing tests pass `data` but no `status` — update them to pass `status="loaded"`. Then add new loading/error tests.

```typescript
// Add to existing describe block in score-chart.test.tsx

it("renders loading skeleton when status is loading", () => {
  render(<ScoreChart data={[]} status="loading" timeRange="3M" showBenchmark={false} />)
  expect(screen.getByTestId("score-chart-loading")).toBeInTheDocument()
  expect(screen.queryByTestId("score-chart")).not.toBeInTheDocument()
  expect(screen.queryByTestId("score-chart-empty")).not.toBeInTheDocument()
})

it("renders error state with retry button when status is error", () => {
  const onRetry = vi.fn()
  render(<ScoreChart data={[]} status="error" timeRange="3M" showBenchmark={false} onRetry={onRetry} />)
  expect(screen.getByTestId("score-chart-error")).toBeInTheDocument()
  expect(screen.getByText("Unable to load score history")).toBeInTheDocument()
  const retryBtn = screen.getByRole("button", { name: /retry/i })
  retryBtn.click()
  expect(onRetry).toHaveBeenCalledOnce()
})

it("renders empty state when status is loaded with insufficient data", () => {
  render(<ScoreChart data={[{ date: "2026-01-01", score: 80 }]} status="loaded" timeRange="3M" showBenchmark={false} />)
  expect(screen.getByTestId("score-chart-empty")).toBeInTheDocument()
})

it("renders chart when status is loaded with sufficient data", () => {
  render(<ScoreChart data={mockData} status="loaded" timeRange="3M" showBenchmark={false} />)
  expect(screen.getByTestId("score-chart")).toBeInTheDocument()
})
```

Also update existing tests to pass `status="loaded"`:
- "renders chart when data is provided" → add `status="loaded"`
- "renders empty state when no data" → add `status="loaded"`
- "renders empty state with single data point" → add `status="loaded"`
- "renders score context strip" → add `status="loaded"`

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-chart.test.tsx`
Expected: FAIL — `status` prop doesn't exist yet, no `score-chart-loading` or `score-chart-error` testids

**Step 3: Implement status-aware ScoreChart**

In `score-chart.tsx`, update the props interface and component body:

```typescript
// Update ScoreChartProps (line 26-34)
interface ScoreChartProps {
  data: ScoreDataPoint[]
  status?: "loading" | "loaded" | "error"
  onRetry?: () => void
  timeRange: TimeRange
  showBenchmark: boolean
  benchmarkData?: ScoreDataPoint[]
  universeRank?: string
  scoringFrequency?: string
  lastScored?: string
}
```

Replace the top of the component function (lines 44-65) with status-aware rendering:

```typescript
export function ScoreChart({
  data,
  status = "loaded",
  onRetry,
  timeRange,
  showBenchmark,
  benchmarkData,
  universeRank,
  scoringFrequency,
  lastScored,
}: ScoreChartProps) {
  const gradientId = useId()

  if (status === "loading") {
    return (
      <div
        className="h-[320px] flex items-center justify-center"
        data-testid="score-chart-loading"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-[80%] max-w-[400px] space-y-3">
            <div className="h-3 bg-white/[0.04] rounded animate-pulse" />
            <div className="h-3 bg-white/[0.04] rounded animate-pulse w-[90%]" />
            <div className="h-3 bg-white/[0.04] rounded animate-pulse w-[70%]" />
            <div className="h-3 bg-white/[0.04] rounded animate-pulse w-[85%]" />
          </div>
          <span className="text-[11px] text-[#5C5955]/60 mt-2">Loading score history…</span>
        </div>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div
        className="h-[320px] flex flex-col items-center justify-center gap-3"
        data-testid="score-chart-error"
      >
        <span className="text-[13px] text-[#C74B50]">Unable to load score history</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-[12px] text-[#5C5955] hover:text-[#E8E6E3] border border-white/[0.08] rounded px-3 py-1 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    )
  }

  if (!data || data.length < 2) {
    // ... existing empty state (unchanged)
  }

  // ... rest of the function (sorted, sliced, chartData, return JSX) stays the same
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-chart.test.tsx`
Expected: PASS — all 8 tests (4 existing updated + 4 new)

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/score-chart.tsx web/src/components/dashboard/panel/__tests__/score-chart.test.tsx
git commit -m "feat(web): add loading/error status states to ScoreChart"
```

---

### Task 2: Add Status States to ScoreHistoryTable

**Files:**
- Modify: `web/src/components/dashboard/panel/score-history-table.tsx:16-18` (props)
- Modify: `web/src/components/dashboard/panel/score-history-table.tsx:22-55` (component body)
- Test: `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`

**Step 1: Write failing tests for loading and error states**

Add to existing `score-history-table.test.tsx`:

```typescript
it("renders loading skeleton when status is loading", () => {
  render(<ScoreHistoryTable history={[]} status="loading" />)
  expect(screen.getByTestId("score-history-loading")).toBeInTheDocument()
  expect(screen.queryByTestId("score-history-table")).not.toBeInTheDocument()
})

it("renders error state when status is error", () => {
  render(<ScoreHistoryTable history={[]} status="error" />)
  expect(screen.getByTestId("score-history-error")).toBeInTheDocument()
  expect(screen.getByText("Unable to load score history")).toBeInTheDocument()
})

it("renders empty state when status is loaded with no data", () => {
  render(<ScoreHistoryTable history={[]} status="loaded" />)
  expect(screen.getByText("No scoring history yet")).toBeInTheDocument()
})
```

Update existing tests to pass `status="loaded"`:
- "renders table with correct number of rows" → add `status="loaded"`
- "renders score values" → add `status="loaded"`
- "renders positive delta with up arrow" → add `status="loaded"`
- "renders negative delta" → add `status="loaded"`
- "sorts by date descending by default" → add `status="loaded"`
- "renders empty state" → add `status="loaded"`
- "handles full ISO datetime strings without showing Invalid Date" → add `status="loaded"`

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-history-table.test.tsx`
Expected: FAIL — `status` prop doesn't exist, no `score-history-loading` or `score-history-error` testids

**Step 3: Implement status-aware ScoreHistoryTable**

In `score-history-table.tsx`, update props and add status rendering before the existing empty check:

```typescript
interface ScoreHistoryTableProps {
  history: ScoreHistoryRow[]
  status?: "loading" | "loaded" | "error"
}

export function ScoreHistoryTable({ history, status = "loaded" }: ScoreHistoryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date")
  const [sortAsc, setSortAsc] = useState(false)

  // ... useMemo and handleSort stay the same ...

  if (status === "loading") {
    return (
      <div className="px-6 pt-4 pb-6" data-testid="score-history-loading">
        <div className="flex items-center justify-between mb-3">
          <div className="h-5 w-32 bg-white/[0.04] rounded animate-pulse" />
          <div className="h-4 w-16 bg-white/[0.04] rounded animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-[44px] bg-white/[0.02] rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div className="px-6 py-8 text-center" data-testid="score-history-error">
        <p className="text-[13px] text-[#C74B50]">Unable to load score history</p>
      </div>
    )
  }

  if (history.length === 0) {
    // ... existing empty state (unchanged)
  }

  // ... rest of the function stays the same
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-history-table.test.tsx`
Expected: PASS — all tests (7 existing updated + 3 new)

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/score-history-table.tsx web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx
git commit -m "feat(web): add loading/error status states to ScoreHistoryTable"
```

---

### Task 3: Wire Status State Machine in AssetPanel

**Files:**
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx:66-90` (state + effect)
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx:191-198` (ScoreChart props)
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx:258` (ScoreHistoryTable props)
- Test: `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`

**Step 1: Write failing tests for fetch lifecycle**

The existing `asset-panel.test.tsx` mocks all child components. We need to mock `getScoreHistory` and verify the status flow. Add at the top of the file:

```typescript
// Add to the existing mock section (after other vi.mock calls)
import * as scoresApi from "@/lib/api/scores"

vi.mock("@/lib/api/scores", () => ({
  getScoreHistory: vi.fn(),
}))
```

Update the `ScoreChart` mock to capture props:

```typescript
vi.mock("../score-chart", () => ({
  ScoreChart: (props: { status?: string; onRetry?: () => void }) => (
    <div data-testid="score-chart" data-status={props.status ?? "none"} onClick={props.onRetry} />
  ),
}))
```

Update the `ScoreHistoryTable` mock similarly:

```typescript
vi.mock("../score-history-table", () => ({
  ScoreHistoryTable: (props: { status?: string }) => (
    <div data-testid="score-history-table" data-status={props.status ?? "none"} />
  ),
}))
```

Add a default mock return for `getScoreHistory` in a `beforeEach` so existing tests still pass:

```typescript
beforeEach(() => {
  vi.mocked(scoresApi.getScoreHistory).mockResolvedValue({
    ticker: "AAPL",
    points: [],
    total_runs: 0,
  })
})
```

Add these tests to the existing describe block:

```typescript
it("passes loading status to ScoreChart while fetching", async () => {
  // Never-resolving promise simulates in-flight request
  vi.mocked(scoresApi.getScoreHistory).mockReturnValue(new Promise(() => {}))
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
  expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loading")
})

it("passes loaded status after successful fetch", async () => {
  const mockHistory = {
    ticker: "AAPL",
    points: [
      { scored_at: "2026-01-01T00:00:00Z", composite_percentile: 80, composite_raw_score: 75, quality_percentile: 85, value_percentile: 80, momentum_percentile: 82, composite_tier: "high", signal: "strong", margin_invest_value: 200, buy_price: 150, sell_price: 250, actual_price: 185, delta: null },
      { scored_at: "2026-01-08T00:00:00Z", composite_percentile: 82, composite_raw_score: 77, quality_percentile: 86, value_percentile: 81, momentum_percentile: 83, composite_tier: "high", signal: "strong", margin_invest_value: 205, buy_price: 152, sell_price: 252, actual_price: 187, delta: 2 },
    ],
    total_runs: 2,
  }
  vi.mocked(scoresApi.getScoreHistory).mockResolvedValue(mockHistory)
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
  await vi.waitFor(() => {
    expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loaded")
  })
})

it("passes error status when fetch fails", async () => {
  vi.mocked(scoresApi.getScoreHistory).mockRejectedValue(new Error("Network error"))
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
  await vi.waitFor(() => {
    expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "error")
  })
})

it("logs error to console when fetch fails", async () => {
  const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})
  vi.mocked(scoresApi.getScoreHistory).mockRejectedValue(new Error("Network error"))
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
  await vi.waitFor(() => {
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("[ScoreHistory]"),
      expect.any(Error),
    )
  })
  consoleSpy.mockRestore()
})

it("retries fetch when onRetry is triggered after error", async () => {
  vi.mocked(scoresApi.getScoreHistory).mockRejectedValueOnce(new Error("fail"))
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
  await vi.waitFor(() => {
    expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "error")
  })
  // Reset to success for retry
  const mockHistory = {
    ticker: "AAPL",
    points: [
      { scored_at: "2026-01-01T00:00:00Z", composite_percentile: 80, composite_raw_score: 75, quality_percentile: 85, value_percentile: 80, momentum_percentile: 82, composite_tier: "high", signal: "strong", margin_invest_value: 200, buy_price: 150, sell_price: 250, actual_price: 185, delta: null },
      { scored_at: "2026-01-08T00:00:00Z", composite_percentile: 82, composite_raw_score: 77, quality_percentile: 86, value_percentile: 81, momentum_percentile: 83, composite_tier: "high", signal: "strong", margin_invest_value: 205, buy_price: 152, sell_price: 252, actual_price: 187, delta: 2 },
    ],
    total_runs: 2,
  }
  vi.mocked(scoresApi.getScoreHistory).mockResolvedValue(mockHistory)
  // Trigger retry via the ScoreChart mock (onClick = onRetry)
  screen.getByTestId("score-chart").click()
  await vi.waitFor(() => {
    expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loaded")
  })
  expect(scoresApi.getScoreHistory).toHaveBeenCalledTimes(2)
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: FAIL — no `status` prop passed, `getScoreHistory` mock not configured for existing tests

**Step 3: Implement the state machine in AssetPanel**

Replace the state declarations and fetch effect in `asset-panel.tsx` (lines 66-90):

```typescript
export function AssetPanel({ isOpen, onClose, ticker, scoredResult, metrics }: AssetPanelProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("3M")
  const [historyData, setHistoryData] = useState<ScoreHistoryResponse | null>(null)
  const [historyStatus, setHistoryStatus] = useState<"loading" | "loaded" | "error">("loading")
  const [retryCount, setRetryCount] = useState(0)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose()
  }, [onClose])

  useEffect(() => {
    if (!isOpen) return
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, handleKeyDown])

  useEffect(() => {
    if (!isOpen || !ticker) return
    let cancelled = false
    setHistoryStatus("loading")
    setHistoryData(null)
    getScoreHistory(ticker)
      .then((data) => {
        if (!cancelled) {
          setHistoryData(data)
          setHistoryStatus("loaded")
        }
      })
      .catch((err) => {
        console.error(`[ScoreHistory] Failed to fetch history for ${ticker}:`, err)
        if (!cancelled) setHistoryStatus("error")
      })
    return () => { cancelled = true }
  }, [isOpen, ticker, retryCount])

  const retryHistory = useCallback(() => {
    setRetryCount((c) => c + 1)
  }, [])
```

Then update the ScoreChart usage (around line 191):

```typescript
<ScoreChart
  data={scoreChartData}
  status={historyStatus}
  onRetry={retryHistory}
  timeRange={timeRange}
  showBenchmark={false}
  universeRank={universeRank}
  scoringFrequency="Scored weekly"
  lastScored={scoredResult.scored_at ? "Recent" : undefined}
/>
```

And the ScoreHistoryTable usage (around line 258):

```typescript
<ScoreHistoryTable history={scoreHistory} status={historyStatus} />
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: PASS — all tests (6 existing + 5 new lifecycle tests)

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/asset-panel.tsx web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx
git commit -m "feat(web): wire score history status state machine in AssetPanel

Replace silent .catch(() => {}) with explicit loading/error/loaded
states. Log errors to console for debugging. Add retry mechanism."
```

---

### Task 4: Run Full Test Suite and Verify

**Files:** None (verification only)

**Step 1: Run all panel-related tests**

Run: `cd web && npx vitest run src/components/dashboard/panel/`
Expected: PASS — all tests across all panel components

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: PASS — no regressions across the entire web app

**Step 3: Run linter**

Run: `cd web && npx eslint src/components/dashboard/panel/score-chart.tsx src/components/dashboard/panel/score-history-table.tsx src/components/dashboard/panel/asset-panel.tsx`
Expected: No errors

**Step 4: Commit (if any lint fixes needed)**

Only if step 3 required changes:
```bash
git add -u && git commit -m "style(web): lint fixes for score history components"
```
