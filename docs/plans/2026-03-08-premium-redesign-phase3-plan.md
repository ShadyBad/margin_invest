# Phase 3: Craft Layer

Implementation plan for Phase 3 of the premium redesign.

**Goal:** Build the accumulation of details that moves the product premium perception up.

**Architecture:** Three workstreams in sequence: (A) Design system cleanup first, (B) Dashboard rebuild, (C) Interaction polish. Workstream A before C to avoid rework.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Vitest, Framer Motion, GSAP

**Ordering:** Tasks 1-3 (design system) then Tasks 4-7 (dashboard) then Tasks 8-11 (interaction/polish).

---

### Task 1: Dark Mode Only — Remove Theme Toggle, Force Dark

**Context:** Design doc 3.5 recommends dark-only. Simplifies CSS management for all subsequent tasks.

**Files:**
- Modify: `web/src/app/layout.tsx` (ThemeProvider — line 80)
- Modify: `web/src/components/nav/navbar.tsx` (ThemeToggle — line 35)
- Modify: `web/src/components/nav/mobile-menu.tsx` (ThemeToggle usage)
- Delete: `web/src/components/nav/theme-toggle.tsx`
- Delete: `web/src/components/nav/__tests__/theme-toggle.test.tsx`
- Modify: `web/src/app/globals.css`
- Modify: `web/src/components/providers/theme-provider.tsx`
- Modify: `web/src/components/nav/__tests__/navbar.test.tsx`
- Modify: `web/src/components/nav/__tests__/mobile-menu.test.tsx`

**Steps:**

1. In layout.tsx, set ThemeProvider to forced dark theme (remove enableSystem, defaultTheme).
2. Remove ThemeToggle import and JSX from navbar.tsx and mobile-menu.tsx.
3. Delete theme-toggle.tsx and its test file.
4. In globals.css: delete `:root` block (lines 424-457, shadcn light-mode vars). Delete shadcn vars from `.dark` block (lines 171-232), keeping only custom design system vars (lines 117-170). Deduplicate `@layer base` rules. Strip shadcn mappings from `@theme inline`, keeping only font vars.
5. Merge dark-mode color values from `.dark {}` into `@theme {}` as new defaults. Delete `.dark {}` block.
6. Simplify ThemeProvider wrapper.
7. Update navbar and mobile-menu tests — remove ThemeToggle assertions/mocks.
8. Run: `cd web && npx vitest run && npx eslint --fix .`
9. Commit: `refactor(web): remove theme toggle, force dark mode only`

---

### Task 2: Opacity Levels + Accent/Bullish Separation + Duration Cleanup

**Context:** Design doc 3.2 requires three accent opacity levels. Currently accent and bullish share the same color value in dark mode. Duration values exceed 350ms ceiling.

**Files:**
- Modify: `web/src/app/globals.css` (new CSS custom properties in @theme)

**Steps:**

1. Add to @theme: `--color-accent-wash` (accent color at 3% opacity), `--color-accent-medium` (accent at 15%). Update existing `--color-accent-subtle` from 10% to 8%.
2. Change `--color-bullish` to a distinct brighter green — currently same hex as accent. Use a green that is visually distinct from the muted emerald accent.
3. Add duration vars: `--duration-fast: 100ms`, `--duration-normal: 200ms`, `--duration-slow: 300ms`. Remove `--duration-reveal` (600ms) and `--duration-transition` (1000ms). Keep `--duration-ambient` for non-interactive animations.
4. Run: `cd web && npx vitest run`
5. Commit: `refactor(web): add opacity levels, separate accent from bullish, clean duration values`

---

### Task 3: Font Size Enforcement — Kill text-[10px] and text-[11px]

**Context:** Design doc 3.2 specifies minimum 12px. 57 files use sub-12px classes.

**Files:** All 57 files returned by grep for `text-[10px]` and `text-[11px]` in `web/src/`.

**Steps:**

1. Batch replace `text-[10px]` with `text-xs` across all 57 files.
2. Batch replace `text-[11px]` with `text-xs` across all files.
3. Verify: `grep -r "text-\[10px\]\|text-\[11px\]" src/` returns nothing.
4. Run: `cd web && npx vitest run && npx eslint --fix .`
5. Commit: `refactor(web): enforce 12px minimum font size across 57 components`

