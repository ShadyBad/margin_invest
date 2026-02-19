import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { InstitutionalMetrics } from "../institutional-metrics"
import type { InstitutionalMetrics as Metrics } from "@/lib/compute-institutional-metrics"

// Mock ProGate to passthrough for testing
vi.mock("../pro-gate", () => ({
  ProGate: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pro-gate">{children}</div>
  ),
}))

const metrics: Metrics = {
  sharpeRatio: 1.84,
  maxDrawdown: -0.124,
  volatility: 18.2,
  avgProfitMargin: null,
  riskClassification: "Moderate",
}

describe("InstitutionalMetrics", () => {
  it("renders all metric cells", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("1.84")).toBeInTheDocument()
    expect(screen.getByText("-12.4%")).toBeInTheDocument()
    expect(screen.getByText("18.2%")).toBeInTheDocument()
    expect(screen.getByText("Moderate")).toBeInTheDocument()
  })

  it("renders metric labels in uppercase", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("SHARPE RATIO")).toBeInTheDocument()
    expect(screen.getByText("MAX DRAWDOWN")).toBeInTheDocument()
    expect(screen.getByText("VOLATILITY")).toBeInTheDocument()
  })

  it("wraps in ProGate", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByTestId("pro-gate")).toBeInTheDocument()
  })

  it("renders nothing when metrics is null", () => {
    const { container } = render(<InstitutionalMetrics metrics={null} />)
    expect(container.firstChild).toBeNull()
  })

  it("shows N/A for null avgProfitMargin", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("N/A")).toBeInTheDocument()
  })
})
