import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SystemStatusStrip } from "../system-status-strip"
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
    },
    {
      score_id: 2,
      ticker: "MSFT",
      name: "Microsoft Corporation",
      score: 75,
      universe_percentile: 85,
      composite_percentile: 85,
      composite_tier: "high",
      signal: "strong",
      quality_percentile: 90,
      value_percentile: 65,
      momentum_percentile: 80,
      actual_price: 420.0,
      buy_price: 380.0,
      sell_price: 480.0,
      price_upside: 0.143,
    },
  ],
  watchlist: [],
  last_updated: "2026-03-09T14:00:00Z",
  total_scored: 3056,
  universe: {
    version: "v4",
    size: 3056,
    scoring_coverage: 1,
    is_complete: true,
    last_scoring_run: "2026-03-09T14:00:00Z",
  },
}

describe("SystemStatusStrip", () => {
  it("renders system status strip with data", () => {
    render(<SystemStatusStrip data={mockData} />)
    expect(screen.getByTestId("system-status-strip")).toBeInTheDocument()
    expect(screen.getByText(/SCORED 3,056/)).toBeInTheDocument()
    expect(screen.getByText(/SURVIVING 2/)).toBeInTheDocument()
  })

  it("renders offline state when data is null", () => {
    render(<SystemStatusStrip data={null} />)
    expect(screen.getByTestId("system-status-strip")).toBeInTheDocument()
    expect(screen.getByText(/SYSTEM OFFLINE/)).toBeInTheDocument()
    expect(screen.getByText(/AWAITING CONNECTION/)).toBeInTheDocument()
  })

  it("shows green pulsing dot when data is present", () => {
    const { container } = render(<SystemStatusStrip data={mockData} />)
    const dot = container.querySelector(".animate-pulse")
    expect(dot).toBeInTheDocument()
    expect(dot).toHaveClass("bg-bullish")
  })

  it("shows grey dot when offline", () => {
    const { container } = render(<SystemStatusStrip data={null} />)
    const dot = container.querySelector(".bg-text-tertiary")
    expect(dot).toBeInTheDocument()
  })

  it("uses monospace font for status text", () => {
    render(<SystemStatusStrip data={mockData} />)
    const statusText = screen.getByText(/SCORED/)
    expect(statusText).toHaveClass("font-mono")
  })

  it("displays last run time", () => {
    render(<SystemStatusStrip data={mockData} />)
    expect(screen.getByText(/LAST RUN/)).toBeInTheDocument()
  })
})
