# Correlation Heatmap — Design Document

**Date:** 2026-02-20
**Status:** Approved

## Problem

The correlation heatmap on the landing page is a static hardcoded visual. Only 3 of 25 cells display numeric values (0.82, 0.62, 0.51) due to an explicit annotation whitelist. No dynamic correlation computation exists anywhere in the stack. The feature is advertised ("Portfolio Correlation Mapping") but not implemented.

## Goal

Build a real, data-driven correlation heatmap that:
1. Shows on the **dashboard** for authenticated users (their top picks)
2. Shows on the **landing page** from pre-computed cached data (public, no auth)
3. Supports two modes: **return correlations** (price co-movement) and **factor score correlations** (scoring similarity)
4. Displays all cell values, not just a few

## Approach

Engine-computed, API-served. Correlation math lives in the engine package. A new API endpoint serves the matrix. Dashboard and landing page both consume the endpoint.

---

## Engine Layer

### Module: `engine/src/margin_engine/correlation.py`

**Return Correlations (Pearson):**
- Input: `dict[str, list[PriceBar]]`
- Process: extract `adj_close` → daily log returns → Pearson correlation
- Window: trailing 252 trading days (1 year)
- Minimum overlap: 30 trading days per pair, otherwise cell is `None`

**Factor Score Correlations (Pearson):**
- Input: `dict[str, FactorBreakdown]`
- Process: build feature vector from sub-score percentiles per ticker → Pearson correlation
- Shows which stocks score similarly, not price co-movement

### Output Model

```python
class ExcludedTicker(BaseModel):
    ticker: str
    reason: str

class CorrelationMatrix(BaseModel):
    tickers: list[str]
    method: Literal["returns", "factors"]
    matrix: list[list[float | None]]      # NxN, symmetric, diagonal=1.0
    sample_sizes: list[list[int]]         # NxN, overlapping observation count
    excluded: list[ExcludedTicker]
    window_days: int
    computed_at: datetime
```

**Invariants:**
- `matrix[i][j] == matrix[j][i]` (symmetric)
- `matrix[i][i] == 1.0` (diagonal)
- All values in `[-1.0, 1.0]` or `None`
- `None` means insufficient overlapping data (< 30 days)

---

## API Layer

### Authenticated Endpoint

```
GET /api/v1/correlations?method=returns|factors&tickers=AAPL,MSFT&window=252
```

- `method` (required): `returns` or `factors`
- `tickers` (optional): comma-separated. Defaults to user's top picks (buy/strong_buy signal)
- `window` (optional, returns only): integer days, default 252, max 504

**Behavior:**
- Caps at 10 tickers. If more qualify, takes top 10 by composite score.
- For `returns`: pulls price history from DB, passes to engine
- For `factors`: pulls latest scores from DB, extracts factor breakdowns, passes to engine

**Error responses:**
- No qualifying picks → 404: "No qualifying picks found. Score some tickers first."
- Fewer than 2 tickers → 400: "Need at least 2 tickers for correlation"

### Public Showcase Endpoint

```
GET /api/v1/correlations/showcase
```

- No auth required
- Returns pre-computed matrix for ~8 curated tickers (AAPL, MSFT, JNJ, COST, V, JPM, XOM, PG)
- Cached in Redis, 24-hour TTL
- Recomputed via CLI: `uv run python -m margin_api.cli correlations --showcase`
- Falls back to hardcoded matrix if cache empty

### Response Shape

```json
{
  "tickers": ["AAPL", "MSFT", "JNJ", "COST", "V"],
  "method": "returns",
  "matrix": [[1.0, 0.82, 0.15, 0.28, 0.45], ...],
  "sample_sizes": [[252, 250, 248, 252, 251], ...],
  "excluded": [],
  "window_days": 252,
  "computed_at": "2026-02-20T12:00:00Z"
}
```

---

## Frontend — Shared Renderer

### Component: `web/src/components/ui/correlation-grid.tsx`

```typescript
interface CorrelationGridProps {
  tickers: string[]
  matrix: (number | null)[][]
  sampleSizes?: number[][]
  showTooltip?: boolean
  className?: string
}
```

**Rendering:**
- Pure CSS grid, `(N+1) x (N+1)` (labels + cells)
- Column headers: ticker symbols, rotated -45deg
- Row headers: ticker symbols, right-aligned
- All cells show numeric values (2 decimal places)
- Diagonal cells: `1.00` in muted `text-text-tertiary`
- `None` cells: `—` with gray background

**Color encoding** (using `color-mix` with CSS variables):

