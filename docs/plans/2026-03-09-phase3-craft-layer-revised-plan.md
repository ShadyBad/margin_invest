# Phase 3 Craft Layer — Implementation Plan

**Goal:** Complete remaining craft layer work from the premium redesign.
**Architecture:** 5 tasks. Tasks 1-3 parallel, Task 4 after 3, Task 5 independent.
**Tech:** Next.js 16, React 19, Tailwind v4, GSAP removal, Framer Motion removal, Vitest
**Design doc:** `docs/plans/2026-03-09-phase3-craft-layer-revised-design.md`

---

### Task 1: Kill Pricing Scroll-Pinning

**Files:** `web/src/components/landing/pricing-section.tsx`

Delete the desktop GSAP pinning path (lines 131-237). Keep only the mobile/simple path (lines 90-129) which does viewport-enter fade-in with 120ms stagger. Remove `useScrollCanvas` import, `headlineRef`/`cardsContainerRef` refs, `isSmoothScrolling` branching. Change useEffect dep from `[isSmoothScrolling]` to `[]`. Remove `min-h-screen` from inner div.

Verify: `cd web && npx vitest run` passes. Commit.

---

### Task 2: Elevate Authority Strip

**Files:** `web/src/components/landing/authority-strip.tsx`

Wrap existing 3-column grid in a contained surface. Change outer section from `border-y border-border-subtle` to `px-6 py-8`. Add inner container with `bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8`. Add terminal header: monospace "SYSTEM PROFILE" label with status dot, matching evidence section pattern. Keep all existing content.

Verify: `cd web && npx vitest run` passes. Commit.

---

### Task 3: Unify Border Radius

**Files:** `web/src/app/globals.css`, `web/src/components/landing/pricing-tier-card.tsx`, `web/src/components/dashboard/stock-card.tsx`

Change `.terminal-card` and `.terminal-card-accent` border-radius from 12px to 16px in globals.css. Change `rounded-2xl` to `rounded-xl` in pricing-tier-card.tsx. Change all `rounded-lg` returns to `rounded-xl` in `getCardTierClasses` in stock-card.tsx. Update exceptional tier gradient overlay `rounded-lg` to `rounded-xl`.

Verify: `cd web && npx vitest run` passes. Commit.

---

### Task 4: Hover State Unification (depends on Task 3)

**Files:** `web/src/components/landing/pricing-tier-card.tsx`

Replace `motion.div` with plain `div`. Remove `whileHover`, `whileTap`, `whileFocus`, `transition` props. Remove `motion`/`useReducedMotion` imports and `spring` const. The existing CSS hover classes are sufficient. For highlighted card, add hover shadow class. Remove `onMouseEnter`/`onMouseLeave` JS handlers from highlighted CTA, replace with CSS `hover:bg-accent-hover`.

Verify: `cd web && npx vitest run` passes. `cd web && npx eslint --fix .` clean. Commit.

---

### Task 5: Dashboard Skeleton Loading

**Files:** Create `web/src/app/dashboard/loading.tsx`

Create Next.js loading file with skeleton blocks matching dashboard layout: greeting bar, conviction badge, sidebar (3 blocks), main content (heading + 3 pick cards grid + recent changes block). Use `animate-pulse` on `bg-bg-subtle rounded-xl` divs. Wrap in `AppShell`. No spinner.

Verify: `cd web && npx vitest run` passes. Commit.

---

## Task Order

| Priority | Task | Effort | Dependencies |
|----------|------|--------|--------------|
| 1 | Kill pricing scroll-pinning | Small | None |
| 2 | Elevate authority strip | Small | None |
| 3 | Unify border radius | Small | None |
| 4 | Hover state unification | Medium | Task 3 |
| 5 | Dashboard skeleton loading | Medium | None |

Tasks 1, 2, 3 can run in parallel. Task 4 after Task 3. Task 5 independent.

## Criteria

- Pricing section loads cards visible (no pinning)
- Authority strip has contained surface with terminal header
- Single border-radius (rounded-xl) across all card surfaces
- All pricing card hover states use CSS transitions (zero Framer Motion)
- Dashboard shows skeleton loading, no blank page
- `cd web && npx vitest run` passes
- `cd web && npx eslint --fix .` clean
