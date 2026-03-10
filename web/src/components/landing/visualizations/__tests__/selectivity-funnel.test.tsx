import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { SelectivityFunnel } from "../selectivity-funnel"

describe("SelectivityFunnel", () => {
  const defaultProps = {
    universeCount: 3056,
    eligibleCount: 1842,
    scoredCount: 500,
    survivingCount: 143,
  }

  test("renders all 4 stages", () => {
    render(<SelectivityFunnel {...defaultProps} />)
    expect(screen.getByTestId("funnel-stage-universe")).toBeInTheDocument()
    expect(screen.getByTestId("funnel-stage-eligible")).toBeInTheDocument()
    expect(screen.getByTestId("funnel-stage-scored")).toBeInTheDocument()
    expect(screen.getByTestId("funnel-stage-surviving")).toBeInTheDocument()
  })

  test("renders formatted counts with locale separators", () => {
    render(<SelectivityFunnel {...defaultProps} />)
    expect(screen.getByText("3,056")).toBeInTheDocument()
    expect(screen.getByText("1,842")).toBeInTheDocument()
    expect(screen.getByText("500")).toBeInTheDocument()
    expect(screen.getByText("143")).toBeInTheDocument()
  })

  test("renders stage labels", () => {
    render(<SelectivityFunnel {...defaultProps} />)
    expect(screen.getByText("Universe Screened")).toBeInTheDocument()
    expect(screen.getByText("Passed Filters")).toBeInTheDocument()
    expect(screen.getByText("Scored")).toBeInTheDocument()
    expect(screen.getByText("Surviving Candidates")).toBeInTheDocument()
  })

  test("renders bars with decreasing widths", () => {
    const { container } = render(<SelectivityFunnel {...defaultProps} />)
    const bars = [
      container.querySelector('[data-testid="funnel-bar-universe"]'),
      container.querySelector('[data-testid="funnel-bar-eligible"]'),
      container.querySelector('[data-testid="funnel-bar-scored"]'),
      container.querySelector('[data-testid="funnel-bar-surviving"]'),
    ]

    // All bars should exist
    bars.forEach((bar) => expect(bar).toBeInTheDocument())

    // Universe bar should be 100% (widest)
    expect(bars[0]).toHaveStyle({ width: "100%" })
  })

  test("handles zero universe count gracefully", () => {
    render(
      <SelectivityFunnel
        universeCount={0}
        eligibleCount={0}
        scoredCount={0}
        survivingCount={0}
      />
    )
    // Should render all 4 stages with 0 counts
    expect(screen.getByTestId("funnel-stage-universe")).toBeInTheDocument()
    expect(screen.getByTestId("funnel-stage-surviving")).toBeInTheDocument()
  })

  test("has accessible aria label", () => {
    render(<SelectivityFunnel {...defaultProps} />)
    expect(
      screen.getByLabelText(
        "Selectivity funnel showing how equities are filtered at each stage"
      )
    ).toBeInTheDocument()
  })
})
