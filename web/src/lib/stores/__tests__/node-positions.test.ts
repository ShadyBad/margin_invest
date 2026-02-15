import { describe, it, expect, beforeEach } from "vitest"
import { useNodePositions } from "../node-positions"

describe("useNodePositions store", () => {
  beforeEach(() => {
    useNodePositions.getState().clear()
  })

  it("starts with empty positions", () => {
    const { positions } = useNodePositions.getState()
    expect(Object.keys(positions)).toHaveLength(0)
  })

  it("sets a node position", () => {
    useNodePositions.getState().setPosition("node-0", { x: 100, y: 200, width: 80, height: 80 })
    const { positions } = useNodePositions.getState()
    expect(positions["node-0"]).toEqual({ x: 100, y: 200, width: 80, height: 80 })
  })

  it("sets multiple node positions independently", () => {
    const { setPosition } = useNodePositions.getState()
    setPosition("node-0", { x: 100, y: 200, width: 80, height: 80 })
    setPosition("node-1", { x: 300, y: 200, width: 80, height: 80 })
    const { positions } = useNodePositions.getState()
    expect(Object.keys(positions)).toHaveLength(2)
    expect(positions["node-1"]?.x).toBe(300)
  })

  it("clears all positions", () => {
    useNodePositions.getState().setPosition("node-0", { x: 0, y: 0, width: 0, height: 0 })
    useNodePositions.getState().clear()
    expect(Object.keys(useNodePositions.getState().positions)).toHaveLength(0)
  })
})
