# Fluid Intelligence — Landing Page Redesign

**Date**: 2026-02-17
**Status**: Approved
**Scope**: Landing page + design system tokens for propagation

## Overview

Replace the current "retro/hacker" WebGL aesthetic (wireframe grids, octahedron nodes, constellation SVG) with a premium, organic visual experience called "Fluid Intelligence." The new system combines a contained WebGL fluid shader hero with CSS-driven glass surfaces, gradient meshes, and Framer Motion scroll animations. A full DNA personalization layer derives visual parameters from user portfolio composition.

### Design Decisions

| Decision | Choice |
|----------|--------|
| Scope | Landing page + design system tokens |
| Personalization | Full DNA system from portfolio composition |
| Page structure | Clean slate — 4-chapter narrative |
| Mobile | CSS-only premium (no WebGL) |
| Color palette | Evolve current warm neutrals + emerald |
| Rendering | Hybrid — WebGL hero only, CSS/Framer Motion everywhere else |

### Inspiration

[Wonderland Amsterdam DDNA](https://wonderlandams.com/works/ddna-online-experience) — timeless forms that constantly shift, soft transitions, horizontal scroll, bespoke visual language built around infinite possibilities.

---

## 1. Page Narrative & Information Architecture

Four "chapters" replace the current 8-section vertical scroll. Each chapter is a self-contained narrative beat. Chapters 2 and 3 use horizontal scroll segments within the vertical flow.

| # | Chapter | Purpose | Scroll |
|---|---------|---------|--------|
| 1 | **The Signal** (Hero) | Brand promise + fluid shader backdrop | Vertical (viewport-locked) |
| 2 | **The Engine** | Analysis pipeline walkthrough | Horizontal (3 panels) |
| 3 | **The Proof** | Conviction in action — real output examples | Horizontal (3-4 panels) |
| 4 | **The Path** | Pricing + CTA | Vertical (single viewport) |

Between chapters, a ~50vh vertical breathing gap with a subtle section indicator creates chapter breaks.

**Mobile**: All horizontal chapters collapse to vertical stacked panels. Chapter structure preserved, scrolling always vertical.

---

## 2. Visual System

### 2.1 Hero Shader ("The Signal")

Full-viewport WebGL canvas with a GLSL fragment shader producing a fluid gradient surface — slow-moving liquid silk with depth.

**Shader technique**: Single full-screen quad. Fragment shader combines:
- Simplex noise at 2-3 octaves (period 8-12s per cycle)
- Color interpolation across 3-4 DNA-derived control points
- Soft caustic highlights (voronoi-derived bright spots drifting across surface)
- Subtle parallax response to mouse position (desktop) or time-based drift (mobile)

**Motion character**: Extremely slow. 10+ seconds for noticeable change. Reads as "calm intelligence" — molten glass cooling, not a lava lamp.

**Default colors** (pre-DNA):
- Base: `#0F0D0B` blending to `#0A2E1F`
- Mid: `#1A5A3E` with warm `#3A2A18` undertone
- Highlights: `#EDE9E3` at 15% opacity

**Scroll dismissal**: As user scrolls past hero, shader darkens (luminance × `1 - progress * 0.8`). Canvas is `position: fixed` with `pointer-events: none`, fading behind content.

### 2.2 Page-Wide Visual Language

Outside the hero, everything is CSS-only:

**Gradient meshes**: Layered `radial-gradient()` with DNA-influenced colors at 5-10% opacity. Positioned at section boundaries for ambient warmth.

**Three depth planes**:
1. Background — gradient meshes, very low opacity
2. Content — cards, text, interactive elements
3. Accent — floating SVG line elements that drift with scroll

**Glass surfaces**: Cards/panels use `backdrop-filter: blur(40px) saturate(1.2)` with `border: 1px solid rgba(255, 255, 255, 0.08)` and `border-radius: 16px`.

**Typography**: Keep Instrument Serif (display) and Inter Tight (body). Add variable font weight animation on headings — weight shifts 400 to 500 as sections enter view.

### 2.3 Color System Evolution

| Token | Current | Evolved |
|-------|---------|---------|
| `--color-bg-deep` | `#110F0D` | `#0F0D0B` (warmer) |
| `--color-bg-surface` | `#F5F2EC` | `#F7F4EE` (lighter) |
| `--color-accent` | `#0E4F3A` | `#0E4F3A` (unchanged) |
| `--color-accent-glow` | N/A | `rgba(14, 79, 58, 0.15)` |
| `--color-warm-under` | N/A | `#2A1F14` (bronze depth) |
| `--color-caustic` | N/A | `rgba(237, 233, 227, 0.12)` |

Light mode: Fluid shader inverts to cream base with emerald/bronze flowing colors. Same motion, different polarity.

---

## 3. Chapter Content & Interaction Design

### 3.1 Chapter 1: "The Signal" (Hero)

- **Headline**: Instrument Serif, 72-88px. Short and declarative (e.g., "Conviction, Quantified.")
- **One-liner**: Inter Tight, 18-20px, 60% opacity. Single-sentence value prop.
- **Dual CTA**: Primary ("Start Scoring") + ghost ("See How It Works" scrolls to Chapter 2)
- **Scroll indicator**: Minimal animated chevron/line, gentle pulse

**Motion**: Word-level staggered entrance. Each word translates Y 20px to 0, opacity 0 to 1, 80ms stagger. Easing: `cubic-bezier(0.22, 1, 0.36, 1)`.

**Scroll behavior**: Hero holds for ~1.2vh of scroll (parallax fade). Content fades, shader darkens — "sinking into depth" transition.

### 3.2 Chapter 2: "The Engine" (Horizontal)

3 panels, each ~90vw with CSS snap points.

**Panel 2a — "Raw Signal"**: Data category list appearing sequentially + scattered dot visualization (CSS-animated drift).

**Panel 2b — "Structured Analysis"**: Dots organize into clusters via CSS transform. Five scoring factors with one-liners. Data points sort into colored lanes.

**Panel 2c — "Conviction Output"**: Clusters compress into abstracted composite score card. Conviction level, factor breakdown bars, signal indicator — editorial treatment, not a screenshot.

### 3.3 Chapter 3: "The Proof" (Horizontal)

3-4 panels.

**Panel 3a — "Sample Analysis"**: Beautifully typeset example output — ticker with composite score, conviction level, key driving factor. Editorial layout.

**Panel 3b — "Factor Depth"**: Single factor drilldown. Animated bar chart drawing in on scroll. Accent color with subtle glow.

**Panel 3c — "Portfolio View"**: Hypothetical 5-6 ticker watchlist ranked by score. Demonstrates comparative conviction power.

**Panel 3d — (Optional) "Track Record"**: Backtesting time-series if data available.

### 3.4 Chapter 4: "The Path" (Pricing + CTA)

Single viewport, vertical.

- Headline: "Choose Your Lens" or "Start Building Conviction"
- Three pricing cards (Scout/Operator/Allocator) with glass morphism treatment
- Middle card elevated with accent glow border
- Final CTA with trust signal below pricing

Cards stagger from below (translateY 40px to 0, 120ms stagger). Hover lifts -4px with soft shadow expansion.

### 3.5 Navigation

**Chapter indicators**: Vertical dots on right edge (desktop) showing current chapter. Horizontal progress line within horizontal chapters. Minimal — thin lines, accent color, low opacity until hovered.

**Keyboard**: Left/right arrows navigate horizontal panels. Escape returns to vertical flow.

---

## 4. DNA Personalization System

### 4.1 Sector-to-Color Mapping

| Sector | Hue Influence |
|--------|--------------|
| Technology | Cool blue `#1A3A5C` |
| Healthcare | Teal `#0E4F4F` |
| Financials | Deep navy `#0F1E3A` |
| Energy | Warm amber `#4A3018` |
| Consumer Discretionary | Soft coral `#5C2A2A` |
| Industrials | Steel gray `#2A2E33` |
| Materials | Bronze `#3A2A14` |
| Utilities | Muted sage `#2A3A2A` |
| Real Estate | Warm stone `#3A3228` |
| Communication Services | Indigo `#2A1E4A` |
| Consumer Staples | Cream shift `#4A4038` |

**Blending**: Weighted average of sector hue vectors based on portfolio allocation percentages. Produces a 3-color gradient control point set (base, mid, accent).

### 4.2 Visual Variables

```
--dna-base:     /* deepest background tone */
--dna-mid:      /* mid-layer gradient color */
--dna-accent:   /* highlight/caustic tint */
--dna-density:  /* 0.0-1.0, from portfolio diversification */
--dna-tempo:    /* 0.5-1.5, from portfolio volatility */
```

- **`--dna-density`**: Concentrated portfolio (3 stocks) = low (cleaner). Diversified (30 stocks) = higher (richer layers).
- **`--dna-tempo`**: High-beta growth = 1.2x speed. Stable dividend = 0.7x. Difference between 8s and 14s animation cycles.

### 4.3 Data Flow

```
User watchlist (DB)
  -> GET /api/v1/users/me/dna
    -> Compute sector weights, diversification score, volatility profile
    -> Return { base, mid, accent, density, tempo }
  -> Next.js server component fetches on page load
    -> Inject as CSS custom properties on <html>
    -> WebGL shader reads same values as uniforms
```

- **Unauthenticated users**: Default palette, no API call
- **Caching**: 1-hour TTL on computed DNA, recompute on watchlist mutation
- **Fallback**: API fails -> cached values -> defaults. Page always renders.

### 4.4 Performance

- DNA values are CSS custom properties only — no React re-renders
- Shader reads uniforms per frame (already in render loop)
- State transitions: `transition: --dna-base 2s ease` for smooth crossfade
- Progressive enhancement: logged-in users get DNA, everyone else gets a beautiful default

---

## 5. Technical Architecture

### 5.1 Rendering Stack

| Layer | Technology | Scope |
|-------|-----------|-------|
| Hero shader | React Three Fiber + GLSL | Chapter 1 only |
| Scroll orchestration | Framer Motion `useScroll` + `useTransform` | All chapters |
| Horizontal scroll | CSS `scroll-snap-type` + `IntersectionObserver` | Chapters 2 & 3 |
| Glass surfaces | CSS `backdrop-filter` | Cards/panels |
| Gradient meshes | CSS `radial-gradient` | Section backgrounds |
| Micro-animations | Framer Motion `useInView` + `motion.*` | Text reveals, entrances |
| DNA injection | CSS custom properties on `<html>` | Global |

### 5.2 Components Removed

All current Three.js scene components replaced by single `FluidShader`:
- `scene-canvas.tsx`
- `ambient-grid.tsx`
- `engine-nodes.tsx`
- `connection-lines.tsx`
- `capability-cards-3d.tsx`
- `postprocessing-stack.tsx`
- `constellation-narrative.tsx`

Net reduction in WebGL complexity.

### 5.3 Horizontal Scroll

CSS `scroll-snap-type: x mandatory` on container. Each panel is `scroll-snap-align: center`. Browser-native momentum and rubber-banding. `IntersectionObserver` detects active panel for progress indicator and animation triggers.

Vertical-to-horizontal: Each horizontal chapter in a `100vh` container with `overflow-x: auto`. Vertical scroll stops naturally at the container boundary. No scroll-hijacking.

### 5.4 Motion System

**Easing vocabulary** (3 curves):

| Name | Curve | Use |
|------|-------|-----|
| `ease-out-expo` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entrances |
| `ease-in-out-smooth` | `cubic-bezier(0.45, 0, 0.55, 1)` | Transitions |
| `ease-out-back` | `cubic-bezier(0.22, 1, 0.36, 1)` | Emphasis/delight |

**Duration ranges**:
- Micro (hover/press): 150-200ms
- Reveal (element entrance): 500-700ms
- Transition (section change): 800-1200ms
- Ambient (shader/breathing): 8000-15000ms

**Stagger**: 60-100ms between items. Max 5 items in sequence.

### 5.5 Accessibility

- `prefers-reduced-motion: reduce` -> shader freezes on single frame, Framer animations instant, horizontal scroll still functional
- WCAG AA contrast maintained against glass surfaces
- Chapter indicators keyboard-navigable with ARIA labels
- Horizontal panels use `role="tabpanel"` with arrow key navigation

### 5.6 Performance Budget

| Metric | Target |
|--------|--------|
| FCP | < 1.2s |
| LCP | < 2.5s |
| CLS | < 0.05 |
| Frame rate (desktop) | 60fps |
| Frame rate (mobile) | 60fps (no WebGL) |
| JS bundle (landing) | < 150KB gzipped |
| Shader compile | < 100ms |

**Strategies**:
- WebGL canvas lazy-loads (hero text SSR renders first)
- Horizontal panel content lazy-renders via IntersectionObserver
- DNA API call parallel with page hydration
- `will-change: transform` applied only during active animations
- Images use Next.js `<Image>` with blur placeholders

---

## 6. Design System Tokens

### 6.1 Color Tokens (Expanded)

```
/* Base palette */
--color-bg-deep
--color-bg-surface
--color-bg-elevated
--color-text-primary
--color-text-secondary
--color-text-muted
--color-accent
--color-accent-glow
--color-warm-under
--color-caustic
--color-border
--color-border-subtle

/* DNA overrides */
--dna-base
--dna-mid
--dna-accent
--dna-density
--dna-tempo

/* Semantic (unchanged) */
--color-bullish
--color-bearish
--color-percentile-[1-5]
```

### 6.2 Motion Tokens

```
--ease-out-expo:       cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out-smooth:  cubic-bezier(0.45, 0, 0.55, 1);
--ease-out-back:       cubic-bezier(0.22, 1, 0.36, 1);
--duration-micro:      150ms;
--duration-reveal:     600ms;
--duration-transition: 1000ms;
--duration-ambient:    calc(10000ms * var(--dna-tempo, 1));
--stagger-base:        80ms;
```

### 6.3 Glass Surface Primitive

```css
.glass {
  background: rgba(var(--color-bg-surface-rgb), 0.6);
  backdrop-filter: blur(40px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.glass-elevated {
  background: rgba(var(--color-bg-surface-rgb), 0.75);
  backdrop-filter: blur(60px) saturate(1.3);
  border: 1px solid var(--color-accent-glow);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
```

### 6.4 Gradient Mesh Utility

```css
.gradient-mesh {
  background:
    radial-gradient(ellipse at 20% 30%, var(--dna-base, var(--color-warm-under)) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, var(--dna-mid, var(--color-accent)) 0%, transparent 50%),
    var(--color-bg-deep);
  opacity: 0.06;
}
```

### 6.5 Propagation Strategy

| Phase | Scope | Changes |
|-------|-------|---------|
| This project | Landing page | Full new visual system |
| Next | Login/auth pages | Glass surfaces over gradient mesh |
| Later | Dashboard | StockCards adopt glass, gradient backgrounds, motion tokens |
| Eventually | Asset panel, settings | Full glass treatment, DNA accents |

---

## 7. File Structure

### New Files

```
web/src/components/landing/
  fluid-shader.tsx          # Hero WebGL shader component
  fluid-shader.glsl         # GLSL fragment shader source
  chapter-hero.tsx           # Chapter 1 layout
  chapter-engine.tsx         # Chapter 2 horizontal panels
  chapter-proof.tsx          # Chapter 3 horizontal panels
  chapter-path.tsx           # Chapter 4 pricing/CTA
  horizontal-scroll.tsx      # Reusable horizontal snap container
  chapter-indicator.tsx      # Vertical dots + horizontal progress
  dna-provider.tsx           # Fetches DNA, injects CSS variables

web/src/components/ui/
  glass-surface.tsx          # Reusable glass card primitive

web/src/lib/
  dna.ts                     # DNA computation (color blending, vector math)

web/src/app/api/v1/users/me/dna/
  route.ts                   # DNA API endpoint
```

### Modified Files

```
web/src/styles/tokens.ts     # New color, motion, glass tokens
web/src/app/page.tsx          # New chapter structure
web/src/app/globals.css       # New tokens, glass utilities, gradient mesh
```

### Removed Files

```
web/src/components/landing/scene-canvas.tsx
web/src/components/landing/ambient-grid.tsx
web/src/components/landing/engine-nodes.tsx
web/src/components/landing/connection-lines.tsx
web/src/components/landing/capability-cards-3d.tsx
web/src/components/landing/postprocessing-stack.tsx
web/src/components/landing/constellation-narrative.tsx
```
