# Frontend UX Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the "Forensic Transparency" UX strategy — FactorRadar chart, enhanced eliminated hero with near-miss framing, FailedComparison component, FormulaTooltip system, sector comparison micro-bars, and trust badges.

**Architecture:** Five new components (`FactorRadar`, `FailedComparison`, `FormulaTooltip`, `SectorNeutralBanner`, `DeterminismBadge`) plus enhancements to four existing components (`EliminatedHero`, `ScoringPillars`/`PillarCard`, `FilterCard`, `HypotheticalScores`). All frontend-only changes with static formula data. API changes deferred to a separate plan (sector_pass_rate, sector champion endpoint, sector distribution data).

**Tech Stack:** Next.js 15, React 19, Recharts 3.7.0 (RadarChart), Tailwind v4, Framer Motion, Vitest + @testing-library/react

**Design Doc:** `docs/plans/2026-02-26-frontend-ux-strategy-design.md`

---

### Task 1: FormulaTooltip Component

The foundation component — used by every subsequent task. Build this first.

**Files:**
- Create: `web/src/components/ui/formula-tooltip.tsx`
- Create: `web/src/lib/formula-definitions.ts`
- Create: `web/src/components/ui/__tests__/formula-tooltip.test.tsx`

**Step 1: Write the formula definitions data**

Create `web/src/lib/formula-definitions.ts` — a static map of all metric formulas:

```typescript
export interface FormulaDefinition {
  name: string
  formula: string
  source: string
  interpretation: string
}

export const FORMULA_DEFINITIONS: Record<string, FormulaDefinition> = {
  // Filters
  beneish_m_score: {
    name: 'Beneish M-Score',
    formula: '-4.84 + 0.92·DSRI + 0.528·GMI + 0.404·AQI + 0.892·SGI + 0.115·DEPI − 0.172·SGAI + 4.679·TATA − 0.327·LVGI',
    source: 'Beneish (1999)',
    interpretation: 'Above −1.78 signals elevated earnings manipulation risk.',
  },
  altman_z_score: {
    name: 'Altman Z-Score',
    formula: '1.2·(WC/TA) + 1.4·(RE/TA) + 3.3·(EBIT/TA) + 0.6·(MVE/TL) + 1.0·(Sales/TA)',
    source: 'Altman (1968)',
    interpretation: 'Below 1.81 = distress zone. Above 2.99 = safe zone.',
  },
  fcf_distress: {
    name: 'Free Cash Flow',
    formula: 'CFO − CapEx',
    source: 'Standard cash flow analysis',
    interpretation: 'Negative FCF means the company is burning cash. Increases dilution risk.',
  },
  interest_coverage: {
    name: 'Interest Coverage Ratio',
    formula: 'EBIT / Interest Expense',
    source: 'Standard credit analysis',
    interpretation: 'Higher is better. Below 1.5× signals debt service risk.',
  },
  current_ratio: {
    name: 'Current Ratio',
    formula: 'Current Assets / Current Liabilities',
    source: 'Standard liquidity analysis',
    interpretation: 'Above 1.0 means short-term obligations are covered.',
  },
  liquidity: {
    name: 'Liquidity Filter',
    formula: 'Market Cap ≥ $300M AND Avg Daily Volume ≥ $1M AND History ≥ 5 years',
    source: 'Standard institutional thresholds',
    interpretation: 'Ensures adequate trading liquidity and data history.',
  },
  // Quality sub-factors
  gross_profitability: {
    name: 'Gross Profitability',
    formula: '(Revenue − COGS) / Total Assets',
    source: 'Novy-Marx (2013)',
    interpretation: 'Higher is better. Measures asset efficiency of gross profit generation.',
  },
  roic_wacc_spread: {
    name: 'ROIC–WACC Spread',
    formula: 'ROIC − WACC',
    source: 'Mauboussin & Callahan (2014)',
    interpretation: 'Positive = creating shareholder value. Wider spread = stronger moat.',
  },
  earnings_quality: {
    name: 'Sloan Accrual Ratio',
    formula: '(Net Income − CFO − CFI) / Total Assets',
    source: 'Sloan (1996)',
    interpretation: 'Lower is better. Negative = cash earnings exceed reported earnings.',
  },
  piotroski_f_score: {
    name: 'Piotroski F-Score',
    formula: 'Sum of 9 binary signals (profitability, leverage, operating efficiency)',
    source: 'Piotroski (2000)',
    interpretation: 'Score 0–9. Higher signals stronger financial health. ≥7 is strong.',
  },
  // Value sub-factors
  ev_fcf: {
    name: 'EV/FCF',
    formula: 'Enterprise Value / Free Cash Flow',
    source: 'Standard valuation metric',
    interpretation: 'Lower is better. Measures how cheaply you buy each dollar of cash flow.',
  },
  shareholder_yield: {
    name: 'Shareholder Yield',
    formula: 'Dividend Yield + Buyback Yield − Net Debt Issuance Yield',
    source: 'Mebane Faber (2013)',
    interpretation: 'Higher is better. Total cash return to shareholders.',
  },
  dcf_margin_of_safety: {
    name: 'DCF Margin of Safety',
    formula: '(Intrinsic Value − Current Price) / Intrinsic Value',
    source: 'Graham & Dodd (1934)',
    interpretation: 'Higher is better. Buffer between price paid and estimated fair value.',
  },
  acquirers_multiple: {
    name: "Acquirer's Multiple",
    formula: 'Enterprise Value / Operating Earnings',
    source: 'Tobias Carlisle (2014)',
    interpretation: 'Lower is better. Finds statistically cheap stocks an acquirer would buy.',
  },
  // Momentum sub-factors
  price_momentum: {
    name: '12-1 Month Price Momentum',
    formula: '(Price₁₂ − Price₁) / Price₁, excluding most recent month',
    source: 'Jegadeesh & Titman (1993)',
    interpretation: 'Higher is better. Captures intermediate-term trend strength.',
  },
  earnings_momentum: {
    name: 'Standardized Unexpected Earnings (SUE)',
    formula: '(EPS_actual − EPS_estimate) / Std Dev of surprises',
    source: 'Latané & Jones (1977)',
    interpretation: 'Higher is better. Measures magnitude of earnings surprise.',
  },
  insider_cluster_buying: {
    name: 'Insider Cluster Buying',
    formula: '≥3 unique insiders buying within 30 days',
    source: 'Lakonishok & Lee (2001)',
    interpretation: 'Cluster buying is a stronger signal than individual insider trades.',
  },
  institutional_accumulation: {
    name: 'Institutional Accumulation',
    formula: 'Net shares added by curated 13F filers / Shares outstanding',
    source: '13F filing analysis',
    interpretation: 'Positive accumulation by top funds signals institutional confidence.',
  },
  // Conviction Engine
  asymmetry_ratio: {
    name: 'Asymmetry Ratio',
    formula: 'Upside to Intrinsic Value / Downside to Stop Loss',
    source: 'Kelly Criterion adaptation',
    interpretation: 'Higher is better. ≥3:1 is favorable risk-reward.',
  },
  max_position_pct: {
    name: 'Max Position %',
    formula: 'f* = (p·b − q) / b, capped at Kelly fraction',
    source: 'Kelly (1956)',
    interpretation: 'Suggested max allocation. Higher conviction = larger position allowed.',
  },
  // Valuation methods
  dcf_valuation: {
    name: 'DCF Valuation',
    formula: 'Sum of discounted future FCFs + Terminal Value',
    source: 'Standard DCF model',
    interpretation: 'Most comprehensive but sensitive to growth and discount rate assumptions.',
  },
  ev_fcf_valuation: {
    name: 'EV/FCF Implied Value',
    formula: 'FCF × Sector Median EV/FCF Multiple',
    source: 'Relative valuation',
    interpretation: 'What the stock would be worth at sector-average multiples.',
  },
  ev_ebit_valuation: {
    name: 'EV/EBIT Implied Value',
    formula: 'EBIT × Sector Median EV/EBIT Multiple',
    source: 'Relative valuation',
    interpretation: 'Operating earnings-based valuation, less sensitive to capex policy.',
  },
  shareholder_yield_valuation: {
    name: 'Shareholder Yield Implied Value',
    formula: 'Total Shareholder Yield / Sector Median Yield',
    source: 'Yield-based valuation',
    interpretation: 'Prices the stock relative to sector cash return expectations.',
  },
}
```

