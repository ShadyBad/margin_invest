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
        growthStage="mature"
      />
    )
    expect(screen.getByTestId("pillar-quality")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-value")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-momentum")).toBeInTheDocument()
  })

  it("shows growth stage weight explanation", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}
        growthStage="mature"
      />
    )
    expect(screen.getByText(/Mature/)).toBeInTheDocument()
    expect(screen.getByText(/Q:30%/)).toBeInTheDocument()
  })

  it("expands sub-factors on click", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}
        growthStage="mature"
      />
    )
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    expect(screen.getByText("Piotroski F-Score")).toBeInTheDocument()
    expect(screen.getByText("85th")).toBeInTheDocument()
  })
})
