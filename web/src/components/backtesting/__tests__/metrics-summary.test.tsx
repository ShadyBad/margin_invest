import { render, screen } from "@testing-library/react"
import { MetricsSummary } from "@/components/backtesting/metrics-summary"

const baseMetrics = {
  cagr: 0.104,
  excess_cagr: 0.031,
  sharpe_ratio: 0.85,
  sortino_ratio: 1.18,
  max_drawdown: 0.28,
  win_rate: 0.57,
  information_ratio: 0.62,
  total_return: 5.42,
  benchmark_total_return: 3.87,
  num_months: 240,
  avg_turnover: 0.18,
}

describe("MetricsSummary", () => {
  it("renders all base metrics", () => {
    render(<MetricsSummary metrics={baseMetrics} />)
    expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    expect(screen.getByTestId("metric-cagr")).toBeInTheDocument()
    expect(screen.getByTestId("metric-excess-cagr")).toBeInTheDocument()
    expect(screen.getByTestId("metric-sharpe-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-sortino-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-max-drawdown")).toBeInTheDocument()
    expect(screen.getByTestId("metric-win-rate")).toBeInTheDocument()
    expect(screen.getByTestId("metric-information-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-total-return")).toBeInTheDocument()
    expect(screen.getByTestId("metric-benchmark-return")).toBeInTheDocument()
    expect(screen.getByTestId("metric-num-months")).toBeInTheDocument()
    expect(screen.getByTestId("metric-avg-turnover")).toBeInTheDocument()
  })

  it("shows cost drag card when cost_drag_bps > 0", () => {
    const metrics = { ...baseMetrics, cost_drag_bps: 110, gross_cagr: 0.115 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cost-drag")).toBeInTheDocument()
    expect(screen.getByTestId("metric-cost-drag")).toHaveTextContent("110")
  })

  it("hides cost drag card when cost_drag_bps is 0", () => {
    const metrics = { ...baseMetrics, cost_drag_bps: 0 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.queryByTestId("metric-cost-drag")).not.toBeInTheDocument()
  })

  it("hides cost drag card when cost_drag_bps is undefined", () => {
    render(<MetricsSummary metrics={baseMetrics} />)
    expect(screen.queryByTestId("metric-cost-drag")).not.toBeInTheDocument()
  })

  it("shows gross CAGR annotation", () => {
    const metrics = { ...baseMetrics, gross_cagr: 0.115 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cagr")).toHaveTextContent("gross:")
  })

  it("shows gross Sharpe annotation", () => {
    const metrics = { ...baseMetrics, gross_sharpe: 0.92 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-sharpe-ratio")).toHaveTextContent("gross:")
  })

  it("shows gross Max Drawdown annotation", () => {
    const metrics = { ...baseMetrics, gross_max_drawdown: 0.25 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-max-drawdown")).toHaveTextContent("gross:")
  })

  it("does not show gross annotations when fields missing", () => {
    render(<MetricsSummary metrics={baseMetrics} />)
    expect(screen.getByTestId("metric-cagr")).not.toHaveTextContent("gross:")
    expect(screen.getByTestId("metric-sharpe-ratio")).not.toHaveTextContent("gross:")
    expect(screen.getByTestId("metric-max-drawdown")).not.toHaveTextContent("gross:")
  })

  it("formats gross CAGR as percentage", () => {
    const metrics = { ...baseMetrics, gross_cagr: 0.115 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cagr")).toHaveTextContent("11.50%")
  })

  it("formats gross Sharpe as ratio", () => {
    const metrics = { ...baseMetrics, gross_sharpe: 0.92 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-sharpe-ratio")).toHaveTextContent("0.92")
  })

  it("formats cost drag as bps/yr", () => {
    const metrics = { ...baseMetrics, cost_drag_bps: 110 }
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cost-drag")).toHaveTextContent("110 bps/yr")
  })
})
