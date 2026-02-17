# Homepage Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the landing page to define "conviction infrastructure" as a category, reorder sections for stronger narrative flow, add a pricing section, and align all copy with the strategic teardown.

**Architecture:** Copy and layout changes across existing section components, one new pricing section component, section reorder in page.tsx, and corresponding test updates. No new dependencies. No structural changes to WebGL scene or constellation animation.

**Tech Stack:** Next.js 15, React, Framer Motion, Vitest, Testing Library

---

### Task 1: Rewrite Hero Section Copy

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (HeroSection tests)

**Context:** The hero is the single highest-leverage change from the strategic teardown. Current copy ("Structure outperforms emotion.") is abstract. New copy defines the category immediately.

**Step 1: Update test assertions for new hero copy**

In `web/src/components/landing/__tests__/sections.test.tsx`, replace the `HeroSection` describe block:

```tsx
describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Conviction scoring for serious investors.")).toBeInTheDocument()
  })

  it("renders the subline", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(
        /deterministic engine that scores every stock across 6 factors/
      )
    ).toBeInTheDocument()
  })

  it("renders the primary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /score your first position/i })).toBeInTheDocument()
  })

  it("renders the secondary link", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /see the methodology/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | head -60`
Expected: 4 FAIL in HeroSection (old copy doesn't match new assertions)

**Step 3: Update hero-section.tsx with new copy**

In `web/src/components/landing/sections/hero-section.tsx`, replace the three content elements:

H1 text (line 29): Change from `Structure outperforms emotion.` to:
```
Conviction scoring for serious investors.
```

Subheading `<motion.p>` text (line 38): Change from `A deterministic scoring engine for capital allocation.` to:
```
A deterministic engine that scores every stock across 6 factors — so you hold with structure, not hope.
```

Primary CTA (line 47): Change from `Explore the Engine` to `Score your first position` (keep href="/dashboard")

Secondary CTA (line 48): Change from `View methodology` to `See the methodology` (keep href="/methodology")

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | head -60`
Expected: All HeroSection tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/hero-section.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat: rewrite hero section — define conviction infrastructure category"
```

---

### Task 2: Create Pricing Section Component

**Files:**
- Create: `web/src/components/landing/sections/pricing-section.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (add PricingSection tests)

**Context:** The teardown defines 3 tiers: Scout (Free), Operator ($29/mo), Allocator ($79/mo). This section sits between EngineProof and CapabilitiesSection. Uses the same grid system (4/8/12 columns), animation easing, and design tokens as all other sections.

**Step 1: Write failing tests for PricingSection**

Add this describe block to `web/src/components/landing/__tests__/sections.test.tsx`:

First, add `PricingSection` to the import from `"../sections"` at the top.

Then add the test block after the EngineProof tests:

```tsx
describe("PricingSection", () => {
  it("renders three tier names", () => {
    render(<PricingSection />)
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("Allocator")).toBeInTheDocument()
  })

  it("renders tier prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })

  it("renders CTA buttons for each tier", () => {
    render(<PricingSection />)
    const links = screen.getAllByRole("link")
    const pricingLinks = links.filter(
      (l) => l.textContent?.match(/start free|start trial|get started/i)
    )
    expect(pricingLinks.length).toBeGreaterThanOrEqual(3)
  })

  it("renders the section heading", () => {
    render(<PricingSection />)
    expect(screen.getByText(/simple, transparent pricing/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | head -60`
Expected: FAIL — PricingSection not exported from "../sections"

**Step 3: Create pricing-section.tsx**

Create `web/src/components/landing/sections/pricing-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  cta: string
  href: string
  highlighted: boolean
}

const tiers: Tier[] = [
  {
    name: "Scout",
    price: "Free",
    period: "",
    description: "Evaluate the engine with real positions.",
    features: [
      "3 ticker analyses per month",
      "Composite score + conviction level",
      "Top-level factor breakdown",
      "5-ticker watchlist",
    ],
    cta: "Start free",
    href: "/dashboard",
    highlighted: false,
  },
  {
    name: "Operator",
    price: "$29",
    period: "/mo",
    description: "Full scoring for active portfolio management.",
    features: [
      "Unlimited ticker analysis",
      "Full 6-factor breakdown",
      "90-day score history",
      "25-ticker watchlist",
      "Conviction change alerts",
    ],
    cta: "Start trial",
    href: "/dashboard",
    highlighted: true,
  },
  {
    name: "Allocator",
    price: "$79",
    period: "/mo",
    description: "Portfolio-level conviction infrastructure.",
    features: [
      "Everything in Operator",
      "Unlimited score history",
      "Portfolio correlation analysis",
      "Sector rotation signals",
      "API access",
    ],
    cta: "Get started",
    href: "/dashboard",
    highlighted: false,
  },
]

function TierCard({ tier, index }: { tier: Tier; index: number }) {
  return (
    <motion.div
      className={`flex flex-col p-6 rounded-[6px] border ${
        tier.highlighted
          ? "border-accent bg-bg-elevated"
          : "border-border-primary bg-bg-primary"
      }`}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1, ease }}
    >
      <div className="mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          {tier.name}
        </span>
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-[36px] font-bold text-text-primary leading-none tracking-[-1px]">
          {tier.price}
        </span>
        {tier.period && (
          <span className="text-[15px] text-text-secondary">{tier.period}</span>
        )}
      </div>
      <p className="text-[14px] text-text-secondary leading-relaxed mb-6">
        {tier.description}
      </p>
      <ul className="flex flex-col gap-2.5 mb-8 flex-1">
        {tier.features.map((feature) => (
          <li
            key={feature}
            className="text-[13px] text-text-secondary flex items-start gap-2"
          >
            <span className="text-accent mt-0.5 flex-shrink-0">&#x2713;</span>
            {feature}
          </li>
        ))}
      </ul>
      <Link
        href={tier.href}
        className={`block text-center text-[14px] font-medium py-3 px-6 rounded-[4px] transition-colors ${
          tier.highlighted
            ? "bg-accent text-white hover:bg-accent-hover"
            : "border border-border-primary text-text-primary hover:bg-bg-subtle"
        }`}
      >
        {tier.cta}
      </Link>
    </motion.div>
  )
}

export function PricingSection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[28px] md:text-[32px] lg:text-[40px] font-bold text-text-primary leading-tight tracking-[-0.3px]">
            Simple, transparent pricing.
          </h2>
          <p className="mt-3 text-[15px] text-text-secondary">
            Billed annually. Cancel anytime.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-[960px] mx-auto">
          {tiers.map((tier, i) => (
            <TierCard key={tier.name} tier={tier} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Export PricingSection from index.ts**

In `web/src/components/landing/sections/index.ts`, add:
```ts
export { PricingSection } from "./pricing-section"
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | head -60`
Expected: All PricingSection tests PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/sections/pricing-section.tsx web/src/components/landing/sections/index.ts web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat: add pricing section with Scout/Operator/Allocator tiers"
```

---

### Task 3: Reorder Homepage Sections + Wire Pricing

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/__tests__/page-assembly.test.tsx`

**Context:** The teardown prescribes a new section order that leads with the engine pipeline immediately after the hero. Current order: Hero → Friction → EngineDiagram → EngineProof → Capabilities → InvestorPositioning → FinalCTA. New order: Hero → EngineDiagram → FrictionSection → EngineProof → CapabilitiesSection → PricingSection → InvestorPositioning → FinalCTA.

**Step 1: Update page-assembly tests for new order and pricing**

In `web/src/components/landing/__tests__/page-assembly.test.tsx`, update the first test:

```tsx
describe("Landing page assembly", () => {
  it("renders all 8 sections in correct order", () => {
    render(<Page />)
    // Hero
    expect(screen.getByText("Conviction scoring for serious investors.")).toBeInTheDocument()
    // Engine Diagram (now second)
    expect(screen.getAllByText("Market Data").length).toBeGreaterThan(0)
    // Friction
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    // Engine Proof
    expect(screen.getByText("What the engine produces.")).toBeInTheDocument()
    // Capabilities
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    // Pricing (NEW)
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("Allocator")).toBeInTheDocument()
    // Investor Positioning
    expect(screen.getByText(/not trading/i)).toBeInTheDocument()
    // Final CTA
    const ctaLinks = screen.getAllByRole("link", { name: /score your first position/i })
    expect(ctaLinks.length).toBeGreaterThanOrEqual(1)
  })

  it("renders the minimal nav with Dashboard link", () => {
    render(<Page />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
    const dashboardLinks = screen.getAllByRole("link", { name: /^dashboard$/i })
    expect(dashboardLinks.length).toBeGreaterThanOrEqual(1)
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose 2>&1 | head -40`
Expected: FAIL — "Conviction scoring" not found (hero still has old copy from this test's perspective), PricingSection not rendered

**Step 3: Update page.tsx**

Replace `web/src/app/page.tsx`:

```tsx
import { LandingScene } from "@/components/landing/scene/landing-scene"
import { NavMinimal } from "@/components/landing/nav-minimal"
import { DevAnnotations } from "@/components/landing/dev-annotations"
import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  PricingSection,
  InvestorPositioning,
  FinalCTA,
} from "@/components/landing/sections"

export default function Home() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      {/* WebGL canvas — fixed behind content */}
      <LandingScene pages={7} />

      {/* HTML overlay — scrollable content */}
      <div className="relative z-10">
        <NavMinimal />
        <HeroSection />
        <EngineDiagram />
        <FrictionSection />
        <EngineProof />
        <CapabilitiesSection />
        <PricingSection />
        <InvestorPositioning />
        <FinalCTA />
        <DevAnnotations />
      </div>
    </main>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose 2>&1 | head -40`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/__tests__/page-assembly.test.tsx
git commit -m "feat: reorder homepage sections — engine pipeline first, add pricing"
```

---

### Task 4: Refresh Final CTA Copy

**Files:**
- Modify: `web/src/components/landing/sections/final-cta.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (FinalCTA tests)

**Context:** Align the closing CTA with the new hero language. Current: "Start with structure." / "Run any equity through the engine." / "Explore the Engine". New: "Score your first position." / "See every stock through the lens of conviction." / "Start free".

**Step 1: Update FinalCTA test assertions**

In `web/src/components/landing/__tests__/sections.test.tsx`, replace the `FinalCTA` describe block:

```tsx
describe("FinalCTA", () => {
  it("renders the CTA heading and button", () => {
    render(<FinalCTA />)
    expect(screen.getByText("Score your first position.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /start free/i })).toBeInTheDocument()
  })

  it("renders the updated CTA subtext", () => {
    render(<FinalCTA />)
    expect(
      screen.getByText("See every stock through the lens of conviction.")
    ).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<FinalCTA />)
    expect(screen.getByRole("link", { name: /methodology/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | grep -E "FAIL|PASS|FinalCTA"`
Expected: FinalCTA tests FAIL

**Step 3: Update final-cta.tsx copy**

In `web/src/components/landing/sections/final-cta.tsx`:

- H2 text (line 30): Change `Start with structure.` to `Score your first position.`
- P text (line 33): Change `Run any equity through the engine.` to `See every stock through the lens of conviction.`
- ButtonPrimary text (line 35): Change `Explore the Engine` to `Start free`

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/sections.test.tsx --reporter=verbose 2>&1 | grep -E "FAIL|PASS|FinalCTA"`
Expected: All FinalCTA tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/final-cta.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat: refresh final CTA copy — align with conviction positioning"
```

---

### Task 5: Full Test Suite + Visual QA

**Files:**
- All modified files from Tasks 1-4

**Context:** Run the complete web test suite to catch any regressions from copy changes across components. Then visual QA in the browser.

**Step 1: Run the full web test suite**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All tests PASS (238+ tests)

**Step 2: Fix any failures**

If any tests fail due to stale copy references (e.g., other test files still referencing "Structure outperforms emotion" or "Explore the Engine"), update those assertions to match the new copy.

Known locations to check:
- `web/src/components/landing/__tests__/page-assembly.test.tsx` — references hero headline and CTA text
- `web/src/components/landing/__tests__/sections.test.tsx` — already updated in Tasks 1, 2, 4
- Any snapshot tests (none expected, but check)

**Step 3: Visual QA in browser**

Start dev server: `cd /Users/brandon/repos/margin_invest/web && npm run dev`

Check at http://localhost:3000 (or next available port):
1. Hero: New headline "Conviction scoring for serious investors." renders correctly
2. Engine Diagram appears immediately below hero (before friction section)
3. Friction section still shows constellation narrative animation
4. Engine Proof section unchanged
5. Capabilities section unchanged
6. **Pricing section** renders with 3 tier cards (Scout/Operator/Allocator)
7. Investor Positioning unchanged
8. Final CTA shows new copy
9. Dark mode: All sections render correctly
10. Mobile (390px): Pricing cards stack vertically

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test regressions from homepage copy refresh"
```

(Only run this step if Step 2 found issues to fix.)
