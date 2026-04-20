import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MarketPulse } from "../market-pulse"

const mockData = {
  breadth_pct: 62.5,
  breadth_direction: "up" as const,
  sector_flows: [
    { sector: "Technology", net_shares: 150000, direction: "up" as const },
    { sector: "Healthcare", net_shares: -50000, direction: "down" as const },
  ],
  consensus_picks: [
    { ticker: "AAPL", curated_holders: 12, agreement_pct: 48.0 },
    { ticker: "MSFT", curated_holders: 10, agreement_pct: 40.0 },
  ],
  flow_trend_pct: 8.3,
  flow_trend_direction: "up" as const,
  as_of_quarter: "Q1 2026",
}

describe("MarketPulse", () => {
  it("renders breadth percentage", () => {
    render(<MarketPulse data={mockData} />)
    expect(screen.getByTestId("breadth-value")).toHaveTextContent("62.5%")
  })

  it("renders sector flow items", () => {
    render(<MarketPulse data={mockData} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
    expect(screen.getByText("Healthcare")).toBeInTheDocument()
  })

  it("renders consensus picks", () => {
    render(<MarketPulse data={mockData} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("48%")).toBeInTheDocument()
  })

  it("renders flow trend", () => {
    render(<MarketPulse data={mockData} />)
    expect(screen.getByTestId("flow-trend-value")).toHaveTextContent("8.3%")
  })
})
