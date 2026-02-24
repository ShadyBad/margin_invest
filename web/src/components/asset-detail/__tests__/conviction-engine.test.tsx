import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConvictionEngine } from "../conviction-engine"

describe("ConvictionEngine", () => {
  it("renders opportunity type with description", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="add_on_pullback"
        capitalAllocation={{
          factor_name: "capital_allocation",
          weight: 0.5,
          average_percentile: 75,
          sub_scores: [
            { name: "moat_durability", raw_value: 0.82, percentile_rank: 82, detail: "Wide" },
            { name: "compounding_power", raw_value: 0.76, percentile_rank: 76, detail: "Strong" },
          ],
        }}
        catalyst={{
          factor_name: "catalyst",
          weight: 0.5,
          average_percentile: 52,
          sub_scores: [
            { name: "catalyst_strength", raw_value: 0.45, percentile_rank: 45, detail: "Moderate" },
          ],
        }}
      />
    )
    expect(screen.getByText("COMPOUNDER")).toBeInTheDocument()
    expect(screen.getByText(/durable competitive advantages/)).toBeInTheDocument()
    expect(screen.getByText("4.2x")).toBeInTheDocument()
    expect(screen.getByText("5.0%")).toBeInTheDocument()
  })

  it("returns null when no conviction data", () => {
    const { container } = render(
      <ConvictionEngine
        opportunityType={null}
        winningTrack={null}
        asymmetryRatio={null}
        maxPositionPct={null}
        timingSignal={null}
        capitalAllocation={null}
        catalyst={null}
      />
    )
    expect(container.firstChild).toBeNull()
  })
})
