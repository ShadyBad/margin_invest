# Homepage Elevation Design

**Date:** 2026-02-14
**Status:** Approved
**Supersedes:** Supplements 2026-02-14-webgl-homepage-design.md (architectural foundation unchanged)

## Objective

Elevate the Margin Invest homepage from a competent SaaS landing page to a top-1% interactive fintech experience. The core problem: the HTML sections and WebGL scene coexist but never fuse. This design creates conceptual integration, differentiated motion, and psychological weight calibrated for sophisticated retail investors.

## Audit Summary

**Overall grade: C+.** Correct narrative arc, disciplined performance architecture, but homogeneous motion, no signature moment, and the strongest copy ("You're not trading. You're operating.") gets the weakest visual treatment. The WebGL scene is optimized into imperceptibility.

### Top 3 Weaknesses

1. No conceptual fusion between WebGL and HTML — the 3D scene decorates rather than integrates
2. Every element uses identical `opacity: 0, y: 20` animation — flattens the emotional arc
3. InvestorPositioning has the best copy and the weakest execution

---

## 1. Narrative Restructuring

### Section Weight Redistribution

| Section | Current Feel | Target Feel | Key Change |
|---|---|---|---|
| Hero | Competent, safe | Commanding, sparse | Remove defensive subhead. More air. |
| Friction | Adequate | Confrontational | Horizontal line entry. SVG viz gets more presence. |
| Engine Diagram | Informative | **Transformative** | Signature moment: HTML → 3D morph. |
| Engine Proof | Strong | Refined | Score counts up. Bars animate. Real or methodology-backed data. |
| Capabilities | Flat | Rhythmic | Alternating L/R entry matching grid position. |
| Positioning | Anemic | **Full-screen climax** | 100vh centered. 1200ms fade. Only center-aligned section. |
| CTA | Generic | Confident | Remove freemium language. Single imperative. |

### Copy Changes

**Hero subhead:**
- Kill: "Institutional-grade analytics for serious retail investors."
- Replace: "A deterministic scoring engine for capital allocation."

**CTA copy:**
- Kill: "No credit card. No commitment. See what the engine produces for any equity."
- Replace: "Run any equity through the engine."

**Positioning section:**
- Keep: "You're not trading. You're operating."
- Add below (secondary text): "Capital allocation as a repeatable process."

### Vertical Rhythm

| Section | Current (top/bottom) | Proposed | Rationale |
|---|---|---|---|
| Hero | 140/80 | 160/120 | Let the thesis breathe |
| Friction | 80/80 | 80/96 | More exit space |
| Engine Diagram | 64/64 | 96/96 | Room for the morph |
| Engine Proof | 80/80 | 64/80 | Tight entry, follows engine |
| Capabilities | 80/80 | 96/96 | Restore designed spacing |
| Positioning | 80/64 | 100vh centered | Full viewport climax |
| CTA | 80/48 | 120/160 | Confident exit |

---

## 2. Signature Moment: Engine Diagram → 3D Morph

The four flat HTML pipeline boxes transform into the four 3D octahedron nodes in real-time as the user scrolls.

### Scroll Choreography

| Scroll Range | Act | HTML | 3D |
|---|---|---|---|
| 0.28–0.35 | **Reveal** | Pipeline boxes fade in sequentially (L→R, 150ms stagger) | Grid brightens 4% → 8% |
| 0.35–0.45 | **Morph** | Boxes fade out: opacity 1→0, scale 1→0.95, translateY 0→-8px | Octahedrons materialize at HTML box positions, float forward (z-axis), spread to 3D formation. Lines draw progressively. |
| 0.45–0.55 | **Prove** | Engine Proof panels enter from right | Assembled engine recedes (z-2→z-5), becomes background. Nodes pulse accent color. |

### Position Synchronization

HTML nodes report viewport positions to a shared store. 3D nodes read screen coords and unproject to world space via camera.

```
HTMLDiagramNode (getBoundingClientRect)
  → shared store (zustand or context)
    → 3D EngineNodes reads screen coords
      → unproject to 3D world space
```

### Crossfade Mechanics

- HTML box at 50% opacity when 3D node reaches 50% opacity — single-object illusion
- Connection lines draw using dashArray + dashOffset animation, L→R, 100ms stagger

### New Component

- `useNodePositions` — hook/store tracking HTML node bounding rects, exposing to 3D scene

### Graceful Degradation

- **Low tier (mobile):** No morph. HTML diagram stays as-is with current fade-in.
- **Medium tier:** Morph plays, simpler geometry (octahedron subdiv 0), no line draw animation.
- **High tier:** Full morph with line draw, accent pulse, grid brightening.

### Constraints

- No camera movement. Objects move, not viewport.
- No particle effects, bloom, or postprocessing.
- No sound.

---

## 3. Motion System

Replace the uniform `opacity: 0, y: 20` pattern with per-section motion signatures.

### Per-Section Motion

