# Phase 3 Craft Layer — Revised Design

**Date:** 2026-03-09
**Status:** Approved
**Basis:** Visual audit of localhost build + code review. Original Phase 3 plan (2026-03-08) was 11 tasks; 8 are already complete. This document covers the 3 remaining original tasks plus 3 new tasks surfaced by the visual audit.

## What's Already Done (Phase 3 Original)

| Task | Status |
|------|--------|
| 1. Dark mode only — remove theme toggle | Done (forcedTheme="dark", ThemeToggle deleted) |
| 2. Opacity levels + accent/bullish separation | Done (tokens in globals.css) |
| 3. Font size enforcement (text-[10px]/[11px]) | Done (0 matches in codebase) |
| 4. Dashboard greeting + change summary | Done (DashboardGreeting component) |
| 5. Score change deltas on pick cards | Done (ScoreDelta component) |
| 6. Market context sidebar | Done (MarketContextSidebar component) |
| 7. Recent changes feed | Done (RecentChanges component) |
| 10. Keyboard navigation (Cmd+K) | Done (useKeyboardNav hook) |

## What Remains

### A. Original Phase 3 Tasks (Incomplete)

**Task 8: Hover State Polish** — Partially done. Stock cards and watchlist rows have correct hover states. Pricing cards have hover via Framer Motion. Nav links have hover. Footer links have hover. But the implementations are inconsistent: some use CSS transitions, some use Framer Motion `whileHover`, some use JS `onMouseEnter`. Needs unification to CSS-only where possible.

**Task 9: Dashboard Skeleton Loading** — Not started. No `loading.tsx` or `SkeletonCard` exists for the dashboard. The dashboard currently shows empty content while data loads.

**Task 11: Asset Detail Polish** — Partially done (some formatting fixes in earlier commits). Remaining: filter diagnostic tables, gradient glow border removal, number rounding audit.

### B. New Tasks From Visual Audit

**Task 12: Kill Pricing Scroll-Pinning** — The single biggest design weakness. The pinned ScrollTrigger timeline creates multiple seconds of empty dark viewport between the pricing headline and card reveal. Replace with immediate visibility + simple viewport-enter fade stagger (matching the FAQ section's approach). Keep the headline. Show the cards on arrival.

**Task 13: Elevate Authority Strip** — Currently renders as naked monospace text floating between hero and evidence section. Needs a contained surface treatment (bg-elevated, border-subtle) to match the evidence panel's visual weight. Should read as a plaque, not a caption.

**Task 14: Unify Border Radius** — Three competing radii: `rounded-2xl` (pricing cards), `rounded-xl` (evidence panel), `rounded-lg` (stock cards, CTAs). Pick one system radius for all card surfaces. Recommendation: `rounded-xl` (16px) everywhere — `rounded-lg` is too tight for large cards, `rounded-2xl` is too round for financial software.

### C. Shadcn Cleanup (Deferred from Task 1)

The `:root` block (lines 305-338 in globals.css) still contains 30+ shadcn oklch variables. The `@theme inline` section maps these to Tailwind. These create a second design system fighting the custom tokens. However, removing them risks breaking any shadcn component still in use. This requires a component audit and is deferred to a separate task.

## Design Decisions

### Pricing Section (Task 12)
- Remove: `ScrollTrigger.create` with `pin: true` and `scrub: 0.5`
- Remove: GSAP timeline with card slide-in animations (x: 80, y: 40, x: -80)
- Remove: Sequential feature checkmark reveals
- Keep: Headline, subtitle, card grid, bottom text, contact CTA
- Replace with: Cards visible on load. Simple viewport-enter fade-in with 120ms stagger (same pattern as FAQ section). No pinning. No scrub.
- Mobile path: unchanged (already uses simple fade-in)

### Authority Strip (Task 13)
- Wrap existing 3-column grid in a contained surface: `bg-bg-elevated border border-border-subtle rounded-xl`
- Add subtle padding increase (current py-6 → py-8)
- Add terminal-style header matching evidence section: `SYSTEM PROFILE` in monospace
- Keep all existing content unchanged

### Border Radius (Task 14)
- Global: all card surfaces → `rounded-xl`
- Affected: `pricing-tier-card.tsx` (rounded-2xl → rounded-xl), `stock-card.tsx` via `getCardTierClasses` (rounded-lg → rounded-xl), `terminal-card` class in globals.css (12px → 16px)
- Evidence panel already uses `rounded-xl` — becomes the standard
- CTA buttons keep `rounded-lg` (smaller interactive elements use smaller radius)

### Hover Unification (Task 8)
- All hover states use CSS transitions only — remove Framer Motion `whileHover`/`whileTap`/`whileFocus` from pricing-tier-card.tsx
- All hover states use `transition-all duration-200` with `ease-out-expo` from tokens
- Stock cards: keep existing (already correct — border + shadow)
- Pricing cards: convert to CSS `hover:-translate-y-0.5 hover:border-accent-medium hover:shadow-card-hover`
- Remove JS `onMouseEnter`/`onMouseLeave` from pricing CTA buttons → use CSS `hover:bg-accent-hover`

### Skeleton Loading (Task 9)
- Create `web/src/app/dashboard/loading.tsx` with skeleton matching actual dashboard layout
- Components: skeleton greeting bar, skeleton sidebar, skeleton pick cards (3), skeleton changes section
- Use `animate-pulse` on `bg-bg-subtle` blocks — standard Next.js loading pattern
- No spinner anywhere

### Asset Detail Polish (Task 11)
- Filter diagnostics: structured table (Check | Value | Threshold | Result)
- Replace gradient glow borders with solid `border border-border-primary shadow-card`
- Audit `.toFixed()` calls — cap at 2 decimal places

## Task Order

| Priority | Task | Effort | Dependencies |
|----------|------|--------|--------------|
| 1 | 12. Kill pricing scroll-pinning | Small | None |
| 2 | 14. Unify border radius | Small | None |
| 3 | 13. Elevate authority strip | Small | None |
| 4 | 8. Hover state unification | Medium | Task 14 (radius) |
| 5 | 9. Dashboard skeleton loading | Medium | None |
| 6 | 11. Asset detail polish | Medium | None |

Tasks 12, 14, 13 can run in parallel (different files). Tasks 8, 9, 11 can run in parallel after.

## Success Criteria

- Pricing section loads cards visible (no empty viewport)
- Authority strip has contained surface treatment
- Single border-radius across all card surfaces
- All hover states use CSS transitions (zero Framer Motion hover)
- Dashboard shows skeleton loading, no blank page
- Filter diagnostics render as structured table
- All percentiles rounded to ≤2 decimal places
- `cd web && npx vitest run` passes
- `cd web && npx eslint --fix .` clean
