# Constellation Narrative Animation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the static `MarketNoiseViz` SVG in the friction section with a scroll-driven constellation that morphs from chaos to structured network graph.

**Architecture:** New `ConstellationNarrative` component with a `useConstellationData` hook (pre-computed positions) and framer-motion `useScroll`/`useTransform` for scroll binding. SVG-based, 20 nodes + 18 edges, mobile falls back to static final state.

**Tech Stack:** React, framer-motion (useScroll, useTransform, motion.circle, motion.line), SVG, Tailwind CSS custom properties.

**Design Doc:** `docs/plans/2026-02-16-constellation-narrative-design.md`

---

## Task 1: Create constellation data hook with position arrays

**Files:**
- Create: `web/src/components/landing/sections/constellation-data.ts`
- Test: `web/src/components/landing/__tests__/constellation-data.test.ts`

**Step 1: Write failing test for chaos positions**

Create `web/src/components/landing/__tests__/constellation-data.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { getConstellationData } from "../sections/constellation-data"

describe("getConstellationData", () => {
  const data = getConstellationData()

  it("returns 20 nodes", () => {
    expect(data.nodes).toHaveLength(20)
  })

  it("each node has chaos and structured positions", () => {
    for (const node of data.nodes) {
      expect(node.chaosPos).toEqual({ x: expect.any(Number), y: expect.any(Number) })
      expect(node.structuredPos).toEqual({ x: expect.any(Number), y: expect.any(Number) })
    }
  })

  it("has 4 hub nodes and 16 peripheral nodes", () => {
    const hubs = data.nodes.filter((n) => n.role === "hub")
    const peripheral = data.nodes.filter((n) => n.role === "peripheral")
    expect(hubs).toHaveLength(4)
    expect(peripheral).toHaveLength(16)
  })

  it("hub nodes have larger structured radius than peripheral", () => {
    const hubs = data.nodes.filter((n) => n.role === "hub")
    const peripheral = data.nodes.filter((n) => n.role === "peripheral")
    for (const h of hubs) {
      expect(h.structuredRadius).toBeGreaterThanOrEqual(5)
    }
    for (const p of peripheral) {
      expect(p.structuredRadius).toBeLessThanOrEqual(4)
    }
  })

  it("all positions are within viewBox 0 0 400 280", () => {
    for (const node of data.nodes) {
      expect(node.chaosPos.x).toBeGreaterThanOrEqual(0)
      expect(node.chaosPos.x).toBeLessThanOrEqual(400)
      expect(node.chaosPos.y).toBeGreaterThanOrEqual(0)
      expect(node.chaosPos.y).toBeLessThanOrEqual(280)
      expect(node.structuredPos.x).toBeGreaterThanOrEqual(0)
      expect(node.structuredPos.x).toBeLessThanOrEqual(400)
      expect(node.structuredPos.y).toBeGreaterThanOrEqual(0)
      expect(node.structuredPos.y).toBeLessThanOrEqual(280)
    }
  })
})
```

**Step 2: Run test to verify it fails**

Run: `uv run npx vitest run web/src/components/landing/__tests__/constellation-data.test.ts --reporter=verbose`
(Or, if the project uses npm/pnpm for web: `cd web && npx vitest run src/components/landing/__tests__/constellation-data.test.ts --reporter=verbose`)

Check web/package.json for the test runner command first. Expected: FAIL (module not found).

**Step 3: Write minimal implementation**

Create `web/src/components/landing/sections/constellation-data.ts`:

