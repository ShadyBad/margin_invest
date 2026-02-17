import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PanelFactorBreakdown } from "../panel-factor-breakdown"
import type { FactorBreakdownResponse } from "@/lib/api/types"

const mockFactor = (name: string, weight: number, avg: number): FactorBreakdownResponse => ({
  factor_name: name,
  weight,
  average_percentile: avg,
  sub_scores: [
    { name: "metric_a", raw_value: 0.5, percentile_rank: avg - 5, detail: "" },
    { name: "metric_b", raw_value: 0.7, percentile_rank: avg + 5, detail: "" },
  ],
})

describe("PanelFactorBreakdown", () => {
  it("renders section header with opportunity type", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack="compounder"
      />
    )
    expect(screen.getByText("Factor Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Compounder")).toBeInTheDocument()
  })

  it("renders factor rows sorted by weight descending", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack="compounder"
      />
    )
    const rows = screen.getAllByTestId(/^factor-row-/)
    expect(rows).toHaveLength(3)
  })

  it("passes correct weight percentages to FactorRow", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack={null}
      />
    )
    expect(screen.getByText("35%")).toBeInTheDocument()
    expect(screen.getByText("30%")).toBeInTheDocument()
    expect(screen.getByText("20%")).toBeInTheDocument()
  })
})