---

### Task 4: Dashboard Greeting + Score Change Summary

**Context:** Design doc 3.1 item 1: "Good morning, Brandon. 2 scores changed since yesterday."

**Files:**
- Create: `web/src/components/dashboard/dashboard-greeting.tsx`
- Create: `web/src/components/dashboard/__tests__/dashboard-greeting.test.tsx`
- Modify: `web/src/app/dashboard/page.tsx` (replace header section)

**Steps:**

1. Write test: renders greeting with name, shows change count when positive, shows "no changes" when 0, shows last updated timestamp.
2. Run test — should fail (module not found).
3. Implement DashboardGreeting: time-based greeting (morning/afternoon/evening), optional name, change count message, last updated line.
4. Run test — should pass.
5. Integrate into dashboard/page.tsx: replace header block with DashboardGreeting, pass session user first name, pass changesCount=0 (API deferred), remove formatLastUpdated helper and MarketRegimeLabel from header.
6. Export from dashboard barrel.
7. Run: `cd web && npx vitest run`
8. Commit: `feat(web): add personalized dashboard greeting with change summary`

---

### Task 5: Score Change Deltas on Pick Cards

**Context:** Design doc 3.1 item 2: Show delta arrow and value next to score.

**Files:**
- Create: `web/src/components/ui/score-delta.tsx`
- Create: `web/src/components/ui/__tests__/score-delta.test.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/lib/api/types.ts`

**Steps:**

1. Write test: positive delta shows up arrow + bullish color, negative shows down arrow + warning color, zero returns null, null previous returns null.
2. Run test — should fail.
3. Implement ScoreDelta: compute delta, return null if zero or no previous, use bullish/warning colors.
4. Run test — should pass.
5. Add `previous_score?: number | null` to PickSummary interface in types.ts.
6. In stock-card.tsx: wrap AnimatedScore with ScoreDelta in a flex container.
7. Export from ui/index.ts.
8. Run: `cd web && npx vitest run`
9. Commit: `feat(web): add score change deltas to pick cards`

---

### Task 6: Market Context Sidebar

**Context:** Design doc 3.1 item 3: Compact left sidebar with universe stats.

**Files:**
- Create: `web/src/components/dashboard/market-context-sidebar.tsx`
- Create: `web/src/components/dashboard/__tests__/market-context-sidebar.test.tsx`
- Modify: `web/src/app/dashboard/page.tsx`

**Steps:**

1. Write test: renders universe size, scored count, picks count; handles null gracefully.
2. Run test — should fail.
3. Implement MarketContextSidebar: sticky aside with stat rows (Universe, Scored, Surviving, Engine, Last run). Hidden below lg breakpoint.
4. Run test — should pass.
5. Integrate into dashboard page: wrap main content in flex layout with sidebar on left. Remove IngestionBanner from main (data consolidated in sidebar).
6. Export from dashboard barrel.
7. Run: `cd web && npx vitest run`
8. Commit: `feat(web): add market context sidebar to dashboard`

---

### Task 7: Recent Changes Feed

**Context:** Design doc 3.1 item 4: Chronological list of score changes.

**Files:**
- Create: `web/src/components/dashboard/recent-changes.tsx`
- Create: `web/src/components/dashboard/__tests__/recent-changes.test.tsx`
- Modify: `web/src/app/dashboard/page.tsx`

**Steps:**

1. Write test: renders each change entry with ticker and transition, renders empty state.
2. Run test — should fail.
3. Implement RecentChanges: export ScoreChange interface, divider-separated rows with ticker, score transition, delta, date. Empty state message.
4. Run test — should pass.
5. Add "Recent Changes" section after Top Picks with empty changes array (API deferred).
6. Export from dashboard barrel.
7. Run: `cd web && npx vitest run`
8. Commit: `feat(web): add recent changes feed to dashboard`

---

### Task 8: Hover State Polish