**Step 2: Write the failing test**

Create `web/src/components/ui/__tests__/formula-tooltip.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FormulaTooltip } from '../formula-tooltip'
import { FORMULA_DEFINITIONS } from '@/lib/formula-definitions'

describe('FormulaTooltip', () => {
  it('renders the trigger element with info icon', () => {
    render(
      <FormulaTooltip metricKey="roic_wacc_spread">
        <span>ROIC–WACC Spread</span>
      </FormulaTooltip>
    )
    expect(screen.getByTestId('formula-trigger-roic_wacc_spread')).toBeInTheDocument()
  })

  it('shows tooltip content on hover', async () => {
    render(
      <FormulaTooltip metricKey="earnings_quality">
        <span>Sloan Accrual Ratio</span>
      </FormulaTooltip>
    )
    const trigger = screen.getByTestId('formula-trigger-earnings_quality')
    fireEvent.mouseEnter(trigger)
    expect(await screen.findByText('(Net Income − CFO − CFI) / Total Assets')).toBeInTheDocument()
    expect(screen.getByText('Sloan (1996)')).toBeInTheDocument()
    expect(
      screen.getByText('Lower is better. Negative = cash earnings exceed reported earnings.')
    ).toBeInTheDocument()
  })

  it('hides tooltip content on mouse leave', async () => {
    render(
      <FormulaTooltip metricKey="earnings_quality">
        <span>Sloan Accrual Ratio</span>
      </FormulaTooltip>
    )
    const trigger = screen.getByTestId('formula-trigger-earnings_quality')
    fireEvent.mouseEnter(trigger)
    await screen.findByText('Sloan (1996)')
    fireEvent.mouseLeave(trigger)
    // Tooltip should be removed after animation
    expect(screen.queryByText('Sloan (1996)')).not.toBeInTheDocument()
  })

  it('renders nothing special when metricKey is not in FORMULA_DEFINITIONS', () => {
    render(
      <FormulaTooltip metricKey="nonexistent_metric">
        <span>Unknown Metric</span>
      </FormulaTooltip>
    )
    // Should still render children but no info icon
    expect(screen.getByText('Unknown Metric')).toBeInTheDocument()
    expect(screen.queryByTestId('formula-trigger-nonexistent_metric')).not.toBeInTheDocument()
  })

  it('every key in FORMULA_DEFINITIONS has all required fields', () => {
    for (const [key, def] of Object.entries(FORMULA_DEFINITIONS)) {
      expect(def.name, `${key} missing name`).toBeTruthy()
      expect(def.formula, `${key} missing formula`).toBeTruthy()
      expect(def.source, `${key} missing source`).toBeTruthy()
      expect(def.interpretation, `${key} missing interpretation`).toBeTruthy()
    }
  })
})
```

**Step 3: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/ui/__tests__/formula-tooltip.test.tsx`
Expected: FAIL — module `../formula-tooltip` not found

**Step 4: Write the FormulaTooltip component**

Create `web/src/components/ui/formula-tooltip.tsx`:

```tsx
'use client'

