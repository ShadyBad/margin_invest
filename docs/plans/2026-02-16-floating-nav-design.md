# Floating Nav Design

**Date:** 2026-02-16
**Status:** Approved

## Problem

Two separate nav components exist (`NavMinimal` for marketing pages, `Nav` for the app shell) with inconsistent visual treatment. Neither matches the premium fintech aesthetic the product requires. The current navs are full-width, flat, and generic.

## Solution

A single `FloatingNav` component that replaces both navs. It renders as a dark charcoal pill floating below the top edge of the viewport — minimal, high-contrast, premium.

### Component API

```tsx
<FloatingNav variant="public" />   // Landing, methodology pages
<FloatingNav variant="app" />      // Dashboard, backtesting, settings
```

**File:** `web/src/components/nav/floating-nav.tsx`

### Layout

Desktop: `[ Icon ]  [ Center Links ]  [ CTA or Avatar ]`

- **Outer wrapper:** `fixed`, centered horizontally, `top-4`
- **Pill container:** dark charcoal bg, `rounded-2xl` (16px), subtle shadow, max-width ~900px
- **Logo:** Geometric "M" icon mark (SVG, stroke-based, ~20x20px). No text. Links to `/`.
- **Center links:** Context-dependent
  - Public: Methodology, Guides, Support
  - App: Dashboard, Backtesting, Settings
- **Right side:**
  - Public: pill CTA button ("Dashboard"), `rounded-full`, slightly lighter bg than pill
  - App: Avatar + sign out (reuses existing Avatar component)

Mobile (< md): Logo left, hamburger right. Dropdown panel below pill with stacked links.

### Styling

**Pill container:**
- Dark mode: `bg-[#111113]`, Light mode: `bg-[#FAFAF9]`
- Border: `border-border-subtle` (1px, barely visible)
- Shadow: `0 2px 16px rgba(0,0,0,0.08)` light / `0 2px 16px rgba(0,0,0,0.3)` dark
- Padding: `px-6 py-3`

**CTA button:**
- `bg-bg-elevated`, `text-text-primary`, `text-[13px]`, `font-semibold`
- `rounded-full`, `px-5 py-2`
- Hover: `bg-bg-subtle`

**Links:**
- Inter Tight, `text-[14px]`, `font-medium`, `tracking-[-0.01em]`
- `text-text-secondary` → `hover:text-text-primary`
- Active: `text-text-primary` (via `usePathname()`)
- Transition: `transition-colors duration-200 ease-out`

**Logo icon:**
- Geometric "M" — two peaks, stroke-based SVG
- `currentColor` inheriting `text-text-primary`
- `opacity-80` → `hover:opacity-100`

### Interactions

- All hover transitions: 200ms ease-out, color/opacity only
- Focus: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent`
- Mobile: hamburger toggles dropdown panel, link click closes menu
- No framer-motion — pure CSS transitions

### Scroll Behavior

None. Nav is `fixed` and always visible with opaque background. No scroll-based opacity or blur transitions.

### Migration

**Replace:**
- `NavMinimal` in `page.tsx` and `methodology/page.tsx` → `<FloatingNav variant="public" />`
- `Nav` in `AppShell` → `<FloatingNav variant="app" />`

**Delete:**
- `web/src/components/landing/nav-minimal.tsx`
- `web/src/components/landing/__tests__/nav-minimal.test.tsx`
- `web/src/components/layout/nav.tsx`
- `web/src/components/layout/__tests__/nav.test.tsx`

**Theme toggle:** Removed from nav. Lives in Settings page.

### Constraints

- No glassmorphism, gradients, or glow effects
- No framer-motion — CSS transitions only
- No new dependencies
- No changes to globals.css or design tokens
- No dropdown menus or nested navigation
- No theme toggle in the nav
