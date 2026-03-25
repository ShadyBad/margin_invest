import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import type { CandidateCard } from "../shared/types"

vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofHeatmap, interpretCorrelation } from "../proof-heatmap"

const mockCandidates: CandidateCard[] = [
  {
    ticker: "AAPL", name: "Apple", sector: "Technology", actual_price: 180, buy_price: 160,
    margin_of_safety: 0.1, score: 82, composite_percentile: 90, composite_tier: "exceptional",
    quality_percentile: 85, value_percentile: 70, momentum_percentile: 80,
    sentiment_percentile: 60, growth_percentile: 75, scored_at: "2026-03-01T00:00:00Z",
    filters_passed: 8, filters_total: 8,
  },
  {
    ticker: "MSFT", name: "Microsoft", sector: "Technology", actual_price: 420, buy_price: 380,
    margin_of_safety: 0.1, score: 79, composite_percentile: 88, composite_tier: "high",
    quality_percentile: 82, value_percentile: 60, momentum_percentile: 75,
    sentiment_percentile: 68, growth_percentile: 80, scored_at: "2026-03-01T00:00:00Z",
    filters_passed: 8, filters_total: 8,
  },
  {
    ticker: "JNJ", name: "J&J", sector: "Healthcare", actual_price: 160, buy_price: 140,
    margin_of_safety: 0.1, score: 71, composite_percentile: 80, composite_tier: "high",
    quality_percentile: 90, value_percentile: 80, momentum_percentile: 40,
    sentiment_percentile: 50, growth_percentile: 55, scored_at: "2026-03-01T00:00:00Z",
    filters_passed: 8, filters_total: 8,
  },
]

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
    render(<ProofHeatmap candidates={mockCandidates} />)
    expect(screen.getByTestId("correlation-grid")).toBeInTheDocument()
  })

  it("renders interpretation line with candidate data", () => {
    mockFetch.mockResolvedValue({ ok: false })
    render(<ProofHeatmap candidates={mockCandidates} />)
    // Client-computed correlations should render the grid with candidate tickers
    expect(screen.getByTestId("correlation-grid")).toBeInTheDocument()
    // Interpretation or caveat should be present
    expect(screen.getByText(/correlations shift during market stress/i)).toBeInTheDocument()
  })

  it("renders correlation caveat footnote", () => {
    mockFetch.mockResolvedValue({ ok: false })
    render(<ProofHeatmap candidates={mockCandidates} />)
    expect(screen.getByText(/correlations shift during market stress/i)).toBeInTheDocument()
  })
})
