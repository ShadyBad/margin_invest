import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MarketContextSidebar } from "../market-context-sidebar"

describe("MarketContextSidebar", () => {
  it("renders universe size formatted with commas", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
      />
    )

    expect(screen.getByText("3,056")).toBeInTheDocument()
  })

  it("renders scored count formatted with commas", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={1234}
        universeSize={3056}
      />
    )

    expect(screen.getByText("1,234")).toBeInTheDocument()
  })

  it("renders picks count", () => {
    render(
      <MarketContextSidebar
        pickCount={7}
        totalScored={500}
        universeSize={3056}
      />
    )

    expect(screen.getByText("7")).toBeInTheDocument()
  })

  it("shows engine version when provided", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
        engineVersion="v4.2.1"
      />
    )

    expect(screen.getByText("v4.2.1")).toBeInTheDocument()
  })

  it("handles null values gracefully with em-dash", () => {
    render(
      <MarketContextSidebar
        pickCount={0}
        totalScored={null}
        universeSize={null}
      />
    )

    const emDashes = screen.getAllByText("\u2014")
    expect(emDashes.length).toBeGreaterThanOrEqual(2)
  })

  it("renders Market Context header", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
      />
    )

    expect(screen.getByText("Market Context")).toBeInTheDocument()
  })

  it("shows last scoring run when provided", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
        lastScoringRun="2026-03-09T10:30:00Z"
      />
    )

    expect(screen.getByTestId("last-run-value")).toHaveTextContent(/\w/)
  })

  it("does not render engine row when engineVersion is not provided", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
      />
    )

    expect(screen.queryByText("Engine")).not.toBeInTheDocument()
  })

  it("does not render last run row when lastScoringRun is not provided", () => {
    render(
      <MarketContextSidebar
        pickCount={12}
        totalScored={500}
        universeSize={3056}
      />
    )

    expect(screen.queryByText("Last Run")).not.toBeInTheDocument()
  })
})
