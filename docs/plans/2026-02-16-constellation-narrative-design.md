# Constellation Narrative Animation Design

**Date:** 2026-02-16
**Status:** Approved
**Section:** Friction section ("Most investors react")

## Purpose

Transform the static constellation visual next to the friction section from decoration into a scroll-driven narrative device. The animation communicates: Reaction → Structure, Chaos → System, Noise → Signal.

## Decisions

- **Trigger:** Scroll-driven (progress maps to scroll position in friction section range)
- **Final formation:** Network graph — 4-hub topology mirroring the engine pipeline
- **Render layer:** SVG in HTML layer using framer-motion `useScroll` + `useTransform`
- **Mobile:** Static SVG showing final structured state (no animation)
- **Approach:** Framer-Motion SVG with pre-computed position interpolation

## Animation Narrative

### Phase 1: Chaos (scroll 0.07–0.09, progress 0%–30%)

"Most investors react."

- 20 nodes at randomized positions — scattered with intentional visual discomfort
- Connections exist but are broken: dashed strokes, low opacity, misaligned endpoints
- 3 "false connections" between distant unrelated nodes — visual noise
- Subtle drift: micro-oscillation (±2px) via sine offset per node, different frequencies
- All nodes and edges in `text-secondary` at 15-25% opacity. No accent color.

### Phase 2: Transition (scroll 0.09–0.12, progress 30%–80%)

"Few operate with structure."

- Nodes migrate from chaos positions toward structured positions
- Stagger: peripheral nodes first (offset 0–0.01), mid-tier next (0.01–0.02), hubs last (0.02–0.03)
- Broken connections heal: dashes fill, opacity rises, endpoints align
- False connections fade out (opacity → 0)
- Drift oscillation dampens progressively
- Hub nodes emerge: slightly larger, transitioning to accent color

### Phase 3: Structure (scroll 0.12–0.14, progress 80%–100%)

"Emotion is expensive."

- All nodes at final structured positions — clean network graph
- 4-5 hub nodes: radius 5.5px, accent color, 0.85 opacity
- 12-15 peripheral nodes: radius 3-3.5px, text-secondary, 0.35-0.55 opacity
- Connections are solid: consistent weight, intentional topology
- Zero drift — complete stillness (contrast with Phase 1 is the payoff)
- Left-to-right flow suggests progression

## Structural Layout

### ViewBox: `0 0 400 280`

### Chaos State

- 20 nodes spread with no grid alignment
- Intentional clustering errors (2-3 too close, gaps elsewhere)
- 12 real edges + 3 false edges, some dashed/broken
- No visual hierarchy — even weight distribution

### Structured State

4-hub network topology:

- Hub nodes (H1–H4): positions (80,140), (160,80), (260,80), (340,140)
  - Radius: 5.5px, accent color, 0.85 opacity
- Peripheral nodes (12-15): arcs around hubs, 30-60px distance
  - Radius: 3-3.5px, text-secondary, 0.35-0.55 opacity
- Hub-to-hub edges: 1.5px stroke, accent, 0.4 opacity
- Hub-to-peripheral edges: 1px stroke, text-secondary, 0.2 opacity
- No peripheral-to-peripheral connections

4 hubs mirror the engine pipeline stages (data → filter → score → rank).

## Motion Timing

| Scroll Range | Progress | Phase | Feel |
|---|---|---|---|
| 0.07–0.09 | 0%–30% | Chaos hold | ~1.5 viewport-heights |
| 0.09–0.12 | 30%–80% | Transition | ~2 viewport-heights |
| 0.12–0.14 | 80%–100% | Structure settle | ~1 viewport-height |

### Stagger

- Peripheral nodes: offset 0–0.01 (move first)
- Mid-tier nodes: offset 0.01–0.02
- Hub nodes: offset 0.02–0.03 (settle last)

Creates convergence effect — intelligence emerging from noise.

### Easing

`[0.22, 1, 0.36, 1]` — matches existing project easing (hero text, engine-diagram morph).

### Edge Animation

- Broken → solid: `strokeDasharray` transitions from `"4 8"` to `"none"`
- False edges: opacity 0.15 → 0 in range 0.09–0.10
- True edges: `strokeDashoffset` draws 100% → 0% in range 0.10–0.13
- Hub-to-hub edges draw last

### Drift (Chaos Phase)

- Amplitude: ±2px per node
- Frequency: 0.3–0.8 Hz (varies per node)
- Dampens to zero as transition begins
- Pre-computed sine offset, not physics simulation

## Component Architecture

```
ConstellationNarrative
├── useConstellationData() — pre-computed position arrays + edge topology
│   ├── chaosPositions: Vec2[]
│   ├── structuredPositions: Vec2[]
│   ├── edges: { from, to, type }[]
│   └── nodeRoles: ('hub' | 'peripheral')[]
│
├── useScrollProgress() — framer-motion useScroll + useTransform → 0-1
│
├── <svg viewBox="0 0 400 280">
│   ├── <g> edges (motion.line per edge)
│   └── <g> nodes (motion.circle per node)
│
└── Mobile: static SVG of structured state
```

Replaces the existing `MarketNoiseViz` component in `friction-section.tsx`.

## Performance Safeguards

1. `will-change: transform, opacity` on SVG container
2. No `useFrame` — purely scroll-driven, no animation loop
3. Pre-computed positions — zero math during scroll
4. 20 nodes + ~18 edges = 38 SVG elements (trivial)
5. `motion.circle` / `motion.line` skip React re-renders
6. Mobile: zero JS animation, static SVG
7. `prefers-reduced-motion`: shows structured state immediately

## Scroll Choreography Integration

Constellation occupies scroll range 0.07–0.14 — currently dead space between hero text and engine diagram morph (starts at 0.32). No animation competition, no WebGL overhead.

Narrative handoff: hero text → constellation resolves → engine diagram begins.

## Visual Constraints

- Controlled, analytical, minimal, premium
- No flashy particles, no glowing neon, no physics simulations
- Accent color (#0E4F3A light / #1C7A5A dark) on hub nodes only
- Text-secondary for all peripheral elements
- Matches existing design tokens in `styles/tokens.ts`