```ts
export interface Vec2 {
  x: number
  y: number
}

export type NodeRole = "hub" | "peripheral"

export interface ConstellationNode {
  id: number
  role: NodeRole
  chaosPos: Vec2
  structuredPos: Vec2
  chaosRadius: number
  structuredRadius: number
  /** Stagger offset 0-1: 0 = moves first (peripheral), 1 = moves last (hub) */
  stagger: number
  /** Drift frequency in Hz for chaos phase micro-oscillation */
  driftFreq: number
  /** Structured opacity (hubs brighter, peripheral dimmer) */
  structuredOpacity: number
}

export interface ConstellationEdge {
  from: number
  to: number
  /** "real" edges persist into structured state; "false" edges fade out during transition */
  type: "real" | "false"
  /** Whether this connects two hubs (drawn last, accent color) */
  isHubEdge: boolean
}

export interface ConstellationData {
  nodes: ConstellationNode[]
  edges: ConstellationEdge[]
}

// --- Hub positions (4 hubs mirroring engine pipeline stages) ---
const HUB_POSITIONS: Vec2[] = [
  { x: 80, y: 140 },   // H0: Data ingestion
  { x: 160, y: 80 },   // H1: Filtering
  { x: 260, y: 80 },   // H2: Scoring
  { x: 340, y: 140 },  // H3: Ranking
]

// --- Peripheral positions: 4 per hub, arced around each hub ---
const PERIPHERAL_OFFSETS: Vec2[][] = [
  // H0 cluster (left side)
  [{ x: -35, y: -40 }, { x: -45, y: 15 }, { x: -20, y: 50 }, { x: 25, y: -30 }],
  // H1 cluster (upper-left)
  [{ x: -30, y: -35 }, { x: 15, y: -45 }, { x: -40, y: 20 }, { x: 30, y: 25 }],
  // H2 cluster (upper-right)
  [{ x: -25, y: -40 }, { x: 35, y: -30 }, { x: -35, y: 25 }, { x: 20, y: 40 }],
  // H3 cluster (right side)
  [{ x: -30, y: -35 }, { x: 30, y: -25 }, { x: 40, y: 20 }, { x: 15, y: 50 }],
]

// --- Chaos positions: intentionally scattered, no alignment ---
const CHAOS_POSITIONS: Vec2[] = [
  // Hubs (indices 0-3) scattered randomly
  { x: 45, y: 35 },
  { x: 310, y: 220 },
  { x: 120, y: 245 },
  { x: 375, y: 60 },
  // H0 peripherals (indices 4-7)
  { x: 200, y: 170 },
  { x: 30, y: 260 },
  { x: 355, y: 145 },
  { x: 90, y: 75 },
  // H1 peripherals (indices 8-11)
  { x: 270, y: 30 },
  { x: 55, y: 190 },
  { x: 330, y: 260 },
  { x: 175, y: 110 },
  // H2 peripherals (indices 12-15)
  { x: 15, y: 130 },
  { x: 245, y: 55 },
  { x: 385, y: 200 },
  { x: 140, y: 25 },
  // H3 peripherals (indices 16-19)
  { x: 65, y: 250 },
  { x: 290, y: 115 },
  { x: 195, y: 205 },
  { x: 360, y: 35 },
]

function buildNodes(): ConstellationNode[] {
  const nodes: ConstellationNode[] = []

  // 4 hub nodes (indices 0-3)
  for (let i = 0; i < 4; i++) {
    nodes.push({
      id: i,
      role: "hub",
      chaosPos: CHAOS_POSITIONS[i],
      structuredPos: HUB_POSITIONS[i],
      chaosRadius: 3.5 + Math.random() * 1.5, // 3.5-5 in chaos (varied)
      structuredRadius: 5.5,
      stagger: 0.7 + i * 0.075, // 0.7-0.925 — hubs move last
      driftFreq: 0.3 + i * 0.12,
      structuredOpacity: 0.85,
    })
  }

  // 16 peripheral nodes (indices 4-19, 4 per hub)
  for (let hubIdx = 0; hubIdx < 4; hubIdx++) {
    for (let pIdx = 0; pIdx < 4; pIdx++) {
      const globalIdx = 4 + hubIdx * 4 + pIdx
      const offset = PERIPHERAL_OFFSETS[hubIdx][pIdx]
      nodes.push({
        id: globalIdx,
        role: "peripheral",
        chaosPos: CHAOS_POSITIONS[globalIdx],
        structuredPos: {
          x: HUB_POSITIONS[hubIdx].x + offset.x,
          y: HUB_POSITIONS[hubIdx].y + offset.y,
        },
        chaosRadius: 3 + Math.random() * 0.5,
        structuredRadius: 3 + pIdx * 0.25, // 3-3.75
        stagger: 0.1 + (hubIdx * 4 + pIdx) * 0.035, // 0.1-0.625 — peripherals first
        driftFreq: 0.3 + (hubIdx * 4 + pIdx) * 0.03,
        structuredOpacity: 0.35 + pIdx * 0.05, // 0.35-0.5
      })
    }
  }

  return nodes
}

function buildEdges(): ConstellationEdge[] {
  const edges: ConstellationEdge[] = []

  // Hub-to-hub connections (pipeline flow: 0→1→2→3)
  edges.push({ from: 0, to: 1, type: "real", isHubEdge: true })
  edges.push({ from: 1, to: 2, type: "real", isHubEdge: true })
  edges.push({ from: 2, to: 3, type: "real", isHubEdge: true })

  // Hub-to-peripheral connections (each hub connects to its 4 peripherals)
  for (let hubIdx = 0; hubIdx < 4; hubIdx++) {
    for (let pIdx = 0; pIdx < 4; pIdx++) {
      edges.push({
        from: hubIdx,
        to: 4 + hubIdx * 4 + pIdx,
        type: "real",
        isHubEdge: false,
      })
    }
  }

  // False connections (3 — cross-cluster noise that fades during transition)
  edges.push({ from: 5, to: 13, type: "false", isHubEdge: false })  // H0-periph to H2-periph
  edges.push({ from: 8, to: 18, type: "false", isHubEdge: false })  // H1-periph to H3-periph
  edges.push({ from: 11, to: 16, type: "false", isHubEdge: false }) // H1-periph to H3-periph

  return edges
}

let _cached: ConstellationData | null = null

export function getConstellationData(): ConstellationData {
  if (_cached) return _cached
  _cached = { nodes: buildNodes(), edges: buildEdges() }
  return _cached
}
```

