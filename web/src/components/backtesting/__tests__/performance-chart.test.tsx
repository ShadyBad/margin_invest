import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PerformanceChart } from "../performance-chart"

const mockSnapshots = [
  {
    date: "2024-01-31",
    portfolio_value: 10200,
    benchmark_value: 10100,
    portfolio_return: 0.02,
    benchmark_return: 0.01,
  },
  {
    date: "2024-02-29",
    portfolio_value: 10500,
    benchmark_value: 10250,
    portfolio_return: 0.03,
    benchmark_return: 0.015,
  },
  {
    date: "2024-03-31",
    portfolio_value: 10400,
    benchmark_value: 10350,
    portfolio_return: -0.01,
    benchmark_return: 0.01,
  },
  {
    date: "2024-04-30",
    portfolio_value: 10800,
    benchmark_value: 10400,
    portfolio_return: 0.04,
    benchmark_return: 0.005,
  },
  {
    date: "2024-05-31",
    portfolio_value: 11000,
    benchmark_value: 10500,
    portfolio_return: 0.02,
    benchmark_return: 0.01,
  },
]

describe("PerformanceChart", () => {
  it("renders SVG chart with data", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const chart = screen.getByTestId("performance-chart")
    expect(chart).toBeInTheDocument()
    expect(chart.tagName.toLowerCase()).toBe("svg")
  })

  it("shows portfolio and benchmark lines", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const portfolioLine = screen.getByTestId("portfolio-line")
    const benchmarkLine = screen.getByTestId("benchmark-line")

    expect(portfolioLine).toBeInTheDocument()
    expect(benchmarkLine).toBeInTheDocument()

    // Both lines should have valid points attributes
    expect(portfolioLine.getAttribute("points")).toBeTruthy()
    expect(benchmarkLine.getAttribute("points")).toBeTruthy()

    // Points should contain numeric coordinates
    const portfolioPoints = portfolioLine.getAttribute("points")!
    expect(portfolioPoints).toMatch(/\d+(\.\d+)?,\d+(\.\d+)?/)
  })

  it("shows legend", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const legend = screen.getByTestId("chart-legend")
    expect(legend).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Benchmark")).toBeInTheDocument()
  })

  it("shows empty message when no snapshots", () => {
    render(<PerformanceChart snapshots={[]} />)
    expect(screen.getByText("No chart data available.")).toBeInTheDocument()
    expect(screen.queryByTestId("performance-chart")).not.toBeInTheDocument()
    expect(screen.getByTestId("performance-chart-empty")).toBeInTheDocument()
  })

  it("shows custom legend labels when provided", () => {
    render(
      <PerformanceChart
        snapshots={mockSnapshots}
        portfolioLabel="Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)"
        benchmarkLabel="S&P 500 (SPY Total Return)"
      />,
    )
    expect(
      screen.getByText(
        "Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)",
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText("S&P 500 (SPY Total Return)"),
    ).toBeInTheDocument()
  })

  it("shows default legend labels when props omitted", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Benchmark")).toBeInTheDocument()
  })

  it("handles single snapshot gracefully", () => {
    const singleSnapshot = [
      {
        date: "2024-01-31",
        portfolio_value: 10200,
        benchmark_value: 10100,
        portfolio_return: 0.02,
        benchmark_return: 0.01,
      },
    ]

    render(<PerformanceChart snapshots={singleSnapshot} />)
    const chart = screen.getByTestId("performance-chart")
    expect(chart).toBeInTheDocument()

    // Lines should still render (as single points)
    const portfolioLine = screen.getByTestId("portfolio-line")
    const benchmarkLine = screen.getByTestId("benchmark-line")
    expect(portfolioLine).toBeInTheDocument()
    expect(benchmarkLine).toBeInTheDocument()

    // Points should be valid numbers (no NaN or Infinity)
    const points = portfolioLine.getAttribute("points")!
    const coords = points.split(",")
    for (const coord of coords) {
      const num = parseFloat(coord)
      expect(Number.isFinite(num)).toBe(true)
    }
  })

  it("shows tooltip on hover with date", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)
    expect(hitAreas.length).toBe(mockSnapshots.length)

    fireEvent.mouseEnter(hitAreas[1])
    const tooltip = screen.getByTestId("chart-tooltip")
    expect(tooltip).toBeInTheDocument()
    expect(tooltip.textContent).toContain("2024-02")
  })

  it("hides tooltip on mouse leave", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)

    fireEvent.mouseEnter(hitAreas[0])
    expect(screen.getByTestId("chart-tooltip")).toBeInTheDocument()

    fireEvent.mouseLeave(hitAreas[0])
    expect(screen.queryByTestId("chart-tooltip")).not.toBeInTheDocument()
  })

  it("does not render tooltips for empty snapshots", () => {
    render(<PerformanceChart snapshots={[]} />)
    expect(screen.queryAllByTestId(/^chart-hit-area-/)).toHaveLength(0)
  })
})
