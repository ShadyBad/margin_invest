import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { StatsSummary } from "../stats-summary"

const mockStats = {
  cagr: 0.1234,
  excessCagr: 0.0456,
  sharpe: 1.45,
  sortino: 2.1,
  maxDrawdown: -0.25,
  winRate: 0.58,
  informationRatio: 0.72,
  totalReturn: 1.85,
  benchmarkReturn: 1.2,
  numMonths: 60,
  avgTurnover: 0.15,
  calmarRatio: 0.49,
}

describe("StatsSummary", () => {
  it("renders all stat labels", () => {
    render(<StatsSummary stats={mockStats} />)

    expect(screen.getByText("PERFORMANCE STATISTICS")).toBeInTheDocument()
    expect(screen.getByText("CAGR")).toBeInTheDocument()
    expect(screen.getByText("Excess CAGR")).toBeInTheDocument()
    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument()
    expect(screen.getByText("Sortino Ratio")).toBeInTheDocument()
    expect(screen.getByText("Max Drawdown")).toBeInTheDocument()
    expect(screen.getByText("Win Rate")).toBeInTheDocument()
    expect(screen.getByText("Information Ratio")).toBeInTheDocument()
    expect(screen.getByText("Total Return")).toBeInTheDocument()
    expect(screen.getByText("Benchmark Return")).toBeInTheDocument()
    expect(screen.getByText("Months")).toBeInTheDocument()
    expect(screen.getByText("Avg Turnover")).toBeInTheDocument()
    expect(screen.getByText("Calmar Ratio")).toBeInTheDocument()
  })

  it("formats percentages correctly", () => {
    render(<StatsSummary stats={mockStats} />)

    // CAGR: 0.1234 => 12.34%
    expect(screen.getByTestId("stat-cagr")).toHaveTextContent("12.34%")
    // Max Drawdown: -0.25 => -25.00%
    expect(screen.getByTestId("stat-maxDrawdown")).toHaveTextContent("-25.00%")
    // Win Rate: 0.58 => 58.00%
    expect(screen.getByTestId("stat-winRate")).toHaveTextContent("58.00%")
  })

  it("formats ratios correctly", () => {
    render(<StatsSummary stats={mockStats} />)

    expect(screen.getByTestId("stat-sharpe")).toHaveTextContent("1.45")
    expect(screen.getByTestId("stat-sortino")).toHaveTextContent("2.10")
    expect(screen.getByTestId("stat-informationRatio")).toHaveTextContent("0.72")
  })

  it("colors positive values green and negative red", () => {
    render(<StatsSummary stats={mockStats} />)

    const cagrValue = screen.getByTestId("stat-cagr")
    expect(cagrValue.className).toContain("text-bullish")

    const drawdownValue = screen.getByTestId("stat-maxDrawdown")
    expect(drawdownValue.className).toContain("text-bearish")
  })

  it("shows month count", () => {
    render(<StatsSummary stats={mockStats} />)

    expect(screen.getByTestId("stat-numMonths")).toHaveTextContent("60")
  })

  it("handles missing calmar ratio", () => {
    const statsWithoutCalmar = { ...mockStats, calmarRatio: undefined }
    render(<StatsSummary stats={statsWithoutCalmar} />)

    expect(screen.queryByText("Calmar Ratio")).not.toBeInTheDocument()
  })
})
