import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofHeatmap, interpretCorrelation } from "../proof-heatmap"

describe("interpretCorrelation", () => {
  it("returns diversification message for low correlations", () => {
    const matrix = [
      [1.0, 0.1, 0.2],
      [0.1, 1.0, 0.15],
      [0.2, 0.15, 1.0],
    ]
    const result = interpretCorrelation(matrix)
    expect(result).toMatch(/strong diversification/)
  })

  it("returns clustering warning for high correlations", () => {
    const matrix = [
      [1.0, 0.85, 0.9],
      [0.85, 1.0, 0.82],
      [0.9, 0.82, 1.0],
    ]
    const result = interpretCorrelation(matrix)
    expect(result).toMatch(/clustering/)
  })

  it("returns empty string for empty matrix", () => {
    const result = interpretCorrelation([])
    expect(result).toBe("")
  })
})

describe("ProofHeatmap", () => {
  beforeEach(() => mockFetch.mockReset())

  it("renders correlation grid", () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        tickers: ["A", "B", "C"],
        matrix: [
          [1.0, 0.1, 0.2],
          [0.1, 1.0, 0.15],
          [0.2, 0.15, 1.0],
        ],
      }),
    })
    render(<ProofHeatmap />)
    expect(screen.getByTestId("correlation-grid")).toBeInTheDocument()
  })

  it("renders interpretation line with fallback data", () => {
    // With fallback data (has a mix of low and moderate correlations)
    // Use a resolved but not-ok response to avoid unhandled rejection
    mockFetch.mockResolvedValue({ ok: false })
    render(<ProofHeatmap />)
    // Fallback matrix has some low correlations, so should show diversification
    expect(screen.getByText(/strong diversification/i)).toBeInTheDocument()
  })

  it("renders correlation caveat footnote", () => {
    mockFetch.mockResolvedValue({ ok: false })
    render(<ProofHeatmap />)
    expect(screen.getByText(/correlations shift during market stress/i)).toBeInTheDocument()
  })
})
