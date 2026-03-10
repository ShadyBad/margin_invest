import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

// Mock HeroSearch to avoid client-side fetch dependencies
vi.mock("../../hero-search", () => ({
  HeroSearch: () => <div data-testid="hero-search">search</div>,
}))

import { HeroSection } from "../hero-section"
import type { HomepageData } from "../../shared/types"

const mockData: HomepageData = {
  candidates: [
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      actual_price: 173.22,
      buy_price: 214.9,
      margin_of_safety: 0.194,
      score: 78.2,
      composite_percentile: 83,
      composite_tier: "high",
      quality_percentile: 85,
      value_percentile: 62,
      momentum_percentile: 71,
      sentiment_percentile: 68,
      growth_percentile: 74,
      scored_at: new Date().toISOString(),
      filters_passed: 8,
      filters_total: 8,
    },
  ],
  allPicks: [],
  last_updated: new Date().toISOString(),
  universe_size: 1842,
  eligible_count: 143,
  total_scored: 1842,
  total_universe: 3056,
  surviving_count: 143,
}

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection data={mockData} />)
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders the subtext", () => {
    render(<HeroSection data={mockData} />)
    expect(
      screen.getByText("Systematic equity analysis. Five factors. Zero emotion.")
    ).toBeInTheDocument()
  })

  it("renders the search bar", () => {
    render(<HeroSection data={mockData} />)
    expect(screen.getByTestId("hero-search")).toBeInTheDocument()
  })

  it("renders SystemReportCard with top candidate", () => {
    render(<HeroSection data={mockData} />)
    expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })

  it("renders SystemReportCard in placeholder mode when data is null", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
    expect(screen.getByText("No data available")).toBeInTheDocument()
  })

  it("uses 90svh min-height (Authority Strip peek)", () => {
    const { container } = render(<HeroSection data={mockData} />)
    const section = container.querySelector("#hero")
    expect(section).toHaveStyle({ minHeight: "90svh" })
  })

  it("has two-column grid on lg breakpoint", () => {
    const { container } = render(<HeroSection data={mockData} />)
    const grid = container.querySelector(".grid")
    expect(grid?.classList.contains("lg:grid-cols-[55%_45%]")).toBe(true)
  })

  it("renders data-hero-card attribute for GSAP targeting", () => {
    const { container } = render(<HeroSection data={mockData} />)
    expect(container.querySelector("[data-hero-card]")).toBeInTheDocument()
  })
})
