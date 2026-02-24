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

  it("renders smart money alignment when institutional accumulation data present", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        institutionalAccumulation={{
          percentile: 82,
          newPositions: 3,
          topFunds: ["Berkshire Hathaway", "Baupost Group"],
        }}
      />
    )
    expect(screen.getByText(/smart money/i)).toBeInTheDocument()
    expect(screen.getByText(/Berkshire Hathaway/)).toBeInTheDocument()
    expect(screen.getByText(/Baupost Group/)).toBeInTheDocument()
    expect(
      screen.getByText(/3 curated institutional investors independently initiated/)
    ).toBeInTheDocument()
  })

  it("does not render smart money section when no data", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
      />
    )
    expect(screen.queryByText(/smart money/i)).not.toBeInTheDocument()
  })

  it("does not render smart money section when topFunds is empty", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        institutionalAccumulation={{
          percentile: 50,
          newPositions: 0,
          topFunds: [],
        }}
      />
    )
    expect(screen.queryByText(/smart money/i)).not.toBeInTheDocument()
  })

  it("uses singular 'investor' when newPositions is 1", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        institutionalAccumulation={{
          percentile: 70,
          newPositions: 1,
          topFunds: ["Bridgewater Associates"],
        }}
      />
    )
    expect(
      screen.getByText(/1 curated institutional investor independently initiated/)
    ).toBeInTheDocument()
  })

  it("shows ML-promoted badge when mlOverride is promoted", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={2.5}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        mlOverride="promoted"
      />
    )
    expect(screen.getByText(/ml-promoted/i)).toBeInTheDocument()
  })

  it("does not show ML badge when mlOverride is none", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={2.5}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        mlOverride="none"
      />
    )
    expect(screen.queryByText(/ml-promoted|ml-demoted/i)).not.toBeInTheDocument()
  })
})