| Range | Color | Opacity |
|-------|-------|---------|
| 0.6 to 1.0 | `--color-accent` | 15%–40% |
| 0.3 to 0.6 | `--color-accent` | 5%–15% |
| -0.3 to 0.3 | `--color-bg-elevated` | neutral |
| -0.6 to -0.3 | `--color-danger` | 5%–15% |
| -1.0 to -0.6 | `--color-danger` | 15%–40% |

**Text contrast:** `|value| >= 0.5` → `text-text-primary`, else `text-text-secondary`

**Tooltip (when enabled):**
```
AAPL x MSFT
p = 0.82
N = 250 days
```
150ms fade using `--duration-micro`.

**Legend:** Horizontal gradient bar (~200px), labels at -1.0, 0.0, +1.0. Font: `text-[9px] text-text-tertiary`.

**Responsive:**
- Desktop (md+): all values visible
- Mobile (<md), N <= 5: values visible
- Mobile (<md), N > 5: hide cell text, color + tap-to-tooltip

---

## Frontend — Dashboard Component

### Component: `web/src/components/dashboard/correlation-heatmap.tsx`

- Placed below Top Picks grid on the dashboard page
- Card styling: `bg-bg-elevated border border-border-primary rounded-lg p-6`
- Section header: `"Portfolio Correlations"` (uppercase tracking)
- Pill toggle at top-right: **Returns** | **Factors** (defaults to Returns)
- Client-side fetch via `getCorrelations(method, tickers?)`
- Loading skeleton while fetching
- Empty state: "Score at least 2 tickers to see portfolio correlations."
- Renders `<CorrelationGrid>` with `showTooltip={true}`

---

## Frontend — Landing Page Update

### Component: `web/src/components/landing/proof-heatmap.tsx`

- Fetches from `GET /api/v1/correlations/showcase`
- Falls back to hardcoded matrix if API unreachable
- Renders `<CorrelationGrid>` with `showTooltip={false}`
- Smaller cell sizing to fit `ProofCard` container
- No mode toggle (showcase is returns-only)

---

## Testing Plan

### Engine Tests (`engine/tests/test_correlation.py`)
- Golden-value test: hand-computed Pearson for 3 tickers x 5 data points
- Symmetry: `matrix[i][j] == matrix[j][i]`
- Diagonal: all `1.0`
- Insufficient overlap (< 30 days) → `None`
- Single ticker → error
- Perfect correlation → `1.0`, perfect inverse → `-1.0`
- NaN/missing price handling
- Factor correlation with known vectors

### API Tests (`api/tests/test_correlation_routes.py`)
- Authenticated endpoint with seeded data → 200, valid shape
- Both methods → valid responses
- Default tickers (omitted param) → top picks
- Explicit tickers → respected, capped at 10
- No picks → 404, < 2 picks → 400
- Showcase endpoint → 200, no auth
- Data contract: dimensions match, values in range, sample_sizes positive

### Frontend Tests (`web/src/components/ui/__tests__/correlation-grid.test.tsx`)
- Correct cell count for NxN input
- All values rendered as 2-decimal strings
- Null cells render `—`
- Color classes applied correctly
- Tooltip on hover with correct data
- Empty state when < 2 tickers
- Fallback data on API failure (landing page)

### Manual Validation
- Spot-check 3 cells against independent calculation
- DevTools network tab: confirm full matrix response
- Light/dark mode visual check
- Mobile viewport check

---

## Ticket

**Title:** Build dynamic portfolio correlation heatmap (dashboard + landing page)

**Impact:** High | **Severity:** Medium

**Repro (current state):**
1. Visit landing page → Proof section → Correlation Heatmap card
2. Only 3 cells show values (0.82, 0.62, 0.51)
3. All data hardcoded, no API, no computation
4. Dashboard has no correlation view

**Acceptance Criteria:**

- **Given** 3+ scored tickers with buy/strong_buy, **When** viewing dashboard, **Then** Portfolio Correlations card renders NxN heatmap
- **Given** the heatmap, **When** toggling Returns/Factors, **Then** matrix updates with corresponding method
- **Given** any cell, **When** hovering/tapping, **Then** tooltip shows ticker pair, value, sample size
- **Given** insufficient data for a pair, **When** rendering, **Then** cell shows `—` with gray background
- **Given** landing page loads with cached data, **Then** proof heatmap shows complete matrix with all values
- **Given** showcase endpoint unavailable, **Then** landing page falls back to hardcoded data
- **Given** mobile viewport with > 5 tickers, **Then** cell text hidden, color encoding preserved, tap-to-tooltip works
- **Given** dark mode, **Then** all text legible, colors use theme CSS variables
- **Given** < 2 qualifying tickers, **Then** empty state message shown