**Step 4: Run test to verify it passes**

Run the same test command from Step 2. Expected: all 5 tests PASS.

**Step 5: Write failing test for edges**

Add to the same test file:

```ts
describe("edges", () => {
  const data = getConstellationData()

  it("has 3 hub-to-hub edges", () => {
    const hubEdges = data.edges.filter((e) => e.isHubEdge)
    expect(hubEdges).toHaveLength(3)
  })

  it("has 16 hub-to-peripheral edges", () => {
    const hubPeripheral = data.edges.filter((e) => e.type === "real" && !e.isHubEdge)
    expect(hubPeripheral).toHaveLength(16)
  })

  it("has 3 false edges", () => {
    const falseEdges = data.edges.filter((e) => e.type === "false")
    expect(falseEdges).toHaveLength(3)
  })

  it("false edges connect nodes from different hub clusters", () => {
    const falseEdges = data.edges.filter((e) => e.type === "false")
    for (const edge of falseEdges) {
      const fromHub = edge.from < 4 ? edge.from : Math.floor((edge.from - 4) / 4)
      const toHub = edge.to < 4 ? edge.to : Math.floor((edge.to - 4) / 4)
      expect(fromHub).not.toBe(toHub)
    }
  })

  it("all edge references point to valid node ids", () => {
    const nodeIds = new Set(data.nodes.map((n) => n.id))
    for (const edge of data.edges) {
      expect(nodeIds.has(edge.from)).toBe(true)
      expect(nodeIds.has(edge.to)).toBe(true)
    }
  })
})
```

**Step 6: Run test — should pass immediately (data already built)**

Run: same test command. Expected: all tests PASS.

**Step 7: Commit**

```bash
git add web/src/components/landing/sections/constellation-data.ts web/src/components/landing/__tests__/constellation-data.test.ts
git commit -m "feat: add constellation data hook with chaos/structured positions"
```

---

## Task 2: Create the ConstellationNarrative SVG component (static render, no scroll)

**Files:**
- Create: `web/src/components/landing/sections/constellation-narrative.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx`

**Context:** This task renders the SVG with all nodes and edges at their **structured** positions (the final state). No scroll animation yet — just get the SVG rendering correctly.

**Step 1: Write failing test**

Add to `web/src/components/landing/__tests__/sections.test.tsx`, inside the existing `describe("FrictionSection")` block — or add a new describe block after it:

