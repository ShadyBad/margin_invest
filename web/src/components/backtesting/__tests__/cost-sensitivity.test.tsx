import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { CostSensitivity } from "../cost-sensitivity"

// Mock recharts to avoid SVG rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sensitivity-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

const rows = [
  { multiplier: 1.0, cagr: 0.104, sharpe: 0.85, max_drawdown: 0.28, cost_drag_bps: 47 },
  { multiplier: 2.0, cagr: 0.089, sharpe: 0.72, max_drawdown: 0.29, cost_drag_bps: 94 },
  { multiplier: 3.0, cagr: 0.074, sharpe: 0.59, max_drawdown: 0.30, cost_drag_bps: 141 },
]

describe("CostSensitivity", () => {
  it("renders the component", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByTestId("cost-sensitivity")).toBeInTheDocument()
  })

  it("renders all multiplier columns", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("Base (1x)")).toBeInTheDocument()
    expect(screen.getByText("Conservative (2x)")).toBeInTheDocument()
    expect(screen.getByText("Stress (3x)")).toBeInTheDocument()
  })

  it("renders CAGR row", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("CAGR")).toBeInTheDocument()
  })

  it("renders chart container", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByTestId("sensitivity-chart")).toBeInTheDocument()
  })

  it("renders empty state when no rows", () => {
    render(<CostSensitivity rows={[]} />)
    expect(screen.getByTestId("cost-sensitivity")).toBeInTheDocument()
  })

  it("renders Sharpe row", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("Sharpe")).toBeInTheDocument()
  })

  it("renders Max DD row", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("Max DD")).toBeInTheDocument()
  })

  it("renders Cost Drag row", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("Cost Drag")).toBeInTheDocument()
  })

  it("formats CAGR as percentages with 2 decimal places", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("10.40%")).toBeInTheDocument()
    expect(screen.getByText("8.90%")).toBeInTheDocument()
    expect(screen.getByText("7.40%")).toBeInTheDocument()
  })

  it("formats Sharpe with 2 decimal places", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("0.85")).toBeInTheDocument()
    expect(screen.getByText("0.72")).toBeInTheDocument()
    expect(screen.getByText("0.59")).toBeInTheDocument()
  })

  it("formats Max DD as percentages with 2 decimal places", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("28.00%")).toBeInTheDocument()
    expect(screen.getByText("29.00%")).toBeInTheDocument()
    expect(screen.getByText("30.00%")).toBeInTheDocument()
  })

  it("formats cost drag as integer bps", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("47 bps")).toBeInTheDocument()
    expect(screen.getByText("94 bps")).toBeInTheDocument()
    expect(screen.getByText("141 bps")).toBeInTheDocument()
  })

  it("renders section title", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("COST SENSITIVITY")).toBeInTheDocument()
  })
})
