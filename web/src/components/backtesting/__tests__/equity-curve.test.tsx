import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { EquityCurve } from "../equity-curve"
import type { EquityCurvePoint, RegimeBand } from "../equity-curve"

function makePoints(count: number): EquityCurvePoint[] {
  const points: EquityCurvePoint[] = []
  for (let i = 0; i < count; i++) {
    const month = String((i % 12) + 1).padStart(2, "0")
    const year = 2005 + Math.floor(i / 12)
    points.push({
      date: `${year}-${month}-28`,
      portfolioValue: 1.0 + i * 0.02,
      benchmarkValue: 1.0 + i * 0.01,
      drawdown: i >= 5 && i <= 10 ? -0.05 * (i - 4) : 0,
    })
  }
  return points
}

describe("EquityCurve", () => {
  it("renders SVG chart with portfolio and benchmark lines", () => {
    const points = makePoints(24)

    render(<EquityCurve points={points} />)

    const svg = screen.getByTestId("equity-curve-chart")
    expect(svg).toBeInTheDocument()
    expect(svg.tagName.toLowerCase()).toBe("svg")

    const portfolioLine = screen.getByTestId("equity-curve-portfolio-line")
    expect(portfolioLine).toBeInTheDocument()
    expect(portfolioLine.tagName.toLowerCase()).toBe("polyline")

    const benchmarkLine = screen.getByTestId("equity-curve-benchmark-line")
    expect(benchmarkLine).toBeInTheDocument()
    expect(benchmarkLine.tagName.toLowerCase()).toBe("polyline")

    // Legend should be present
    const legend = screen.getByTestId("equity-curve-legend")
    expect(legend).toBeInTheDocument()
    expect(legend.textContent).toContain("Portfolio")
    expect(legend.textContent).toContain("Benchmark")
  })

  it("renders regime bands as colored rectangles when provided", () => {
    const points = makePoints(24)
    const regimeBands: RegimeBand[] = [
      { startIndex: 0, endIndex: 5, regime: "bull" },
      { startIndex: 6, endIndex: 12, regime: "bear" },
      { startIndex: 13, endIndex: 18, regime: "sideways" },
      { startIndex: 19, endIndex: 23, regime: "crisis" },
    ]

    render(<EquityCurve points={points} regimeBands={regimeBands} />)

    const bands = screen.getAllByTestId(/^equity-curve-regime-band-/)
    expect(bands).toHaveLength(4)

    // Each band should be a rect element
    for (const band of bands) {
      expect(band.tagName.toLowerCase()).toBe("rect")
    }

    // Verify specific regime bands exist
    expect(screen.getByTestId("equity-curve-regime-band-0")).toBeInTheDocument()
    expect(screen.getByTestId("equity-curve-regime-band-1")).toBeInTheDocument()
    expect(screen.getByTestId("equity-curve-regime-band-2")).toBeInTheDocument()
    expect(screen.getByTestId("equity-curve-regime-band-3")).toBeInTheDocument()
  })

  it("shows drawdown shading when drawdown values are negative", () => {
    const points = makePoints(24)
    // Points index 5-10 have negative drawdown via makePoints

    render(<EquityCurve points={points} showDrawdown={true} />)

    const drawdownArea = screen.getByTestId("equity-curve-drawdown-area")
    expect(drawdownArea).toBeInTheDocument()
    // Drawdown area is rendered as a path element (filled polygon)
    expect(drawdownArea.tagName.toLowerCase()).toBe("path")
  })

  it("handles empty points array with empty state message", () => {
    render(<EquityCurve points={[]} />)

    const emptyState = screen.getByTestId("equity-curve-empty")
    expect(emptyState).toBeInTheDocument()
    expect(emptyState.textContent).toContain("No equity curve data")

    // Should not render SVG
    expect(screen.queryByTestId("equity-curve-chart")).not.toBeInTheDocument()
  })

  it("hides drawdown when showDrawdown is false", () => {
    const points = makePoints(24)

    render(<EquityCurve points={points} showDrawdown={false} />)

    // SVG should render
    expect(screen.getByTestId("equity-curve-chart")).toBeInTheDocument()

    // Drawdown area should not be present
    expect(screen.queryByTestId("equity-curve-drawdown-area")).not.toBeInTheDocument()
  })

  it("renders without regime bands when not provided", () => {
    const points = makePoints(12)

    render(<EquityCurve points={points} />)

    expect(screen.getByTestId("equity-curve-chart")).toBeInTheDocument()
    expect(screen.queryAllByTestId(/^equity-curve-regime-band-/)).toHaveLength(0)
  })

  it("shows tooltip on hover with correct data", () => {
    const points = makePoints(12)

    render(<EquityCurve points={points} />)

    // Tooltip should not be visible initially
    expect(screen.queryByTestId("equity-curve-tooltip")).not.toBeInTheDocument()

    // Hover over a hit area
    const hitArea = screen.getByTestId("equity-curve-hit-0")
    fireEvent.mouseEnter(hitArea)

    // Tooltip should now be visible
    const tooltip = screen.getByTestId("equity-curve-tooltip")
    expect(tooltip).toBeInTheDocument()
    expect(tooltip.textContent).toContain("Portfolio")
    expect(tooltip.textContent).toContain("Benchmark")

    // Mouse leave should hide tooltip
    fireEvent.mouseLeave(hitArea)
    expect(screen.queryByTestId("equity-curve-tooltip")).not.toBeInTheDocument()
  })
})
