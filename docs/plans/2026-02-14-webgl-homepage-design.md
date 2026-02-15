# Margin Invest — WebGL Homepage Design

**Date**: 2026-02-14
**Status**: Approved
**Supersedes**: 2026-02-13-marketing-site-design.md (landing page sections)

## Overview

Rebuild the existing Framer Motion landing page as a performance-first hybrid WebGL experience using React Three Fiber. Single continuous 3D scene with HTML content overlay. Scroll position drives scene state.

Reference: wonderlandams.com/works/fwa-thecoolclub — interactive 3D content (not decorative background).

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WebGL library | React Three Fiber + Drei | Native React integration, demand rendering, lazy-loadable |
| Migration strategy | Rebuild from scratch | Clean break from Framer Motion landing, no hybrid legacy |
| Theme support | Both light and dark | Matches existing app; next-themes already configured |
| Mobile strategy | Graceful degradation | Full WebGL desktop, reduced tablet, CSS-only mobile |
| Architecture | Scroll-driven single canvas | Single WebGL context, performant, cohesive progressive reveal |

## Architecture

```
<main>
  <R3FCanvas>            // fixed, full viewport, z-index: 0
    <ScrollControls>     // maps scroll to 3D scene state
      <AmbientGrid />    // Layer 1: always visible, 4% opacity grid plane
      <EngineNodes />    // Layer 2: sections 3-4, four assembled nodes
      <CapabilityCards /> // Layer 3: section 5, staggered card planes
    </ScrollControls>
  </R3FCanvas>

  <div class="html-overlay">  // absolute positioned, z-index: 1
    <HeroSection />
    <FrictionSection />
    <EngineDiagram />
    <EngineProof />
    <CapabilitiesSection />
    <InvestorPositioning />
    <FinalCTA />
  </div>
</main>
```

Canvas loaded via `next/dynamic` with `ssr: false`. `<Suspense>` fallback renders static CSS version.

## Performance Budget

- Target: 60fps desktop, 30fps tablet, no WebGL mobile
- `frameloop="demand"` — render only when scene changes
- DPR cap: `Math.min(window.devicePixelRatio, 1.5)`
- No postprocessing (no bloom, SSAO, or color grading)
- InstancedMesh for repeated geometry (nodes, cards)
- Lazy-load entire R3F bundle (~150kb gzipped)

### Quality Tiers

| Tier | DPR | Geometry | Particles | Trigger |
|------|-----|----------|-----------|---------|
| High | 1.5 | Full | Yes | Desktop, `hardwareConcurrency >= 4` |
| Medium | 1.0 | Simplified | Reduced | Tablet or `hardwareConcurrency < 4` |
| Low | n/a | None | None | Mobile `<768px` (CSS fallback) |

Detection: `navigator.hardwareConcurrency` + viewport width.

## 3D Scene Layers

### Layer 1 — Ambient Grid (all sections)

Subtle grid plane at z:-5. 4% opacity. Adapts to theme:
- Light: dark grid lines on warm off-white
- Dark: light grid lines on dark navy

Gentle parallax drift on scroll (not mouse-driven).

### Layer 2 — Engine Nodes (sections 3-4)

Four geometric primitives (chamfered octahedrons). Start off-screen right, progressively assemble into horizontal line as section 3 scrolls in. Connected by thin line geometry (BufferGeometry + LineBasicMaterial). Active node uses `accent-primary` emissive highlight.

Section 4: nodes compress/recede as HTML engine proof content takes over.

### Layer 3 — Capability Cards (section 5)

Four flat card planes with 5-8 degree 3D rotation. Stagger into view at different Y positions. Cards are geometric only — no text in WebGL. HTML overlays provide content.

### Scroll State Mapping

| Scroll % | 3D State | HTML Section |
|----------|----------|--------------|
| 0-15% | Grid only | Hero |
| 15-30% | Grid subtle shift | Friction |
| 30-50% | Nodes assemble progressively | Engine Diagram |
| 50-60% | Nodes compress/recede | Engine Proof |
| 60-75% | Card planes float in | Capabilities |
| 75-90% | Cards settle, scene quiets | Investor Positioning |
| 90-100% | Scene fades to minimal | Final CTA |

