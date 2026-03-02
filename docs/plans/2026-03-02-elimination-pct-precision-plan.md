# Elimination Percentage Precision Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the rounding issue where the elimination percentage displays "100%" instead of the actual value (e.g. "99.72%") by introducing adaptive decimal precision.

**Architecture:** Create a shared formatting utility `formatEliminationPct(eliminated, total)` that uses 2 decimals by default, expanding to 4 when 2 would misleadingly round to 100%. Update the two display sites (homepage vignette, asset-detail gauntlet) to use it.

**Tech Stack:** TypeScript, Vitest, React, Next.js

---

### Task 1: Create `formatEliminationPct` utility with tests

**Files:**
- Create: `web/src/lib/format-elimination-pct.ts`
- Create: `web/src/lib/__tests__/format-elimination-pct.test.ts`

**Step 1: Write the failing tests**

Create `web/src/lib/__tests__/format-elimination-pct.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { formatEliminationPct } from "../format-elimination-pct"

describe("formatEliminationPct", () => {
  it("returns '0%' when total is 0", () => {
    expect(formatEliminationPct(0, 0)).toBe("0")
  })

  it("returns '0%' when eliminated is 0", () => {
    expect(formatEliminationPct(0, 7300)).toBe("0")
  })

  it("formats normal percentages to 2 decimals, strips trailing zeros", () => {
    // 2000/7300 = 27.397...% → "27.4"
    expect(formatEliminationPct(2000, 7300)).toBe("27.4")
  })

  it("formats a clean percentage without unnecessary decimals", () => {
    // 7300/7300 = 100% → "100"
    expect(formatEliminationPct(7300, 7300)).toBe("100")
  })

  it("does NOT round to 100 when the true value is less than 100", () => {
    // 7299/7300 = 99.9863...% — 2 decimals would give 99.99, fine
    expect(formatEliminationPct(7299, 7300)).toBe("99.99")
  })

  it("expands to 4 decimals when 2 decimals would round to 100", () => {
    // 72999/73000 = 99.99863...% — 2 decimals rounds to 100.00 → expand
    expect(formatEliminationPct(72999, 73000)).toBe("99.9986")
  })

  it("handles the typical case from production (e.g. 99.72%)", () => {
    // 5580/5600 = 99.642...% → "99.64"
    expect(formatEliminationPct(5580, 5600)).toBe("99.64")
  })

  it("handles exact 50%", () => {
    expect(formatEliminationPct(500, 1000)).toBe("50")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/lib/__tests__/format-elimination-pct.test.ts`
Expected: FAIL — module not found

**Step 3: Write the implementation**

Create `web/src/lib/format-elimination-pct.ts`:

```ts
/**
 * Format an elimination percentage with adaptive precision.
 *
 * - 2 decimal places by default, trailing zeros stripped.
 * - If 2 decimals would round to 100 but the true value is < 100,
 *   expands to 4 decimals (also trailing-zero stripped).
 * - Returns the numeric string WITHOUT the "%" suffix so callers
 *   can position it however they like.
 */
export function formatEliminationPct(eliminated: number, total: number): string {
  if (total === 0) return "0"

  const pct = (eliminated / total) * 100

  // True 100%
  if (eliminated >= total) return "100"

  // Try 2 decimals first
  const twoDecimal = pct.toFixed(2)
  if (parseFloat(twoDecimal) < 100) {
    return stripTrailingZeros(twoDecimal)
  }

  // 2 decimals rounded to 100 but it's not really 100 → use 4
  const fourDecimal = pct.toFixed(4)
  return stripTrailingZeros(fourDecimal)
}

function stripTrailingZeros(s: string): string {
  if (!s.includes(".")) return s
  return s.replace(/\.?0+$/, "")
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/lib/__tests__/format-elimination-pct.test.ts`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add web/src/lib/format-elimination-pct.ts web/src/lib/__tests__/format-elimination-pct.test.ts
git commit -m "feat(web): add formatEliminationPct utility with adaptive precision"
```

---

### Task 2: Update `EliminationVignette` to accept string percentage

**Files:**
- Modify: `web/src/components/landing/elimination-vignette.tsx`
- Modify: `web/src/components/landing/__tests__/elimination-vignette.test.tsx`

**Step 1: Update the component**

In `web/src/components/landing/elimination-vignette.tsx`:

Change the prop type from `number` to `string`:

```ts
interface EliminationVignetteProps {
  eliminatedPct?: string
}
```

Change the fallback on line 55 from:

```ts
const pct = eliminatedPct ?? 70
```

to:

```ts
const pct = eliminatedPct ?? "70"
```

No other changes needed — `{pct}%` in the JSX works with strings too.

**Step 2: Update the test**

In `web/src/components/landing/__tests__/elimination-vignette.test.tsx`, change line 27:

From: `render(<EliminationVignette eliminatedPct={72} />)`
To: `render(<EliminationVignette eliminatedPct="72.45" />)`

And line 28:

From: `expect(screen.getByText(/72%/)).toBeInTheDocument()`
To: `expect(screen.getByText(/72\.45%/)).toBeInTheDocument()`

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/elimination-vignette.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/landing/elimination-vignette.tsx web/src/components/landing/__tests__/elimination-vignette.test.tsx
git commit -m "refactor(web): update EliminationVignette to accept string percentage"
```

---

### Task 3: Update `homepage-client.tsx` to use `formatEliminationPct`

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`

**Step 1: Update the component**

Add import at top:

```ts
import { formatEliminationPct } from "@/lib/format-elimination-pct"
```

Replace lines 32-36 (the `EliminationVignette` prop):

From:
```tsx
<EliminationVignette
  eliminatedPct={
    data && data.total_scored > 0
      ? Math.round(((data.total_scored - data.eligible_count) / data.total_scored) * 100)
      : undefined
  }
/>
```

To:
```tsx
<EliminationVignette
  eliminatedPct={
    data && data.total_scored > 0
      ? formatEliminationPct(data.total_scored - data.eligible_count, data.total_scored)
      : undefined
  }
/>
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/`
Expected: PASS

**Step 3: Commit**

```bash
git add web/src/components/landing/homepage-client.tsx
git commit -m "fix(web): use adaptive precision for homepage elimination percentage"
```

---

### Task 4: Update `EliminationGauntlet` to use `formatEliminationPct`

**Files:**
- Modify: `web/src/components/asset-detail/elimination-gauntlet.tsx`
- Modify: `web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`

**Step 1: Update the component**

Add import at top of `elimination-gauntlet.tsx`:

```ts
import { formatEliminationPct } from "@/lib/format-elimination-pct"
```

Replace lines 13-14:

From:
```ts
const eliminatedPct = totalScored != null && filtersSurvivedCount != null && totalScored > 0
  ? Math.round(((totalScored - filtersSurvivedCount) / totalScored) * 100)
  : null
```

To:
```ts
const eliminatedPct = totalScored != null && filtersSurvivedCount != null && totalScored > 0
  ? formatEliminationPct(totalScored - filtersSurvivedCount, totalScored)
  : null
```

**Step 2: Update the test**

In `web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`, line 50:

From: `expect(screen.getByText(/70% of the universe/i)).toBeInTheDocument()`
To: `expect(screen.getByText(/70\.25% of the universe/i)).toBeInTheDocument()`

This is because `(2847-847)/2847 = 70.2495...%` → `"70.25"` with adaptive formatting (previously `Math.round` produced `70`).

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`
Expected: PASS

**Step 4: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass, no regressions

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/elimination-gauntlet.tsx web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx
git commit -m "fix(web): use adaptive precision for asset-detail elimination percentage"
```
