import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MarketContextPanel } from "../market-context-panel"
import type { DashboardResponse } from "@/lib/api/types"

const mockData: DashboardResponse = {
  picks: [
    {
      score_id: 1,
      ticker: "AAPL",
      name: "Apple Inc.",
      score: 82,
      universe_percentile: 92,
      composite_percentile: 92,
      composite_tier: "exceptional",
      signal: "strong",
      quality_percentile: 88,
      value_percentile: 72,
      momentum_percentile: 95,
      actual_price: 185.5,
      buy_price: 150.0,
      sell_price: 210.0,
      price_upside: 0.132,
      sector: "Technology",
    },
    {
      score_id: 2,
      ticker: "UNH",
      name: "UnitedHealth Group Inc.",
      score: 78,
      universe_percentile: 89,
      composite_percentile: 89,
      composite_tier: "strong",
      signal: "strong",
      quality_percentile: 91,
      value_percentile: 74,
      momentum_percentile: 72,
      actual_price: 512.35,
      buy_price: 445.0,
      sell_price: null,
      price_upside: null,
      sector: "Healthcare",
    },
    {
      score_id: 3,
      ticker: "NVDA",
      name: "NVIDIA Corp.",
      score: 71,
      universe_percentile: 79,
      composite_percentile: 79,
      composite_tier: "stable",
      signal: "stable",
      quality_percentile: 85,
      value_percentile: 52,
      momentum_percentile: 91,
      actual_price: 138.25,
      buy_price: 118.0,
      sell_price: null,
      price_upside: null,
      sector: "Technology",
    },
  ],
  watchlist: [],
  last_updated: "2026-03-09T14:00:00Z",
  total_scored: 500,
  universe: {
    version: "v4.2.1",
    size: 3056,
    scoring_coverage: 1,
    is_complete: true,
    last_scoring_run: "2026-03-09T14:00:00Z",
  },
}

describe("MarketContextPanel", () => {
  it("renders market context header", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Market Context")).toBeInTheDocument()
  })

  it("renders universe size", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Universe")).toBeInTheDocument()
    expect(screen.getByText("3,056")).toBeInTheDocument()
  })

  it("renders scored count", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Scored")).toBeInTheDocument()
    expect(screen.getByText("500")).toBeInTheDocument()
  })

  it("renders surviving count", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Surviving")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()
  })

  it("renders engine version", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Engine")).toBeInTheDocument()
    expect(screen.getByText("v4.2.1")).toBeInTheDocument()
  })

  it("shows em-dash placeholders when data is null", () => {
    render(<MarketContextPanel data={null} />)
    const emDashes = screen.getAllByText("\u2014")
    // Universe, Scored, Surviving, Engine, Last Run = at least 5 em-dashes
    expect(emDashes.length).toBeGreaterThanOrEqual(5)
  })

  it("renders sector breakdown when picks have sectors", () => {
    render(<MarketContextPanel data={mockData} />)
    expect(screen.getByText("Sector Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Technology")).toBeInTheDocument()
    expect(screen.getByText("Healthcare")).toBeInTheDocument()
  })

  it("shows correct sector counts", () => {
    render(<MarketContextPanel data={mockData} />)
    // Technology: 2 picks (AAPL + NVDA), Healthcare: 1 pick (UNH)
    expect(screen.getByText("2")).toBeInTheDocument()
    expect(screen.getByText("1")).toBeInTheDocument()
  })

  it("does not render sector breakdown when data is null", () => {
    render(<MarketContextPanel data={null} />)
    expect(screen.queryByText("Sector Breakdown")).not.toBeInTheDocument()
  })

  it("uses terminal-card class", () => {
    const { container } = render(<MarketContextPanel data={mockData} />)
    const card = container.querySelector(".terminal-card")
    expect(card).toBeInTheDocument()
  })

  it("is sticky positioned", () => {
    const { container } = render(<MarketContextPanel data={mockData} />)
    const stickyEl = container.querySelector(".sticky")
    expect(stickyEl).toBeInTheDocument()
  })
})