import { useState, useRef, useEffect, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { FORMULA_DEFINITIONS } from '@/lib/formula-definitions'

interface FormulaTooltipProps {
  metricKey: string
  children: ReactNode
}

export function FormulaTooltip({ metricKey, children }: FormulaTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLSpanElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const definition = FORMULA_DEFINITIONS[metricKey]

  // Close on click outside (for mobile tap-to-open behavior)
  useEffect(() => {
    if (!isOpen) return
    function handleClickOutside(e: MouseEvent) {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  if (!definition) {
    return <>{children}</>
  }

  return (
    <span
      ref={triggerRef}
      className="relative inline-flex items-center gap-1 cursor-help"
      data-testid={`formula-trigger-${metricKey}`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onClick={() => setIsOpen((prev) => !prev)}
    >
      {children}
      <svg
        className="w-3 h-3 text-tertiary opacity-60 hover:opacity-100 transition-opacity shrink-0"
        viewBox="0 0 16 16"
        fill="currentColor"
      >
        <path d="M8 0a8 8 0 100 16A8 8 0 008 0zm.93 12.14h-1.9V7.22h1.9v4.92zm-.95-5.87a1.07 1.07 0 110-2.14 1.07 1.07 0 010 2.14z" />
      </svg>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={tooltipRef}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-2 z-50 w-80 p-3 rounded-lg border border-white/[0.08] bg-[var(--color-bg-elevated)] shadow-lg"
          >
            <p className="text-xs font-semibold text-primary mb-1.5">{definition.name}</p>
            <p className="text-[11px] font-mono text-accent leading-relaxed mb-1.5">
              {definition.formula}
            </p>
            <p className="text-[10px] italic text-secondary mb-1">{definition.source}</p>
            <p className="text-[10px] text-tertiary leading-relaxed">
              {definition.interpretation}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  )
}
```

**Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/ui/__tests__/formula-tooltip.test.tsx`
Expected: PASS (all 5 tests)

**Step 6: Commit**

```bash
git add web/src/components/ui/formula-tooltip.tsx web/src/lib/formula-definitions.ts web/src/components/ui/__tests__/formula-tooltip.test.tsx
git commit -m "feat(web): add FormulaTooltip component with formula definitions"
```

---

### Task 2: FactorRadar Component

New Recharts RadarChart showing the stock's factor profile vs sector median and P90.

**Files:**
- Create: `web/src/components/asset-detail/factor-radar.tsx`
- Create: `web/src/components/asset-detail/__tests__/factor-radar.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/asset-detail/__tests__/factor-radar.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FactorRadar } from '../factor-radar'

// Mock recharts to avoid canvas issues in test environment
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: ({ dataKey }: any) => <div data-testid="polar-angle-axis" data-key={dataKey} />,
  Radar: ({ name, dataKey }: any) => <div data-testid={`radar-${name}`} data-key={dataKey} />,
  Legend: () => <div data-testid="legend" />,
}))

const mockFactors = {
  quality: { average_percentile: 87, factor_name: 'quality', weight: 0.35, sub_scores: [] },
  value: { average_percentile: 72, factor_name: 'value', weight: 0.30, sub_scores: [] },
  momentum: { average_percentile: 94, factor_name: 'momentum', weight: 0.35, sub_scores: [] },
}

describe('FactorRadar', () => {
  it('renders the radar chart with stock data', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
      />
    )
    expect(screen.getByTestId('factor-radar')).toBeInTheDocument()
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument()
  })

  it('displays section header with sector name', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
      />
    )
    expect(screen.getByText(/Factor Profile/)).toBeInTheDocument()
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
  })

  it('shows percentile values for each axis', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
      />
    )
    expect(screen.getByText(/87/)).toBeInTheDocument()
    expect(screen.getByText(/72/)).toBeInTheDocument()
    expect(screen.getByText(/94/)).toBeInTheDocument()
  })

  it('renders three radar series (stock, median, p90)', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
      />
    )
    expect(screen.getByTestId('radar-Stock')).toBeInTheDocument()
    expect(screen.getByTestId('radar-Sector Median')).toBeInTheDocument()
    expect(screen.getByTestId('radar-Sector Top 10%')).toBeInTheDocument()
  })

  it('falls back to horizontal bars on mobile (via className)', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
      />
    )
    // Radar wrapper should be hidden on mobile
    const radarWrapper = screen.getByTestId('radar-desktop')
    expect(radarWrapper.className).toContain('hidden')
    expect(radarWrapper.className).toContain('md:block')

    // Mobile bars should be visible on mobile
    const mobileBars = screen.getByTestId('radar-mobile')
    expect(mobileBars.className).toContain('md:hidden')
  })

  it('renders dimmed variant for hypothetical scores', () => {
    render(
      <FactorRadar
        quality={mockFactors.quality}
        value={mockFactors.value}
        momentum={mockFactors.momentum}
        sectorName="Technology"
        variant="dimmed"
      />
    )
    const container = screen.getByTestId('factor-radar')
    expect(container.className).toContain('opacity-60')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/factor-radar.test.tsx`
Expected: FAIL — module `../factor-radar` not found

**Step 3: Write the FactorRadar component**

Create `web/src/components/asset-detail/factor-radar.tsx`:

```tsx
'use client'

import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
} from 'recharts'
import type { FactorBreakdownResponse } from '@/lib/api/types'

interface FactorRadarProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  sectorName?: string
  variant?: 'default' | 'dimmed'
  onAxisClick?: (factor: string) => void
}

export function FactorRadar({
  quality,
  value,
  momentum,
  sectorName,
  variant = 'default',
  onAxisClick,
}: FactorRadarProps) {
  const data = [
    {
      axis: `Quality (${Math.round(quality.average_percentile)})`,
      factor: 'quality',
      stock: quality.average_percentile,
      median: 50,
      p90: 90,
    },
    {
      axis: `Value (${Math.round(value.average_percentile)})`,
      factor: 'value',
      stock: value.average_percentile,
      median: 50,
      p90: 90,
    },
    {
      axis: `Momentum (${Math.round(momentum.average_percentile)})`,
      factor: 'momentum',
      stock: momentum.average_percentile,
      median: 50,
      p90: 90,
    },
  ]

  const isDimmed = variant === 'dimmed'

  return (
    <section
      data-testid="factor-radar"
      className={`terminal-card p-6 ${isDimmed ? 'opacity-60' : ''}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-primary">
          {isDimmed ? 'Hypothetical Factor Profile' : 'Factor Profile'}
        </h3>
        {sectorName && (
          <span className="text-[10px] font-mono text-tertiary uppercase tracking-wider">
            vs. {sectorName} sector
          </span>
        )}
      </div>

      {isDimmed && (
        <p className="text-[10px] text-warning mb-3">
          This stock did not pass filters. Profile shown for reference only.
        </p>
      )}

      {/* Desktop: Radar chart */}
      <div data-testid="radar-desktop" className="hidden md:block">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
            <PolarGrid stroke="var(--color-border)" strokeOpacity={0.3} />
            <PolarAngleAxis
              dataKey="axis"
              tick={{
                fontSize: 11,
                fill: 'var(--color-text-secondary)',
                fontFamily: 'var(--font-geist-mono)',
              }}
              onClick={(_: any, index: number) => onAxisClick?.(data[index].factor)}
              style={{ cursor: onAxisClick ? 'pointer' : 'default' }}
            />
            <Radar
              name="Sector Top 10%"
              dataKey="p90"
              stroke="var(--color-text-tertiary)"
              strokeDasharray="4 4"
              fill="none"
              strokeWidth={1}
            />
            <Radar
              name="Sector Median"
              dataKey="median"
              stroke="var(--color-text-tertiary)"
              fill="none"
              strokeWidth={1.5}
              strokeOpacity={0.5}
            />
            <Radar
              name="Stock"
              dataKey="stock"
              stroke="var(--color-accent)"
              fill="var(--color-accent)"
              fillOpacity={isDimmed ? 0.08 : 0.15}
              strokeWidth={2}
              strokeDasharray={isDimmed ? '6 3' : undefined}
            />
            <Legend
              wrapperStyle={{ fontSize: 10, fontFamily: 'var(--font-geist-mono)' }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Mobile: Horizontal comparison bars */}
      <div data-testid="radar-mobile" className="md:hidden space-y-3">
        {data.map((d) => (
          <div
            key={d.factor}
            className="cursor-pointer"
            onClick={() => onAxisClick?.(d.factor)}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-secondary capitalize">{d.factor}</span>
              <span className="text-xs font-mono text-primary">
                {Math.round(d.stock)}th
              </span>
            </div>
            <div className="relative h-2 bg-white/[0.04] rounded-full overflow-hidden">
              {/* Sector median marker */}
              <div
                className="absolute top-0 h-full w-px bg-white/20"
                style={{ left: '50%' }}
              />
              {/* P90 marker */}
              <div
                className="absolute top-0 h-full w-px bg-white/10"
                style={{ left: '90%' }}
              />
              {/* Stock value */}
              <div
                className="h-full rounded-full bg-accent/40 transition-all duration-500"
                style={{ width: `${d.stock}%` }}
              />
            </div>
          </div>
        ))}
        <div className="flex gap-4 text-[9px] text-tertiary font-mono mt-1">
          <span>| Sector Median</span>
          <span>| Top 10%</span>
        </div>
      </div>

      {onAxisClick && (
        <p className="text-[9px] text-tertiary mt-3 text-center">
          Click any axis for sub-factor breakdown
        </p>
      )}
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/factor-radar.test.tsx`
Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/factor-radar.tsx web/src/components/asset-detail/__tests__/factor-radar.test.tsx
git commit -m "feat(web): add FactorRadar component with radar chart and mobile bars"
```

---

### Task 3: Wire FactorRadar into Asset Detail View

Insert FactorRadar between EliminationGauntlet and ScoringPillars for passing tickers, and as dimmed variant in HypotheticalScores for eliminated tickers.

**Files:**
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`
- Modify: `web/src/components/asset-detail/hypothetical-scores.tsx`
- Modify: `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`

**Step 1: Write/update the failing test**

Add to `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`:

```tsx
// Add to the existing describe block:

it('renders FactorRadar between gauntlet and pillars for passing ticker', async () => {
  render(<AssetDetailView ticker="AAPL" scoreData={makeScoreResponse()} historyData={null} apiError={null} />)
  await waitFor(() => {
    expect(screen.getByTestId('factor-radar')).toBeInTheDocument()
  })
})

it('renders dimmed FactorRadar in hypothetical section for eliminated ticker', async () => {
  const eliminatedScore = makeScoreResponse({
    filters_passed: [
      { name: 'beneish_m_score', passed: false, value: -1.42, threshold: -1.78, detail: '', verdict: 'fail' },
      { name: 'altman_z_score', passed: true, value: 3.2, threshold: 1.81, detail: '', verdict: 'pass' },
      { name: 'fcf_distress', passed: true, value: 1000000, threshold: 0, detail: '', verdict: 'pass' },
      { name: 'interest_coverage', passed: true, value: 5.0, threshold: 1.5, detail: '', verdict: 'pass' },
      { name: 'current_ratio', passed: true, value: 2.0, threshold: 1.0, detail: '', verdict: 'pass' },
      { name: 'liquidity', passed: true, value: 50000000000, threshold: 300000000, detail: '', verdict: 'pass' },
    ],
  })
  render(<AssetDetailView ticker="TSLA" scoreData={eliminatedScore} historyData={null} apiError={null} />)
  await waitFor(() => {
    expect(screen.getByTestId('hypothetical-scores')).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/asset-detail-view.test.tsx`
Expected: FAIL — FactorRadar not rendered

**Step 3: Wire FactorRadar into asset-detail-view.tsx**

In `asset-detail-view.tsx`:
- Add import: `import { FactorRadar } from './factor-radar'`
- In the passing ticker flow, insert `<FactorRadar>` between EliminationGauntlet and ScoringPillars
- Pass `quality={scoreData.quality}`, `value={scoreData.value}`, `momentum={scoreData.momentum}`, `sectorName={scoreData.sector}`

In `hypothetical-scores.tsx`:
- Add import: `import { FactorRadar } from './factor-radar'`
- Insert `<FactorRadar variant="dimmed">` above the existing pillar cards grid
- Pass the hypothetical quality/value/momentum data

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/asset-detail-view.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/asset-detail-view.tsx web/src/components/asset-detail/hypothetical-scores.tsx web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx
git commit -m "feat(web): wire FactorRadar into asset detail and hypothetical scores"
```

---

### Task 4: DeterminismBadge and SectorNeutralBanner

Two small trust-building components.

**Files:**
- Create: `web/src/components/asset-detail/determinism-badge.tsx`
- Create: `web/src/components/asset-detail/sector-neutral-banner.tsx`
- Create: `web/src/components/asset-detail/__tests__/determinism-badge.test.tsx`
- Create: `web/src/components/asset-detail/__tests__/sector-neutral-banner.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/asset-detail/__tests__/determinism-badge.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DeterminismBadge } from '../determinism-badge'

describe('DeterminismBadge', () => {
  it('renders the determinism statement', () => {
    render(<DeterminismBadge />)
    expect(screen.getByText(/Deterministic/)).toBeInTheDocument()
    expect(screen.getByText(/same inputs produce this exact output/)).toBeInTheDocument()
  })

  it('shows tooltip on hover', async () => {
    render(<DeterminismBadge />)
    fireEvent.mouseEnter(screen.getByTestId('determinism-badge'))
    expect(
      await screen.findByText(/zero human intervention/)
    ).toBeInTheDocument()
  })
})
```

Create `web/src/components/asset-detail/__tests__/sector-neutral-banner.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SectorNeutralBanner } from '../sector-neutral-banner'

describe('SectorNeutralBanner', () => {
  it('renders sector name and peer count', () => {
    render(<SectorNeutralBanner sectorName="Technology" sectorCode="4510" />)
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/GICS 4510/)).toBeInTheDocument()
  })

  it('shows why tooltip on hover', async () => {
    render(<SectorNeutralBanner sectorName="Technology" sectorCode="4510" />)
    fireEvent.mouseEnter(screen.getByText('Why?'))
    expect(
      await screen.findByText(/Sector-neutral ranking ensures fair comparison/)
    ).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/determinism-badge.test.tsx src/components/asset-detail/__tests__/sector-neutral-banner.test.tsx`
Expected: FAIL — modules not found

**Step 3: Write the DeterminismBadge**

Create `web/src/components/asset-detail/determinism-badge.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

export function DeterminismBadge() {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      data-testid="determinism-badge"
      className="relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-white/[0.06] bg-white/[0.02] cursor-help"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className="text-[10px] font-mono text-tertiary">
        &#x2B21; Deterministic — same inputs produce this exact output. No human override.
      </span>
      <AnimatePresence>
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-1.5 z-50 w-72 p-2.5 rounded-lg border border-white/[0.08] bg-[var(--color-bg-elevated)] shadow-lg"
          >
            <p className="text-[10px] text-secondary leading-relaxed">
              This score was computed algorithmically with zero human intervention. The same
              financial data inputs will always produce this exact same score, percentile, and
              signal.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

**Step 4: Write the SectorNeutralBanner**

Create `web/src/components/asset-detail/sector-neutral-banner.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface SectorNeutralBannerProps {
  sectorName: string
  sectorCode?: string
}

export function SectorNeutralBanner({ sectorName, sectorCode }: SectorNeutralBannerProps) {
  const [showWhy, setShowWhy] = useState(false)

  return (
    <div
      data-testid="sector-neutral-banner"
      className="flex items-start gap-2 px-3 py-2 rounded border border-white/[0.06] bg-white/[0.02] text-[10px] text-secondary leading-relaxed"
    >
      <span className="text-accent mt-px shrink-0">&#9675;</span>
      <span>
        Sector-neutral scoring: all factors ranked within{' '}
        <span className="text-primary font-medium">{sectorName}</span>
        {sectorCode && (
          <span className="text-tertiary font-mono"> (GICS {sectorCode})</span>
        )}{' '}
        before cross-sector combination.{' '}
        <span
          className="relative inline-block text-accent cursor-help underline decoration-dotted underline-offset-2"
          onMouseEnter={() => setShowWhy(true)}
          onMouseLeave={() => setShowWhy(false)}
        >
          Why?
          <AnimatePresence>
            {showWhy && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.15 }}
                className="absolute left-0 top-full mt-1.5 z-50 w-64 p-2.5 rounded-lg border border-white/[0.08] bg-[var(--color-bg-elevated)] shadow-lg"
              >
                <p className="text-[10px] text-secondary leading-relaxed">
                  Sector-neutral ranking ensures fair comparison within peer groups. Comparing a
                  tech company&apos;s ROIC to a utility&apos;s ROIC is meaningless — percentiles
                  are computed within each sector first, then combined.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </span>
      </span>
    </div>
  )
}
```

**Step 5: Wire into asset-detail-view.tsx**

- Import both components
- Place `<DeterminismBadge />` between HeroHeader and EliminationGauntlet
- Place `<SectorNeutralBanner sectorName={scoreData.sector} />` just above `<ScoringPillars>` (after FactorRadar)

**Step 6: Run all tests**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/determinism-badge.test.tsx src/components/asset-detail/__tests__/sector-neutral-banner.test.tsx`
Expected: PASS

**Step 7: Commit**

```bash
git add web/src/components/asset-detail/determinism-badge.tsx web/src/components/asset-detail/sector-neutral-banner.tsx web/src/components/asset-detail/__tests__/determinism-badge.test.tsx web/src/components/asset-detail/__tests__/sector-neutral-banner.test.tsx web/src/components/asset-detail/asset-detail-view.tsx
git commit -m "feat(web): add DeterminismBadge and SectorNeutralBanner trust components"
```

---

### Task 5: Enhance ScoringPillars Sub-Factor Rows with Sector Micro-Bars

Add a visual sector comparison bar to each sub-factor row in PillarCard.

**Files:**
- Create: `web/src/components/asset-detail/sector-micro-bar.tsx`
- Create: `web/src/components/asset-detail/__tests__/sector-micro-bar.test.tsx`
- Modify: `web/src/components/asset-detail/pillar-card.tsx`

**Step 1: Write the failing test**

Create `web/src/components/asset-detail/__tests__/sector-micro-bar.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SectorMicroBar } from '../sector-micro-bar'

describe('SectorMicroBar', () => {
  it('renders the bar with stock position marker', () => {
    render(<SectorMicroBar percentile={87} />)
    expect(screen.getByTestId('sector-micro-bar')).toBeInTheDocument()
    const marker = screen.getByTestId('stock-position')
    expect(marker.style.left).toBe('87%')
  })

  it('shows median and p90 markers', () => {
    render(<SectorMicroBar percentile={72} />)
    expect(screen.getByTestId('median-marker')).toBeInTheDocument()
    expect(screen.getByTestId('p90-marker')).toBeInTheDocument()
  })

  it('applies exceptional color for high percentiles', () => {
    render(<SectorMicroBar percentile={95} />)
    const fill = screen.getByTestId('percentile-fill')
    expect(fill.className).toContain('bg-[var(--color-pct-exceptional)]')
  })

  it('applies weak color for low percentiles', () => {
    render(<SectorMicroBar percentile={15} />)
    const fill = screen.getByTestId('percentile-fill')
    expect(fill.className).toContain('bg-[var(--color-pct-weak)]')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/sector-micro-bar.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the SectorMicroBar component**

Create `web/src/components/asset-detail/sector-micro-bar.tsx`:

```tsx
interface SectorMicroBarProps {
  percentile: number
}

function getPercentileColor(p: number): string {
  if (p >= 90) return 'bg-[var(--color-pct-exceptional)]'
  if (p >= 70) return 'bg-[var(--color-pct-strong)]'
  if (p >= 40) return 'bg-[var(--color-pct-average)]'
  if (p >= 20) return 'bg-[var(--color-pct-below)]'
  return 'bg-[var(--color-pct-weak)]'
}

export function SectorMicroBar({ percentile }: SectorMicroBarProps) {
  return (
    <div data-testid="sector-micro-bar" className="mt-1 mb-0.5">
      <div className="relative h-1 bg-white/[0.04] rounded-full overflow-visible">
        {/* Sector median (P50) marker */}
        <div
          data-testid="median-marker"
          className="absolute top-[-1px] h-[6px] w-px bg-white/25"
          style={{ left: '50%' }}
        />
        {/* P90 marker */}
        <div
          data-testid="p90-marker"
          className="absolute top-[-1px] h-[6px] w-px bg-white/15"
          style={{ left: '90%' }}
        />
        {/* Fill */}
        <div
          data-testid="percentile-fill"
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-500 ${getPercentileColor(percentile)}`}
          style={{ width: `${percentile}%`, opacity: 0.6 }}
        />
        {/* Stock position marker */}
        <div
          data-testid="stock-position"
          className="absolute top-[-2px] w-1.5 h-1.5 rounded-full bg-accent border border-accent/60"
          style={{ left: `${percentile}%`, transform: 'translateX(-50%)' }}
        />
      </div>
    </div>
  )
}
```

**Step 4: Wire SectorMicroBar into PillarCard**

In `web/src/components/asset-detail/pillar-card.tsx`:
- Import `SectorMicroBar`
- After each sub-factor row in the expanded table, add: `<SectorMicroBar percentile={sub.percentile_rank} />`
- Only render when the pillar is expanded (already gated by the expand state)

**Step 5: Run all tests**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/sector-micro-bar.test.tsx`
Expected: PASS (all 4 tests)

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/sector-micro-bar.tsx web/src/components/asset-detail/__tests__/sector-micro-bar.test.tsx web/src/components/asset-detail/pillar-card.tsx
git commit -m "feat(web): add SectorMicroBar to sub-factor rows in PillarCard"
```

---

### Task 6: Wire FormulaTooltip into Existing Components

Apply the FormulaTooltip to FilterCard, PillarCard, ConvictionEngine, and ValuationSection.

**Files:**
- Modify: `web/src/components/asset-detail/filter-card.tsx`
- Modify: `web/src/components/asset-detail/pillar-card.tsx`
- Modify: `web/src/components/asset-detail/conviction-engine.tsx`
- Modify: `web/src/components/asset-detail/valuation-section.tsx`
- Modify: `web/src/components/asset-detail/factor-radar.tsx`

**Step 1: Write the failing test**

Add to an existing test file or create a focused integration test:

Create `web/src/components/asset-detail/__tests__/formula-integration.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FilterCard } from '../filter-card'
import { FORMULA_DEFINITIONS } from '@/lib/formula-definitions'

// Mock recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  RadarChart: ({ children }: any) => <div>{children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  Radar: () => null,
  Legend: () => null,
}))

describe('FormulaTooltip integration', () => {
  it('FilterCard shows formula tooltip trigger for beneish_m_score', () => {
    render(
      <FilterCard
        filter={{
          name: 'beneish_m_score',
          passed: false,
          value: -1.42,
          threshold: -1.78,
          detail: 'Q3 2025 filing',
          verdict: 'fail',
        }}
        defaultExpanded={true}
      />
    )
    expect(screen.getByTestId('formula-trigger-beneish_m_score')).toBeInTheDocument()
  })

  it('shows formula on hover of filter metric', async () => {
    render(
      <FilterCard
        filter={{
          name: 'beneish_m_score',
          passed: false,
          value: -1.42,
          threshold: -1.78,
          detail: 'Q3 2025 filing',
          verdict: 'fail',
        }}
        defaultExpanded={true}
      />
    )
    fireEvent.mouseEnter(screen.getByTestId('formula-trigger-beneish_m_score'))
    const def = FORMULA_DEFINITIONS.beneish_m_score
    expect(await screen.findByText(def.formula)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/formula-integration.test.tsx`
Expected: FAIL — FilterCard doesn't render formula-trigger

**Step 3: Wire FormulaTooltip into each component**

In each file, wrap the metric name display with `<FormulaTooltip metricKey={...}>`:

**filter-card.tsx**: Wrap the filter display name with `<FormulaTooltip metricKey={filter.name}>`. The filter name (e.g., `beneish_m_score`) maps directly to `FORMULA_DEFINITIONS` keys.

**pillar-card.tsx**: Replace the existing formula expansion click handler with `<FormulaTooltip metricKey={normalizeSubFactorKey(sub.name)}>` wrapping the sub-factor name. Keep the existing inline formula expansion as a fallback for richer detail.

**conviction-engine.tsx**: Wrap metric card labels (Asymmetry Ratio, Max Position %) with FormulaTooltip using keys `asymmetry_ratio`, `max_position_pct`.

**valuation-section.tsx**: Wrap valuation method names (DCF, EV/FCF, etc.) with FormulaTooltip using keys `dcf_valuation`, `ev_fcf_valuation`, `ev_ebit_valuation`, `shareholder_yield_valuation`.

**factor-radar.tsx**: Wrap axis labels in the mobile bar view with FormulaTooltip for quality/value/momentum composites (these don't have individual formulas but can show weight info).

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/formula-integration.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/filter-card.tsx web/src/components/asset-detail/pillar-card.tsx web/src/components/asset-detail/conviction-engine.tsx web/src/components/asset-detail/valuation-section.tsx web/src/components/asset-detail/factor-radar.tsx web/src/components/asset-detail/__tests__/formula-integration.test.tsx
git commit -m "feat(web): wire FormulaTooltip into filter, pillar, conviction, and valuation components"
```

---

### Task 7: Enhance EliminatedHero with Protective Framing

Add protective framing for mega-cap tickers and a one-line hypothetical teaser.

**Files:**
- Modify: `web/src/components/asset-detail/eliminated-hero.tsx`
- Modify: `web/src/components/asset-detail/__tests__/eliminated-hero.test.tsx` (or create if doesn't exist)

**Step 1: Write the failing test**

Create/update `web/src/components/asset-detail/__tests__/eliminated-hero.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EliminatedHero } from '../eliminated-hero'

const baseProps = {
  ticker: 'TSLA',
  name: 'Tesla, Inc.',
  sector: 'Consumer Discretionary',
  growthStage: 'High Growth',
  price: 248.5,
  priceChange: -2.3,
  filtersPassed: [
    { name: 'beneish_m_score', passed: false, value: -1.42, threshold: -1.78, detail: '', verdict: 'fail' as const },
    { name: 'altman_z_score', passed: true, value: 3.2, threshold: 1.81, detail: '', verdict: 'pass' as const },
    { name: 'fcf_distress', passed: true, value: 1000000, threshold: 0, detail: '', verdict: 'pass' as const },
    { name: 'interest_coverage', passed: true, value: 5.0, threshold: 1.5, detail: '', verdict: 'pass' as const },
    { name: 'current_ratio', passed: true, value: 2.0, threshold: 1.0, detail: '', verdict: 'pass' as const },
    { name: 'liquidity', passed: true, value: 50000000000, threshold: 300000000, detail: '', verdict: 'pass' as const },
  ],
  dataCoverage: 0.92,
  scoredAt: '2026-02-26T10:00:00Z',
}

describe('EliminatedHero', () => {
  it('renders protective framing for mega-cap tickers', () => {
    render(<EliminatedHero {...baseProps} marketCap={800_000_000_000} />)
    expect(screen.getByText(/Our filters don't care/i)).toBeInTheDocument()
  })

  it('renders clinical framing for small-cap tickers', () => {
    render(<EliminatedHero {...baseProps} ticker="SMLL" name="SmallCo Inc." marketCap={500_000_000} />)
    expect(screen.queryByText(/Our filters don't care/i)).not.toBeInTheDocument()
    expect(screen.getByText(/1 of 6 forensic filters failed/i)).toBeInTheDocument()
  })

  it('shows hypothetical teaser line when hypotheticalPercentile is provided', () => {
    render(
      <EliminatedHero {...baseProps} marketCap={800_000_000_000} hypotheticalPercentile={74} />
    )
    expect(screen.getByText(/74th percentile/)).toBeInTheDocument()
    expect(screen.getByText(/If it passed/i)).toBeInTheDocument()
  })

  it('does not show hypothetical teaser when not provided', () => {
    render(<EliminatedHero {...baseProps} marketCap={500_000_000} />)
    expect(screen.queryByText(/If it passed/)).not.toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/eliminated-hero.test.tsx`
Expected: FAIL — no protective framing text or hypothetical teaser

**Step 3: Enhance EliminatedHero**

In `web/src/components/asset-detail/eliminated-hero.tsx`:

Add new optional props:
```typescript
interface EliminatedHeroProps {
  // ... existing props
  marketCap?: number
  hypotheticalPercentile?: number | null
}
```

Add protective framing block (after the red elimination banner, around line 74):
```tsx
{/* Protective framing for mega-caps */}
{marketCap && marketCap >= 100_000_000_000 ? (
  <p className="text-xs text-secondary leading-relaxed mt-3 max-w-lg">
    {name} is among the largest companies by market cap. Our filters don&apos;t care.{' '}
    {failedCount} forensic {failedCount === 1 ? 'signal' : 'signals'} flagged elevated
    risk — the same signals that preceded the majority of major accounting restatements
    in academic studies.
  </p>
) : null}

{/* Hypothetical teaser */}
{hypotheticalPercentile != null && (
  <p className="text-[10px] font-mono text-tertiary mt-2">
    If it passed: Would have scored in the{' '}
    <span className="text-secondary">{hypotheticalPercentile}th percentile</span>.
  </p>
)}
```

**Step 4: Wire new props in asset-detail-view.tsx**

Pass `marketCap={scoreData.market_cap}` and `hypotheticalPercentile={scoreData.composite_percentile}` to EliminatedHero. The composite_percentile is the hypothetical score from the existing score data.

**Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/eliminated-hero.test.tsx`
Expected: PASS

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/eliminated-hero.tsx web/src/components/asset-detail/__tests__/eliminated-hero.test.tsx web/src/components/asset-detail/asset-detail-view.tsx
git commit -m "feat(web): enhance EliminatedHero with protective framing and hypothetical teaser"
```

---

### Task 8: Enhance FilterCard with Sector Context Line

Add "X% of stocks in this sector pass this filter" line to failed filters.

**Files:**
- Modify: `web/src/components/asset-detail/filter-card.tsx`
- Modify: `web/src/components/asset-detail/__tests__/filter-card.test.tsx`

**Step 1: Write the failing test**

Add to existing `filter-card.test.tsx`:

```tsx
it('shows sector pass rate on failed filters when provided', () => {
  render(
    <FilterCard
      filter={{
        name: 'beneish_m_score',
        passed: false,
        value: -1.42,
        threshold: -1.78,
        detail: 'Q3 2025 filing',
        verdict: 'fail',
      }}
      defaultExpanded={true}
      sectorPassRate={0.68}
      sectorName="Consumer Discretionary"
    />
  )
  expect(screen.getByText(/68% of Consumer Discretionary stocks pass this filter/)).toBeInTheDocument()
})

it('does not show sector pass rate on passing filters', () => {
  render(
    <FilterCard
      filter={{
        name: 'beneish_m_score',
        passed: true,
        value: -2.5,
        threshold: -1.78,
        detail: '',
        verdict: 'pass',
      }}
      defaultExpanded={true}
      sectorPassRate={0.68}
      sectorName="Consumer Discretionary"
    />
  )
  expect(screen.queryByText(/68%/)).not.toBeInTheDocument()
})

it('does not show sector pass rate when not provided', () => {
  render(
    <FilterCard
      filter={{
        name: 'beneish_m_score',
        passed: false,
        value: -1.42,
        threshold: -1.78,
        detail: '',
        verdict: 'fail',
      }}
      defaultExpanded={true}
    />
  )
  expect(screen.queryByText(/stocks pass this filter/)).not.toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: FAIL — no sector pass rate text

**Step 3: Add sector context line to FilterCard**

Add optional props to FilterCard:
```typescript
interface FilterCardProps {
  // ... existing
  sectorPassRate?: number | null
  sectorName?: string | null
}
```

Insert between the Value/Threshold row and the "WHY THIS MATTERS" block (around line 91-94):
```tsx
{!filter.passed && sectorPassRate != null && sectorName && (
  <p className="text-[10px] text-tertiary mt-1.5">
    {Math.round(sectorPassRate * 100)}% of {sectorName} stocks pass this filter.
  </p>
)}
```

Note: `sectorPassRate` will be undefined for now (API doesn't return it yet). The component gracefully handles absence. When the API enhancement ships, just pass the data through.

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/filter-card.tsx web/src/components/asset-detail/__tests__/filter-card.test.tsx
git commit -m "feat(web): add sector pass rate context line to FilterCard for failed filters"
```

---

### Task 9: FailedComparison Component

Side-by-side comparison showing what passed where this stock failed.

**Files:**
- Create: `web/src/components/asset-detail/failed-comparison.tsx`
- Create: `web/src/components/asset-detail/__tests__/failed-comparison.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`

**Step 1: Write the failing test**

Create `web/src/components/asset-detail/__tests__/failed-comparison.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FailedComparison } from '../failed-comparison'

const mockFailedFilters = [
  {
    filterName: 'beneish_m_score',
    filterDisplayName: 'Beneish M-Score',
    stockValue: -1.42,
    threshold: -1.78,
    championValue: -2.91,
    championTicker: 'AAPL',
    sectorMedian: -2.44,
  },
  {
    filterName: 'earnings_quality',
    filterDisplayName: 'Sloan Accrual Ratio',
    stockValue: 0.12,
    threshold: 0.10,
    championValue: -0.04,
    championTicker: 'AAPL',
    sectorMedian: 0.02,
  },
]

describe('FailedComparison', () => {
  it('renders the comparison header', () => {
    render(
      <FailedComparison
        ticker="TSLA"
        failedFilters={mockFailedFilters}
      />
    )
    expect(screen.getByText(/Where TSLA Failed, Others Passed/)).toBeInTheDocument()
  })

  it('shows both failed filter comparisons', () => {
    render(
      <FailedComparison
        ticker="TSLA"
        failedFilters={mockFailedFilters}
      />
    )
    expect(screen.getByText('Beneish M-Score')).toBeInTheDocument()
    expect(screen.getByText('Sloan Accrual Ratio')).toBeInTheDocument()
  })

  it('shows stock value vs champion value for each filter', () => {
    render(
      <FailedComparison
        ticker="TSLA"
        failedFilters={mockFailedFilters}
      />
    )
    expect(screen.getByText(/TSLA/)).toBeInTheDocument()
    expect(screen.getByText('FAIL')).toBeTruthy()
    expect(screen.getByText('PASS')).toBeTruthy()
  })

  it('shows comparison stock attribution', () => {
    render(
      <FailedComparison
        ticker="TSLA"
        failedFilters={mockFailedFilters}
      />
    )
    expect(screen.getByText(/AAPL/)).toBeInTheDocument()
    expect(screen.getByText(/highest-scoring in same sector/)).toBeInTheDocument()
  })

  it('renders nothing when failedFilters is empty', () => {
    const { container } = render(
      <FailedComparison ticker="TSLA" failedFilters={[]} />
    )
    expect(container.firstChild).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/failed-comparison.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the FailedComparison component**

Create `web/src/components/asset-detail/failed-comparison.tsx`:

```tsx
export interface FailedFilterComparison {
  filterName: string
  filterDisplayName: string
  stockValue: number
  threshold: number
  championValue: number | null
  championTicker: string | null
  sectorMedian: number | null
}

interface FailedComparisonProps {
  ticker: string
  failedFilters: FailedFilterComparison[]
}

function formatValue(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toFixed(2)
}

export function FailedComparison({ ticker, failedFilters }: FailedComparisonProps) {
  if (failedFilters.length === 0) return null

  // Use the first champion ticker for the attribution line
  const championTicker = failedFilters.find((f) => f.championTicker)?.championTicker

  return (
    <section data-testid="failed-comparison" className="terminal-card p-6">
      <h3 className="text-sm font-semibold text-primary mb-4">
        Where {ticker} Failed, Others Passed
      </h3>

      <div className="space-y-5">
        {failedFilters.map((f) => (
          <div key={f.filterName}>
            <p className="text-xs font-medium text-secondary mb-2">{f.filterDisplayName}</p>

            {/* Stock row */}
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-mono text-tertiary w-12">{ticker}</span>
              <div className="flex-1 relative h-2 bg-white/[0.04] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-bearish/50"
                  style={{
                    width: `${Math.min(100, Math.max(5, Math.abs(f.stockValue / (f.threshold * 2)) * 100))}%`,
                  }}
                />
              </div>
              <span className="text-[10px] font-mono text-tertiary w-14 text-right">
                {formatValue(f.stockValue)}
              </span>
              <span className="text-[9px] font-mono text-bearish font-semibold w-8">FAIL</span>
            </div>

            {/* Champion row */}
            {f.championTicker && f.championValue != null && (
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono text-tertiary w-12">
                  {f.championTicker}
                </span>
                <div className="flex-1 relative h-2 bg-white/[0.04] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-bullish/50"
                    style={{
                      width: `${Math.min(100, Math.max(5, Math.abs(f.championValue / (f.threshold * 2)) * 100))}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] font-mono text-tertiary w-14 text-right">
                  {formatValue(f.championValue)}
                </span>
                <span className="text-[9px] font-mono text-bullish font-semibold w-8">PASS</span>
              </div>
            )}

            {/* Threshold + Sector median */}
            <div className="flex gap-4 mt-1">
              <span className="text-[9px] text-tertiary">
                Threshold: {formatValue(f.threshold)}
              </span>
              {f.sectorMedian != null && (
                <span className="text-[9px] text-tertiary">
                  Sector median: {formatValue(f.sectorMedian)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {championTicker && (
        <p className="text-[9px] text-tertiary mt-4 pt-3 border-t border-white/[0.06]">
          Comparison stock: {championTicker} (highest-scoring in same sector)
        </p>
      )}
    </section>
  )
}
```

**Step 4: Wire into asset-detail-view.tsx**

In the eliminated flow, insert `<FailedComparison>` between EliminationGauntlet and HypotheticalScores. For now, construct `failedFilters` from the existing `scoreData.filters_passed` array (without champion data — those fields will be `null` until the API enhancement ships):

```tsx
const failedFilterComparisons = scoreData.filters_passed
  .filter((f) => !f.passed)
  .map((f) => ({
    filterName: f.name,
    filterDisplayName: FILTER_METADATA[f.name]?.displayName || f.name,
    stockValue: f.value ?? 0,
    threshold: f.threshold ?? 0,
    championValue: null, // API enhancement needed
    championTicker: null, // API enhancement needed
    sectorMedian: null,   // API enhancement needed
  }))
```

**Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/failed-comparison.test.tsx`
Expected: PASS (all 5 tests)

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/failed-comparison.tsx web/src/components/asset-detail/__tests__/failed-comparison.test.tsx web/src/components/asset-detail/asset-detail-view.tsx
git commit -m "feat(web): add FailedComparison component for eliminated ticker near-miss flow"
```

---

### Task 10: Run Full Test Suite and Final Verification

Ensure all existing tests still pass alongside the new ones.

**Files:**
- No new files

**Step 1: Run the full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass (existing ~978 + new ~25)

**Step 2: Fix any broken tests**

If any existing tests break due to new components in the render tree (e.g., asset-detail-view tests may need updated mocks for FactorRadar, DeterminismBadge, SectorNeutralBanner, FailedComparison), add appropriate mocks:

```tsx
vi.mock('../factor-radar', () => ({
  FactorRadar: () => <div data-testid="factor-radar" />,
}))
vi.mock('../determinism-badge', () => ({
  DeterminismBadge: () => <div data-testid="determinism-badge" />,
}))
vi.mock('../sector-neutral-banner', () => ({
  SectorNeutralBanner: () => <div data-testid="sector-neutral-banner" />,
}))
vi.mock('../failed-comparison', () => ({
  FailedComparison: () => <div data-testid="failed-comparison" />,
}))
```

**Step 3: Run full suite again after fixes**

Run: `cd web && npx vitest run`
Expected: ALL PASS

**Step 4: Commit any test fixes**

```bash
git add -A web/src/components/asset-detail/__tests__/
git commit -m "fix(web): update existing tests for new UX strategy components"
```

---

## Task Dependency Graph

```
Task 1: FormulaTooltip + formula-definitions (foundation)
   |
   +---> Task 2: FactorRadar (uses FormulaTooltip on axis labels)
   |        |
   |        +---> Task 3: Wire FactorRadar into AssetDetailView
   |
   +---> Task 4: DeterminismBadge + SectorNeutralBanner (independent)
   |
   +---> Task 5: SectorMicroBar for PillarCard sub-factors
   |
   +---> Task 6: Wire FormulaTooltip into all existing components
   |
   +---> Task 8: FilterCard sector context line enhancement

Task 7: Enhanced EliminatedHero (independent of Task 1)

Task 9: FailedComparison component (independent of Task 1)

Task 10: Full test suite verification (depends on all above)
```

**Parallelizable groups:**
- **Group A** (sequential): Task 1 → Task 6
- **Group B** (parallel with A after Task 1): Task 2 → Task 3
- **Group C** (parallel with B): Task 4, Task 5, Task 8
- **Group D** (parallel with all): Task 7, Task 9
- **Group E** (final): Task 10

## API Enhancements Deferred (Separate Plan)

These data requirements are designed into the components but return `null`/absent gracefully:
1. `sector_pass_rate` on `FilterResultResponse` — needed for FilterCard sector context line
2. Sector champion endpoint — needed for FailedComparison champion data
3. Sector distribution (P10/P50/P90) per sub-factor — needed for SectorMicroBar to show real sector data
4. Sector peer count — needed for SectorNeutralBanner
5. `market_cap` on `ScoreResponse` — needed for EliminatedHero protective framing threshold