| Section | Element | Animation | Duration | Special |
|---|---|---|---|---|
| Hero | H1 | `opacity: 0→1` (no movement) | 800ms | Slowest on page. Permanence. |
| Hero | Subhead | `opacity: 0→1` (fade only) | 500ms, 400ms delay | |
| Hero | CTAs | `opacity: 0, y: 12` → visible | 450ms, 550ms delay | Keep current |
| Friction | H3 lines | `opacity: 0, x: -40` → visible | 500ms, 200ms stagger | Horizontal. Confrontational. |
| Friction | SVG viz | `opacity: 0, scale: 0.95` → visible | 800ms, 300ms delay | Grows in |
| Engine | Pipeline | Scroll-driven | Continuous | Signature morph |
| Proof | Panels | `opacity: 0, x: 60` → visible | 500ms, 150ms stagger | Enter from right |
| Proof | Score | Count-up 0→78.4 | 1200ms | `[0.16, 1, 0.3, 1]` easing |
| Proof | Bars | Width 0%→target | 800ms, 200ms delay | Data viz entry |
| Capabilities | Left cards | `opacity: 0, x: -30` → visible | 500ms, 120ms stagger | From their grid side |
| Capabilities | Right cards | `opacity: 0, x: 30` → visible | 500ms, 120ms stagger | From their grid side |
| Positioning | H2 | `opacity: 0→1` (no movement) | **1200ms** | Absolute stillness. Climax. |
| Positioning | Subtext | `opacity: 0→1` | 600ms, 800ms delay | After H2 settles |
| CTA | Block | `opacity: 0, y: 12` → visible | 500ms | Quick, actionable |

### Easing

- Default: `[0.22, 1, 0.36, 1]` (unchanged)
- Data animations (count-up, bars): `[0.16, 1, 0.3, 1]`

---

## 4. Layout Changes

### Hero

- Add `lg:mt-[20px]` to headline — slightly below mathematical center
- Remove `max-w-[640px]` from subhead — let it run full 8 columns

### Friction

- Show SVG viz on tablet: `hidden md:block md:col-start-5 md:col-span-4`
- Increase scatter point radii by 1.5x, line strokeWidth to 0.8
- Increase accent point opacity from 20-25% to 35%

### Engine Diagram

- Section label: `mb-10` → `mb-16`
- Node boxes: `w-16 h-16` → `w-20 h-20`
- Remove Unicode icons (`◈ △ ⬡ ◉`) — replace with simple monoline SVG icons or remove entirely
- Remove tablet step numbers (redundant with sequential layout)

### Engine Proof

- Left column: `lg:col-span-5` → `lg:col-span-4`
- Right column: `lg:col-start-7 lg:col-span-6` → `lg:col-start-6 lg:col-span-7`

### Positioning

- Remove grid. Full-screen centered layout:
  ```
  min-h-screen flex items-center justify-center
  text-center max-w-[800px] px-[8vw]
  ```
- Only center-aligned section on the page (contrast creates emphasis)

### CTA

- Top padding: 80px → 120px

---

## 5. WebGL Intensification

| Element | Current | Target | Rationale |
|---|---|---|---|
| Ambient grid opacity | 4% | 8% baseline, 12% during engine section | Should be felt, not invisible |
| Capability card 3D planes | 6% opacity | 15% opacity + 0.5px accent border at 20% via `<Edges>` | Register as cards, not ghosts |
| Engine node material | `opacity: 0.85`, no emissive | Add `emissive={ACCENT_COLOR}`, `emissiveIntensity={0.3}` | Subtle glow in dark mode |

---

## 6. Psychological Refinements

### Data Credibility

- Engine Proof panels: If real scores available, use them. If not, change ticker label to "Sample Output" and add methodology citation link below panels.
- Friction section: Add citation `"* Barber & Odean, 2000; Dalbar QAIB, 2023"` below the behavioral finance claim.

### Nav CTA

- Change nav CTA from "Explore the Engine" to "Dashboard" or "Sign In" — avoid duplicate CTA labels visible simultaneously with hero.

---

## 7. Removals

| Element | Reason |
|---|---|
| "Institutional-grade analytics for serious retail investors" | Defensive positioning |
| "No credit card. No commitment." | Freemium SaaS language |
| Unicode diagram icons (`◈ △ ⬡ ◉`) | Placeholder aesthetic |
| Tablet step numbers in engine diagram | Visual clutter |

---

## 8. Unchanged Elements

- Color system (all tokens, light/dark modes)
- Font choices (Inter Tight + Geist Mono)
- Quality tier gating logic
- `frameloop="demand"`
- DPR capping at 1.5
- InstancedMesh batching
- Performance budget
- ButtonPrimary / ButtonSecondary styling
- Footer structure

---

## 9. Component Impact Summary

| Component | Change Level | Description |
|---|---|---|
| `hero-section.tsx` | Moderate | Copy, padding, motion, remove max-width |
| `friction-section.tsx` | Moderate | Horizontal motion, SVG visibility, citation, scatter sizing |
| `engine-diagram.tsx` | **Major** | Scroll-driven morph, position refs, fade-out logic, icon removal |
| `engine-proof.tsx` | Moderate | Panel entry direction, count-up score, animated bars, column widths |
| `capabilities-section.tsx` | Minor | Alternating L/R motion |
| `investor-positioning.tsx` | **Major** | Full-screen centered layout, 1200ms fade |
| `final-cta.tsx` | Minor | Copy change, padding |
| `nav-minimal.tsx` | Minor | CTA label change |
| `engine-nodes.tsx` | **Major** | Read HTML positions, start at HTML coords, lerp to 3D |
| `connection-lines.tsx` | Moderate | Progressive draw animation |
| `ambient-grid.tsx` | Minor | Opacity increase, scroll-driven brightening |
| `capability-cards-3d.tsx` | Minor | Opacity increase, add Edges |
| `scene-canvas.tsx` | Minor | Scroll range adjustments |
| `useNodePositions` (new) | **New** | Shared store for HTML→3D position sync |

**Total: 13 modified components, 1 new hook. 0 new dependencies.**
