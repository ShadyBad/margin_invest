# Cards Scroll Parallax Design

Date: 2026-02-17
Approach: Remove sticky scroll trap, keep parallax card drift

## Problem

The landing page card section uses `h-[200vh]` with a `sticky top-0 h-screen` inner container. This locks the viewport while cards slide left/right — the page appears to stop scrolling. Users expect continuous vertical scroll.

## Design

Remove the sticky mechanism entirely. Cards become part of normal document flow and drift horizontally as a parallax effect driven by scroll position.

### Changes to `chapter-cards.tsx`

1. **Section height:** Remove `h-[200vh]`, use natural content height with vertical padding (`py-24` or similar)
2. **Remove sticky wrapper:** Replace `<div className="sticky top-0 h-screen flex flex-col items-center justify-center gap-8">` with a simple flex container (no sticky, no h-screen)
3. **`useScroll` offset:** Keep `["start end", "end start"]` — tracks section through viewport for 0→1 progress range
4. **CardRow x transform:** Widen to `["30%", "-30%"]` / `["-30%", "30%"]` to compensate for shorter scroll distance
5. **Mobile container:** Remove `overflow-y-auto max-h-screen` (no longer viewport-locked)
6. **Spotlight opacity:** Unchanged — still driven by scrollYProgress

### Result

- Page scrolls continuously, no pause or lock
- Cards drift L/R synchronized with vertical scroll
- Spotlight opacity still highlights focal cards
- Responsive: desktop two rows, mobile single column

### Files modified

- `web/src/components/landing/chapter-cards.tsx` (only file)
