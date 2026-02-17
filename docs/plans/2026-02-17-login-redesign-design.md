# Login Page Redesign

**Date:** 2026-02-17
**Status:** Approved

## Problem

The current login page is functional but visually flat — a static dark background with full-width OAuth buttons and a credentials form. It doesn't match the premium fintech aesthetic of the rest of the product. There's no animation, no WebGL, hardcoded colors instead of design tokens, and the layout lacks the calm, immersive quality the brand requires.

## Solution

A centered glassmorphism login card floating over a purpose-built WebGL background ("Liquidity Flow"). OAuth-first with icon-only buttons, credentials form collapsed by default behind a "Continue with email" toggle.

### Layout

Full-screen viewport, no scroll. WebGL canvas fills the background. Card centered vertically and horizontally.

**Card dimensions:**
- Width: `max-w-[420px]`, `w-[calc(100%-32px)]` on mobile
- Padding: `px-8 py-10` (desktop), `px-6 py-8` (mobile)
- Border radius: `rounded-3xl` (24px)

**Card surface:**
- Background: `rgba(17, 17, 19, 0.6)`
- Backdrop filter: `blur(16px) saturate(1.2)`
- Border: `1px rgba(255, 255, 255, 0.06)`
- Shadow: `0 8px 32px rgba(0, 0, 0, 0.4)`

**Card content stack (top to bottom):**
1. Logo icon (geometric "M", same as FloatingNav) — centered
2. Heading: "Sign in to Margin Invest"
3. Subtext: "Secure login with bank-grade encryption"
4. OAuth icon row (Google, Apple, GitHub)
5. Divider line with "or"
6. "Continue with email" toggle
7. Footer: "Don't have an account? Create one"

**Expanded credentials state:**
- Smooth height animation reveals email + password fields
- Password visibility toggle icon
- "Sign In" submit button
- Text toggles to "Back to social login"

### Color Palette

| Role | Value |
|------|-------|
| Page background (fallback) | `var(--bg-primary)` / `#0D0F12` |
| Card background | `rgba(17, 17, 19, 0.6)` |
| Card border | `rgba(255, 255, 255, 0.06)` |
| Input background | `rgba(255, 255, 255, 0.04)` |
| Input border | `rgba(255, 255, 255, 0.08)` |
| Input border (focus) | `var(--accent)` / `#10B981` |
| Text primary | `var(--text-primary)` |
| Text secondary | `var(--text-secondary)` |
| OAuth icon fill | `var(--text-primary)` (monochrome) |
| OAuth hover bg | `rgba(255, 255, 255, 0.08)` |
| Submit button | `var(--accent)` |
| Apple disabled | `opacity-40`, `cursor-not-allowed` |

### Typography

All Inter Tight (`--font-sans`).

| Element | Size | Weight | Extra |
|---------|------|--------|-------|
| Heading | `text-xl` (20px) | `font-semibold` | `tracking-[-0.02em]` |
| Subtext | `text-[13px]` | `font-normal` | — |
| Input labels | `text-[13px]` | `font-medium` | — |
| Input values | `text-[15px]` | `font-normal` | — |
| Button | `text-[15px]` | `font-semibold` | — |
| Footer link | `text-[13px]` | `font-medium` | — |
| "or" divider | `text-[12px]` | `font-normal` | `tracking-[0.05em]` uppercase |

### WebGL Background — "Liquidity Flow"

A minimal, purpose-built R3F scene evoking market depth and capital flow.

**Composition:**
- 3-4 large gradient orbs using simplex noise for smooth shape deformation. Colors: `#0A1628`, `#0D3B4F`, `#121830`, one subtle warm `#2A1A0E`
- 40-60 tiny particles (`0.15-0.3` opacity) drifting upward with slight horizontal sine wave
- Soft radial vignette darkening edges, light concentrated at center

**Motion:**
- Orb drift: ~0.2-0.5px/frame (glacial)
- Orb morph: 8-12s cycle via noise
- Particle drift: 0.3-0.8px/frame upward
- No sudden movements, no flashing, no pulsing

**Technical:**
- Component: `web/src/components/login/login-scene.tsx`
- `@react-three/fiber` Canvas, `dpr={[1, 1.5]}`
- Shader-based orbs (`ShaderMaterial` + noise), particles via `Points`
- `next/dynamic` with `ssr: false`
- Fallback: solid `bg-bg-primary` if WebGL fails
- Target: < 5ms frame time, 4-5 draw calls total

### OAuth Icons

Three icons in a centered horizontal row, `gap-4`:
- Container: `48x48`, `rounded-xl`, `rgba(255, 255, 255, 0.04)` bg, `1px rgba(255, 255, 255, 0.06)` border
- Icons: 20x20px, monochrome `text-text-primary`
- Google: "G" SVG, GitHub: octocat mark SVG, Apple: Apple logo SVG
- Hover (Google, GitHub): bg → `rgba(255, 255, 255, 0.08)`, `scale-105`, `200ms ease-out`
- Apple: `opacity-40`, `cursor-not-allowed`, no hover, no click handler

### Interactions

**Credentials expand/collapse:**
- `grid-rows-[0fr]` → `grid-rows-[1fr]` with `overflow-hidden`, `300ms ease-out`
- "Continue with email" ↔ "Back to social login" text toggle

**Input fields:**
- Height: `h-12` (48px)
- Inner shadow: `inset 0 1px 2px rgba(0, 0, 0, 0.2)`
- Focus: accent border + `ring-1 ring-accent/30`
- Password: eye icon toggle, `text-text-secondary` → `text-text-primary` on hover

**Submit button:**
- Full width, `h-12`, `rounded-xl`
- `bg-accent text-white font-semibold`
- Hover: `brightness-110`, Active: `scale-[0.98]`, `150ms ease-out`

**Page load animation (CSS @keyframes, no framer-motion):**
- Card: fade + slide up (`opacity 0→1`, `translateY 16px→0`), `500ms ease-out`, `100ms delay`
- WebGL: canvas fade in `opacity 0→1`, `800ms`

### File Structure

**Create:**
- `web/src/components/login/login-scene.tsx` — WebGL background
- `web/src/components/login/login-card.tsx` — Glass card with OAuth + credentials
- `web/src/components/login/__tests__/login-card.test.tsx` — Tests

**Modify:**
- `web/src/app/login/page.tsx` — Rewrite as thin server component

**Delete:**
- `web/src/app/login/login-buttons.tsx` — Replaced by login-card.tsx
- `web/src/app/login/__tests__/login-buttons.test.tsx` — Replaced by new tests

### Accessibility

- OAuth buttons: `aria-label` ("Sign in with Google", etc.)
- Apple: `aria-disabled="true"`
- Form inputs: proper `<label>` elements
- Password toggle: `aria-label`
- Focus order: OAuth → email toggle → inputs → submit → footer
- Visible focus states: `focus-visible:outline`
- WebGL canvas: `aria-hidden="true"`
- `prefers-reduced-motion`: skip load animation, stop/slow WebGL particles

### Constraints

- No changes to register, MFA, or auth error pages
- No Apple OAuth provider wiring (icon visual-only)
- No "Remember me" or "Forgot password"
- No framer-motion on login — CSS keyframes only
- No changes to auth.ts or session handling
- No new design tokens in globals.css
- No new npm dependencies
