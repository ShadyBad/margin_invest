import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KpiGrid } from "../kpi-grid"

describe("KpiGrid", () => {
  const baseProps = {
    sharpeRatio: 1.42,
    maxDrawdown: -0.15,
    volatility: 22.5,
    avgProfitMargin: null as number | null,
    scoreDelta: 3.2,
    delta: 0.155,
  }

  it("renders all 6 KPI cells", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("SHARPE RATIO")).toBeInTheDocument()
    expect(screen.getByText("MAX DRAWDOWN")).toBeInTheDocument()
    expect(screen.getByText("VOLATILITY")).toBeInTheDocument()
    expect(screen.getByText("AVG PROFIT MARGIN")).toBeInTheDocument()
    expect(screen.getByText("SCORE DELTA")).toBeInTheDocument()
    expect(screen.getByText("PRICE DELTA")).toBeInTheDocument()
  })

  it("renders numeric values correctly", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("1.42")).toBeInTheDocument()
    expect(screen.getByText("-15.0%")).toBeInTheDocument()
    expect(screen.getByText("22.5%")).toBeInTheDocument()
  })

  it("renders null values as dashes", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByTestId("kpi-avg-profit-margin-value")).toHaveTextContent("\u2014")
  })

  it("renders score delta with sign prefix", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("+3.2")).toBeInTheDocument()
  })

  it("renders null score delta as dash with unavailable reason", () => {
    render(<KpiGrid {...baseProps} scoreDelta={null} />)
    expect(screen.getByTestId("kpi-score-delta-value")).toHaveTextContent("\u2014")
    expect(screen.getByText("First scoring run")).toBeInTheDocument()
  })

  it("renders negative score delta without plus sign", () => {
    render(<KpiGrid {...baseProps} scoreDelta={-2.5} />)
    expect(screen.getByText("-2.5")).toBeInTheDocument()
  })

  it("renders positive price delta with plus sign and percentage", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByTestId("kpi-price-delta-value")).toHaveTextContent("+15.5%")
  })

  it("renders negative price delta with percentage", () => {
    render(<KpiGrid {...baseProps} delta={-0.082} />)
    expect(screen.getByTestId("kpi-price-delta-value")).toHaveTextContent("-8.2%")
  })

  it("renders null price delta with default unavailable reason", () => {
    render(<KpiGrid {...baseProps} delta={null} />)
    expect(screen.getByTestId("kpi-price-delta-value")).toHaveTextContent("\u2014")
    expect(screen.getByText("Requires valuation data")).toBeInTheDocument()
  })

  it("renders null price delta with custom unavailable reason", () => {
    render(<KpiGrid {...baseProps} delta={null} deltaUnavailable="IPO too recent" />)
    expect(screen.getByTestId("kpi-price-delta-value")).toHaveTextContent("\u2014")
    expect(screen.getByText("IPO too recent")).toBeInTheDocument()
  })

  it("passes unavailable reason for metrics when null", () => {
    render(
      <KpiGrid
        {...baseProps}
        sharpeRatio={null}
        sharpeRatioUnavailable="Insufficient history"
      />
    )
    expect(screen.getByTestId("kpi-sharpe-ratio-value")).toHaveTextContent("\u2014")
    expect(screen.getByText("Insufficient history")).toBeInTheDocument()
  })

  it("price delta cell spans full width", () => {
    const { container } = render(<KpiGrid {...baseProps} />)
    const colSpanDiv = container.querySelector(".col-span-2")
    expect(colSpanDiv).toBeInTheDocument()
    expect(colSpanDiv?.querySelector('[data-testid="kpi-price-delta-value"]')).toBeInTheDocument()
  })
})
