import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreChart } from "../score-chart"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  ComposedChart: ({ children }: { children: React.ReactNode }) => <div data-testid="composed-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
}))

const mockData = [
  { date: "2026-01-01", score: 80, signal: "strong" },
  { date: "2026-01-08", score: 82, signal: "strong" },
  { date: "2026-01-15", score: 85, signal: "strong" },
  { date: "2026-01-22", score: 87, signal: "strong" },
]

describe("ScoreChart", () => {
  it("renders chart when data is provided", () => {
    render(<ScoreChart data={mockData} timeRange="3M" showBenchmark={false} />)
    expect(screen.getByTestId("score-chart")).toBeInTheDocument()
    expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
  })

  it("renders empty state when no data", () => {
    render(<ScoreChart data={[]} timeRange="3M" showBenchmark={false} />)
    expect(screen.getByTestId("score-chart-empty")).toBeInTheDocument()
    expect(screen.getByText("Score tracking begins after the next scoring run")).toBeInTheDocument()
    expect(screen.getByText("Scores are computed weekly")).toBeInTheDocument()
  })

  it("renders empty state with single data point", () => {
    render(<ScoreChart data={[{ date: "2026-01-01", score: 80 }]} timeRange="3M" showBenchmark={false} />)
    expect(screen.getByTestId("score-chart-empty")).toBeInTheDocument()
  })

  it("renders score context strip", () => {
    render(
      <ScoreChart
        data={mockData}
        timeRange="3M"
        showBenchmark={false}
        universeRank="Top 3%"
        scoringFrequency="Scored weekly"
        lastScored="2h ago"
      />
    )
    expect(screen.getByText("Top 3%")).toBeInTheDocument()
    expect(screen.getByText("Scored weekly")).toBeInTheDocument()
  })
})
