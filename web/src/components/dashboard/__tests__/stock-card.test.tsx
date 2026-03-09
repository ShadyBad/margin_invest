import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { StockCard } from "../stock-card"
import type { PickSummary } from "@/lib/api/types"

// Mock the API call
vi.mock("@/lib/api/scores", () => ({
  getScore: vi.fn(),
  getMetrics: vi.fn(),
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

// Mock sector-colors utility
vi.mock("@/lib/sector-colors", () => ({
  getSectorColor: (sector: string | null | undefined) => {
    const map: Record<string, string> = {
      "Information Technology": "var(--color-sector-tech)",
      "Energy": "var(--color-sector-energy)",
    }
    return map[sector ?? ""] ?? "var(--color-border-primary)"
  },
}))

// Mock AssetPanel (slide-over panel)
vi.mock("../panel", () => ({
  AssetPanel: ({ isOpen, ticker }: { isOpen: boolean; ticker: string }) =>
    isOpen ? <div data-testid={`asset-panel-${ticker}`} /> : null,
}))

const basePick: PickSummary = {
  ticker: "AAPL",
  name: "Apple Inc.",
  score: 92,
  universe_percentile: 95,
  composite_percentile: 95,
  composite_tier: "exceptional",
  signal: "strong",
  quality_percentile: 90,
  value_percentile: 85,
  momentum_percentile: 88,
  actual_price: 150,
  buy_price: 140,
  sell_price: 180,
  price_upside: 0.2,
}

describe("StockCard visual hierarchy", () => {
  it("renders exceptional card with rounded-xl and sector bar", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("rounded-xl")
    expect(card.className).toContain("border-l-2")
  })

  it("renders high card with sector bar", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "high", score: 80 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("rounded-xl")
  })

  it("renders watchlist card with sector bar and no conviction glow", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "watchlist", score: 55 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    expect(card.className).toContain("border-l-2")
    expect(card.className).toContain("rounded-xl")
  })

  it("renders exceptional score in accent color with display font", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "exceptional", score: 92 }} />)
    expect(screen.getByText("92")).toHaveClass("text-accent")
    expect(screen.getByText("92")).toHaveClass("font-display")
  })

  it("renders watchlist score in muted color", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "watchlist", score: 55 }} />)
    expect(screen.getByText("55")).toHaveClass("text-text-secondary")
  })

  it("renders composite label below score", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "exceptional", score: 92 }} />)
    expect(screen.getByText("composite")).toBeInTheDocument()
  })

  it("renders exceptional card with radial gradient overlay but no top accent stripe", () => {
    render(<StockCard pick={{ ...basePick, composite_tier: "exceptional", score: 92 }} />)
    const card = screen.getByTestId("stock-card-AAPL")
    // Top accent stripe was removed; only the radial gradient overlay remains
    const stripe = card.querySelector(".bg-accent.h-\\[2px\\]")
    expect(stripe).not.toBeInTheDocument()
    // Radial gradient overlay should still exist
    const overlay = card.querySelector(".pointer-events-none")
    expect(overlay).toBeInTheDocument()
  })
})

describe("StockCard Buy Below row removed", () => {
  it("does not render Buy Below section (moved to price ladder in detail panel)", () => {
    render(<StockCard pick={basePick} />)
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

describe("StockCard ML override indicator", () => {
  it("shows ML promoted indicator", () => {
    render(<StockCard pick={{ ...basePick, ml_override: "promoted" }} />)
    expect(screen.getByTestId(`ml-override-${basePick.ticker}`)).toBeInTheDocument()
  })

  it("does not show ML indicator when override is none", () => {
    render(<StockCard pick={{ ...basePick, ml_override: "none" }} />)
    expect(screen.queryByTestId(`ml-override-${basePick.ticker}`)).not.toBeInTheDocument()
  })
})