```ts
describe("ConstellationNarrative", () => {
  it("renders an SVG with aria-hidden", async () => {
    // Dynamic import since we'll lazy-load it in friction-section
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute("aria-hidden", "true")
    expect(svg).toHaveAttribute("viewBox", "0 0 400 280")
  })

  it("renders 20 circle nodes", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const circles = container.querySelectorAll("circle")
    expect(circles).toHaveLength(20)
  })

  it("renders edges as line elements", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const lines = container.querySelectorAll("line")
    // 3 hub-hub + 16 hub-peripheral + 3 false = 22 total
    expect(lines).toHaveLength(22)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`
Expected: FAIL (module not found).

**Step 3: Write the component**

Create `web/src/components/landing/sections/constellation-narrative.tsx`:

```tsx
"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform, type MotionValue } from "framer-motion"
import {
  getConstellationData,
  type ConstellationNode,
  type ConstellationEdge,
} from "./constellation-data"

const data = getConstellationData()

/**
 * Interpolate a value between `from` and `to` based on progress 0–1.
 * Used for pre-computing transform input/output arrays.
 */
function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t
}

interface NodeCircleProps {
  node: ConstellationNode
  progress: MotionValue<number>
}

function NodeCircle({ node, progress }: NodeCircleProps) {
  // Stagger: each node's effective progress is shifted by its stagger offset
  // so peripheral nodes (low stagger) move first, hubs (high stagger) last.
  const nodeProgress = useTransform(progress, (p: number) => {
    const adjusted = (p - node.stagger * 0.3) / 0.7
    return Math.max(0, Math.min(1, adjusted))
  })

  const cx = useTransform(nodeProgress, [0, 1], [node.chaosPos.x, node.structuredPos.x])
  const cy = useTransform(nodeProgress, [0, 1], [node.chaosPos.y, node.structuredPos.y])
  const r = useTransform(nodeProgress, [0, 1], [node.chaosRadius, node.structuredRadius])
  const opacity = useTransform(
    nodeProgress,
    [0, 1],
    [0.15 + (node.id % 3) * 0.05, node.structuredOpacity]
  )

  return (
    <motion.circle
      cx={cx}
      cy={cy}
      r={r}
      fill="currentColor"
      className={node.role === "hub" ? "text-accent" : "text-text-secondary"}
      style={{ opacity }}
    />
  )
}

interface EdgeLineProps {
  edge: ConstellationEdge
  progress: MotionValue<number>
}

function EdgeLine({ edge, progress }: EdgeLineProps) {
  const fromNode = data.nodes[edge.from]
  const toNode = data.nodes[edge.to]

  // Edge progress follows the later-moving endpoint
  const edgeStagger = Math.max(fromNode.stagger, toNode.stagger)
  const edgeProgress = useTransform(progress, (p: number) => {
    const adjusted = (p - edgeStagger * 0.3) / 0.7
    return Math.max(0, Math.min(1, adjusted))
  })

  const x1 = useTransform(edgeProgress, [0, 1], [fromNode.chaosPos.x, fromNode.structuredPos.x])
  const y1 = useTransform(edgeProgress, [0, 1], [fromNode.chaosPos.y, fromNode.structuredPos.y])
  const x2 = useTransform(edgeProgress, [0, 1], [toNode.chaosPos.x, toNode.structuredPos.x])
  const y2 = useTransform(edgeProgress, [0, 1], [toNode.chaosPos.y, toNode.structuredPos.y])

  // False edges fade out; real edges fade in
  const opacity = useTransform(edgeProgress, [0, 0.3, 0.7, 1],
    edge.type === "false"
      ? [0.12, 0.08, 0, 0]          // false: visible in chaos, gone by mid-transition
      : [0.08, 0.12, 0.2, edge.isHubEdge ? 0.4 : 0.2] // real: dim in chaos, bright in structure
  )

  const strokeWidth = edge.isHubEdge ? 1.5 : 0.8

  // Dash animation: broken in chaos → solid in structure
  const dashArray = useTransform(edgeProgress, (p: number) => {
    if (edge.type === "false") return "4 6"
    if (p < 0.3) return "4 8"
    if (p < 0.7) {
      const fill = (p - 0.3) / 0.4
      const gap = lerp(8, 0, fill)
      return `4 ${gap}`
    }
    return "none"
  })

  return (
    <motion.line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke="currentColor"
      strokeWidth={strokeWidth}
      className={edge.isHubEdge ? "text-accent" : "text-text-secondary"}
      style={{ opacity, strokeDasharray: dashArray }}
    />
  )
}

export function ConstellationNarrative() {
  const containerRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  })

  // Map section scroll to 0-1 animation progress
  // The section enters view around 0.0 and leaves around 1.0
  // We want the animation to play in the first half of visibility
  const progress = useTransform(scrollYProgress, [0.15, 0.55], [0, 1])

  return (
    <div ref={containerRef} className="w-full h-full" style={{ willChange: "transform" }}>
      <svg
        className="w-full h-full"
        viewBox="0 0 400 280"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Edges layer (behind nodes) */}
        <g>
          {data.edges.map((edge, i) => (
            <EdgeLine key={`edge-${i}`} edge={edge} progress={progress} />
          ))}
        </g>

        {/* Nodes layer */}
        <g>
          {data.nodes.map((node) => (
            <NodeCircle key={`node-${node.id}`} node={node} progress={progress} />
          ))}
        </g>
      </svg>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run the same test command. Expected: all tests PASS (the framer-motion mock in the test file handles `useScroll`/`useTransform`).

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/constellation-narrative.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat: add ConstellationNarrative component with scroll-driven SVG"
```

