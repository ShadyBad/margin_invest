# Premium Editorial Transformation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Margin Invest's landing page and dashboard into a premium editorial experience with multi-font typography, warm neutral colors, generous spacing, evolved WebGL, and a redesigned stock card system.

**Architecture:** Layer editorial polish onto existing Next.js 15 + Tailwind v4 + R3F stack. Typography adds Instrument Serif via `next/font/google`. Color warmth is achieved through CSS custom property updates. WebGL evolution adds `@react-three/postprocessing`. Stock card gets three-tier visual hierarchy. All changes are additive — no structural layout rewrites.

**Tech Stack:** Next.js 15, Tailwind CSS v4 (`@theme` tokens), React Three Fiber + Drei + postprocessing, Framer Motion, Recharts, Vitest + RTL

**Test runner:** `cd /Users/brandon/repos/margin_invest/web && npx vitest run` (must run from web/ directory)

---

## Task 1: Add Instrument Serif Display Font

**Files:**
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/app/globals.css`

**Step 1: Add Instrument Serif import to layout.tsx**

In `web/src/app/layout.tsx`, add the import and font instance:

```tsx
import { Inter_Tight, Geist_Mono, Instrument_Serif } from "next/font/google";

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
});
```

Then add the variable to the body className:

```tsx
<body
  className={`${interTight.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased bg-bg-primary text-text-primary`}
>
```

**Step 2: Register the CSS variable in globals.css**

In `web/src/app/globals.css`, update the `@theme inline` block (line 133-136):

```css
@theme inline {
  --font-sans: var(--font-inter-tight);
  --font-mono: var(--font-geist-mono);
  --font-display: var(--font-instrument-serif);
}
```

**Step 3: Run tests to verify nothing breaks**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All 278+ tests pass (font addition is purely additive)

**Step 4: Verify in browser**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`
Open http://localhost:3000, inspect elements and confirm `--font-instrument-serif` is available in computed styles.

**Step 5: Commit**

```bash
git add web/src/app/layout.tsx web/src/app/globals.css
git commit -m "feat: add Instrument Serif display font to font stack"
```

---

## Task 2: Warm Neutral Color System

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: Update dark mode tokens**

In `web/src/app/globals.css`, update the `.dark` block (lines 57-83):

```css
.dark {
  --color-bg-primary: #110F0D;
  --color-bg-elevated: #1A1714;
  --color-bg-subtle: #211E1A;

  --color-text-primary: #EDE9E3;
  --color-text-secondary: #A39E96;
  --color-text-tertiary: #6B6660;

  --color-accent: #1A7A5A;
  --color-accent-hover: #1F8F6A;
  --color-accent-subtle: rgba(26, 122, 90, 0.10);

  --color-border-primary: #2A2621;
  --color-border-subtle: rgba(237, 233, 227, 0.06);

  --color-bullish: #1A7A5A;
  --color-bearish: #D45A5F;
  --color-warning: #D4A843;
  --color-danger: #D45A5F;

  --color-surface-overlay: rgba(237, 233, 227, 0.03);

  --color-grid-line: rgba(255, 255, 255, 0.04);
  --color-divider: rgba(255, 255, 255, 0.06);
}
```

**Step 2: Update light mode tokens**

In the `@theme` block (lines 10-54), update these three values:

```css
  --color-bg-primary: #F5F2EC;
  --color-bg-elevated: #FEFDFB;
  --color-bg-subtle: #EBE7DF;
```

**Step 3: Add new tokens to @theme block**

Add these after the existing shadow tokens:

```css
  /* Warm surface wash */
  --color-surface-warm: rgba(180, 160, 130, 0.03);

  /* WebGL glow tinting */
  --color-glow-accent: rgba(26, 122, 90, 0.15);
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass (CSS-only changes)

**Step 5: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat: shift color system to warm neutral palette"
```

---

