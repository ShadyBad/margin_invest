import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ScoringPillars } from "../scoring-pillars"
import type { FactorBreakdownResponse } from "@/lib/api/types"

const quality: FactorBreakdownResponse = {
  factor_name: "quality",
  weight: 0.3,
  average_percentile: 72,
  sub_scores: [
    { name: "piotroski_f_score", raw_value: 7, percentile_rank: 85, detail: "Strong" },
    { name: "gross_profitability", raw_value: 0.43, percentile_rank: 78, detail: "Above avg" },
  ],
}

const value: FactorBreakdownResponse = {
  factor_name: "value",
  weight: 0.4,
  average_percentile: 81,
  sub_scores: [
    { name: "ev_fcf", raw_value: 18.5, percentile_rank: 75, detail: "Reasonable" },
  ],
}

const momentum: FactorBreakdownResponse = {
  factor_name: "momentum",
  weight: 0.3,
  average_percentile: 68,
  sub_scores: [
    { name: "price_momentum", raw_value: 0.15, percentile_rank: 70, detail: "Positive" },
  ],
}

describe("ScoringPillars", () => {
  it("renders three pillar cards", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}


      />
    )
    expect(screen.getByTestId("pillar-quality")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-value")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-momentum")).toBeInTheDocument()
  })

  it("expands sub-factors on click", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}


      />
    )
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    expect(screen.getByText("Piotroski F-Score")).toBeInTheDocument()
    expect(screen.getByText("85th")).toBeInTheDocument()
  })

  it("shows formula when sub-factor row is clicked", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}


      />
    )
    // Expand the quality pillar
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    // Click on the Gross Profitability sub-factor row
    fireEvent.click(screen.getByText("Gross Profitability"))
    // Expect to see the formula and source (FormulaTooltip hover + inline expansion may both render)
    expect(screen.getAllByText(/Revenue - COGS/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Novy-Marx/).length).toBeGreaterThanOrEqual(1)
  })

  it("hides formula when sub-factor row is clicked again", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}


      />
    )
    // Expand the quality pillar
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    // Click to expand formula — first click opens both tooltip and inline formula
    fireEvent.click(screen.getByText("Gross Profitability"))
    expect(screen.getAllByText(/Revenue - COGS/).length).toBeGreaterThanOrEqual(1)
    // Click again to collapse — second click toggles both off
    const nameElements = screen.getAllByText("Gross Profitability")
    fireEvent.click(nameElements[0])
    expect(screen.queryAllByText(/Revenue - COGS/).length).toBe(0)
  })

  it("shows fx indicator on sub-factors with formulas", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}


      />
    )
    // Expand the quality pillar
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    // Both sub-factors have formulas, so "fx" indicators should be visible
    const fxIndicators = screen.getAllByText("fx")
    expect(fxIndicators.length).toBeGreaterThanOrEqual(2)
  })
})
