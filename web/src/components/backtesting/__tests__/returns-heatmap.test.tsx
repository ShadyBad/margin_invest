import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { ReturnsHeatmap } from "../returns-heatmap"

const mockReturns = [
  { date: "2024-01-01", portfolio_return: 0.05, benchmark_return: 0.02 }, // +3% excess (strong positive)
  { date: "2024-02-01", portfolio_return: 0.03, benchmark_return: 0.02 }, // +1% excess (positive)
  { date: "2024-03-01", portfolio_return: 0.01, benchmark_return: 0.02 }, // -1% excess (negative)
  { date: "2024-04-01", portfolio_return: -0.01, benchmark_return: 0.02 }, // -3% excess (strong negative)
  { date: "2025-01-01", portfolio_return: 0.04, benchmark_return: 0.01 }, // +3% excess (strong positive, different year)
]

describe("ReturnsHeatmap", () => {
  it("renders heatmap with data", () => {
    render(<ReturnsHeatmap returns={mockReturns} />)

    const heatmap = screen.getByTestId("returns-heatmap")
    expect(heatmap).toBeInTheDocument()

    // Year labels should be visible
    expect(screen.getByText("2024")).toBeInTheDocument()
    expect(screen.getByText("2025")).toBeInTheDocument()

    // Month abbreviations should be visible
    expect(screen.getByText("Jan")).toBeInTheDocument()
    expect(screen.getByText("Dec")).toBeInTheDocument()
  })

  it("shows correct number of cells", () => {
    render(<ReturnsHeatmap returns={mockReturns} />)

    // 2 years x 12 months = 24 cells total
    const cells = screen.getAllByRole("cell")
    expect(cells).toHaveLength(24)

    // Each data cell should have proper testid
    expect(screen.getByTestId("heatmap-cell-2024-01")).toBeInTheDocument()
    expect(screen.getByTestId("heatmap-cell-2024-02")).toBeInTheDocument()
    expect(screen.getByTestId("heatmap-cell-2024-03")).toBeInTheDocument()
    expect(screen.getByTestId("heatmap-cell-2024-04")).toBeInTheDocument()
    expect(screen.getByTestId("heatmap-cell-2025-01")).toBeInTheDocument()
  })

  it("shows empty state when no data", () => {
    render(<ReturnsHeatmap returns={[]} />)

    expect(screen.getByText("No return data available.")).toBeInTheDocument()
    expect(screen.getByTestId("returns-heatmap")).toBeInTheDocument()
  })

  it("cells have correct color classes for positive/negative returns", () => {
    render(<ReturnsHeatmap returns={mockReturns} />)

    // Strong positive (>2%): bg-bullish/80
    const strongPositive = screen.getByTestId("heatmap-cell-2024-01")
    expect(strongPositive.className).toContain("bg-bullish/80")
    expect(strongPositive).toHaveTextContent("3.0%")

    // Positive (0-2%): bg-bullish/30
    const positive = screen.getByTestId("heatmap-cell-2024-02")
    expect(positive.className).toContain("bg-bullish/30")
    expect(positive).toHaveTextContent("1.0%")

    // Negative (-2% to 0): bg-bearish/30
    const negative = screen.getByTestId("heatmap-cell-2024-03")
    expect(negative.className).toContain("bg-bearish/30")
    expect(negative).toHaveTextContent("-1.0%")

    // Strong negative (<-2%): bg-bearish/80
    const strongNegative = screen.getByTestId("heatmap-cell-2024-04")
    expect(strongNegative.className).toContain("bg-bearish/80")
    expect(strongNegative).toHaveTextContent("-3.0%")
  })
})
