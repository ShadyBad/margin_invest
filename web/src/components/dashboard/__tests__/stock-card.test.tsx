import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { StockCard } from "../stock-card"
import type { PickSummary } from "@/lib/api/types"

// Mock the API call
vi.mock("@/lib/api/scores", () => ({
  getScore: vi.fn(),
}))

// Mock UI components
vi.mock("@/components/ui", () => ({
  ActionPill: () => <div data-testid="action-pill" />,
  Sparkline: () => <div data-testid="sparkline" />,
  PercentileBar: ({ label }: { label: string }) => <div data-testid={`percentile-bar-${label}`} />,
  ConvictionBadge: ({ level }: { level: string }) => <div data-testid={`conviction-badge-${level}`} />,
}))

// Mock AssetDetail
vi.mock("../asset-detail", () => ({
  AssetDetail: () => <div data-testid="asset-detail" />,
}))

const basePick: PickSummary = {
  ticker: "AAPL",
  name: "Apple Inc.",
  score: 92,
  universe_percentile: 95,
  composite_percentile: 95,
  conviction_level: "exceptional",
  signal: "buy",
  quality_percentile: 90,
  value_percentile: 85,
  momentum_percentile: 88,
  actual_price: 150,
  buy_price: 140,
  sell_price: 180,
  price_upside: 0.2,
}

describe("StockCard visual hierarchy", () => {
  it("renders exceptional card with accent border and rounded-lg", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-accent/30")
    expect(card.className).toContain("rounded-lg")
  })

  it("renders high card with left accent border", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "high", score: 80 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("border-l-accent")
    expect(card.className).toContain("rounded-lg")
  })

  it("renders watchlist card with no accent border", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "watchlist", score: 55 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).not.toContain("border-accent/30")
    expect(card.className).not.toContain("border-l-accent")
    expect(card.className).toContain("rounded-lg")
  })

  it("renders exceptional score in accent color with display font", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    expect(screen.getByText("92")).toHaveClass("text-accent")
    expect(screen.getByText("92")).toHaveClass("font-display")
  })

  it("renders watchlist score in muted color", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "watchlist", score: 55 }} />)
    expect(screen.getByText("55")).toHaveClass("text-text-secondary")
  })

  it("renders conviction label below score", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    expect(screen.getByText("conviction")).toBeInTheDocument()
  })

  it("renders exceptional card with top accent stripe", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    // The stripe is a child div with bg-accent
    const stripe = card.querySelector(".bg-accent.h-\\[2px\\]")
    expect(stripe).toBeInTheDocument()
  })
})
