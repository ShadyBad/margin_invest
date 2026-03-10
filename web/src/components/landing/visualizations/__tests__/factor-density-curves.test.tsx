import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { FactorDensityCurves, computeDistributions } from "../factor-density-curves"
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

describe("computeDistributions", () => {
  test("computes min, median, max for each factor", () => {
    const candidates = [
      makeCandidate({ quality_percentile: 20, value_percentile: 30, momentum_percentile: 40, sentiment_percentile: 50, growth_percentile: 60 }),
      makeCandidate({ quality_percentile: 80, value_percentile: 70, momentum_percentile: 60, sentiment_percentile: 50, growth_percentile: 40 }),
      makeCandidate({ quality_percentile: 50, value_percentile: 50, momentum_percentile: 50, sentiment_percentile: 50, growth_percentile: 50 }),
    ]
    const dists = computeDistributions(candidates)
    expect(dists).toHaveLength(5)

    // Quality: values [20, 80, 50] -> min=20, median=50, max=80
    expect(dists[0]).toEqual({ label: "QUALITY", min: 20, median: 50, max: 80 })
    // Value: values [30, 70, 50] -> min=30, median=50, max=70
    expect(dists[1]).toEqual({ label: "VALUE", min: 30, median: 50, max: 70 })
  })

  test("returns defaults for empty candidates", () => {
    const dists = computeDistributions([])
    expect(dists).toHaveLength(5)
    dists.forEach((d) => {
      expect(d.min).toBe(0)
      expect(d.median).toBe(50)
      expect(d.max).toBe(100)
    })
  })
})

describe("FactorDensityCurves", () => {
  const candidates = [
    makeCandidate({ quality_percentile: 70, value_percentile: 60 }),
    makeCandidate({ quality_percentile: 90, value_percentile: 80 }),
  ]

  test("renders 5 factor panels", () => {
    render(<FactorDensityCurves candidates={candidates} />)
    expect(screen.getByTestId("density-panel-QUALITY")).toBeInTheDocument()
    expect(screen.getByTestId("density-panel-VALUE")).toBeInTheDocument()
    expect(screen.getByTestId("density-panel-MOMENTUM")).toBeInTheDocument()
    expect(screen.getByTestId("density-panel-SENTIMENT")).toBeInTheDocument()
    expect(screen.getByTestId("density-panel-GROWTH")).toBeInTheDocument()
  })

  test("renders factor labels in mono-label style", () => {
    render(<FactorDensityCurves candidates={candidates} />)
    expect(screen.getByText("QUALITY")).toBeInTheDocument()
    expect(screen.getByText("VALUE")).toBeInTheDocument()
    expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
    expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
    expect(screen.getByText("GROWTH")).toBeInTheDocument()
  })

  test("renders min/median/max dots for each factor", () => {
    const { container } = render(<FactorDensityCurves candidates={candidates} />)
    expect(container.querySelector('[data-testid="density-min-QUALITY"]')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="density-median-QUALITY"]')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="density-max-QUALITY"]')).toBeInTheDocument()
  })

  test("renders range bars connecting min to max", () => {
    const { container } = render(<FactorDensityCurves candidates={candidates} />)
    const rangeBar = container.querySelector('[data-testid="density-range-QUALITY"]')
    expect(rangeBar).toBeInTheDocument()
  })

  test("has accessible aria label", () => {
    render(<FactorDensityCurves candidates={candidates} />)
    expect(
      screen.getByLabelText("Factor percentile distributions across all candidates")
    ).toBeInTheDocument()
  })
})
