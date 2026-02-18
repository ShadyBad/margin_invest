# Sector Card Outlines Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add sector-colored 2px left accent bars to dashboard candidate cards using CSS custom properties and a unified sector color palette.

**Architecture:** Sector colors defined as CSS variables in globals.css (light + dark), resolved via a TypeScript lookup map. The API's `PickSummary` schema gains a `sector` field populated from the existing `Asset.sector` column. The `StockCard` component applies sector color as an inline `borderLeftColor` style. Existing DNA `SECTOR_COLORS` are replaced with the new palette.

**Tech Stack:** CSS custom properties, TypeScript, Tailwind v4, FastAPI/Pydantic, React, Vitest

---

### Task 1: Add sector CSS variables to globals.css

**Files:**
- Modify: `web/src/app/globals.css:44-48` (after percentile colors in `@theme`)
- Modify: `web/src/app/globals.css:100-117` (in `.dark` block)

**Step 1: Add light mode sector variables**

Insert after the `--color-percentile-weak` line (line 48), before the elevation shadows block:

```css
  /* Sector accent colors (card left-bar, DNA blending) */
  --color-sector-tech: #5B7A8A;
  --color-sector-healthcare: #4F7A6B;
  --color-sector-financials: #4A5E7A;
  --color-sector-consumer-disc: #8A6254;
  --color-sector-consumer-staples: #7A7250;
  --color-sector-energy: #8A6E3A;
  --color-sector-industrials: #6B6E72;
  --color-sector-materials: #7A6050;
  --color-sector-real-estate: #7A7060;
  --color-sector-utilities: #5A7A5A;
  --color-sector-comms: #6E5A7A;
```

**Step 2: Add dark mode sector overrides**

Insert at the end of the `.dark` block (after `--color-caustic`, line 117):

```css
  --color-sector-tech: #7A9AAA;
  --color-sector-healthcare: #6A9A8A;
  --color-sector-financials: #6A7E9A;
  --color-sector-consumer-disc: #AA8274;
  --color-sector-consumer-staples: #9A9270;
  --color-sector-energy: #AA8E5A;
  --color-sector-industrials: #8B8E92;
  --color-sector-materials: #9A8070;
  --color-sector-real-estate: #9A9080;
  --color-sector-utilities: #7A9A7A;
  --color-sector-comms: #8E7A9A;
```

**Step 3: Verify CSS parses correctly**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next lint`
Expected: No CSS parse errors

**Step 4: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat(web): add sector color CSS variables for light and dark modes"
```

---

### Task 2: Create sector-colors.ts lookup map

**Files:**
- Create: `web/src/lib/sector-colors.ts`
- Test: `web/src/lib/__tests__/sector-colors.test.ts`

**Step 1: Write the failing test**

Create `web/src/lib/__tests__/sector-colors.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { getSectorColor, SECTOR_BORDER_COLOR } from "../sector-colors"

describe("SECTOR_BORDER_COLOR", () => {
  it("maps all 11 GICS sectors", () => {
    expect(Object.keys(SECTOR_BORDER_COLOR)).toHaveLength(11)
  })

  it("returns CSS variable references", () => {
    expect(SECTOR_BORDER_COLOR["Information Technology"]).toBe("var(--color-sector-tech)")
    expect(SECTOR_BORDER_COLOR["Energy"]).toBe("var(--color-sector-energy)")
  })
})

describe("getSectorColor", () => {
  it("returns sector color for known sector", () => {
    expect(getSectorColor("Information Technology")).toBe("var(--color-sector-tech)")
  })

  it("returns fallback for unknown sector", () => {
    expect(getSectorColor("Unknown")).toBe("var(--color-border-primary)")
  })

  it("returns fallback for null", () => {
    expect(getSectorColor(null)).toBe("var(--color-border-primary)")
  })

  it("returns fallback for undefined", () => {
    expect(getSectorColor(undefined)).toBe("var(--color-border-primary)")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/__tests__/sector-colors.test.ts`
Expected: FAIL — module not found

**Step 3: Write the implementation**

Create `web/src/lib/sector-colors.ts`:

