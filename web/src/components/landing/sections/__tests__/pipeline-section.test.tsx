import { describe, test, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PipelineSection } from "../pipeline-section"
import type { HomepageData, CandidateCard } from "../../shared/types"

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
    makeCandidate({ ticker: "AAPL", name: "Apple Inc.", score: 82.4 }),
    makeCandidate({ ticker: "MSFT", name: "Microsoft Corp", score: 78.1 }),
    makeCandidate({ ticker: "JNJ", name: "Johnson & Johnson", score: 71.3 }),
  ],
  allPicks: [
    makeCandidate({ ticker: "AAPL", sector: "Technology" }),
    makeCandidate({ ticker: "MSFT", sector: "Technology" }),
    makeCandidate({ ticker: "JNJ", sector: "Healthcare" }),
  ],
  last_updated: "2026-03-09T12:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("PipelineSection", () => {
  test("renders pipeline headline with universe count", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText(/stocks to the ones worth your screen/i)).toBeInTheDocument()
  })

  test("renders three subsections", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText("Eliminate the Noise")).toBeInTheDocument()
    expect(screen.getByText("Score What Remains")).toBeInTheDocument()
    expect(screen.getByText("Surface the Survivors")).toBeInTheDocument()
  })

  test("renders Eliminate the Noise subsection", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText("Eliminate the Noise")).toBeInTheDocument()
    expect(screen.getByText(/forensic filters/i)).toBeInTheDocument()
  })

  test("renders Score What Remains subsection", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText("Score What Remains")).toBeInTheDocument()
    expect(screen.getByText(/five orthogonal factors/i)).toBeInTheDocument()
  })

  test("renders Surface the Survivors subsection", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText("Surface the Survivors")).toBeInTheDocument()
    expect(screen.getByText(/highest-scoring positions/i)).toBeInTheDocument()
  })

  test("renders funnel diagram with live data", () => {
    const { container } = render(<PipelineSection data={mockData} />)
    const funnelStages = container.querySelectorAll("[data-funnel-stage]")
    expect(funnelStages.length).toBeGreaterThanOrEqual(4)
  })

  test("renders radar chart for top candidate", () => {
    const { container } = render(<PipelineSection data={mockData} />)
    const dataPolygon = container.querySelector("[data-data-polygon]")
    expect(dataPolygon).toBeInTheDocument()
  })

  test("renders mini candidate stack", () => {
    const { container } = render(<PipelineSection data={mockData} />)
    const cards = container.querySelectorAll("[data-candidate-card]")
    expect(cards.length).toBeGreaterThanOrEqual(3)
  })

  test("shows 3 editorial spread subsections", () => {
    const { container } = render(<PipelineSection data={mockData} />)
    const spreads = container.querySelectorAll("[data-editorial-spread]")
    expect(spreads).toHaveLength(3)
  })

  test("renders gracefully when data is null", () => {
    render(<PipelineSection data={null} />)
    expect(screen.getByText("Eliminate the Noise")).toBeInTheDocument()
    expect(screen.getByText("Score What Remains")).toBeInTheDocument()
    expect(screen.getByText("Surface the Survivors")).toBeInTheDocument()
    // Shows placeholder text for missing data
    expect(screen.getByText("---")).toBeInTheDocument()
  })

  test("displays elimination stats", () => {
    render(<PipelineSection data={mockData} />)
    // 3056 - 842 = 2,214 eliminated
    expect(screen.getByText(/2,214 eliminated/)).toBeInTheDocument()
    expect(screen.getByText(/842 remain/)).toBeInTheDocument()
  })

  test("displays surviving count", () => {
    render(<PipelineSection data={mockData} />)
    expect(screen.getByText(/12 candidates surfaced/)).toBeInTheDocument()
  })
})