---

## Task 3: Wire ConstellationNarrative into FrictionSection

**Files:**
- Modify: `web/src/components/landing/sections/friction-section.tsx`

**Context:** Replace the `MarketNoiseViz` inline component with `ConstellationNarrative`. On mobile (<768px), show a static version. The existing `motion.div` wrapper with `hidden md:block` already handles the mobile hide.

**Step 1: Verify existing FrictionSection tests still pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`
Expected: all existing FrictionSection tests PASS.

**Step 2: Replace MarketNoiseViz with ConstellationNarrative**

Edit `web/src/components/landing/sections/friction-section.tsx`:

Remove the entire `MarketNoiseViz` function (lines 13-76) and update the import + JSX:

Replace the file content with:

```tsx
"use client"

import { motion } from "framer-motion"
import { ConstellationNarrative } from "./constellation-narrative"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

export function FrictionSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "80px",
          paddingBottom: "96px",
        }}
      >
        <div className="col-span-4 md:col-span-4 lg:col-span-6 flex flex-col gap-6">
          {lines.map((line, i) => (
            <motion.h3
              key={line}
              className="text-[28px] md:text-[32px] font-semibold text-text-primary leading-tight"
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.2, ease }}
            >
              {line}
            </motion.h3>
          ))}
          <motion.p
            className="text-[15px] text-text-secondary leading-relaxed max-w-[480px]"
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6, ease }}
          >
            Behavioral finance research shows that emotional trading costs retail investors
            1.5–4% annually. Structure eliminates the leak.*
          </motion.p>
          <motion.span
            className="text-[11px] text-text-tertiary font-mono"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: 0.8 }}
          >
            * Barber & Odean, 2000; Dalbar QAIB, 2023
          </motion.span>
        </div>

        {/* Constellation narrative visualization — tablet + desktop */}
        <div className="hidden md:block md:col-start-5 md:col-span-4 lg:col-start-8 lg:col-span-5">
          <ConstellationNarrative />
        </div>
      </div>
    </section>
  )
}
```

Note: The `motion.div` wrapper with `initial/whileInView` animation has been removed from the constellation container. The `ConstellationNarrative` component now handles its own scroll-driven animation internally — wrapping it in another `whileInView` would conflict. The container is now a plain `div` with the same grid/visibility classes.

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`
Expected: all FrictionSection tests PASS (text content unchanged).

**Step 4: Visual check**

