import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { HypotheticalScores } from "../hypothetical-scores"

const props = {
  ticker: "TSLA",
  compositeScore: 61.4,
  compositePercentile: 38,
  compositeTier: "none",
  quality: {
    factor_name: "quality",
    weight: 0.3,
    average_percentile: 54,
    sub_scores: [],
  },
  value: {
    factor_name: "value",
    weight: 0.25,
    average_percentile: 42,
    sub_scores: [],
  },
  momentum: {
    factor_name: "momentum",
    weight: 0.35,
    average_percentile: 78,
    sub_scores: [],
  },
  growthStage: "high_growth" as const,
}

describe("HypotheticalScores", () => {
  it("is collapsed by default", () => {
    render(<HypotheticalScores {...props} />)
    expect(screen.queryByTestId("hypothetical-content")).not.toBeInTheDocument()
    expect(screen.getByText(/What if TSLA had passed/)).toBeInTheDocument()
  })

  it("expands on click", () => {
    render(<HypotheticalScores {...props} />)
    fireEvent.click(screen.getByTestId("hypothetical-toggle"))
    expect(screen.getByTestId("hypothetical-content")).toBeInTheDocument()
    expect(screen.getByText("HYPOTHETICAL SCORES")).toBeInTheDocument()
  })

  it("shows narrative conclusion about low score", () => {
    render(<HypotheticalScores {...props} />)
    fireEvent.click(screen.getByTestId("hypothetical-toggle"))
    expect(screen.getByText(/38th percentile/)).toBeInTheDocument()
    expect(screen.getByText(/below the threshold/)).toBeInTheDocument()
  })
})