```typescript
/**
 * Sector-to-CSS-variable mapping for card left-bar coloring.
 * Colors are defined in globals.css as --color-sector-* variables.
 */
export const SECTOR_BORDER_COLOR: Record<string, string> = {
  "Information Technology": "var(--color-sector-tech)",
  "Health Care": "var(--color-sector-healthcare)",
  "Financials": "var(--color-sector-financials)",
  "Consumer Discretionary": "var(--color-sector-consumer-disc)",
  "Consumer Staples": "var(--color-sector-consumer-staples)",
  "Energy": "var(--color-sector-energy)",
  "Industrials": "var(--color-sector-industrials)",
  "Materials": "var(--color-sector-materials)",
  "Real Estate": "var(--color-sector-real-estate)",
  "Utilities": "var(--color-sector-utilities)",
  "Communication Services": "var(--color-sector-comms)",
}

export function getSectorColor(sector: string | null | undefined): string {
  return SECTOR_BORDER_COLOR[sector ?? ""] ?? "var(--color-border-primary)"
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/__tests__/sector-colors.test.ts`
Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add web/src/lib/sector-colors.ts web/src/lib/__tests__/sector-colors.test.ts
git commit -m "feat(web): add sector-colors.ts lookup map with CSS variable references"
```

---

### Task 3: Replace DNA sector colors with new palette

**Files:**
- Modify: `web/src/lib/dna.ts:1-13` (SECTOR_COLORS constant)
- Modify: `api/src/margin_api/routes/dna.py:20-32` (SECTOR_COLORS dict)
- Test: `api/tests/routes/test_dna.py` (existing tests — verify they still pass)

**Step 1: Update frontend DNA colors**

Replace lines 1-13 in `web/src/lib/dna.ts`:

```typescript
export const SECTOR_COLORS: Record<string, string> = {
  "Information Technology": "#5B7A8A",
  "Health Care": "#4F7A6B",
  "Financials": "#4A5E7A",
  "Energy": "#8A6E3A",
  "Consumer Discretionary": "#8A6254",
  "Industrials": "#6B6E72",
  "Materials": "#7A6050",
  "Utilities": "#5A7A5A",
  "Real Estate": "#7A7060",
  "Communication Services": "#6E5A7A",
  "Consumer Staples": "#7A7250",
}
```

**Step 2: Update backend DNA colors**

Replace lines 20-32 in `api/src/margin_api/routes/dna.py`:

```python
SECTOR_COLORS: dict[str, str] = {
    "Information Technology": "#5b7a8a",
    "Health Care": "#4f7a6b",
    "Financials": "#4a5e7a",
    "Energy": "#8a6e3a",
    "Consumer Discretionary": "#8a6254",
    "Industrials": "#6b6e72",
    "Materials": "#7a6050",
    "Utilities": "#5a7a5a",
    "Real Estate": "#7a7060",
    "Communication Services": "#6e5a7a",
    "Consumer Staples": "#7a7250",
}
```

**Step 3: Run DNA tests to verify nothing breaks**

Run: `uv run pytest api/tests/routes/test_dna.py -v`
Expected: The `test_single_sector_uses_sector_color` test should pass since it compares against `SECTOR_COLORS["Information Technology"]` dynamically. All tests should PASS.

**Step 4: Commit**

```bash
git add web/src/lib/dna.ts api/src/margin_api/routes/dna.py
git commit -m "refactor: replace dark DNA sector colors with unified muted earth tone palette"
```

---

### Task 4: Add sector field to API PickSummary

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py:36` (add field)
- Modify: `api/src/margin_api/routes/dashboard.py:92` (add to SELECT)
- Modify: `api/src/margin_api/routes/dashboard.py:29-69` (add to _pick_summary_from_row)
- Test: `api/tests/test_dashboard.py` (add test for sector field)

**Step 1: Write the failing test**

Add to `api/tests/test_dashboard.py` inside `TestDashboardPicks` class (after `test_pick_includes_signal_and_conviction`):

```python
    async def test_pick_includes_sector(self, client):
        """Each pick includes the asset's GICS sector."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        aapl_pick = data["picks"][0]
        assert aapl_pick["sector"] == "Information Technology"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardPicks::test_pick_includes_sector -v`
Expected: FAIL — "sector" key not in response

**Step 3: Add sector field to PickSummary schema**

In `api/src/margin_api/schemas/dashboard.py`, add after line 36 (`timing_signal`):

```python
    sector: str | None = None
```

**Step 4: Add Asset.sector to the dashboard query SELECT**

In `api/src/margin_api/routes/dashboard.py`, modify line 92 to also select `Asset.sector`:

```python
    base = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"), Asset.sector.label("asset_sector"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
    )
```

**Step 5: Pass sector into PickSummary construction**

In `api/src/margin_api/routes/dashboard.py`, add to `_pick_summary_from_row()` inside the `PickSummary(...)` constructor (after `margin_of_safety`):

```python
        sector=getattr(row, "asset_sector", None),
```

