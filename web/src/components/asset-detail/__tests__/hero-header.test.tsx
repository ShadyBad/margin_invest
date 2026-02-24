import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroHeader } from "../hero-header"
import { EliminatedHero } from "../eliminated-hero"

const baseProps = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  growthStage: "mature",
  actualPrice: 187.42,
  priceChange: 1.23,
  priceChangePercent: 0.66,
  compositeScore: 78.3,
  universePercentile: 96,
  universeSize: 2847,
  convictionLevel: "high",
  signal: "buy",
  dataCoverage: 0.94,
  scoredAt: "2026-02-23T12:00:00Z",
  dataFreshness: "fresh" as const,
  priceSource: "live" as const,
  scoreHistory: [70, 72, 75, 78, 78.3],
}

describe("HeroHeader", () => {
  it("renders ticker and company name", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders four metric cards", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByTestId("metric-score")).toHaveTextContent("78.3")
    expect(screen.getByTestId("metric-percentile")).toHaveTextContent("Top 4%")
    expect(screen.getByTestId("metric-conviction")).toHaveTextContent("HIGH")
    expect(screen.getByTestId("metric-signal")).toHaveTextContent("BUY")
  })

  it("renders metadata ribbon", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByTestId("metadata-ribbon")).toHaveTextContent("94%")
  })

  it("renders growth stage and sector", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/Mature/i)).toBeInTheDocument()
  })

  it("renders price with change", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByText("$187.42")).toBeInTheDocument()
  })

  it("renders universe size in percentile card", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByTestId("metric-percentile")).toHaveTextContent("of 2847 stocks")
  })

  it("applies freshness color class to scored-at metadata", () => {
    const recentDate = new Date(Date.now() - 30 * 60 * 1000).toISOString() // 30 min ago
    render(<HeroHeader {...baseProps} scoredAt={recentDate} />)
    const ribbon = screen.getByTestId("metadata-ribbon")
    expect(ribbon.querySelector("[data-freshness]")).toHaveClass("text-bullish")
  })

  it("applies stale color when scored more than 24h ago", () => {
    const oldDate = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString() // 25h ago
    render(<HeroHeader {...baseProps} scoredAt={oldDate} />)
    const ribbon = screen.getByTestId("metadata-ribbon")
    expect(ribbon.querySelector("[data-freshness]")).toHaveClass("text-warning")
  })

  it("shows style tag in metadata area", () => {
    render(<HeroHeader {...baseProps} style="growth" />)
    expect(screen.getByText("Growth")).toBeInTheDocument()
  })

  it("handles missing optional props gracefully", () => {
    render(
      <HeroHeader
        ticker="MSFT"
        name="Microsoft"
        compositeScore={65.0}
        universePercentile={80}
        convictionLevel="medium"
        signal="hold"
        dataCoverage={0.85}
      />
    )
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByTestId("metric-score")).toHaveTextContent("65.0")
  })
})

describe("EliminatedHero", () => {
  it("shows elimination banner with failure count", () => {
    render(
      <EliminatedHero
        ticker="TSLA"
        name="Tesla Inc."
        sector="Consumer Discretionary"
        growthStage="high_growth"
        actualPrice={241.87}
        failedCount={2}
        totalFilters={6}
        dataCoverage={0.91}
        scoredAt="2026-02-23T08:00:00Z"
      />
    )
    expect(screen.getByTestId("eliminated-banner")).toBeInTheDocument()
    expect(screen.getByText(/Failed 2 of 6/)).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
  })

  it("renders growth stage formatted", () => {
    render(
      <EliminatedHero
        ticker="TSLA"
        name="Tesla Inc."
        growthStage="high_growth"
        failedCount={1}
        totalFilters={6}
        dataCoverage={0.8}
      />
    )
    expect(screen.getByText(/High Growth/)).toBeInTheDocument()
  })

  it("shows price when provided", () => {
    render(
      <EliminatedHero
        ticker="GME"
        name="GameStop"
        actualPrice={15.5}
        failedCount={3}
        totalFilters={6}
        dataCoverage={0.7}
      />
    )
    expect(screen.getByText("$15.50")).toBeInTheDocument()
  })
})
