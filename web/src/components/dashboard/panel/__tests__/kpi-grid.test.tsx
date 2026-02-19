import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KpiGrid } from "../kpi-grid"

describe("KpiGrid", () => {
  const baseProps = {
    sharpeRatio: 1.42,
    maxDrawdown: -0.15,
    volatility: 22.5,
    avgProfitMargin: null,
    allocationWeight: 5,
    scoreDelta: 3.2,
  }

  it("renders all 6 KPI cells", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("SHARPE RATIO")).toBeInTheDocument()
    expect(screen.getByText("MAX DRAWDOWN")).toBeInTheDocument()
    expect(screen.getByText("VOLATILITY")).toBeInTheDocument()
    expect(screen.getByText("AVG PROFIT MARGIN")).toBeInTheDocument()
    expect(screen.getByText("ALLOCATION")).toBeInTheDocument()
    expect(screen.getByText("SCORE DELTA")).toBeInTheDocument()
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
})