**Step 6: Run the test to verify it passes**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardPicks::test_pick_includes_sector -v`
Expected: PASS

**Step 7: Run full dashboard test suite to verify no regressions**

Run: `uv run pytest api/tests/test_dashboard.py -v`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/src/margin_api/routes/dashboard.py api/tests/test_dashboard.py
git commit -m "feat(api): add sector field to PickSummary dashboard response"
```

---

### Task 5: Add sector to frontend PickSummary type

**Files:**
- Modify: `web/src/lib/api/types.ts:115` (add field)

**Step 1: Add sector to PickSummary interface**

In `web/src/lib/api/types.ts`, add after `timing_signal` (line 115):

```typescript
  sector?: string | null
```

**Step 2: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): add sector field to PickSummary frontend type"
```

---

### Task 6: Update StockCard to use sector left bar

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx:1-8` (add import)
- Modify: `web/src/components/dashboard/stock-card.tsx:23-32` (update getCardTierClasses)
- Modify: `web/src/components/dashboard/stock-card.tsx:93` (add inline style + border class)
- Test: `web/src/components/dashboard/__tests__/stock-card.test.tsx`

**Step 1: Write the failing tests**

Add a new describe block to `web/src/components/dashboard/__tests__/stock-card.test.tsx`:

```typescript
describe("StockCard sector left bar", () => {
  it("applies sector color as left border style", () => {
    render(<StockCard pick={{ ...basePick, sector: "Information Technology" }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-sector-tech)")
  })

  it("applies border-l-2 class for sector bar width", () => {
    render(<StockCard pick={{ ...basePick, sector: "Energy" }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
  })

  it("falls back to border-primary when sector is null", () => {
    render(<StockCard pick={{ ...basePick, sector: null }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-border-primary)")
  })

  it("falls back to border-primary when sector is undefined", () => {
    render(<StockCard pick={basePick} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-border-primary)")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: FAIL — sector not applied, no border-l-2 class

**Step 3: Update the component**

3a. Add import at the top of `stock-card.tsx` (after line 7):

```typescript
import { getSectorColor } from "@/lib/sector-colors"
```

3b. Update `getCardTierClasses` to remove conviction-based border classes. Replace the function (lines 23-32):

```typescript
function getCardTierClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "rounded-lg"
    case "high":
      return "rounded-lg"
    default:
      return "rounded-lg"
  }
}
```

3c. Update the card element's className and style (line 93). Replace the className/style attributes on the card div:

```tsx
      className={`relative bg-bg-elevated border border-border-primary border-l-2 cursor-pointer transition-all hover:scale-[1.01] hover:border-accent/20 p-6 ${getCardTierClasses(pick.conviction_level)} ${getCardShadow(pick.conviction_level)} ${className}`}
      style={{
        borderLeftColor: getSectorColor(pick.sector),
        transition: `transform 200ms ${INTERACTION_EASE}, box-shadow 200ms ${INTERACTION_EASE}, border-color 200ms ${INTERACTION_EASE}`,
      }}
```

Note: `border-l-2` is added to the base classes. The `borderLeftColor` inline style sets the sector color. The `hover:border-accent/20` only affects the base `border-color` (top/right/bottom); `border-left-color` is set inline so it takes precedence.

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: New sector tests PASS

**Step 5: Update broken existing tests**

The existing tests assert `border-accent/30` (exceptional) and `border-l-accent` (high). These classes no longer exist. Update the assertions in the existing `stock-card.test.tsx`:

Test "renders exceptional card with accent border and rounded-lg" — replace assertion:
```typescript
  it("renders exceptional card with rounded-lg and sector bar", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("rounded-lg")
    expect(card.className).toContain("border-l-2")
  })
```

Test "renders high card with left accent border" — replace assertion:
```typescript
  it("renders high card with sector bar", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "high", score: 80 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("rounded-lg")
  })
```

Test "renders watchlist card with no accent border" — update:
```typescript
  it("renders watchlist card with sector bar and no conviction glow", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "watchlist", score: 55 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("rounded-lg")
  })
```

**Step 6: Run full test suite to verify no regressions**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/dashboard/__tests__/stock-card.test.tsx
git commit -m "feat(web): apply sector-colored left accent bar to StockCard"
```

---

### Task 7: Run full test suites and verify

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All tests PASS (294+)

**Step 2: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests PASS

**Step 3: Commit if any remaining fixes were needed**

If all clean, no commit needed. If fixes were required, commit them:

```bash
git commit -am "fix: resolve test regressions from sector card outlines"
```
