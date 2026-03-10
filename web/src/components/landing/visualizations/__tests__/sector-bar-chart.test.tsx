import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { SectorBarChart, groupBySector } from "../sector-bar-chart"
import type { CandidateCard } from "../../shared/types"

function makeCandidate(overrides: Partial<CandidateCard> = {}): CandidateCard {
  return {
    ticker: "AAPL",
    name: "Apple Inc",
    sector: "Technology",
    actual_price: 180,
    buy_price: 150,
    margin_of_safety: 20,
    score: 85,
    composite_percentile: 90,
    composite_tier: "exceptional",
    quality_percentile: 85,
    value_percentile: 72,
    momentum_percentile: 65,
    sentiment_percentile: 58,
    growth_percentile: 90,
    scored_at: "2026-03-01",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("groupBySector", () => {
  test("groups candidates by sector and sorts by count descending", () => {
    const candidates = [
      makeCandidate({ sector: "Technology" }),
      makeCandidate({ sector: "Technology" }),
      makeCandidate({ sector: "Healthcare" }),
      makeCandidate({ sector: "Financials" }),
      makeCandidate({ sector: "Financials" }),
      makeCandidate({ sector: "Financials" }),
    ]
    const groups = groupBySector(candidates)
    expect(groups[0]).toEqual({ sector: "Financials", count: 3 })
    expect(groups[1]).toEqual({ sector: "Technology", count: 2 })
    expect(groups[2]).toEqual({ sector: "Healthcare", count: 1 })
  })

  test("uses 'Unknown' for empty sector", () => {
    const candidates = [makeCandidate({ sector: "" })]
    const groups = groupBySector(candidates)
    expect(groups[0].sector).toBe("Unknown")
  })
})

describe("SectorBarChart", () => {
  test("renders sector rows with counts", () => {
    const candidates = [
      makeCandidate({ sector: "Technology" }),
      makeCandidate({ sector: "Technology" }),
      makeCandidate({ sector: "Healthcare" }),
    ]
    render(<SectorBarChart candidates={candidates} />)
    expect(screen.getByTestId("sector-row-Technology")).toBeInTheDocument()
    expect(screen.getByTestId("sector-row-Healthcare")).toBeInTheDocument()
    expect(screen.getByText("2")).toBeInTheDocument()
    expect(screen.getByText("1")).toBeInTheDocument()
  })

  test("renders empty state when no candidates", () => {
    render(<SectorBarChart candidates={[]} />)
    expect(
      screen.getByText("Sector data available after scoring cycle")
    ).toBeInTheDocument()
  })

  test("renders bars for each sector", () => {
    const candidates = [
      makeCandidate({ sector: "Technology" }),
      makeCandidate({ sector: "Financials" }),
    ]
    const { container } = render(<SectorBarChart candidates={candidates} />)
    expect(
      container.querySelector('[data-testid="sector-bar-Technology"]')
    ).toBeInTheDocument()
    expect(
      container.querySelector('[data-testid="sector-bar-Financials"]')
    ).toBeInTheDocument()
  })

  test("has accessible aria label", () => {
    const candidates = [makeCandidate()]
    render(<SectorBarChart candidates={candidates} />)
    expect(
      screen.getByLabelText("Sector distribution of surviving candidates")
    ).toBeInTheDocument()
  })
})
