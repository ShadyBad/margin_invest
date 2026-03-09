import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PillarsSection } from "../pillars-section"
import type { HomepageData, CandidateCard } from "../types"

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
    filters_passed: 6,
    filters_total: 6,
    ...overrides,
  }
}

const mockData: HomepageData = {
  candidates: [
    makeCandidate({
      ticker: "AAPL",
      name: "Apple Inc.",
      score: 82.4,
      quality_percentile: 90,
      value_percentile: 70,
      momentum_percentile: 78,
      sentiment_percentile: 65,
      growth_percentile: 72,
      filters_passed: 6,
      filters_total: 6,
    }),
  ],
  allPicks: [
    makeCandidate({ ticker: "AAPL", sector: "Technology" }),
    makeCandidate({ ticker: "MSFT", sector: "Technology" }),
    makeCandidate({ ticker: "JNJ", sector: "Healthcare" }),
    makeCandidate({ ticker: "PFE", sector: "Healthcare" }),
    makeCandidate({ ticker: "JPM", sector: "Financials" }),
  ],
  last_updated: "2026-03-09T12:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("PillarsSection", () => {
  it("renders 3 pillar headings", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Multi-Factor Scoring")).toBeInTheDocument()
    expect(screen.getByText("Sector-Neutral Ranking")).toBeInTheDocument()
  })

  it("shows elimination rate with live data", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText(/842/)).toBeInTheDocument()
    expect(screen.getByText(/3,056/)).toBeInTheDocument()
  })

  it("shows factor breakdown for top candidate", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })

  it("shows sector distribution from allPicks", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
    expect(screen.getByText("Healthcare")).toBeInTheDocument()
  })

  it("renders gracefully when data is null", () => {
    render(<PillarsSection data={null} />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Multi-Factor Scoring")).toBeInTheDocument()
    expect(screen.getByText("Sector-Neutral Ranking")).toBeInTheDocument()
  })
})
