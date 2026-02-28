import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { CapacityChart } from "@/components/backtesting/capacity-chart"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="capacity-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
}))

const rows = [
  { aum: 1e6, cagr: 0.104, sharpe: 0.85, avg_impact_bps: 2 },
  { aum: 1e7, cagr: 0.1, sharpe: 0.8, avg_impact_bps: 8 },
  { aum: 1e8, cagr: 0.08, sharpe: 0.6, avg_impact_bps: 25 },
  { aum: 1e9, cagr: 0.04, sharpe: 0.3, avg_impact_bps: 80 },
]

describe("CapacityChart", () => {
  it("renders the chart", () => {
    render(<CapacityChart rows={rows} breakevenAum={500e6} />)
    expect(screen.getByTestId("capacity-chart")).toBeInTheDocument()
  })

  it("shows breakeven annotation", () => {
    render(<CapacityChart rows={rows} breakevenAum={500e6} />)
    expect(screen.getByTestId("breakeven-callout")).toBeInTheDocument()
    expect(screen.getByTestId("breakeven-callout")).toHaveTextContent("$500M")
  })

  it("shows no breakeven when null", () => {
    render(<CapacityChart rows={rows} breakevenAum={null} />)
    expect(screen.queryByTestId("breakeven-callout")).not.toBeInTheDocument()
  })

  it("renders empty state", () => {
    render(<CapacityChart rows={[]} breakevenAum={null} />)
    expect(screen.getByTestId("capacity-chart")).toBeInTheDocument()
  })
})
