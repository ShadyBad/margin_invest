import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { ResultsShowcaseSection } from "../results-showcase-section"
import type { HomepageData } from "../types"
import type { CandidateCard } from "../types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Corp",
    sector: "Technology",
    actual_price: 100,
    buy_price: 120,
    margin_of_safety: 0.167,
    score: 70,
    composite_percentile: 75,
    composite_tier: "high",
    quality_percentile: 80,
    value_percentile: 65,
    momentum_percentile: 72,
    sentiment_percentile: 60,
    growth_percentile: 68,
    scored_at: "2026-03-09T12:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

const mockCandidates: CandidateCard[] = [
  makeCandidate({ ticker: "AAPL", name: "Apple Inc.", score: 82.4, quality_percentile: 90, value_percentile: 70, momentum_percentile: 78 }),
  makeCandidate({ ticker: "MSFT", name: "Microsoft Corp.", score: 79.1, quality_percentile: 88, value_percentile: 60, momentum_percentile: 74 }),
  makeCandidate({ ticker: "JNJ", name: "Johnson & Johnson", score: 75.6, quality_percentile: 76, value_percentile: 82, momentum_percentile: 65 }),
  makeCandidate({ ticker: "EXTRA", name: "Extra Corp", score: 60 }),
]

const mockData: HomepageData = {
  candidates: mockCandidates,
  allPicks: mockCandidates,
  last_updated: "2026-03-09T12:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("ResultsShowcaseSection", () => {
  it("renders top 3 candidate tickers and scores", () => {
    render(<ResultsShowcaseSection data={mockData} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("JNJ")).toBeInTheDocument()
    expect(screen.getByText("82.4")).toBeInTheDocument()
    expect(screen.getByText("79.1")).toBeInTheDocument()
    expect(screen.getByText("75.6")).toBeInTheDocument()
    // 4th candidate should not be shown
    expect(screen.queryByText("EXTRA")).not.toBeInTheDocument()
  })

  it("renders cycle stats line with live numbers", () => {
    render(<ResultsShowcaseSection data={mockData} />)
    expect(screen.getByText(/842 stocks scored/)).toBeInTheDocument()
    expect(screen.getByText(/830 eliminated/)).toBeInTheDocument()
    expect(screen.getByText(/12 survived/)).toBeInTheDocument()
  })

  it("shows placeholder when data is null", () => {
    render(<ResultsShowcaseSection data={null} />)
    expect(
      screen.getByText("Scoring data loads after the engine completes a cycle.")
    ).toBeInTheDocument()
  })

  it("shows in-progress message when candidates array is empty", () => {
    const emptyData: HomepageData = {
      ...mockData,
      candidates: [],
    }
    render(<ResultsShowcaseSection data={emptyData} />)
    expect(
      screen.getByText(
        "Scoring in progress — results appear after each cycle."
      )
    ).toBeInTheDocument()
  })
})