## Task 3: Editorial Spacing — Landing Sections

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`
- Modify: `web/src/components/landing/sections/engine-diagram.tsx`
- Modify: `web/src/components/landing/sections/friction-section.tsx`
- Modify: `web/src/components/landing/sections/engine-proof.tsx`
- Modify: `web/src/components/landing/sections/capabilities-section.tsx`
- Modify: `web/src/components/landing/sections/pricing-section.tsx`
- Modify: `web/src/components/landing/sections/final-cta.tsx`
- Modify: `web/src/components/landing/sections/metrics-strip.tsx`

**Step 1: Update HeroSection spacing and typography**

In `web/src/components/landing/sections/hero-section.tsx`:

Change the container style (line 15-19):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "180px",
  paddingBottom: "140px",
}}
```

Change the h1 classes (line 24):
```tsx
className="font-display text-[56px] md:text-[72px] lg:text-[88px] font-normal leading-[1.05] tracking-[-0.04em] text-text-primary"
```

Note: `font-display` uses the new Instrument Serif. Changed from `font-bold` to `font-normal` since Instrument Serif only has weight 400. Sizes bumped up.

Change the subtitle gap (line 33): `mt-6` → `mt-8`

Change the CTA gap (line 41): `mt-10` → `mt-12`

**Step 2: Update EngineDiagram spacing**

In `web/src/components/landing/sections/engine-diagram.tsx`:

Update the container style (lines 139-145):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "140px",
  paddingBottom: "140px",
}}
```

**Step 3: Update FrictionSection spacing**

In `web/src/components/landing/sections/friction-section.tsx`:

Update the container style (lines 19-25):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "120px",
  paddingBottom: "140px",
}}
```

**Step 4: Update EngineProof spacing**

In `web/src/components/landing/sections/engine-proof.tsx`:

Update the container style (lines 177-183):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "100px",
  paddingBottom: "120px",
}}
```

**Step 5: Update CapabilitiesSection spacing**

In `web/src/components/landing/sections/capabilities-section.tsx`:

Update the container style (lines 52-57):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "140px",
  paddingBottom: "140px",
}}
```

**Step 6: Update PricingSection spacing**

In `web/src/components/landing/sections/pricing-section.tsx`:

Update the container style (lines 145-151):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "140px",
  paddingBottom: "140px",
}}
```

**Step 7: Update FinalCTA spacing**

In `web/src/components/landing/sections/final-cta.tsx`:

Update the container style (lines 14-19):
```tsx
style={{
  maxWidth: "1200px",
  paddingLeft: "10vw",
  paddingRight: "10vw",
  paddingTop: "160px",
  paddingBottom: "180px",
}}
```

**Step 8: Update MetricsStrip**

In `web/src/components/landing/sections/metrics-strip.tsx`:

Update the container style (line 15):
```tsx
style={{ maxWidth: "1200px", margin: "0 auto", paddingLeft: "10vw", paddingRight: "10vw" }}
```

**Step 9: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 10: Commit**

```bash
git add web/src/components/landing/sections/
git commit -m "feat: apply editorial spacing to all landing sections"
```

---

## Task 4: Editorial Typography — Landing Sections

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx` (already updated in Task 3)
- Modify: `web/src/components/landing/sections/engine-proof.tsx`
- Modify: `web/src/components/landing/sections/pricing-section.tsx`
- Modify: `web/src/components/landing/sections/final-cta.tsx`
- Modify: `web/src/components/landing/sections/metrics-strip.tsx`
- Modify: `web/src/components/landing/sections/friction-section.tsx`

**Step 1: Update EngineProof heading**

In `web/src/components/landing/sections/engine-proof.tsx`, change the h2 (line 192):
```tsx
<h2 className="font-display text-[36px] md:text-[44px] lg:text-[56px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]">
```

Also change the composite score number (line 63) to use display font:
```tsx
<span className="text-[36px] font-display text-text-primary leading-none tracking-[-1px]">
```

