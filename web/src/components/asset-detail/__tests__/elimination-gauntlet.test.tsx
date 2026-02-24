import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EliminationGauntlet } from "../elimination-gauntlet"
import type { FilterResultResponse } from "@/lib/api/types"

const allPassing: FilterResultResponse[] = [
  { name: "liquidity", passed: true, value: 2890000, threshold: 200000000, detail: "Market cap $2.89T", verdict: "pass", missing_fields: null },
  { name: "beneish_m_score", passed: true, value: -2.87, threshold: -2.22, detail: "M-Score: -2.87", verdict: "pass", missing_fields: null },
  { name: "altman_z_score", passed: true, value: 5.12, threshold: 1.1, detail: "Z-Score: 5.12", verdict: "pass", missing_fields: null },
  { name: "current_ratio", passed: true, value: 0.99, threshold: 0.8, detail: "CR: 0.99 (Tech threshold)", verdict: "pass", missing_fields: null },
  { name: "fcf_distress", passed: true, value: 104300, threshold: 0, detail: "Positive FCF", verdict: "pass", missing_fields: null },
  { name: "interest_coverage", passed: true, value: 29.4, threshold: 3.0, detail: "Coverage: 29.4x", verdict: "pass", missing_fields: null },
]

const withFailures: FilterResultResponse[] = [
  { name: "liquidity", passed: true, value: 782000, threshold: 200000000, detail: "Market cap $782B", verdict: "pass", missing_fields: null },
  { name: "beneish_m_score", passed: true, value: -2.45, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
  { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "Below safe zone", verdict: "fail", missing_fields: null },
  { name: "current_ratio", passed: true, value: 1.2, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
  { name: "fcf_distress", passed: false, value: -2100, threshold: 0, detail: "Negative FCF", verdict: "fail", missing_fields: null },
  { name: "interest_coverage", passed: true, value: 8.5, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
]

describe("EliminationGauntlet", () => {
  it("shows pass count for all-passing filters", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} />)
    expect(screen.getByText("6 of 6 passed")).toBeInTheDocument()
  })

  it("shows all 6 filter cards", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} />)
    expect(screen.getAllByTestId(/^filter-card-/)).toHaveLength(6)
  })

  it("sorts failed filters to top when eliminated", () => {
    render(<EliminationGauntlet filters={withFailures} eliminated={true} />)
    const cards = screen.getAllByTestId(/^filter-card-/)
    // Failed filters should be first
    expect(cards[0]).toHaveAttribute("data-testid", "filter-card-altman_z_score")
    expect(cards[1]).toHaveAttribute("data-testid", "filter-card-fcf_distress")
  })

  it("shows WHY THIS MATTERS for failed filters", () => {
    render(<EliminationGauntlet filters={withFailures} eliminated={true} />)
    expect(screen.getByText(/predicts bankruptcy probability/)).toBeInTheDocument()
  })

  it("shows elimination rate when context provided", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} totalScored={2847} filtersSurvivedCount={847} />)
    expect(screen.getByText(/70% of the universe/i)).toBeInTheDocument()
  })

  it("does not show universe context when props are missing", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} />)
    expect(screen.queryByText(/of the universe/i)).not.toBeInTheDocument()
  })
})