## Design Tokens

### Colors

Already defined in `globals.css`. No changes needed — tokens match spec:

**Light Mode:**
- `bg-primary`: #F4F3EF
- `bg-secondary`: #ECEAE4
- `text-primary`: #121212
- `text-secondary`: #4A4A4A (current is #5C5C5C — update to #4A4A4A)
- `accent-primary`: #0E4F3A
- `divider`: rgba(18,18,18,0.06)
- `grid-line`: rgba(18,18,18,0.04)

**Dark Mode:**
- `bg-primary`: #0D0F12
- `bg-secondary`: #14171B
- `text-primary`: #E8E8E6
- `text-secondary`: #A5A5A3 (current is #9B9B98 — update to #A5A5A3)
- `accent-primary`: #1C7A5A (current is #1A7A5A — update)
- `divider`: rgba(255,255,255,0.06)
- `grid-line`: rgba(255,255,255,0.04)

New tokens to add: `grid-line` (both modes).

### Typography

| Token | Desktop | Tablet | Mobile | Weight | Line Height | Tracking |
|-------|---------|--------|--------|--------|-------------|----------|
| H1 | 72px | 56px | 48px | 700 | 1.0 | -0.5px |
| H2 | 48px | 40px | 36px | 700 | 1.1 | -0.3px |
| H3 | 32px | 28px | 24px | 600 | 1.2 | 0 |
| Body | 18px | 17px | 16px | 400 | 1.5 | 0 |
| Caption | 14px | 13px | 13px | 400 | 1.4 | 0.2px |

Font: Inter Tight (already configured). No serif or decorative fonts.

Current H1 is 68px — update to 72px.

## Section Details

### 1. Hero — Philosophy

- **Layout**: Left-aligned, columns 1-8 of 12. Right 4 columns: breathing space.
- **H1**: "Structure outperforms emotion." — 72px bold, -0.5px tracking
- **Subline**: "Institutional-grade analytics for serious retail investors." — 18px body, text-secondary, 16px top margin
- **Primary CTA**: "Explore the Engine" — accent-primary filled, 48px height, 24px horizontal padding, 4px radius max
- **Secondary**: "View methodology" — text link, underline on hover, same line as CTA
- **3D**: Ambient grid visible behind. No other geometry.
- **Spacing**: 160px top (below nav), 120px bottom

### 2. Friction Recognition

- **Layout**: Left cols 1-6 (text), right cols 8-12 (data visual)
- Three stacked H3 lines (32px), 32px vertical gap:
  - "Most investors react."
  - "Few operate with structure."
  - "Emotion is expensive."
- CSS stagger-reveal on scroll (not WebGL)
- **Right**: Abstract muted SVG scatter/noise at 15% opacity. Decorative only.
- **Spacing**: 96px top/bottom

### 3. Conceptual Engine Diagram

- **Layout**: Full 12 columns centered
- Four labeled nodes horizontal:
  1. Market Data
  2. Risk Modeling
  3. Allocation Engine
  4. Decision Clarity
- HTML labels positioned beneath 3D node positions
- 1px connecting lines (WebGL LineBasicMaterial)
- Active node: accent-primary highlight (progressive left-to-right on scroll)
- **Annotation**: "This section transitions into interactive WebGL stage." — caption, text-secondary
- **Spacing**: 120px top/bottom

### 4. Engine UI Proof

- **Layout**: Left cols 1-5 (copy), right cols 7-12 (mockups)
- Left: H2 + body describing engine output
- Right: 2-3 dashboard UI screenshots with border-subtle, 6px radius, 16px gap, slight rotation (-1 to 2 degrees)
- **Annotation**: "WebGL stage morph ends here." — caption below images
- **3D**: Nodes have compressed/receded
- **Spacing**: 96px top/bottom