**Step 2: Update PricingSection heading**

In `web/src/components/landing/sections/pricing-section.tsx`, change the h2 (line 160):
```tsx
<h2 className="font-display text-[32px] md:text-[40px] lg:text-[48px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]">
```

Also update tier price display to use display font. In TierCard (line 98):
```tsx
<span className="text-[36px] font-display text-text-primary leading-none tracking-[-1px]">
```

**Step 3: Update FinalCTA heading**

In `web/src/components/landing/sections/final-cta.tsx`, change the h2 (line 29):
```tsx
<h2 className="font-display text-[32px] md:text-[40px] lg:text-[48px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em] mb-4">
```

**Step 4: Update MetricsStrip numbers to use display font**

In `web/src/components/landing/sections/metrics-strip.tsx`, we want the numbers to use the display font. Restructure the metrics to separate numbers from labels:

```tsx
const metrics = [
  { number: "2,400+", label: "equities scored daily" },
  { number: "6", label: "quantitative factors" },
  { label: "Updated every market close" },
]
```

And update the rendering:
```tsx
{metrics.map((m, i) => (
  <span key={m.label} className="flex items-center gap-6">
    {i > 0 && <span className="text-border-primary">|</span>}
    <span>
      {m.number && <span className="font-display text-[15px]">{m.number} </span>}
      {m.label}
    </span>
  </span>
))}
```

**Step 5: Update FrictionSection headings**

In `web/src/components/landing/sections/friction-section.tsx`, change the h3 class (line 31):
```tsx
className="font-display text-[32px] md:text-[36px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]"
```

**Step 6: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 7: Commit**

```bash
git add web/src/components/landing/sections/
git commit -m "feat: apply Instrument Serif to landing section headings and numbers"
```

---

## Task 5: Stock Card Three-Tier Redesign

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/ui/conviction-badge.tsx`
- Modify: `web/src/app/globals.css`
- Modify: `web/src/components/dashboard/__tests__/stock-card.test.tsx`

**Step 1: Add card animation keyframe to globals.css**

In `web/src/app/globals.css`, add after the login keyframes (after line 170):

```css
@keyframes score-glow-pulse {
  0%, 100% { opacity: 0.03; }
  50% { opacity: 0.06; }
}

.score-glow-pulse {
  animation: score-glow-pulse 2s ease-in-out infinite;
}
```

**Step 2: Update ConvictionBadge for exceptional filled treatment**

In `web/src/components/ui/conviction-badge.tsx`, update the styles:

```tsx
const badgeStyles: Record<string, string> = {
  exceptional: "bg-accent text-white border-accent",
  high: "bg-accent/10 text-accent-hover border-accent/20",
  watchlist: "bg-bg-elevated text-text-secondary border-border-primary",
  none: "bg-bg-primary text-text-secondary border-border-primary",
}
```

Also add size variation — exceptional badge gets slightly larger:

```tsx
export function ConvictionBadge({ level, className = "" }: ConvictionBadgeProps) {
  const style = badgeStyles[level] || badgeStyles.none
  const sizeClass = level === "exceptional" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs"
  return (
    <span className={`inline-flex items-center rounded-sm font-medium border ${sizeClass} ${style} ${className}`}>
      {level}
    </span>
  )
}
```

**Step 3: Redesign StockCard with three-tier hierarchy**

In `web/src/components/dashboard/stock-card.tsx`, update `getCardTierClasses`:

```tsx
function getCardTierClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "border-accent/30 rounded-lg"
    case "high":
      return "border-l-2 border-l-accent rounded-lg"
    default:
      return "rounded-lg"
  }
}

function getCardShadow(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "shadow-[0_0_30px_rgba(26,122,90,0.08),0_4px_16px_rgba(0,0,0,0.3)] hover:shadow-[0_0_40px_rgba(26,122,90,0.12),0_6px_20px_rgba(0,0,0,0.35)]"
    default:
      return "shadow-card hover:shadow-card-hover"
  }
}

function getScoreClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "text-[56px] font-display text-accent leading-none tracking-[-0.04em]"
    case "high":
      return "text-[48px] font-display text-text-primary leading-none tracking-[-0.04em]"
    default:
      return "text-[48px] font-display text-text-secondary leading-none tracking-[-0.04em]"
  }
}
```

Update the card container div classes (line 69):
```tsx
<div
  className={`bg-bg-elevated border border-border-primary p-8 cursor-pointer transition-all hover:scale-[1.01] hover:border-accent/20 ${expanded ? "col-span-full" : ""} ${getCardTierClasses(pick.conviction_level)} ${getCardShadow(pick.conviction_level)} ${className}`}
```

For exceptional cards, add the top accent stripe and warm gradient:
```tsx
{pick.conviction_level === "exceptional" && (
  <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent rounded-t-lg" />
)}
```

The container needs `relative` added. Also add warm gradient for exceptional:
```tsx
{pick.conviction_level === "exceptional" && (
  <div className="absolute inset-0 rounded-lg pointer-events-none bg-[radial-gradient(ellipse_at_top_left,rgba(180,160,130,0.04),transparent_50%),radial-gradient(ellipse_at_bottom_right,rgba(26,122,90,0.03),transparent_50%)]" />
)}
```

Update the score display (line 126-131) to use the new helper:
```tsx
<div className="mb-6">
  <span className={getScoreClasses(pick.conviction_level)}>
    {(pick.score || pick.composite_percentile).toFixed(0)}
  </span>
  <span className="block text-[11px] font-medium text-text-tertiary tracking-[0.15em] uppercase mt-1">
    conviction
  </span>
</div>
```

Update card padding from `p-6` to `p-8`.

Update header-to-body gap from `mb-1` to `mb-3`.

Update percentile bar factor labels to small uppercase tracking:
```tsx
<PercentileBar value={pick.quality_percentile} label="QUALITY" />
```

Wait — the labels are passed as strings. Instead, update the PercentileBar label display to add tracking. Actually, leave the label values as-is and update the label `<span>` in PercentileBar in Task 6.

**Step 4: Update tests**

In `web/src/components/dashboard/__tests__/stock-card.test.tsx`, update any class-based assertions if they check for `rounded-sm` or specific shadow classes. The main testid-based queries should still work.

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 6: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/ui/conviction-badge.tsx web/src/app/globals.css web/src/components/dashboard/__tests__/
git commit -m "feat: redesign stock card with three-tier conviction hierarchy"
```

---

## Task 6: Refined Percentile Bar & Dashboard Spacing

**Files:**
- Modify: `web/src/components/ui/percentile-bar.tsx`
- Modify: `web/src/components/dashboard/picks-grid.tsx`
- Modify: `web/src/app/dashboard/page.tsx`
- Modify: `web/src/components/dashboard/portfolio-conviction.tsx`

**Step 1: Update PercentileBar styling**

In `web/src/components/ui/percentile-bar.tsx`:

Update the label span (line 22) to add uppercase tracking:
```tsx
<span className="text-[11px] text-text-tertiary w-40 shrink-0 truncate uppercase tracking-[0.1em]" title={label}>
```

Update the bar height to 8px and add inner shadow:
```tsx
<div className="flex-1 h-[8px] bg-bg-primary rounded-full overflow-hidden shadow-[inset_0_1px_2px_rgba(0,0,0,0.1)]">
```

**Step 2: Update PicksGrid gap**

