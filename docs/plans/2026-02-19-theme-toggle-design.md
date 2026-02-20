# Theme Toggle Design

**Date:** 2026-02-19
**Status:** Approved

## Goal

Add a light/dark theme toggle to the Margin Invest navbar. Persist the user's choice, respect system preference on first load, and avoid flash of wrong theme.

## Current State

- `next-themes` v0.4.6 installed and configured in `layout.tsx` with `attribute="class"`, `defaultTheme="dark"`, `enableSystem`
- `suppressHydrationWarning` on `<html>` — no-flicker strategy already in place
- CSS variables defined in `globals.css` with light defaults and `.dark` overrides
- Design tokens used throughout: `bg-bg-primary`, `text-text-primary`, etc.
- **No existing theme toggle component**
- Navbar, user-dropdown, and mobile-menu have hardcoded `bg-[#111113]` values that don't respond to theme changes

## Design

### New Component: `ThemeToggle`

**File:** `web/src/components/nav/theme-toggle.tsx`

- Uses `useTheme()` from `next-themes` (`resolvedTheme`, `setTheme`)
- Renders `<button>` with Sun (in dark mode) or Moon (in light mode) SVG icon
- `aria-label` reflects the action: "Switch to light mode" / "Switch to dark mode"
- Styled: `text-text-secondary hover:text-text-primary`, visible focus ring
- Renders invisible placeholder until client-mounted (prevents hydration mismatch)

### Navbar Integration

**Desktop** (`navbar.tsx`): Place `<ThemeToggle />` in the right-side flex container, always visible regardless of auth state.

**Mobile** (`mobile-menu.tsx`): Place `<ThemeToggle />` in mobile menu near bottom of items.

### Hardcoded Color Fixes

| File | Old | New |
|------|-----|-----|
| `navbar.tsx` | `bg-[#111113] dark:bg-[#111113] light:bg-[#FAFAF9]` | `bg-bg-elevated` |
| `mobile-menu.tsx` | `bg-[#111113] dark:bg-[#111113]` | `bg-bg-elevated` |
| `user-dropdown.tsx` | `bg-[#111113]` | `bg-bg-elevated` |

### Persistence & No-Flicker

Handled by existing `next-themes` setup:
- `localStorage` key `theme` (automatic)
- Blocking `<script>` sets `class` before paint
- `enableSystem` respects `prefers-color-scheme` when no stored preference

## Test Plan

| Scenario | Expected |
|---|---|
| First load, no preference | Uses system theme |
| Click toggle in dark mode | Switches to light, icon changes to Moon, localStorage updated |
| Click toggle in light mode | Switches to dark, icon changes to Sun |
| Refresh after toggling | Persists choice, no flash |
| Keyboard: Tab + Enter | Toggle activates, focus ring visible |
| Mobile: open menu | Toggle visible in mobile menu |
| Screen reader | Announces "Switch to light/dark mode" |

## Files Touched

- **New:** `web/src/components/nav/theme-toggle.tsx`
- **Modified:** `web/src/components/nav/navbar.tsx`
- **Modified:** `web/src/components/nav/mobile-menu.tsx`
- **Modified:** `web/src/components/nav/user-dropdown.tsx`
