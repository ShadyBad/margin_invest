# Strategic Dominance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Margin Invest from B- product wrapping into A- experience that converts, retains, and signals premium — following the approved strategic dominance design.

**Architecture:** All changes are in the `web/` Next.js 15 frontend. No engine or API changes in Phase 1. Components use Vitest + React Testing Library for tests. Tailwind CSS v4 with CSS custom properties defined in `globals.css`. Framer Motion for animations.

**Tech Stack:** Next.js 15, React, TypeScript, Tailwind CSS v4, Framer Motion, Vitest, React Testing Library

**Test command:** `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run --reporter verbose`

---

## Phase 1: "Make It Convert" (P0)

### Task 1: 5-Tier Percentile Bar Color Encoding

The current `PercentileBar` uses a 4-tier system where everything above 70 looks the same emerald green. The new 5-tier system creates visual differentiation between "strong" and "exceptional."

**Files:**
- Modify: `web/src/components/ui/percentile-bar.tsx`
- Test: `web/src/components/ui/__tests__/percentile-bar.test.tsx`

**Step 1: Update the existing test to cover 5-tier colors**

Add tests for the new color tiers. The existing test file already exists — add new test cases:

```tsx
// In web/src/components/ui/__tests__/percentile-bar.test.tsx
// Add these test cases:

it("renders exceptional tier (90-100) with bright green", () => {
  render(<PercentileBar value={95} label="Quality" />)
  const bar = document.querySelector("[style]")
  expect(bar?.className).toContain("bg-percentile-exceptional")
})

it("renders strong tier (70-89) with emerald", () => {
  render(<PercentileBar value={75} label="Quality" />)
  const bar = document.querySelector("[style]")
  expect(bar?.className).toContain("bg-percentile-strong")
})

it("renders average tier (50-69) with gray", () => {
  render(<PercentileBar value={55} label="Quality" />)
  const bar = document.querySelector("[style]")
  expect(bar?.className).toContain("bg-percentile-average")
})

it("renders below-average tier (30-49) with amber", () => {
  render(<PercentileBar value={35} label="Quality" />)
  const bar = document.querySelector("[style]")
  expect(bar?.className).toContain("bg-percentile-below")
})

it("renders weak tier (0-29) with red", () => {
  render(<PercentileBar value={15} label="Quality" />)
  const bar = document.querySelector("[style]")
  expect(bar?.className).toContain("bg-percentile-weak")
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/ui/__tests__/percentile-bar.test.tsx --reporter verbose`
Expected: FAIL — `bg-percentile-exceptional` class doesn't exist yet

**Step 3: Add CSS custom properties for 5-tier colors**

In `web/src/app/globals.css`, add inside the existing `@theme` block (after the existing color definitions):

```css
--color-percentile-exceptional: #10B981;
--color-percentile-strong: #1C7A5A;
--color-percentile-average: #6B7280;
--color-percentile-below: #D97706;
--color-percentile-weak: #DC2626;
```

**Step 4: Update PercentileBar component**

Replace the `getColor` function and update bar styling in `web/src/components/ui/percentile-bar.tsx`:

```tsx
interface PercentileBarProps {
  value: number
  label?: string
  showValue?: boolean
  className?: string
}

export function PercentileBar({ value, label, showValue = true, className = "" }: PercentileBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value))

  const getColor = (v: number) => {
    if (v >= 90) return "bg-percentile-exceptional"
    if (v >= 70) return "bg-percentile-strong"
    if (v >= 50) return "bg-percentile-average"
    if (v >= 30) return "bg-percentile-below"
    return "bg-percentile-weak"
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {label && (
        <span className="text-sm text-text-secondary w-40 shrink-0 truncate" title={label}>
          {label}
        </span>
      )}
      <div className="flex-1 h-[6px] bg-bg-primary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-r-full transition-all ${getColor(clampedValue)}`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showValue && (
        <span className="text-sm font-mono text-text-primary w-10 text-right">
          {clampedValue.toFixed(0)}
        </span>
      )}
    </div>
  )
}
```

Key changes:
- `getColor` now returns 5 tiers instead of 4
- Bar height changed from `h-2` to `h-[6px]`
- Right end cap: `rounded-r-full` on the fill div (track stays `rounded-full`)

**Step 5: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/ui/__tests__/percentile-bar.test.tsx --reporter verbose`
Expected: PASS

