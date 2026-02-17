# Premium Editorial Transformation — Design Document

**Date:** 2026-02-17
**Scope:** Landing page + Dashboard (light touches on nav/onboarding)
**Approach:** Hybrid A+B — Editorial foundation with select component redesigns
**Priority axis:** Editorial aesthetic as foundation, WebGL and charts build on refined canvas

---

## 1. Typography System

**New font stack (three tiers):**

| Tier | Font | Usage |
|------|------|-------|
| Display | Instrument Serif (Google Fonts, `next/font`) | Hero headlines, section titles, card score numbers, portfolio conviction number, pricing tier prices, metrics strip numbers |
| Body | Inter Tight (existing) | All UI text, descriptions, navigation, buttons, labels |
| Data | Geist Mono (existing) | Percentiles, prices, timestamps, axis labels |

**Scale (desktop):**
- Hero headline: 88px (up from 72px), Instrument Serif
- Section headings: 56px (up from 48px), Instrument Serif
- Card score number: 48px default / 56px exceptional tier, Instrument Serif
- Body/UI: unchanged

**Refinements:**
- Display type tracking: -0.04em, leading: 1.05
- `font-feature-settings: "ss01"` on Instrument Serif for stylistic alternates
- Expose as `--font-display` CSS variable via `@theme inline`

---

## 2. Color System — Warm Neutral

### Dark mode

| Token | Current | New |
|-------|---------|-----|
| `bg-primary` | `#0D0F12` | `#110F0D` |
| `bg-elevated` | `#151820` | `#1A1714` |
| `bg-subtle` | `#1A1D24` | `#211E1A` |
| `text-primary` | `#E8E8E6` | `#EDE9E3` |
| `text-secondary` | `#A5A5A3` | `#A39E96` |
| `text-tertiary` | `#6B6B68` | `#6B6660` |
| `border-primary` | `#252830` | `#2A2621` |
| `border-subtle` | `rgba(232,232,230,0.06)` | `rgba(237,233,227,0.06)` |
| `accent` | `#1C7A5A` | `#1A7A5A` (minimal shift) |

### Light mode

| Token | Current | New |
|-------|---------|-----|
| `bg-primary` | `#F4F3EF` | `#F5F2EC` |
| `bg-elevated` | `#FFFFFF` | `#FEFDFB` |
| `bg-subtle` | `#ECEAE4` | `#EBE7DF` |

### New tokens

- `--color-surface-warm: rgba(180, 160, 130, 0.03)` — warm wash for card backgrounds
- `--color-glow-accent: rgba(26, 122, 90, 0.15)` — WebGL bloom tinting

---

## 3. Spacing & Negative Space

### Landing page sections

| Element | Current | New |
|---------|---------|-----|
| Vertical padding | 96px | 140px desktop / 96px tablet / 64px mobile |
| Horizontal padding | 8vw | 10vw desktop / 6vw mobile |
| Max content width | 1280px | 1200px |
| Hero top padding | 96px | 180px |
| Inter-element gaps | varies | 24px base, 40px between major blocks |

### Dashboard cards

| Element | Current | New |
|---------|---------|-----|
| Card padding | `p-6` | `p-8` desktop / `p-6` mobile |
| Grid gap | `gap-6` | `gap-8` |
| Header-to-body | `mb-1` | `mb-3` |
| Score-to-details | `mb-4` | `mb-6` |

### Principles
- Hero: 40% of viewport height is empty space
- Section separation via space alone (no borders/dividers)
- Dashboard header: 48px top padding before first card row

---

## 4. Stock Card Redesign

### Three-tier visual hierarchy

**Exceptional tier:**
- Full card glow: `0 0 30px rgba(26, 122, 90, 0.08), 0 4px 16px rgba(0,0,0,0.3)`
- Score: Instrument Serif at 56px, emerald color, subtle pulsing glow behind (2s ease-in-out infinite, 3-6% opacity)
- Background: warm radial gradient top-left (amber 4%) + accent radial bottom-right (emerald 3%)
- Full border in `accent/30`
- 2px solid accent stripe across top
- Conviction badge: filled background (emerald bg, white text), slightly larger
- Percentile bars 90+: subtle glow on fill element

