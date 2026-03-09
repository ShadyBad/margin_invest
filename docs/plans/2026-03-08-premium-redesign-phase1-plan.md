# Premium Redesign Phase 1 — Kill Trust Destroyers

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan one step at a time.

**Goal:** Remove every signal that makes a sophisticated user close the tab — data inconsistencies, unformatted numbers, consumer-tier patterns, insecure copy.

**Architecture:** Seven independent UI changes, each a discrete commit. No API changes needed. All changes are in `web/src/components/landing/` and `web/src/components/asset-detail/`. Existing tests must continue to pass after each change.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Vitest, GSAP (animations)

**Design doc:** `docs/plans/2026-03-08-premium-redesign-design.md` — Phase 1 (sections 1.1-1.6)

---

### Task 1: Remove LIVE Badge from Hero

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx`

**Step 1: Check for tests asserting the LIVE badge**

Run: `cd web && grep -r "Live" src/components/landing/__tests__/ -l 2>/dev/null`

If any tests assert on the "Live" text or pulsing dot, update them to remove those assertions.

**Step 2: Remove the LIVE badge eyebrow block**

In `hero-section.tsx`, delete the entire `{/* Eyebrow tag */}` block (lines 101-116). This is the div containing the pulsing green dot spans and the "Live" text span. Delete from the opening div through its closing tag.

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All existing tests pass.

**Step 4: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 5: Commit**

Message: "fix(web): remove LIVE badge from hero section"

---

### Task 2: Remove Comparison Table from Homepage

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`

**Step 1: Remove DifferentiatorSection from homepage**

In `homepage-client.tsx`:

1. Delete the import on line 10: the DifferentiatorSection import
2. Delete the usage on line 57: the DifferentiatorSection JSX element

Keep the `differentiator-section.tsx` file on disk.

**Step 2: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`

**Step 3: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`

**Step 4: Commit**

Message: "fix(web): remove competitor comparison table from homepage"

---

### Task 3: Update Hero Subtext Copy

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx`

**Step 1: Check for tests asserting the old copy**

Run: `cd web && grep -r "deterministic capital allocation" src/ -l`

Update any matching test files.

**Step 2: Replace the hero subtext**

In `hero-section.tsx`, find the paragraph with `data-hero-subtext` attribute (lines 123-126). Replace its inner text:

- Old: "A deterministic capital allocation system that replaces narrative with structure. Search any ticker — the system shows you the quantitative evidence."
- New: "A deterministic scoring engine for 3,056 US equities. No opinions. No overrides. Search one."

**Step 3: Run tests and commit**

Message: "fix(web): update hero subtext to product-focused copy"

---

### Task 4: Update Pricing Section Copy and CTAs

**Files:**
- Modify: `web/src/components/landing/pricing-section.tsx`
- Modify: `web/src/components/landing/pricing-tier-card.tsx`

**Step 1: Check for tests asserting pricing copy**

Run: `cd web && grep -r "Founding members\|Get Started\|not another guru" src/ -l`

Update any matching tests.

**Step 2: Update pricing-section.tsx**

2a. Replace the heading (line 57):
- Old: "Invest in your process, not another guru."
- New: "Start free. Full access from $19/month."

2b. Delete the "founding members" paragraph (lines 71-73):
- Delete the p tag containing "Founding members lock in this price forever. Pricing increases after launch."

2c. Update the scoring line (lines 74-76):
- Old text: "Scoring 3,000+ US equities daily for founding members"
- New text: "Scoring 3,056 US equities daily"
- Also change `text-[11px]` to `text-xs` (minimum 12px per design system)

**Step 3: Update pricing-tier-card.tsx CTAs**

In `pricing-tier-card.tsx`, add a CTA mapping after the Tier interface (after line 13):

```tsx
const CTA_TEXT: Record<string, string> = {
  Scout: "Search Any Ticker",
  Analyst: "Start Analyzing",
  Portfolio: "Start Building",
}
```

Replace both "Get Started" strings (lines 114 and 121) with:
`{CTA_TEXT[tier.name] ?? "Get Started"}`

**Step 4: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`

**Step 5: Commit**

Message: "fix(web): update pricing copy and tier-specific CTAs"

---

### Task 5: Remove Homepage Disclaimer

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx`

**Step 1: Check for tests asserting the disclaimer**

Run: `cd web && grep -r "Methodology in development" src/ -l`

Update any matching tests.

**Step 2: Remove the disclaimer paragraph**

In `proof-section.tsx`, delete lines 100-104 — the paragraph containing "Methodology in development" text.

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`

**Step 4: Commit**

Message: "fix(web): remove methodology disclaimer from homepage"

---

### Task 6: Add Scroll Affordance to Engine Pipeline

**Files:**
- Modify: `web/src/components/landing/engine-section.tsx`

**Step 1: Verify current state**

The engine section already has desktop gradient fade masks (lines 152-153) and mobile vertical stack (line 180). Only a text affordance is missing.

**Step 2: Add scroll hint text**

In `engine-section.tsx`, after line 177 (closing tag of the `hidden md:block` wrapper), add:

```tsx
<p className="hidden md:block text-center text-xs text-text-tertiary mt-4 font-mono opacity-60">
  Scroll to explore the engine pipeline
</p>
```

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`

**Step 4: Commit**

Message: "fix(web): add scroll hint for engine pipeline cards"

---

### Task 7: Format Percentiles to Integers

**Files:**
- Create: `web/src/lib/format-percentile.ts`
- Create: `web/src/lib/__tests__/format-percentile.test.ts`
- Modify: `web/src/components/asset-detail/eliminated-hero.tsx`

**Step 1: Write the failing test**

Create `web/src/lib/__tests__/format-percentile.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { formatPercentile } from "../format-percentile"

describe("formatPercentile", () => {
  it("rounds to nearest integer", () => {
    expect(formatPercentile(72)).toBe("72")
  })
  it("rounds float with many decimals", () => {
    expect(formatPercentile(99.574)).toBe("100")
  })
  it("handles zero", () => {
    expect(formatPercentile(0)).toBe("0")
  })
  it("clamps above 100", () => {
    expect(formatPercentile(105)).toBe("100")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/__tests__/format-percentile.test.ts --reporter=verbose`
Expected: FAIL — module not found

**Step 3: Write the implementation**

Create `web/src/lib/format-percentile.ts`:

```typescript
/** Format a percentile value for display. Always an integer, clamped 0-100. */
export function formatPercentile(value: number): string {
  return String(Math.round(Math.min(100, Math.max(0, value))))
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/__tests__/format-percentile.test.ts --reporter=verbose`
Expected: PASS

**Step 5: Fix eliminated-hero raw percentile**

In `eliminated-hero.tsx` line 107, wrap the raw float:

- Old: `{ordinalSuffix(hypotheticalPercentile)} percentile`
- New: `{ordinalSuffix(Math.round(hypotheticalPercentile))} percentile`

Other asset-detail components already use `Math.round()` — no changes needed.

**Step 6: Run full test suite**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 7: Commit**

Message: "fix(web): round percentile values to integers for display"

---

## Verification Checklist

After all 7 items are complete:

1. Full test suite: `cd web && npx vitest run`
2. Build: `cd web && npx next build`
3. Lint: `cd web && npx eslint --fix .`

Visual spot-check (run dev server):
- No LIVE badge in hero
- No comparison table on homepage
- Hero subtext updated to new copy
- Pricing heading and CTAs updated
- No "founding members" text on homepage
- No "Methodology in development" disclaimer on homepage
- Engine pipeline has scroll hint on desktop
- Percentiles display as integers on asset detail pages
