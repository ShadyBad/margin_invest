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
  { x: 80, y: 140 }, // H0: Data ingestion
  { x: 160, y: 80 }, // H1: Filtering
  { x: 260, y: 80 }, // H2: Scoring
  { x: 340, y: 140 }, // H3: Ranking
]

// --- Peripheral positions: 4 per hub, arced around each hub ---
const PERIPHERAL_OFFSETS: Vec2[][] = [
  // H0 cluster (left side)
  [
    { x: -35, y: -40 },
    { x: -45, y: 15 },
    { x: -20, y: 50 },
    { x: 25, y: -30 },
  ],
  // H1 cluster (upper-left)
  [
    { x: -30, y: -35 },
    { x: 15, y: -45 },
    { x: -40, y: 20 },
    { x: 30, y: 25 },
  ],
  // H2 cluster (upper-right)
  [
    { x: -25, y: -40 },
    { x: 35, y: -30 },
    { x: -35, y: 25 },
    { x: 20, y: 40 },
  ],
  // H3 cluster (right side)
  [
    { x: -30, y: -35 },
    { x: 30, y: -25 },
    { x: 40, y: 20 },
    { x: 15, y: 50 },
  ],
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
      chaosRadius: 3.5 + i * 0.4, // deterministic: 3.5, 3.9, 4.3, 4.7
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
        chaosRadius: 3 + pIdx * 0.15, // deterministic: 3.0, 3.15, 3.3, 3.45
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

  // Hub-to-hub connections (pipeline flow: 0->1->2->3)
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

  // False connections (3 -- cross-cluster noise that fades during transition)
  edges.push({ from: 5, to: 13, type: "false", isHubEdge: false }) // H0-periph to H2-periph
  edges.push({ from: 8, to: 18, type: "false", isHubEdge: false }) // H1-periph to H3-periph
  edges.push({ from: 11, to: 16, type: "false", isHubEdge: false }) // H1-periph to H3-periph

  return edges
}

let _cached: ConstellationData | null = null

export function getConstellationData(): ConstellationData {
  if (_cached) return _cached
  _cached = { nodes: buildNodes(), edges: buildEdges() }
  return _cached
}