In `web/src/components/dashboard/picks-grid.tsx`, update grid gap (line 39):
```tsx
className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 ${className}`}
```

Update stagger delay from 50ms to 60ms (line 13):
```tsx
transition: { duration: 0.4, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] },
```

**Step 3: Update dashboard page spacing**

In `web/src/app/dashboard/page.tsx`, add top padding to the header section:
```tsx
<div className="mb-10 pt-12 flex items-start justify-between">
```

**Step 4: Update PortfolioConviction to use display font**

In `web/src/components/dashboard/portfolio-conviction.tsx`, change the score number to use Instrument Serif:
```tsx
<span className="text-[40px] font-display text-accent leading-none tracking-[-0.04em]">{score.toFixed(0)}</span>
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 6: Commit**

```bash
git add web/src/components/ui/percentile-bar.tsx web/src/components/dashboard/picks-grid.tsx web/src/app/dashboard/page.tsx web/src/components/dashboard/portfolio-conviction.tsx
git commit -m "feat: refine percentile bar, grid spacing, and dashboard typography"
```

---

## Task 7: WebGL Postprocessing Stack

**Files:**
- Create: `web/src/components/landing/scene/postprocessing-stack.tsx`
- Modify: `web/src/components/landing/scene/scene-canvas.tsx`
- Modify: `web/package.json` (add dependency)

**Step 1: Install @react-three/postprocessing**

```bash
cd /Users/brandon/repos/margin_invest/web && npm install @react-three/postprocessing
```

**Step 2: Create PostprocessingStack component**

Create `web/src/components/landing/scene/postprocessing-stack.tsx`:

```tsx
"use client"

import { EffectComposer, Bloom, Vignette, ChromaticAberration } from "@react-three/postprocessing"
import { BlendFunction } from "postprocessing"
import { Vector2 } from "three"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface PostprocessingStackProps {
  tier: QualityTier
}

export function PostprocessingStack({ tier }: PostprocessingStackProps) {
  if (tier === "low") return null

  return (
    <EffectComposer>
      <Bloom
        luminanceThreshold={0.8}
        luminanceSmoothing={0.3}
        intensity={0.3}
        radius={0.6}
        blendFunction={BlendFunction.ADD}
      />
      <Vignette
        offset={0.3}
        darkness={0.5}
        blendFunction={BlendFunction.NORMAL}
      />
      {tier === "high" && (
        <ChromaticAberration
          offset={new Vector2(0.001, 0.001)}
          blendFunction={BlendFunction.NORMAL}
        />
      )}
    </EffectComposer>
  )
}
```

**Step 3: Wire into SceneCanvas**

In `web/src/components/landing/scene/scene-canvas.tsx`:

Add the import:
```tsx
import { PostprocessingStack } from "./postprocessing-stack"
```

Change `frameloop` from `"demand"` to `"always"` (postprocessing needs continuous rendering):
```tsx
frameloop="always"
```

