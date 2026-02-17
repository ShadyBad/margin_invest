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