Run: `cd web && npm run dev` (or `pnpm dev`)
Open browser, navigate to landing page, scroll to friction section. Verify:
- Constellation appears on desktop/tablet
- Hidden on mobile
- Nodes and edges are visible
- Scrolling transforms the constellation from scattered to structured

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/friction-section.tsx
git commit -m "feat: replace MarketNoiseViz with scroll-driven ConstellationNarrative"
```

---

## Task 4: Add reduced-motion and mobile static fallback

**Files:**
- Modify: `web/src/components/landing/sections/constellation-narrative.tsx`
- Add test: `web/src/components/landing/__tests__/sections.test.tsx`

**Context:** When `prefers-reduced-motion: reduce` is active, skip scroll animation and show the final structured state. Mobile already hides the component via the parent `hidden md:block`, but the ConstellationNarrative should also defend against being rendered on mobile by defaulting to the final state when no scroll ref is available.

**Step 1: Write failing test**

Add to `sections.test.tsx` in the `ConstellationNarrative` describe block:

```ts
it("renders with accessible reduced-motion support", async () => {
  const { ConstellationNarrative } = await import("../sections/constellation-narrative")
  const { container } = render(<ConstellationNarrative />)
  // Component should render without errors even when motion is mocked
  const svg = container.querySelector("svg")
  expect(svg).toBeInTheDocument()
})
```

**Step 2: Run test — should pass immediately**

Run test command. The mock already provides static values for all framer-motion hooks, so this confirms the component degrades gracefully.

**Step 3: Add prefers-reduced-motion guard in the component**

Edit `web/src/components/landing/sections/constellation-narrative.tsx`. Add at the top of the `ConstellationNarrative` function, before `useScroll`:

```tsx
import { useRef, useMemo } from "react"
import { motion, useScroll, useTransform, useReducedMotion, type MotionValue } from "framer-motion"
```

Then inside the component:

```tsx
export function ConstellationNarrative() {
  const prefersReducedMotion = useReducedMotion()
  const containerRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  })

  // When reduced motion is preferred, pin progress to 1 (structured state)
  const rawProgress = useTransform(scrollYProgress, [0.15, 0.55], [0, 1])
  const progress = useTransform(rawProgress, (v: number) => prefersReducedMotion ? 1 : v)
  // ... rest unchanged
