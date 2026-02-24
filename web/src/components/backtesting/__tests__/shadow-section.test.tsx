import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ShadowSection } from "../shadow-section"

describe("ShadowSection", () => {
  it("renders cannot-be-backdated badge", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.0}
        maxDrawdown={0.0}
        numDays={1}
        positions={[]}
      />
    )
    expect(screen.getByText(/cannot be backdated/i)).toBeInTheDocument()
  })

  it("renders tracking-since date", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[{ ticker: "AAPL", weight: 0.5 }]}
      />
    )
    expect(screen.getByText(/2026-02-24/)).toBeInTheDocument()
  })

  it("shows positions when available", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[
          { ticker: "AAPL", weight: 0.5 },
          { ticker: "MSFT", weight: 0.3 },
        ]}
      />
    )
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("shows empty positions message when no positions", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.0}
        maxDrawdown={0.0}
        numDays={1}
        positions={[]}
      />
    )
    expect(screen.getByText(/Tracking has just begun/i)).toBeInTheDocument()
  })

  it("renders data-testid shadow-section", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.0}
        maxDrawdown={0.0}
        numDays={1}
        positions={[]}
      />
    )
    expect(screen.getByTestId("shadow-section")).toBeInTheDocument()
  })

  it("displays total return as percentage", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[]}
      />
    )
    expect(screen.getByText(/1\.20%/)).toBeInTheDocument()
  })

  it("displays max drawdown as percentage", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[]}
      />
    )
    expect(screen.getByText(/0\.50%/)).toBeInTheDocument()
  })

  it("displays number of days tracked", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={42}
        positions={[]}
      />
    )
    expect(screen.getByText(/42/)).toBeInTheDocument()
  })

  it("displays position weights", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[{ ticker: "AAPL", weight: 0.5 }]}
      />
    )
    expect(screen.getByText("50.0%")).toBeInTheDocument()
  })
})