Add PostprocessingStack inside Suspense, after ScrollControls:
```tsx
<Suspense fallback={null}>
  <ambientLight intensity={0.5} />
  <pointLight position={[5, 5, 5]} intensity={0.3} />
  <ScrollControls pages={pages} damping={0.15}>
    <AmbientGrid tier={tier} />
    <EngineNodes tier={tier} />
    <ConnectionLines />
    <CapabilityCards3D />
  </ScrollControls>
  <PostprocessingStack tier={tier} />
</Suspense>
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass (WebGL components are dynamically imported with SSR disabled, tests use jsdom)

**Step 5: Commit**

```bash
git add web/src/components/landing/scene/postprocessing-stack.tsx web/src/components/landing/scene/scene-canvas.tsx web/package.json web/package-lock.json
git commit -m "feat: add WebGL postprocessing stack (bloom, vignette, chromatic aberration)"
```

---

## Task 8: WebGL Node Behavior Evolution

**Files:**
- Modify: `web/src/components/landing/scene/engine-nodes.tsx`
- Modify: `web/src/components/landing/scene/connection-lines.tsx`

**Step 1: Add breathing animation to EngineNodes**

In `web/src/components/landing/scene/engine-nodes.tsx`:

Add a time ref and breathing calculation inside the `useFrame` callback. After line 87 (scale calculation):

```tsx
// Breathing animation — each node oscillates at its own rate
const time = performance.now() / 1000
const breathPeriod = 3 + i * 0.8 // 3-6.2s per node
const breathScale = 0.95 + 0.1 * (0.5 + 0.5 * Math.sin(time * (2 * Math.PI / breathPeriod)))
const finalScale = THREE.MathUtils.lerp(0.01, 1, nodeProgress) * (1 - recedeProgress * 0.5) * breathScale
tempObj.scale.setScalar(finalScale)
```

This replaces the current scale line (line 87):
```tsx
const scale = THREE.MathUtils.lerp(0.01, 1, nodeProgress) * (1 - recedeProgress * 0.5)
tempObj.scale.setScalar(scale)
```

Also add `invalidate()` call since we need continuous rendering for breathing:
```tsx
const { camera, size, invalidate } = useThree()
```

And call `invalidate()` at the end of `useFrame`.

**Step 2: Increase node spacing**

Update `FORMATION_POSITIONS` (line 11-16) to spread 1.4x:

```tsx
const FORMATION_POSITIONS: [number, number, number][] = [
  [-6.3, 0, 0],
  [-2.1, 0, 0],
  [2.1, 0, 0],
  [6.3, 0, 0],
]
```

**Step 3: Reduce connection line opacity**

In `web/src/components/landing/scene/connection-lines.tsx`, find the material opacity and reduce it to 0.4. Also add slight width variation if the line uses `lineWidth` or similar.

Specifically, find the `<lineBasicMaterial>` and update:
```tsx
<lineBasicMaterial transparent opacity={0.4} color="#0E4F3A" />
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 5: Commit**

```bash
git add web/src/components/landing/scene/engine-nodes.tsx web/src/components/landing/scene/connection-lines.tsx
git commit -m "feat: add breathing animation to WebGL nodes, increase spacing, soften connections"
```

---

## Task 9: Score Count-Up Animation

**Files:**
- Create: `web/src/components/ui/animated-score.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Create: `web/src/components/ui/__tests__/animated-score.test.tsx`

**Step 1: Write the test**

Create `web/src/components/ui/__tests__/animated-score.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AnimatedScore } from "../animated-score"

