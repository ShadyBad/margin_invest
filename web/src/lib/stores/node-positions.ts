import { create } from "zustand"

export interface NodeRect {
  x: number
  y: number
  width: number
  height: number
}

interface NodePositionsState {
  positions: Record<string, NodeRect>
  setPosition: (id: string, rect: NodeRect) => void
  clear: () => void
}

export const useNodePositions = create<NodePositionsState>((set) => ({
  positions: {},
  setPosition: (id, rect) =>
    set((state) => ({
      positions: { ...state.positions, [id]: rect },
    })),
  clear: () => set({ positions: {} }),
}))