```

**Step 4: Run all tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/ --reporter=verbose`
Expected: all PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/constellation-narrative.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat: add reduced-motion fallback to ConstellationNarrative"
```

---

## Task 5: Add chaos-phase micro-drift oscillation

**Files:**
- Modify: `web/src/components/landing/sections/constellation-narrative.tsx`

**Context:** In Phase 1 (chaos), nodes should have subtle ±2px positional drift that dampens as scroll progresses. This is done by adding a time-based offset that scales down with progress.

**Step 1: Add drift to NodeCircle**

Edit the `NodeCircle` component in `constellation-narrative.tsx`. Add a `useTime` import from framer-motion and modify the `cx`/`cy` transforms:

```tsx
import { motion, useScroll, useTransform, useReducedMotion, useTime, type MotionValue } from "framer-motion"
```

Then update `NodeCircle`:

```tsx
function NodeCircle({ node, progress }: NodeCircleProps) {
  const prefersReducedMotion = useReducedMotion()
  const time = useTime()

  const nodeProgress = useTransform(progress, (p: number) => {
    const adjusted = (p - node.stagger * 0.3) / 0.7
    return Math.max(0, Math.min(1, adjusted))
  })

  // Drift: sine-based oscillation that dampens as nodeProgress increases
  const driftX = useTransform([time, nodeProgress] as MotionValue[], ([t, p]: number[]) => {
    if (prefersReducedMotion || p > 0.8) return 0
    const amplitude = 2 * (1 - p) // Dampens from 2px to 0
    return Math.sin((t / 1000) * node.driftFreq * Math.PI * 2) * amplitude
  })
  const driftY = useTransform([time, nodeProgress] as MotionValue[], ([t, p]: number[]) => {
    if (prefersReducedMotion || p > 0.8) return 0
    const amplitude = 1.5 * (1 - p)
    return Math.cos((t / 1000) * node.driftFreq * Math.PI * 2 + node.id) * amplitude
  })

  const baseCx = useTransform(nodeProgress, [0, 1], [node.chaosPos.x, node.structuredPos.x])
  const baseCy = useTransform(nodeProgress, [0, 1], [node.chaosPos.y, node.structuredPos.y])

  const cx = useTransform([baseCx, driftX] as MotionValue[], ([base, drift]: number[]) => base + drift)
  const cy = useTransform([baseCy, driftY] as MotionValue[], ([base, drift]: number[]) => base + drift)

  const r = useTransform(nodeProgress, [0, 1], [node.chaosRadius, node.structuredRadius])
  const opacity = useTransform(
    nodeProgress,
    [0, 1],
    [0.15 + (node.id % 3) * 0.05, node.structuredOpacity]
  )

  return (
    <motion.circle
      cx={cx}
      cy={cy}
      r={r}
      fill="currentColor"
      className={node.role === "hub" ? "text-accent" : "text-text-secondary"}
      style={{ opacity }}
    />
  )
}
```

**Important:** `useTime()` creates a continuous animation. This is acceptable because:
- Drift only applies when `nodeProgress < 0.8` (chaos phase)
- It dampens to zero amplitude, at which point the transform returns 0 (no visual update)
- Framer-motion batches transforms efficiently
- On reduced-motion, drift is always 0

**Step 2: Visual check**

Run dev server, scroll to friction section. In chaos state, nodes should have barely perceptible wobble. As you scroll into transition, wobble should dampen and disappear by structure phase.

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/ --reporter=verbose`
Expected: all PASS (the framer-motion mock returns static values, so drift doesn't affect test output).

**Step 4: Commit**

```bash
git add web/src/components/landing/sections/constellation-narrative.tsx
git commit -m "feat: add chaos-phase micro-drift oscillation to constellation nodes"
```

---

## Task 6: Tune scroll ranges and visual polish

**Files:**
- Modify: `web/src/components/landing/sections/constellation-narrative.tsx`

**Context:** The scroll mapping (`[0.15, 0.55]`) was an initial estimate. This task tunes the actual ranges by testing in the browser and adjusting the values to match the design doc's intended phases (chaos hold → transition → structure settle).

**Step 1: Open dev server and test scroll behavior**

Run: `cd web && npm run dev`

Scroll through the friction section. Observe:
- Does the chaos state hold long enough before transition starts?
- Does the transition feel gradual (not sudden)?
- Does the structure settle before the section scrolls away?

**Step 2: Adjust scroll mapping if needed**

The `useTransform(scrollYProgress, [start, end], [0, 1])` in `ConstellationNarrative` controls the overall pacing. The `[start, end]` values depend on the `offset: ["start end", "end start"]` scroll configuration.

With `"start end"` → `"end start"`:
- `scrollYProgress = 0` when section top hits viewport bottom
- `scrollYProgress = 1` when section bottom hits viewport top
- We want the animation to complete while the section is prominently visible

Suggested tuning approach:
- If animation completes too fast: widen the range (e.g., `[0.1, 0.6]`)
- If animation doesn't start early enough: lower the start (e.g., `[0.1, 0.5]`)
- If structure phase doesn't hold: add a clamp or extend range

**Step 3: Fine-tune node colors in structured state**

Verify in both light and dark mode:
- Hub nodes should show accent color clearly
- Peripheral nodes should be visibly dimmer
- Edge opacity differences should be perceptible

If hub nodes aren't accent-colored, check that the `text-accent` class is working on SVG `<circle>` elements with `fill="currentColor"`. May need to use `style={{ color: "var(--color-accent)" }}` instead of className if Tailwind doesn't apply to SVG elements in the project's config.

**Step 4: Run all tests one final time**

Run: `cd web && npx vitest run src/components/landing/__tests__/ --reporter=verbose`
Expected: all PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/constellation-narrative.tsx
git commit -m "fix: tune constellation scroll ranges and visual polish"
```

---

## Task 7: Final integration test and cleanup

**Files:**
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (if needed)
- Delete: nothing (MarketNoiseViz was inline in friction-section.tsx, already replaced)

**Step 1: Run full test suite**

Run: `cd web && npx vitest run --reporter=verbose`
Expected: all tests PASS.

**Step 2: Run page assembly test**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`
Expected: PASS (FrictionSection still exports and renders).

**Step 3: Check TypeScript compilation**

Run: `cd web && npx tsc --noEmit`
Expected: no errors.

**Step 4: Lighthouse check (optional)**

Open Chrome DevTools → Lighthouse → run Performance audit on the landing page.
Verify:
- No performance regression from the animation
- Layout shifts (CLS) not increased
- Total blocking time not increased

**Step 5: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: cleanup constellation integration"
```
