# Pricing Card Hover Interaction Design

**Date**: 2026-02-20
**Status**: Approved
**Scope**: Subtle hover/tap/focus interaction for Analyst, Portfolio, and Institutional pricing cards

## Objective

Add a subtle upward lift on hover to the three pricing tier cards (Analyst, Portfolio, Institutional) to indicate selectability. Must preserve the existing warm, minimalist theme.

## Approach

Framer Motion `whileHover` / `whileTap` with spring physics. Chosen over pure Tailwind for natural spring feel and built-in tap state. Matches the Framer Motion pattern already used by `GuideCard`.

## Motion Values

| State | translateY | shadow | scale | Spring |
|-------|-----------|--------|-------|--------|
| Rest | 0 | shadow-card | 1 | — |
| Hover | -4px | shadow-card-hover | 1 | stiffness: 400, damping: 25 |
| Tap | -1px | shadow-card | 0.995 | stiffness: 500, damping: 30 |

## Accessibility

- `focus-visible` mirrors hover state (translate + shadow) via Tailwind classes
- `prefers-reduced-motion`: disable spring animations, fall back to outline ring
- Cards contain a `Link` — semantically correct

## Performance

- `transform: translateY()` is GPU-composited — no layout thrashing
- Shadow via `box-shadow` triggers paint only (not layout) — acceptable for hover
- 4px translate within 24px grid gap — no neighbor displacement

## Files to Change

1. `web/src/components/landing/pricing-tier-card.tsx` — add `"use client"`, wrap in `motion.div`, add hover/tap/focus variants

## Acceptance Criteria

1. On hover/focus, card lifts ~4px with spring physics
2. On tap/click, card presses down slightly
3. Motion disabled when `prefers-reduced-motion` is active (outline fallback)
4. No layout shift or neighbor displacement
5. All three cards behave identically (including highlighted Portfolio card)
6. Works across Chrome, Firefox, Safari desktop