**High tier:**
- Left border accent (existing)
- Standard shadow system
- Score: Instrument Serif at 48px, text-primary color
- Standard conviction badge

**Standard/Low tier:**
- Clean, neutral, no special treatment
- Score: Instrument Serif at 48px, text-secondary color

### Common card changes
- Border radius: `rounded-sm` (2px) → `rounded-lg` (8px)
- Hover: `scale(1.01)` + shadow elevation + border color shift (200ms)
- Factor labels: uppercase tracking (0.1em), dimmer color
- Percentile bars: 8px height, rounded ends, subtle inner shadow
- Score number: "conviction" label below in small caps

---

## 5. WebGL Evolution

### Postprocessing stack (`@react-three/postprocessing`)
- **Bloom:** luminance threshold 0.8, intensity 0.3, radius 0.6
- **Vignette:** offset 0.3, darkness 0.5
- **Chromatic aberration:** offset [0.001, 0.001] (high quality tier only)

### Node behavior
- Reduce node count by 30%
- Increase spacing (spread multiplier 1.4x)
- Breathing scale animation: 0.95-1.05, seeded random, 3-6s period per node
- Connection lines: opacity to 40%, slight width variation

### Scroll reactivity
- Camera parallax depth: 0.02
- Viewport-center nodes: slightly brighter/larger
- Section transitions: nodes shift position over 2s

### Quality tiers
- **High:** full postprocessing + all behaviors
- **Medium:** bloom only + reduced count + breathing
- **Low:** no postprocessing, static nodes, minimal count

---

## 6. Hybrid Chart System

### Recharts enhancements
- Gradient fills: vertical gradient (accent 15% → transparent)
- Warm grid lines: `grid-line` token color
- Custom tooltip: warm elevated card (rounded-lg, shadow-card, Instrument Serif value, Inter Tight labels)
- Axis labels: Geist Mono 11px, `text-tertiary`
- Active dots: outer glow ring (2px accent at 20%)

### WebGL ambient layer (`ChartGlowCanvas`)
- Canvas behind chart area (z-index below, pointer-events none)
- Soft glow correlating with score trend (upward = brighter green)
- 5-8 slow drifting particles at very low opacity
- Quality tiers: high = full, medium = simplified, low = disabled

---

## 7. Landing Page Composition

Section order unchanged. Refinements per section:

1. **Hero** — Instrument Serif 88px headline, 180px top padding, larger CTA with warm hover glow
2. **Metrics Strip** — centered with max-width, subtle border top/bottom, numbers in Instrument Serif
3. **Engine Diagram** — 140px vertical padding, evolved WebGL constellation
4. **Capability Showcase** — warm elevated card treatment, increased card gap
5. **Friction Diagram** — generous spacing, typography refinements
6. **Proof Section** — Instrument Serif for metric numbers, warmer cards
7. **Pricing** — tier names in Instrument Serif, existing refinements kept
8. **Final CTA** — Instrument Serif headline, more vertical space, dramatic presence
9. **Footer** — warm border-top, minimal refinement

---

## 8. Motion & Interaction

### Easing system
- **Enter:** `[0.22, 1, 0.36, 1]` (kept)
- **Interaction:** `[0.19, 1, 0.22, 1]` (snappier, Wonderland-inspired)

### Card interactions
- Hover: `scale(1.01)` + shadow + border shift (200ms interaction curve)
- Exceptional hover: glow intensifies (shadow spread increases)
- Expand: Framer Motion `layout` spring animation

### Scroll reveals
- Landing: fade up + 16px translate
- Dashboard cards: 60ms stagger delay (from 50ms)
- Percentile bars: fill delayed 200ms after card enters view

### Micro-interactions
- Score numbers: count-up from 0 to final value over 600ms on viewport entry
- Conviction badge: scale bounce (1.0 → 1.05 → 1.0 over 300ms)

---

## Reference Sites

- **Wonderland (wonderlandams.com):** Multi-font editorial system, generous spacing, restraint as premium signal
- **Ventriloc (ventriloc.vercel.app):** Dimensional graph inspiration (hybrid 2D + 3D depth)

## Dependencies

- `@react-three/postprocessing` — new dependency for WebGL effects
- `Instrument Serif` — Google Font, loaded via `next/font/google`