**Context:** Design doc 3.3 hover table. Consistent hover feedback everywhere.

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/dashboard/watchlist-picks-list.tsx`
- Modify: `web/src/components/landing/pricing-tier-card.tsx`
- Modify: `web/src/components/nav/nav-links.tsx`
- Modify: `web/src/components/landing/footer-section.tsx`

**Steps:**

1. StockCard: replace hover:scale with hover:border-accent-medium + hover:shadow-card-hover. Remove scale — shadow elevation only. 150ms transition.
2. WatchlistRow: add hover:bg accent-wash with 100ms transition.
3. PricingTierCard: add hover:translate-y-0.5 + hover:border-accent-medium with 200ms transition.
4. NavLinks: ensure hover:text-text-primary with 100ms transition.
5. Footer links: same hover pattern as nav links.
6. Run: `cd web && npx vitest run`
7. Commit: `refactor(web): unify hover states across all interactive elements`

---

### Task 9: Dashboard Skeleton Loading

**Context:** Design doc 3.3: Pulsing placeholders matching exact dimensions. No spinner.

**Files:**
- Modify: `web/src/components/ui/skeleton-card.tsx`
- Modify: `web/src/app/dashboard/loading.tsx`

**Steps:**

1. Rewrite SkeletonCard to match StockCard structure: header (ticker + badge), name, score + action pill, price row, three percentile bars.
2. Update dashboard loading.tsx: add SkeletonSidebar, greeting skeleton area, SkeletonWatchlistRow. Mirror actual dashboard layout.
3. Run: `cd web && npx vitest run`
4. Commit: `refactor(web): improve dashboard skeleton loading to match actual layout`

---

### Task 10: Keyboard Navigation

**Context:** Design doc 3.3: Cmd+K for ticker search, Esc to close overlays.

**Files:**
- Create: `web/src/hooks/use-keyboard-nav.ts`
- Create: `web/src/hooks/__tests__/use-keyboard-nav.test.ts`
- Modify: `web/src/components/nav/ticker-search.tsx`

**Steps:**

1. Write test: Cmd+K fires onCmdK callback, Escape fires onEscape callback.
2. Implement useKeyboardNav hook: listen for keydown on document, handle Cmd/Ctrl+K and Escape. Cleanup on unmount.
3. Wire into TickerSearch: focus/open search on Cmd+K. Add keyboard hint badge.
4. Run: `cd web && npx vitest run`
5. Commit: `feat(web): add Cmd+K keyboard shortcut for global ticker search`

---

### Task 11: Asset Detail Polish

**Context:** Design doc 3.4: Number rounding, filter tables, solid borders.

**Files:**
- Modify: `web/src/components/asset-detail/filter-card.tsx`
- Modify: `web/src/components/asset-detail/pillar-card.tsx`
- Modify: `web/src/components/asset-detail/conviction-engine.tsx`

**Steps:**

1. In filter-card.tsx: replace raw diagnostic strings with structured table (Check, Value, Threshold, Result). Use computed_metrics data.
2. In pillar-card.tsx and conviction-engine.tsx: replace gradient glow borders with solid border + shadow-card.
3. Audit .toFixed() calls exceeding 2 decimal places. Add formatting where raw numbers render unformatted.
4. Run: `cd web && npx vitest run`
5. Commit: `refactor(web): polish asset detail — structured filter table, solid borders, number rounding`

---

## Task Summary

| Task | Section | Description | Depends on |
|------|---------|-------------|------------|
| 1 | 3.5 | Dark mode only — remove theme toggle | - |
| 2 | 3.2 | Opacity levels + accent/bullish separation | Task 1 |
| 3 | 3.2 | Font size enforcement (57 files) | - |
| 4 | 3.1 | Dashboard greeting + change summary | - |
| 5 | 3.1 | Score change deltas on pick cards | - |
| 6 | 3.1 | Market context sidebar | - |
| 7 | 3.1 | Recent changes feed | - |
| 8 | 3.3 | Hover state polish | Tasks 1-2 |
| 9 | 3.3 | Dashboard skeleton loading | Tasks 4, 6 |
| 10 | 3.3 | Keyboard navigation | - |
| 11 | 3.4 | Asset detail polish | Tasks 1-2 |

**Parallel-safe groups:**
- Tasks 1+3+4+5 can run in parallel (different file sets)
- Tasks 6+7+10 can run in parallel after Task 4
- Tasks 8+9+11 should run last (depend on design system cleanup)
