import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { SystemReportCard } from "../system-report-card"
import type { CandidateCard } from "../../shared/types"

const mockCandidate: CandidateCard = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  actual_price: 173.22,
  buy_price: 214.9,
  margin_of_safety: 0.194,
  score: 85.3,
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
}

describe("SystemReportCard", () => {
  test("renders candidate ticker and name", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  test("renders SYSTEM REPORT header", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
  })

  test("renders composite score rounded", () => {
    const { container } = render(<SystemReportCard candidate={mockCandidate} />)
    const scoreEl = container.querySelector(".text-mono-data")
    expect(scoreEl).toBeInTheDocument()
    expect(scoreEl?.textContent).toBe("85")
  })

  test("renders Composite Score label", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    expect(screen.getByText("Composite Score")).toBeInTheDocument()
  })

  test("renders all 5 factor labels via FactorBars", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    expect(screen.getByText("QUALITY")).toBeInTheDocument()
    expect(screen.getByText("VALUE")).toBeInTheDocument()
    expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
    expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
    expect(screen.getByText("GROWTH")).toBeInTheDocument()
  })

  test("renders scored timestamp", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    // Should show "Scored just now" or "Scored Xm ago" since scored_at is now
    expect(screen.getByText(/^Scored /)).toBeInTheDocument()
  })

  test("renders status dot with bullish color when candidate present", () => {
    render(<SystemReportCard candidate={mockCandidate} />)
    const dot = screen.getByTestId("status-dot")
    expect(dot).toHaveStyle({ backgroundColor: "var(--color-bullish)" })
  })

  test("has data-hero-card attribute for GSAP targeting", () => {
    const { container } = render(<SystemReportCard candidate={mockCandidate} />)
    expect(container.querySelector("[data-hero-card]")).toBeInTheDocument()
  })

  test("renders placeholder dashes when candidate is null", () => {
    render(<SystemReportCard candidate={null} />)
    const dashes = screen.getAllByText("\u2014")
    // At least ticker, name, score, and 5 factor values = 8 dashes
    expect(dashes.length).toBeGreaterThanOrEqual(7)
  })

  test("renders SYSTEM REPORT header when candidate is null", () => {
    render(<SystemReportCard candidate={null} />)
    expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
  })

  test("renders 'No data available' when candidate is null", () => {
    render(<SystemReportCard candidate={null} />)
    expect(screen.getByText("No data available")).toBeInTheDocument()
  })

  test("renders status dot with tertiary color when candidate is null", () => {
    render(<SystemReportCard candidate={null} />)
    const dot = screen.getByTestId("status-dot")
    expect(dot).toHaveStyle({ backgroundColor: "var(--color-text-tertiary)" })
  })

  test("renders factor placeholder labels when candidate is null", () => {
    render(<SystemReportCard candidate={null} />)
    expect(screen.getByText("QUALITY")).toBeInTheDocument()
    expect(screen.getByText("VALUE")).toBeInTheDocument()
    expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
    expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
    expect(screen.getByText("GROWTH")).toBeInTheDocument()
  })

  test("renders relative time correctly for older timestamps", () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
    const oldCandidate = { ...mockCandidate, scored_at: twoHoursAgo }
    render(<SystemReportCard candidate={oldCandidate} />)
    expect(screen.getByText("Scored 2h ago")).toBeInTheDocument()
  })
})
