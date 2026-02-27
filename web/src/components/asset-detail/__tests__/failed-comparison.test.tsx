import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FailedComparison } from "../failed-comparison"
import type { FailedFilterComparison } from "../failed-comparison"

const mockFailedFilters: FailedFilterComparison[] = [
  {
    filterName: "beneish_m_score",
    filterDisplayName: "Beneish M-Score",
    stockValue: -1.42,
    threshold: -1.78,
    championValue: -2.91,
    championTicker: "AAPL",
    sectorMedian: -2.44,
  },
  {
    filterName: "earnings_quality",
    filterDisplayName: "Sloan Accrual Ratio",
    stockValue: 0.12,
    threshold: 0.1,
    championValue: -0.04,
    championTicker: "AAPL",
    sectorMedian: 0.02,
  },
]

describe("FailedComparison", () => {
  it("renders comparison header with ticker name", () => {
    render(<FailedComparison ticker="TSLA" failedFilters={mockFailedFilters} />)
    expect(screen.getByText(/Where TSLA Failed, Others Passed/)).toBeInTheDocument()
  })

  it("shows both failed filter display names", () => {
    render(<FailedComparison ticker="TSLA" failedFilters={mockFailedFilters} />)
    expect(screen.getByText("Beneish M-Score")).toBeInTheDocument()
    expect(screen.getByText("Sloan Accrual Ratio")).toBeInTheDocument()
  })

  it("shows FAIL and PASS labels", () => {
    render(<FailedComparison ticker="TSLA" failedFilters={mockFailedFilters} />)
    const failBadges = screen.getAllByText("FAIL")
    const passBadges = screen.getAllByText("PASS")
    expect(failBadges.length).toBe(2)
    expect(passBadges.length).toBe(2)
  })

  it("shows comparison stock attribution line with championTicker and highest-scoring in same sector", () => {
    render(<FailedComparison ticker="TSLA" failedFilters={mockFailedFilters} />)
    expect(
      screen.getByText(/Comparison stock: AAPL \(highest-scoring in same sector\)/)
    ).toBeInTheDocument()
  })

  it("returns null when failedFilters is empty", () => {
    const { container } = render(<FailedComparison ticker="TSLA" failedFilters={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it("handles null champion gracefully (no PASS row)", () => {
    const filtersWithNullChampion: FailedFilterComparison[] = [
      {
        filterName: "beneish_m_score",
        filterDisplayName: "Beneish M-Score",
        stockValue: -1.42,
        threshold: -1.78,
        championValue: null,
        championTicker: null,
        sectorMedian: -2.44,
      },
    ]
    render(<FailedComparison ticker="TSLA" failedFilters={filtersWithNullChampion} />)
    expect(screen.getAllByText("FAIL")).toHaveLength(1)
    expect(screen.queryByText("PASS")).not.toBeInTheDocument()
  })

  it("does not show attribution line when no champion data", () => {
    const filtersWithNullChampion: FailedFilterComparison[] = [
      {
        filterName: "beneish_m_score",
        filterDisplayName: "Beneish M-Score",
        stockValue: -1.42,
        threshold: -1.78,
        championValue: null,
        championTicker: null,
        sectorMedian: null,
      },
    ]
    render(<FailedComparison ticker="TSLA" failedFilters={filtersWithNullChampion} />)
    expect(screen.queryByText(/Comparison stock/)).not.toBeInTheDocument()
  })
})