**Step 6: Commit**

```bash
git add web/src/components/ui/percentile-bar.tsx web/src/components/ui/__tests__/percentile-bar.test.tsx web/src/app/globals.css
git commit -m "feat(web): add 5-tier percentile bar color encoding

Differentiates exceptional (90+), strong (70-89), average (50-69),
below-average (30-49), and weak (0-29) with distinct colors."
```

---

### Task 2: Stock Card Visual Hierarchy

Cards currently look identical regardless of conviction level. This adds tiered visual treatment so exceptional picks visually pop.

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Test: `web/src/components/dashboard/__tests__/stock-card.test.tsx` (create if doesn't exist)

**Step 1: Write test for tiered card styling**

Create `web/src/components/dashboard/__tests__/stock-card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { StockCard } from "../stock-card"
import type { PickSummary } from "@/lib/api/types"

// Mock the API call
vi.mock("@/lib/api/scores", () => ({
  getScore: vi.fn(),
}))

const basePick: PickSummary = {
  ticker: "AAPL",
  name: "Apple Inc.",
  score: 92,
  universe_percentile: 95,
  composite_percentile: 95,
  conviction_level: "exceptional",
  signal: "buy",
  quality_percentile: 90,
  value_percentile: 85,
  momentum_percentile: 88,
  actual_price: 150,
  buy_price: 140,
  sell_price: 180,
  price_upside: 0.2,
}

describe("StockCard visual hierarchy", () => {
  it("renders exceptional card with left accent border", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("border-l-accent")
  })

  it("renders high card with subtle left border", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "high", score: 80 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l")
    expect(card.className).not.toContain("border-l-2")
  })

  it("renders watchlist card with no left border", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "watchlist", score: 55 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).not.toContain("border-l-accent")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/dashboard/__tests__/stock-card.test.tsx --reporter verbose`
Expected: FAIL — no tiered classes applied

**Step 3: Add tiered styling to StockCard**

In `web/src/components/dashboard/stock-card.tsx`, add a helper function before the component:

```tsx
function getCardTierClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "border-l-2 border-l-accent bg-accent/[0.03]"
    case "high":
      return "border-l border-l-border-primary"
    default:
      return ""
  }
}
```

Then update the card's root `div` className:

```tsx
<div
  className={`bg-bg-elevated border border-border-primary rounded-sm p-6 cursor-pointer transition-all ${expanded ? "col-span-full" : ""} ${getCardTierClasses(pick.conviction_level)} ${className}`}
  data-testid={`stock-card-${pick.ticker}`}
  // ... rest unchanged
>
```

Also update the score display to use tier-appropriate color:

```tsx
<span className={`text-3xl font-bold ${
  pick.conviction_level === "exceptional" ? "text-accent" :
  pick.conviction_level === "high" ? "text-text-primary" :
  "text-text-secondary"
}`}>
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/dashboard/__tests__/stock-card.test.tsx --reporter verbose`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/dashboard/__tests__/stock-card.test.tsx
git commit -m "feat(web): add visual hierarchy to stock cards by conviction level

Exceptional: left accent border + subtle bg tint
High: subtle left border
Watchlist: no left border, muted score color"
```

---

### Task 3: Portfolio Conviction Score in Dashboard Header

The dashboard header currently shows just "Dashboard" + "Last updated." Add a portfolio-level conviction score (average of all scores) to create an immediate value metric.

**Files:**
- Create: `web/src/components/dashboard/portfolio-conviction.tsx`
- Modify: `web/src/app/dashboard/page.tsx`
- Modify: `web/src/lib/api/types.ts` (add portfolio score to DashboardResponse)
- Test: `web/src/components/dashboard/__tests__/portfolio-conviction.test.tsx`

**Step 1: Write the test for PortfolioConviction component**

Create `web/src/components/dashboard/__tests__/portfolio-conviction.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { PortfolioConviction } from "../portfolio-conviction"

describe("PortfolioConviction", () => {
  it("renders the portfolio score", () => {
    render(<PortfolioConviction score={74} label="Operating" />)
    expect(screen.getByText("74")).toBeInTheDocument()
    expect(screen.getByText("Operating")).toBeInTheDocument()
  })

  it("renders Operating label for scores >= 60", () => {
    render(<PortfolioConviction score={65} label="Operating" />)
    expect(screen.getByText("Operating")).toBeInTheDocument()
  })

  it("renders Building label for scores 30-59", () => {
    render(<PortfolioConviction score={45} label="Building" />)
    expect(screen.getByText("Building")).toBeInTheDocument()
  })

  it("renders Reviewing label for scores < 30", () => {
    render(<PortfolioConviction score={20} label="Reviewing" />)
    expect(screen.getByText("Reviewing")).toBeInTheDocument()
  })

  it("renders nothing when score is null", () => {
    const { container } = render(<PortfolioConviction score={null} label={null} />)
    expect(container.firstChild).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/dashboard/__tests__/portfolio-conviction.test.tsx --reporter verbose`
Expected: FAIL — component doesn't exist

**Step 3: Create PortfolioConviction component**

Create `web/src/components/dashboard/portfolio-conviction.tsx`:

```tsx
interface PortfolioConvictionProps {
  score: number | null
  label: string | null
  className?: string
}

export function PortfolioConviction({ score, label, className = "" }: PortfolioConvictionProps) {
  if (score == null) return null

  return (
    <div className={`flex flex-col items-end ${className}`} data-testid="portfolio-conviction">
      <span className="text-[11px] font-medium text-text-secondary tracking-[0.2px] uppercase mb-1">
        Portfolio Conviction
      </span>
      <div className="flex items-baseline gap-2">
        <span className="text-[40px] font-bold font-mono text-accent leading-none tracking-[-1px]">
          {score.toFixed(0)}
        </span>
        <span className="text-[13px] text-text-secondary font-mono">/100</span>
      </div>
      {label && (
        <span className="text-[13px] text-accent font-medium mt-1">
          {label}
        </span>
      )}
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/dashboard/__tests__/portfolio-conviction.test.tsx --reporter verbose`
Expected: PASS

**Step 5: Compute portfolio score in dashboard page**

In `web/src/app/dashboard/page.tsx`, add a helper to compute portfolio score from picks, and wire the component into the header. Add the import and helper function:

```tsx
import { PortfolioConviction } from "@/components/dashboard/portfolio-conviction"

function computePortfolioConviction(picks: PickSummary[]): { score: number; label: string } | null {
  if (picks.length === 0) return null
  const avg = picks.reduce((sum, p) => sum + (p.score || p.composite_percentile), 0) / picks.length
  const score = Math.round(avg)
  const label = score >= 60 ? "Operating" : score >= 30 ? "Building" : "Reviewing"
  return { score, label }
}
```

Also import `PickSummary`:

```tsx
import type { DashboardResponse, PickSummary } from "@/lib/api/types"
```

Then update the dashboard header JSX from:

```tsx
<div className="mb-8">
  <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
  {data?.last_updated && (
    <p className="text-sm text-text-secondary mt-1">
      Last updated: {formatLastUpdated(data.last_updated)}
    </p>
  )}
</div>
```

To:

```tsx
<div className="mb-8 flex items-start justify-between">
  <div>
    <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
    {data?.last_updated && (
      <p className="text-sm text-text-secondary mt-1">
        Last updated: {formatLastUpdated(data.last_updated)}
      </p>
    )}
  </div>
  {data?.picks && (() => {
    const conviction = computePortfolioConviction(data.picks)
    return conviction ? (
      <PortfolioConviction score={conviction.score} label={conviction.label} />
    ) : null
  })()}
</div>
```

**Step 6: Export from barrel**

Add to `web/src/components/dashboard/index.ts`:

```tsx
export { PortfolioConviction } from "./portfolio-conviction"
```

**Step 7: Run all dashboard tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/app/dashboard/__tests__/ src/components/dashboard/__tests__/ --reporter verbose`
Expected: PASS

**Step 8: Commit**

```bash
git add web/src/components/dashboard/portfolio-conviction.tsx web/src/components/dashboard/__tests__/portfolio-conviction.test.tsx web/src/components/dashboard/index.ts web/src/app/dashboard/page.tsx
git commit -m "feat(web): add portfolio conviction score to dashboard header

Computes average score across all picks and displays it prominently
with Operating/Building/Reviewing status label."
```

---

### Task 4: Free Tier Scarcity Indicator in FloatingNav

The free tier's 3-ticker limit is invisible. Add a visible counter pill in the app nav.

**Files:**
- Create: `web/src/components/nav/usage-pill.tsx`
- Modify: `web/src/components/nav/floating-nav.tsx`
- Test: `web/src/components/nav/__tests__/usage-pill.test.tsx`

**Step 1: Write the test**

Create `web/src/components/nav/__tests__/usage-pill.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { UsagePill } from "../usage-pill"

describe("UsagePill", () => {
  it("renders usage count", () => {
    render(<UsagePill used={1} limit={3} />)
    expect(screen.getByText("1/3")).toBeInTheDocument()
  })

  it("shows warning style when limit reached", () => {
    render(<UsagePill used={3} limit={3} />)
    const pill = screen.getByTestId("usage-pill")
    expect(pill.className).toContain("text-warning")
  })

  it("shows accent style when under limit", () => {
    render(<UsagePill used={1} limit={3} />)
    const pill = screen.getByTestId("usage-pill")
    expect(pill.className).toContain("text-accent")
  })

  it("renders nothing for unlimited plans", () => {
    const { container } = render(<UsagePill used={0} limit={null} />)
    expect(container.firstChild).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/usage-pill.test.tsx --reporter verbose`
Expected: FAIL — component doesn't exist

**Step 3: Create UsagePill component**

Create `web/src/components/nav/usage-pill.tsx`:

```tsx
interface UsagePillProps {
  used: number
  limit: number | null
  className?: string
}

export function UsagePill({ used, limit, className = "" }: UsagePillProps) {
  if (limit == null) return null

  const atLimit = used >= limit

  return (
    <span
      className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
        atLimit
          ? "bg-warning/10 text-warning"
          : "bg-accent/10 text-accent"
      } ${className}`}
      data-testid="usage-pill"
      title={atLimit
        ? `All ${limit} analyses used this month`
        : `${limit - used} analyses remaining this month`
      }
    >
      {used}/{limit}
    </span>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/usage-pill.test.tsx --reporter verbose`
Expected: PASS

**Step 5: Wire into FloatingNav**

In `web/src/components/nav/floating-nav.tsx`, import and add the pill to the app variant nav. Add it between the center links and the right side (Avatar/Sign Out):

Import at top:
```tsx
import { UsagePill } from "./usage-pill"
```

In the desktop right side section (the `hidden md:flex` div), add the pill before the session check. For now, hardcode the values since we don't have a usage API endpoint yet — we'll add a TODO comment:

```tsx
{/* Desktop right side */}
<div className="hidden md:flex items-center gap-3">
  {variant === "app" && (
    // TODO: Wire to real usage API endpoint
    <UsagePill used={0} limit={3} />
  )}
  {variant === "public" ? (
    // ... existing code unchanged
```

**Step 6: Run all nav tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/ --reporter verbose`
Expected: PASS

**Step 7: Commit**

```bash
git add web/src/components/nav/usage-pill.tsx web/src/components/nav/__tests__/usage-pill.test.tsx web/src/components/nav/floating-nav.tsx
git commit -m "feat(web): add free tier usage pill to app nav

Shows X/3 analyses used counter. Turns amber when limit reached.
Hidden for unlimited plans."
```

---

### Task 5: Onboarding Flow

This is the highest-impact conversion fix. Currently all CTAs go to `/dashboard` which shows pre-scored tickers the user didn't choose. The new flow lets users enter their own tickers and see personalized scores.

**Files:**
- Create: `web/src/app/onboarding/page.tsx`
- Create: `web/src/components/onboarding/ticker-input.tsx`
- Create: `web/src/components/onboarding/scoring-animation.tsx`
- Create: `web/src/components/onboarding/onboarding-results.tsx`
- Test: `web/src/components/onboarding/__tests__/ticker-input.test.tsx`
- Modify: `web/src/components/landing/sections/hero-section.tsx` (change CTA href)
- Modify: `web/src/components/landing/sections/pricing-section.tsx` (change CTA hrefs)
- Modify: `web/src/components/landing/sections/final-cta.tsx` (change CTA href)

**Step 1: Write test for TickerInput component**

Create `web/src/components/onboarding/__tests__/ticker-input.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react"
import { TickerInput } from "../ticker-input"

describe("TickerInput", () => {
  it("renders input field with placeholder", () => {
    render(<TickerInput onSubmit={vi.fn()} />)
    expect(screen.getByPlaceholderText("AAPL, MSFT, GOOGL")).toBeInTheDocument()
  })

  it("calls onSubmit with parsed tickers", () => {
    const onSubmit = vi.fn()
    render(<TickerInput onSubmit={onSubmit} />)
    const input = screen.getByPlaceholderText("AAPL, MSFT, GOOGL")
    fireEvent.change(input, { target: { value: "AAPL, MSFT, GOOGL" } })
    fireEvent.click(screen.getByText("Score my positions"))
    expect(onSubmit).toHaveBeenCalledWith(["AAPL", "MSFT", "GOOGL"])
  })

  it("disables submit with empty input", () => {
    render(<TickerInput onSubmit={vi.fn()} />)
    const button = screen.getByText("Score my positions")
    expect(button).toBeDisabled()
  })

  it("uppercases and trims tickers", () => {
    const onSubmit = vi.fn()
    render(<TickerInput onSubmit={onSubmit} />)
    const input = screen.getByPlaceholderText("AAPL, MSFT, GOOGL")
    fireEvent.change(input, { target: { value: " aapl , msft " } })
    fireEvent.click(screen.getByText("Score my positions"))
    expect(onSubmit).toHaveBeenCalledWith(["AAPL", "MSFT"])
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/onboarding/__tests__/ticker-input.test.tsx --reporter verbose`
Expected: FAIL — module not found

**Step 3: Create TickerInput component**

Create `web/src/components/onboarding/ticker-input.tsx`:

```tsx
"use client"

import { useState } from "react"

interface TickerInputProps {
  onSubmit: (tickers: string[]) => void
  loading?: boolean
}

export function TickerInput({ onSubmit, loading = false }: TickerInputProps) {
  const [value, setValue] = useState("")

  const parseTickers = (input: string): string[] =>
    input
      .split(/[,\s]+/)
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0)

  const tickers = parseTickers(value)

  const handleSubmit = () => {
    if (tickers.length > 0) {
      onSubmit(tickers)
    }
  }

  return (
    <div className="w-full max-w-[480px]">
      <label className="block text-[13px] text-text-secondary mb-2">
        What are you holding?
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="AAPL, MSFT, GOOGL"
        className="w-full text-[17px] bg-bg-elevated border border-border-primary rounded-[4px] px-4 py-3 text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSubmit()
        }}
        disabled={loading}
      />
      <p className="text-[12px] text-text-tertiary mt-2">
        Enter 1-5 tickers, separated by commas
      </p>
      <button
        onClick={handleSubmit}
        disabled={tickers.length === 0 || loading}
        className="mt-4 w-full bg-accent text-white font-semibold text-[15px] rounded-[4px] h-12 hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Scoring..." : "Score my positions"}
      </button>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/onboarding/__tests__/ticker-input.test.tsx --reporter verbose`
Expected: PASS

**Step 5: Create the onboarding page**

Create `web/src/app/onboarding/page.tsx`:

```tsx
import type { Metadata } from "next"
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"

export const metadata: Metadata = {
  title: "Score Your Portfolio | Margin Invest",
  description: "Enter your tickers and see conviction scores in 60 seconds.",
}

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      <OnboardingFlow />
    </div>
  )
}
```

**Step 6: Create OnboardingFlow client component**

Create `web/src/components/onboarding/onboarding-flow.tsx`:

```tsx
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { TickerInput } from "./ticker-input"

type Stage = "input" | "scoring" | "results"

export function OnboardingFlow() {
  const [stage, setStage] = useState<Stage>("input")
  const [tickers, setTickers] = useState<string[]>([])
  const router = useRouter()

  const handleSubmit = async (inputTickers: string[]) => {
    setTickers(inputTickers)
    setStage("scoring")

    // Simulate scoring delay, then redirect to dashboard
    // In production, this would call the scoring API
    await new Promise((resolve) => setTimeout(resolve, 2000))
    router.push("/dashboard")
  }

  return (
    <div className="w-full max-w-[560px]">
      <div className="bg-bg-elevated/60 backdrop-blur-[16px] border border-border-subtle rounded-[8px] p-8 md:p-10">
        {stage === "input" && (
          <div className="flex flex-col items-center text-center">
            <h1 className="text-[28px] md:text-[32px] font-bold text-text-primary leading-tight tracking-[-0.3px] mb-2">
              Score your portfolio.
            </h1>
            <p className="text-[15px] text-text-secondary mb-8">
              Enter your tickers and see conviction scores in 60 seconds.
            </p>
            <TickerInput onSubmit={handleSubmit} />
          </div>
        )}

        {stage === "scoring" && (
          <div className="flex flex-col items-center text-center py-8">
            <div className="flex items-center gap-3 mb-6">
              {["Data", "Filter", "Score", "Rank"].map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full border border-accent/40 flex items-center justify-center text-[11px] font-mono text-accent animate-pulse">
                    {i + 1}
                  </div>
                  <span className="text-[12px] text-text-secondary">{step}</span>
                  {i < 3 && <span className="text-text-tertiary mx-1">&rarr;</span>}
                </div>
              ))}
            </div>
            <p className="text-[15px] text-text-secondary">
              Scoring {tickers.join(", ")}...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 7: Update landing page CTAs to point to /onboarding**

In `web/src/components/landing/sections/hero-section.tsx`, change:
```tsx
<ButtonPrimary href="/dashboard">Score your first position</ButtonPrimary>
```
To:
```tsx
<ButtonPrimary href="/onboarding">Score your first position</ButtonPrimary>
```

In `web/src/components/landing/sections/pricing-section.tsx`, change all `href: "/dashboard"` to `href: "/onboarding"` in the tiers array.

In `web/src/components/landing/sections/final-cta.tsx`, change:
```tsx
<ButtonPrimary href="/dashboard">Start free</ButtonPrimary>
```
To:
```tsx
<ButtonPrimary href="/onboarding">Start free</ButtonPrimary>
```

**Step 8: Run all landing page tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/landing/__tests__/ --reporter verbose`
Expected: PASS (update any tests that assert `/dashboard` hrefs to `/onboarding`)

**Step 9: Commit**

```bash
git add web/src/app/onboarding/ web/src/components/onboarding/ web/src/components/landing/sections/hero-section.tsx web/src/components/landing/sections/pricing-section.tsx web/src/components/landing/sections/final-cta.tsx
git commit -m "feat(web): add onboarding flow with ticker input

New /onboarding page lets users enter their own tickers before
seeing the dashboard. All landing page CTAs now point here instead
of directly to /dashboard."
```

---

### Task 6: Fix Sparkline Visibility

Sparklines show dashed empty lines when price data isn't loaded (it only loads on card expand). Hide the sparkline entirely when no data is available.

**Files:**
- Modify: `web/src/components/ui/sparkline.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Read the current sparkline component**

Read `web/src/components/ui/sparkline.tsx` to understand the current empty state rendering.

**Step 2: Update sparkline to return null when no data**

In the Sparkline component, if `bars` is null/undefined/empty, return null instead of rendering an empty dashed line:

```tsx
// At the top of the Sparkline component:
if (!bars || bars.length === 0) return null
```

**Step 3: Run existing tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run --reporter verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/ui/sparkline.tsx
git commit -m "fix(web): hide sparkline when no price data available

Returns null instead of rendering empty dashed line for cards
where price history hasn't been loaded yet."
```

---

## Phase 2: "Make It Premium" (P1)

### Task 7: Score Interpretation Layer

Add one-line contextual interpretation below each factor in the expanded card view. This transforms data into understanding.

**Files:**
- Create: `web/src/lib/score-interpretation.ts`
- Test: `web/src/lib/__tests__/score-interpretation.test.ts`
- Modify: `web/src/components/dashboard/factor-breakdown.tsx`

**Step 1: Write tests for interpretation logic**

Create `web/src/lib/__tests__/score-interpretation.test.ts`:

```ts
import { getFactorInterpretation } from "../score-interpretation"

describe("getFactorInterpretation", () => {
  it("returns exceptional interpretation for 90+ quality", () => {
    const result = getFactorInterpretation("quality", 95, "Technology")
    expect(result).toContain("Top 5%")
  })

  it("returns strong interpretation for 70-89", () => {
    const result = getFactorInterpretation("value", 82, "Healthcare")
    expect(result).toContain("Top 18%")
  })

  it("returns average interpretation for 50-69", () => {
    const result = getFactorInterpretation("momentum", 55, "Energy")
    expect(result).toContain("Middle of")
  })

  it("returns weak interpretation for below 30", () => {
    const result = getFactorInterpretation("quality", 15, "Technology")
    expect(result).toContain("Bottom")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/lib/__tests__/score-interpretation.test.ts --reporter verbose`

**Step 3: Create interpretation logic**

Create `web/src/lib/score-interpretation.ts`:

```ts
const FACTOR_DESCRIPTORS: Record<string, { high: string; low: string }> = {
  quality: { high: "Strong ROE, consistent margins, low debt", low: "Weak profitability or high leverage" },
  value: { high: "Undervalued vs sector peers on FCF and earnings", low: "Trading at premium valuation" },
  momentum: { high: "Strong uptrend across multiple timeframes", low: "Weak or declining price action" },
  capital_allocation: { high: "Efficient capital deployment", low: "Suboptimal capital allocation" },
  catalyst: { high: "Strong catalysts identified", low: "Limited near-term catalysts" },
}

export function getFactorInterpretation(
  factorName: string,
  percentile: number,
  sector?: string,
): string {
  const descriptor = FACTOR_DESCRIPTORS[factorName.toLowerCase()]
  const sectorLabel = sector ? ` in ${sector}` : ""
  const rank = 100 - Math.round(percentile)

  if (percentile >= 90) {
    return `Top ${rank}%${sectorLabel}. ${descriptor?.high ?? "Exceptional across metrics."}`
  }
  if (percentile >= 70) {
    return `Top ${rank}%${sectorLabel}. ${descriptor?.high ?? "Strong performance."}`
  }
  if (percentile >= 50) {
    return `Middle of the pack${sectorLabel}. Room for improvement.`
  }
  if (percentile >= 30) {
    return `Below average${sectorLabel}. ${descriptor?.low ?? "Underperforming peers."}`
  }
  return `Bottom ${Math.round(percentile)}%${sectorLabel}. ${descriptor?.low ?? "Significant weakness."}`
}
```

**Step 4: Run test to verify it passes**

**Step 5: Wire into FactorBreakdown component**

In `web/src/components/dashboard/factor-breakdown.tsx`, update the `FactorSection` to show interpretation text below the factor name. Import the function and add interpretation below each sub-score's PercentileBar.

**Step 6: Commit**

```bash
git add web/src/lib/score-interpretation.ts web/src/lib/__tests__/score-interpretation.test.ts web/src/components/dashboard/factor-breakdown.tsx
git commit -m "feat(web): add contextual score interpretation to factor breakdown

Shows one-line interpretation per factor (e.g., 'Top 16% in Technology.
Strong ROE, consistent margins.') below each percentile bar."
```

---

### Task 8: Pricing Section Improvements

Add psychological anchoring: "Most popular" badge, annual savings display, crossed-out monthly price.

**Files:**
- Modify: `web/src/components/landing/sections/pricing-section.tsx`

**Step 1: Update pricing-section.tsx**

Key changes to the `tiers` array and `TierCard` component:

1. Add `badge?: string` to Tier interface
2. Add `monthlyPrice?: string` to Tier interface
3. Set Operator tier: `badge: "Most popular"`, `monthlyPrice: "$39"`
4. Set Allocator tier: `monthlyPrice: "$99"`
5. Add "billed annually" text and savings copy
6. Add badge rendering in TierCard
7. Add subtle gradient to Operator card: `bg-gradient-to-t from-bg-elevated to-accent/[0.04]`

**Step 2: Run existing landing tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/landing/__tests__/ --reporter verbose`
Expected: PASS

**Step 3: Commit**

```bash
git add web/src/components/landing/sections/pricing-section.tsx
git commit -m "feat(web): add pricing psychology — badges, anchoring, annual savings

Most popular badge on Operator, crossed-out monthly prices,
annual savings display, subtle gradient on highlighted tier."
```

---

### Task 9: Dashboard Motion Continuity

Bridge the gap between cinematic landing page and static dashboard with subtle load animations.

**Files:**
- Modify: `web/src/components/dashboard/picks-grid.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Add staggered card entrance animation**

Wrap each `StockCard` in `picks-grid.tsx` with Framer Motion:

```tsx
"use client"

import { motion } from "framer-motion"
import { StockCard } from "./stock-card"
import { EmptyState } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] },
  }),
}

// ... rest of component wrapping each StockCard in:
<motion.div
  key={pick.ticker}
  custom={index}
  initial="hidden"
  animate="visible"
  variants={cardVariants}
>
  <StockCard pick={pick} />
</motion.div>
```

**Step 2: Add score number animation**

In `stock-card.tsx`, animate the score display on first render using a simple CSS animation (avoid adding Framer Motion dependency to keep the component lightweight):

Add `tabular-nums` font feature to score display for stable width during animation.

**Step 3: Add percentile bar width animation**

In `percentile-bar.tsx`, add a CSS transition on the fill div's width:

```css
transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
```

The bar already has `transition-all` so this mostly works. Ensure initial render starts from 0 width by using a client-side effect.

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run --reporter verbose`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/picks-grid.tsx web/src/components/dashboard/stock-card.tsx web/src/components/ui/percentile-bar.tsx
git commit -m "feat(web): add dashboard motion continuity

Staggered card entrance, animated percentile bar fill,
bridges cinematic landing → app experience."
```

---

## Phase 3: "Make It Sticky" (P2)

### Task 10: Social Proof Metrics Strip

Add a minimal operational metrics strip below the hero section.

**Files:**
- Create: `web/src/components/landing/sections/metrics-strip.tsx`
- Modify: `web/src/app/page.tsx`

**Step 1: Create MetricsStrip component**

```tsx
"use client"

import { motion } from "framer-motion"

const metrics = [
  { label: "Scoring 2,400+ equities daily" },
  { label: "6 quantitative factors" },
  { label: "Updated every market close" },
]

export function MetricsStrip() {
  return (
    <motion.div
      className="flex items-center justify-center gap-6 text-[13px] font-mono text-text-tertiary tracking-[0.3px] py-4"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {metrics.map((m, i) => (
        <span key={m.label} className="flex items-center gap-6">
          {i > 0 && <span className="text-border-primary">|</span>}
          {m.label}
        </span>
      ))}
    </motion.div>
  )
}
```

**Step 2: Add between HeroSection and EngineDiagram in page.tsx**

**Step 3: Commit**

```bash
git add web/src/components/landing/sections/metrics-strip.tsx web/src/app/page.tsx
git commit -m "feat(web): add social proof metrics strip below hero

Shows operational credibility signals: equities scored, factors, update frequency."
```

---

### Task 11: Elevation System for Dashboard Cards

Add depth/shadow to dashboard cards for premium perception.

**Files:**
- Modify: `web/src/app/globals.css`
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Add elevation shadow tokens to globals.css**

```css
--shadow-card: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
--shadow-card-hover: 0 2px 8px rgba(0,0,0,0.3);
--shadow-modal: 0 8px 32px rgba(0,0,0,0.5);
```

**Step 2: Apply to stock cards**

In `stock-card.tsx`, add shadow to the card:

```tsx
className={`bg-bg-elevated border border-border-primary rounded-sm p-6 cursor-pointer
  transition-all shadow-[0_1px_3px_rgba(0,0,0,0.12),0_1px_2px_rgba(0,0,0,0.08)]
  hover:shadow-[0_2px_8px_rgba(0,0,0,0.3)] hover:border-accent/20
  ${expanded ? "col-span-full" : ""}
  ${getCardTierClasses(pick.conviction_level)} ${className}`}
```

**Step 3: Run tests and commit**

```bash
git add web/src/app/globals.css web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): add elevation system to dashboard cards

Subtle shadows and hover effects create depth hierarchy,
bridging the perception gap between landing page and dashboard."
```

---

## Task Dependencies

```
Task 1 (percentile bars) ─── no deps, start immediately
Task 2 (card hierarchy) ──── no deps, can parallel with Task 1
Task 3 (portfolio score) ─── no deps, can parallel
Task 4 (usage pill) ──────── no deps, can parallel
Task 5 (onboarding) ──────── no deps, can parallel
Task 6 (sparkline fix) ───── no deps, can parallel

Task 7 (interpretation) ──── after Task 1 (uses same bars)
Task 8 (pricing) ─────────── after Task 5 (pricing CTAs updated)
Task 9 (motion) ──────────── after Task 1, 2 (animates bars and cards)

Task 10 (social proof) ───── no deps
Task 11 (elevation) ──────── after Task 2 (builds on card changes)
```

Tasks 1-6 can all be executed in parallel. Tasks 7-9 have soft dependencies. Tasks 10-11 are independent.
