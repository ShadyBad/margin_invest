# Chapter Dots Navigation Design

Date: 2026-02-17
Approach: Self-contained ChapterIndicator with IntersectionObserver

## Problem

The landing page has three full-screen sections (Signal, Engine, Path) with a fixed right-side dot indicator that is currently static — hardcoded to chapter 0 with no scroll detection or click navigation.

## Design

Make `ChapterIndicator` a self-contained smart component that detects the active section via IntersectionObserver and scrolls to sections on click.

### Section IDs

- `ChapterHero`: add `id="signal"`
- `ChapterCards`: already has `id="engine"`
- `ChapterPath`: add `id="path"`

### ChapterIndicator internals

1. Hardcodes `SECTIONS = [{ id: "signal", label: "The Signal" }, { id: "engine", label: "The Engine" }, { id: "path", label: "The Path" }]`
2. `activeIndex` state (default 0)
3. IntersectionObserver with `threshold: 0.4` — when a section crosses 40% visibility, it becomes active
4. Click handler: `document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })`
5. Observer cleanup on unmount
6. Props removed — component is fully self-contained

### page.tsx

Remove static props: `<ChapterIndicator chapters={3} activeChapter={0} labels={[...]} />` becomes `<ChapterIndicator />`.

### Visual (unchanged)

- Fixed right-6, vertically centered, z-50
- Hidden below lg breakpoint
- Active dot: accent color, scale-125
- Inactive dots: tertiary color, opacity-40, hover opacity-70
- 300ms transition

### Files modified

1. `web/src/components/landing/chapter-indicator.tsx` — self-contained with IntersectionObserver
2. `web/src/components/landing/chapter-hero.tsx` — add `id="signal"`
3. `web/src/components/landing/chapter-path.tsx` — add `id="path"`
4. `web/src/app/page.tsx` — remove static props
5. `web/src/components/landing/__tests__/chapter-indicator.test.tsx` — update tests
