import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConvictionEngine } from "../conviction-engine"

describe("ConvictionEngine", () => {
  it("renders opportunity type with description", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="add_on_pullback"
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
        asymmetryRatio={null}
        maxPositionPct={null}
        timingSignal={null}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders timing signal for buy_now", () => {
    render(
      <ConvictionEngine
        opportunityType="mispricing"
        asymmetryRatio={3.1}
        maxPositionPct={4.0}
        timingSignal="buy_now"
      />
    )
    expect(screen.getByText("BUY NOW")).toBeInTheDocument()
  })

  it("renders mispricing opportunity type", () => {
    render(
      <ConvictionEngine
        opportunityType="mispricing"
        asymmetryRatio={2.5}
        maxPositionPct={3.0}
        timingSignal="add_on_pullback"
      />
    )
    expect(screen.getByText("MISPRICING")).toBeInTheDocument()
    expect(screen.getByText(/undervaluing this stock/)).toBeInTheDocument()
  })

  it("renders with null asymmetry and position", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        asymmetryRatio={null}
        maxPositionPct={null}
        timingSignal={null}
      />
    )
    expect(screen.getByText("COMPOUNDER")).toBeInTheDocument()
    // Null values should render dashes
    expect(screen.getByTestId("conviction-engine")).toBeInTheDocument()
  })
})
