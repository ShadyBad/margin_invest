# Nav Active Underline Design

**Date:** 2026-02-21

## Problem

Navigation links in the menu bar don't visually indicate the current page beyond a text color change. Users should see an animated underline on the active page's menu item.

## Design

### Scope

Single file change: `web/src/components/nav/nav-links.tsx`.

### Implementation

Each `<Link>` gets `relative` positioning and an `::after` pseudo-element styled as a horizontal line:

- **Dimensions:** Full width of the text, 1.5px tall, positioned 2px below the text baseline
- **Color:** `bg-text-primary` (matches text color, respects theme)
- **Default state:** `scale-x-0` (invisible)
- **Active state:** `scale-x-100` (fully visible), origin-center so it expands from the middle
- **Hover state (non-active only):** `scale-x-100` at ~50% opacity — a preview underline
- **Transition:** `transition-transform duration-300 ease-out` for smooth slide-in animation

### Mobile

No underline treatment. Mobile menu uses color-only active state (existing behavior unchanged).

### Approach

CSS `::after` pseudo-element via Tailwind `after:` variants. No extra DOM elements, GPU-accelerated transform animation.
