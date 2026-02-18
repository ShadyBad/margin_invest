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
  AnimatedScore: ({ value, className }: { value: number; className?: string }) => (
    <span className={className} data-testid="animated-score">{Math.round(value)}</span>
  ),
}))

// Mock AssetPanel (slide-over panel)
vi.mock("../panel", () => ({
  AssetPanel: ({ isOpen, ticker }: any) =>
    isOpen ? <div data-testid={`asset-panel-${ticker}`} /> : null,
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
  it("renders exceptional card with rounded-lg and sector bar", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("rounded-lg")
    expect(card.className).toContain("border-l-2")
  })

  it("renders high card with sector bar", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "high", score: 80 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("rounded-lg")
  })

  it("renders watchlist card with sector bar and no conviction glow", () => {
    render(<StockCard pick={{ ...basePick, conviction_level: "watchlist", score: 55 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
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

describe("StockCard Buy Below row", () => {
  it("renders Buy Below price on card", () => {
    render(<StockCard pick={basePick} />)
    expect(screen.getByText("Buy Below:")).toBeInTheDocument()
    expect(screen.getByText("$140.00")).toBeInTheDocument()
  })

  it("renders Buy Below in green when actual price is below buy price", () => {
    render(<StockCard pick={{ ...basePick, actual_price: 130, buy_price: 140 }} />)
    const buyBelowValue = screen.getByTestId("buy-below-value")
    expect(buyBelowValue).toHaveClass("text-bullish")
  })

  it("renders Buy Below explanation text", () => {
    render(<StockCard pick={basePick} />)
    expect(screen.getByText("Fundamentals-based entry price")).toBeInTheDocument()
  })

  it("does not render Buy Below row when buy_price is null", () => {
    render(<StockCard pick={{ ...basePick, buy_price: null }} />)
    expect(screen.queryByText("Buy Below:")).not.toBeInTheDocument()
  })
})

describe("StockCard sector left bar", () => {
  it("applies sector color as left border style", () => {
    render(<StockCard pick={{ ...basePick, sector: "Information Technology" }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-sector-tech)")
  })

  it("applies border-l-2 class for sector bar width", () => {
    render(<StockCard pick={{ ...basePick, sector: "Energy" }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
  })

  it("falls back to border-primary when sector is null", () => {
    render(<StockCard pick={{ ...basePick, sector: null }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-border-primary)")
  })

  it("falls back to border-primary when sector is undefined", () => {
    render(<StockCard pick={basePick} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.style.borderLeftColor).toBe("var(--color-border-primary)")
  })
})
