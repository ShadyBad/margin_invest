# Counter-Flow Cards Landing Page Redesign

**Date:** 2026-02-17
**Status:** Approved

## Problem

The current landing page has too much vertical space. Three 50vh spacers and two full-screen horizontal scroll sections create ~5.5 screens of content. Users scroll through dead space before reaching the value proposition. The horizontal scroll pattern also breaks the natural vertical scroll expectation.

## Solution

Replace the Engine and Proof horizontal scroll chapters with a single counter-flow card section. Two rows of cards move in opposite horizontal directions as the user scrolls vertically — top row left, bottom row right. Cards fade and blur based on proximity to the viewport center, creating a depth-of-field spotlight effect.

The opposing motion is a metaphor for market dynamics: capital flows in different directions, risk and opportunity coexist, buyers and sellers act in parallel. The movement is subtle and controlled — analytical, not decorative.

## Page Structure

```
Hero (100vh) → Counter-Flow Cards (~200vh scroll height) → Pricing/CTA (min-h-screen)
```

**Before:** ~5.5 screens. **After:** ~4 screens. Approximately 250vh of vertical space removed.

| Location | Before | After |
|----------|--------|-------|
| Hero → Content | 50vh spacer | 0 (direct transition) |
| Engine → Proof | 50vh spacer + two 100vh sections | Merged into single card section |
| Content → Pricing | 50vh spacer | py-16 (64px) |

## Card Layout

### Desktop (≥768px)

Two horizontal rows, vertically stacked within the section. Each row contains 5 cards at ~320px fixed width. Cards extend beyond viewport edges; `overflow: hidden` on the section clips them.

At any scroll position, ~3-4 cards are visible per row. The card closest to viewport center is the spotlight — fully opaque and sharp. Cards further from center progressively fade and blur.

**Top row ("The Engine") — moves left on scroll:**
1. Raw Signal — market data firehose
2. Elimination Filters — fail-fast filtering
3. Factor Analysis — multi-factor scoring
4. Sector Normalization — cross-sector comparison
5. Conviction Output — final composite score

**Bottom row ("The Proof") — moves right on scroll:**
1. Sample AAPL Score — real scoring output
2. Factor Breakdown — percentile visualization
3. Growth vs Value — stage-aware weighting
4. Portfolio View — multi-stock comparison
5. Historical Accuracy — backtest results

Cards use the existing `GlassSurface` component.

### Mobile (<768px)

Single column. Cards from both rows interleaved (engine, proof, engine, proof...). No horizontal translation. Centered at full width minus padding (`px-6`, max ~360px). Tight vertical spacing (`gap-4`). The scroll-fade depth-of-field effect is preserved in the vertical dimension.

## Animation Mechanics

**Library:** Framer Motion (`useScroll`, `useTransform`). Already used throughout the project.

### Horizontal Translation (scroll-linked)

`useScroll` targets the card section container with `offset: ["start end", "end start"]`, producing `scrollYProgress` from 0 to 1.

`useTransform` maps this to `translateX`:
- Top row: `[0, 1]` → `["20%", "-20%"]`
- Bottom row: `[0, 1]` → `["-20%", "20%"]`

Rows are always in motion relative to scroll — no dead zones, no snapping. Linear mapping; the scroll itself provides natural easing.

### Per-Card Depth-of-Field (opacity + blur)

Each card tracks its own viewport position via `useScroll({ target: cardRef, offset: ["start end", "end start"] })`.

**Opacity curve** (5-point):
- Progress `[0, 0.3, 0.5, 0.7, 1]` → Opacity `[0.15, 0.6, 1, 0.6, 0.15]`

**Blur curve** (5-point):
- Progress `[0, 0.3, 0.5, 0.7, 1]` → Blur `[4px, 1.5px, 0px, 1.5px, 4px]`

Applied via `filter: blur()` and `opacity` on `motion.div` wrappers. Framer Motion GPU-promotes these properties.

### Reduced Motion

When `prefers-reduced-motion` is enabled:
- Disable horizontal translation
- Disable blur
- Keep opacity fade (center bright, edges dim) to preserve content hierarchy

## Component Changes

**Removed:**
- `ChapterEngine` — replaced by card section top row
- `ChapterProof` — replaced by card section bottom row
- `HorizontalScroll` — no longer needed

**Added:**
- `ChapterCards` — new counter-flow card section component

**Modified:**
- `page.tsx` — new 3-section layout, remove 50vh spacers
- `ChapterIndicator` — 3 dots instead of 4 (Hero, Cards, Pricing)

**Unchanged:**
- `ChapterHero` — full-screen hero stays as-is
- `ChapterPath` — pricing/CTA stays as-is
- `FluidShader` / `FluidShaderLoader` — WebGL background continues behind cards
- `DNAProvider` — personalization unchanged
- `GlassSurface` — reused by new cards

## Transitions

- **Hero → Cards:** No spacer. Cards begin fading in immediately as user scrolls past hero.
- **Cards → Pricing:** Small gap (`py-16` / 64px). Last cards fade out naturally.
- Fluid shader background provides visual continuity across all sections.