describe("AnimatedScore", () => {
  it("renders the final value", () => {
    render(<AnimatedScore value={87} className="test" />)
    // The component renders a span — even if animating, the final value should appear
    const el = screen.getByTestId("animated-score")
    expect(el).toBeInTheDocument()
  })

  it("applies className", () => {
    render(<AnimatedScore value={42} className="text-accent" />)
    const el = screen.getByTestId("animated-score")
    expect(el.className).toContain("text-accent")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/ui/__tests__/animated-score.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement AnimatedScore**

Create `web/src/components/ui/animated-score.tsx`:

```tsx
"use client"

import { useRef, useEffect } from "react"
import { useInView, useMotionValue, animate } from "framer-motion"

interface AnimatedScoreProps {
  value: number
  className?: string
  duration?: number
}

export function AnimatedScore({ value, className = "", duration = 0.6 }: AnimatedScoreProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const motionValue = useMotionValue(0)

  useEffect(() => {
    if (!isInView) return
    const controls = animate(motionValue, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
    })
    return controls.stop
  }, [isInView, motionValue, value, duration])

  useEffect(() => {
    const unsubscribe = motionValue.on("change", (v) => {
      if (ref.current) ref.current.textContent = Math.round(v).toString()
    })
    return unsubscribe
  }, [motionValue])

  return (
    <span ref={ref} className={className} data-testid="animated-score">
      {Math.round(value)}
    </span>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/ui/__tests__/animated-score.test.tsx`
Expected: PASS

**Step 5: Export from ui barrel**

Add to `web/src/components/ui/index.ts`:
```tsx
export { AnimatedScore } from "./animated-score"
```

**Step 6: Wire into StockCard**

In `web/src/components/dashboard/stock-card.tsx`, import and use AnimatedScore:

```tsx
import { ActionPill, Sparkline, PercentileBar, ConvictionBadge, AnimatedScore } from "@/components/ui"
```

Replace the score `<span>` with:
```tsx
<AnimatedScore
  value={pick.score || pick.composite_percentile}
  className={getScoreClasses(pick.conviction_level)}
/>
```

**Step 7: Run full tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 8: Commit**

```bash
git add web/src/components/ui/animated-score.tsx web/src/components/ui/__tests__/animated-score.test.tsx web/src/components/ui/index.ts web/src/components/dashboard/stock-card.tsx
git commit -m "feat: add count-up score animation with viewport trigger"
```

---

## Task 10: Enhanced Recharts Styling

**Files:**
- Modify: `web/src/components/dashboard/price-chart.tsx`

**Step 1: Add gradient definition and warm tooltip**

In `web/src/components/dashboard/price-chart.tsx`:

Add a gradient `<defs>` inside the `<ComposedChart>`:

```tsx
<ComposedChart data={data}>
  <defs>
    <linearGradient id="accentGradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.15} />
      <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
    </linearGradient>
  </defs>
```

Replace the CartesianGrid (line 93):
```tsx
<CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid-line)" />
```

Update XAxis tick styling (line 95):
```tsx
<XAxis
  dataKey="date"
  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-tertiary)" }}
  interval="preserveStartEnd"
  stroke="var(--color-grid-line)"
/>
```

Update YAxis tick styling (line 100):
```tsx
<YAxis
  yAxisId="price"
  domain={["auto", "auto"]}
  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-tertiary)" }}
  width={60}
  tickFormatter={(v: number) => `$${v}`}
  stroke="var(--color-grid-line)"
/>
```

Update Tooltip (line 108):
```tsx
<Tooltip
  contentStyle={{
    backgroundColor: "var(--color-bg-elevated)",
    border: "1px solid var(--color-border-primary)",
    borderRadius: "8px",
    fontSize: "12px",
    fontFamily: "var(--font-sans)",
    boxShadow: "var(--shadow-card)",
  }}
  labelStyle={{ fontFamily: "var(--font-display)", fontSize: "14px" }}
/>
```

Add an Area chart for the gradient fill (after the Line):
```tsx
<Line
  type="monotone"
  dataKey="close"
  stroke="currentColor"
  strokeWidth={1.5}
  dot={false}
  className="text-accent"
  yAxisId="price"
/>
```

Wait — Recharts `ComposedChart` supports Area. Add an Area with the gradient:
```tsx
import { Area } from "recharts"
```

Add Area before the Line:
```tsx
<Area
  type="monotone"
  dataKey="close"
  fill="url(#accentGradient)"
  stroke="none"
  yAxisId="price"
/>
```

Also update the chart header to use display font:
```tsx
<h4 className="text-sm font-semibold text-text-primary">Price History</h4>
```

**Step 2: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 3: Commit**

```bash
git add web/src/components/dashboard/price-chart.tsx
git commit -m "feat: enhance Recharts with gradient fills, warm tooltip, refined typography"
```

---

## Task 11: Card Hover & Interaction Polish

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/ui/percentile-bar.tsx`

**Step 1: Add interaction easing constant**

In `web/src/components/dashboard/stock-card.tsx`, add at the top:

```tsx
const INTERACTION_EASE = "cubic-bezier(0.19, 1, 0.22, 1)"
```

Update the card container `transition-all` to use specific properties:
```tsx
style={{ transition: `transform 200ms ${INTERACTION_EASE}, box-shadow 200ms ${INTERACTION_EASE}, border-color 200ms ${INTERACTION_EASE}` }}
```

**Step 2: Add conviction badge scale bounce**

Wrap the ConvictionBadge in a motion.div:

```tsx
import { motion } from "framer-motion"
```

```tsx
<motion.div
  initial={{ scale: 0.95 }}
  animate={{ scale: 1 }}
  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1], type: "spring", stiffness: 300, damping: 15 }}
>
  <ConvictionBadge level={pick.conviction_level} />
</motion.div>
```

**Step 3: Add delayed percentile bar fill**

In `web/src/components/ui/percentile-bar.tsx`, add a delay to the width transition when first rendered. Since this is a CSS-only component (no Framer Motion), use a CSS animation approach:

Update the bar fill div (line 28):
```tsx
<div
  className={`h-full rounded-r-full ${getColor(clampedValue)}`}
  style={{
    width: `${clampedValue}%`,
    transition: "width 600ms cubic-bezier(0.22, 1, 0.36, 1) 200ms",
  }}
/>
```

This adds a 200ms delay before the fill animates in, creating a cascade effect when a card appears.

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 5: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/ui/percentile-bar.tsx
git commit -m "feat: add interaction polish — hover easing, badge bounce, bar delay"
```

---

## Task 12: Final Visual Pass & Landing Warm-Up

**Files:**
- Modify: `web/src/components/landing/button-primary.tsx`
- Modify: `web/src/components/landing/capability-block.tsx`
- Modify: `web/src/components/landing/sections/engine-proof.tsx`

**Step 1: Update ButtonPrimary hover**

In `web/src/components/landing/button-primary.tsx`, add a warm hover glow:

```tsx
<Link
  href={href}
  className={`inline-flex items-center justify-center bg-accent text-white font-semibold text-[15px] rounded-[6px] hover:bg-accent-hover transition-all hover:shadow-[0_0_20px_rgba(26,122,90,0.2)] px-6 ${
    size === "large" ? "h-14" : "h-12"
  }`}
>
```

Note: also changed border radius from `rounded-[4px]` to `rounded-[6px]` for warmer feel.

**Step 2: Warm up CapabilityBlock**

In `web/src/components/landing/capability-block.tsx`, update the title to use display font:

```tsx
<h3 className="font-display text-[28px] md:text-[32px] lg:text-[36px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]">
```

**Step 3: Update EngineProof panel score display**

In `web/src/components/landing/sections/engine-proof.tsx`, the CompositeScorePanel's animated number (line 64) — make it use display font:

```tsx
<span className="text-[36px] font-display text-text-primary leading-none tracking-[-1px]">
```

**Step 4: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass

**Step 5: Visual verification**

Run dev server and verify:
- Landing: warm backgrounds, serif headlines, generous spacing, glowing CTA button
- Dashboard: three-tier cards, warm colors, refined bars, count-up scores
- WebGL: bloom/vignette visible, breathing nodes, softer connections

**Step 6: Commit**

```bash
git add web/src/components/landing/button-primary.tsx web/src/components/landing/capability-block.tsx web/src/components/landing/sections/engine-proof.tsx
git commit -m "feat: final visual pass — warm button glow, editorial capability titles, proof panel typography"
```

---

## Summary

| Task | Description | Deps |
|------|-------------|------|
| 1 | Add Instrument Serif display font | none |
| 2 | Warm neutral color system | none |
| 3 | Editorial spacing — landing sections | none |
| 4 | Editorial typography — landing sections | 1 |
| 5 | Stock card three-tier redesign | 1, 2 |
| 6 | Refined percentile bar & dashboard spacing | 1 |
| 7 | WebGL postprocessing stack | none |
| 8 | WebGL node behavior evolution | 7 |
| 9 | Score count-up animation | 1, 5 |
| 10 | Enhanced Recharts styling | 2 |
| 11 | Card hover & interaction polish | 5 |
| 12 | Final visual pass & landing warm-up | 1, 2, 3, 4 |

**Parallelization:** Tasks 1, 2, 3, 7 can run independently. Tasks 4-6 depend on 1. Tasks 8 depends on 7. Tasks 9-11 depend on 5. Task 12 is the final pass.