### 5. Capabilities — Staggered

**NOT a grid.** Asymmetric staggered layout:
```
[Block 1 — cols 1-5]            [Block 2 — cols 7-12, +48px Y offset]
        [Block 3 — cols 2-7, +32px Y offset]
                                       [Block 4 — cols 8-12, +64px Y offset]
```

Each block: H3 title + one-line body caption. Alternating blocks get `bg-secondary` tint.
- Structured Allocation
- Quantified Risk
- Scenario Modeling
- Bias Reduction

**3D**: Card planes at matching positions with slight z-depth.
**Spacing**: 120px top/bottom

### 6. Empowered Positioning

- **Layout**: Columns 1-8, left-aligned
- **H2**: "You're not trading. You're operating."
- 1-2 sentences supporting copy, text-secondary
- No 3D active — scene minimal
- **Spacing**: 96px top/bottom

### 7. Final CTA

- **Layout**: Centered (exception to left-align pattern)
- 160px top padding, 120px bottom
- Primary CTA only: "Explore the Engine"
- No secondary links or additional copy
- **3D**: Grid fades to near-invisible

## Component Library

| Component | Props | Notes |
|-----------|-------|-------|
| `NavMinimal` | `theme`, `onCTAClick` | Logo left, CTA right. No hamburger — mobile collapses to CTA only |
| `ButtonPrimary` | `children`, `size`, `href` | accent-primary bg, white text, 48px h, 24px px, 4px radius |
| `ButtonSecondary` | `children`, `href` | Text link, underline on hover |
| `Divider` | `opacity?` | 1px, divider token color |
| `GridOverlay` | `opacity?` | SVG 12-col grid lines, dev reference |
| `DiagramNode` | `label`, `active`, `index` | HTML label positioned below 3D object |
| `CapabilityBlock` | `title`, `description`, `tinted?` | H3 + body, optional bg-secondary |
| `UIImageFrame` | `src`, `alt`, `rotation?` | border-subtle, 6px radius, optional rotation |
| `SectionWrapper` | `children`, `id`, `padding?` | max-w 1280px, 8vw side padding |

All components use flex/grid (auto-layout equivalent).

## Responsive Breakpoints

| Breakpoint | Grid | Columns | WebGL | Side Padding |
|-----------|------|---------|-------|-------------|
| Desktop (>1024px) | 12-col | 12 | Full scene | 8vw |
| Tablet (768-1024px) | 8-col | 8 | Reduced (grid + simplified nodes) | 6vw |
| Mobile (<768px) | 4-col | 4 | None — CSS animations | 5vw |

**Mobile adjustments:**
- Engine Diagram: nodes stack vertically (4 rows)
- Capabilities: single-column stack, alternating bg-secondary tint
- Hero: subline + CTA stack below headline
- All stagger offsets collapse to 0

## Dev Annotation Notes

These are implementation constraints embedded in the design:

1. **Render-on-demand WebGL**: `frameloop="demand"`, invalidate on scroll only
2. **Quality tiers**: Detect via hardwareConcurrency + viewport, set at mount
3. **DPR caps**: Never exceed 1.5x, mobile gets no WebGL
4. **No postprocessing**: Zero shader passes beyond default
5. **InstancedMesh**: All repeated geometry (nodes, cards) use instancing
6. **Progressive reveal**: Scroll position mapped to scene state via ScrollControls
7. **Lazy bundle**: `next/dynamic` import of canvas component, SSR disabled

## Dependencies to Add

```bash
uv run -- npx --prefix web npm install @react-three/fiber @react-three/drei three
uv run -- npx --prefix web npm install -D @types/three
```

Estimated bundle addition: ~150kb gzipped (lazy-loaded, not in critical path).

## What This Replaces

- All files in `web/src/components/landing/` — rebuilt from scratch
- `web/src/app/page.tsx` — new page composition
- Framer Motion remains for non-WebGL animations (friction reveal, etc.) but is no longer the primary animation system for the landing page
