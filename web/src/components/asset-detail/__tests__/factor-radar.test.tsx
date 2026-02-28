import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  RadarChart: ({ children }: { children: ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: ({ dataKey }: { dataKey: string }) => (
    <div data-testid="polar-angle-axis" data-key={dataKey} />
  ),
  Radar: ({ name, dataKey }: { name: string; dataKey: string }) => (
    <div data-testid={`radar-${name}`} data-key={dataKey} />
  ),
  Legend: () => <div data-testid="legend" />,
}))

import { FactorRadar } from "../factor-radar"
import type { FactorBreakdownResponse } from "@/lib/api/types"

const quality: FactorBreakdownResponse = {
  factor_name: "quality",
  weight: 0.3,
  average_percentile: 87,
  sub_scores: [
    { name: "piotroski_f_score", raw_value: 7, percentile_rank: 85, detail: "Strong" },
    { name: "gross_profitability", raw_value: 0.43, percentile_rank: 89, detail: "Above avg" },
  ],
}

const value: FactorBreakdownResponse = {
  factor_name: "value",
  weight: 0.4,
  average_percentile: 72,
  sub_scores: [
    { name: "ev_fcf", raw_value: 18.5, percentile_rank: 72, detail: "Reasonable" },
  ],
}

const momentum: FactorBreakdownResponse = {
  factor_name: "momentum",
  weight: 0.3,
  average_percentile: 94,
  sub_scores: [
    { name: "price_momentum", raw_value: 0.15, percentile_rank: 94, detail: "Strong" },
  ],
}

describe("FactorRadar", () => {
  it("renders radar chart with stock data", () => {
    render(
      <FactorRadar quality={quality} value={value} momentum={momentum} />
    )
    expect(screen.getByTestId("factor-radar")).toBeInTheDocument()
    expect(screen.getByTestId("radar-chart")).toBeInTheDocument()
  })

  it("displays section header with sector name", () => {
    render(
      <FactorRadar
        quality={quality}
        value={value}
        momentum={momentum}
        sectorName="Technology"
      />
    )
    expect(screen.getByText("Factor Profile")).toBeInTheDocument()
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
  })

  it("shows percentile values for each axis", () => {
    render(
      <FactorRadar quality={quality} value={value} momentum={momentum} />
    )
    expect(screen.getByText(/87/)).toBeInTheDocument()
    expect(screen.getByText(/72/)).toBeInTheDocument()
    expect(screen.getByText(/94/)).toBeInTheDocument()
  })

  it("renders three radar series", () => {
    render(
      <FactorRadar quality={quality} value={value} momentum={momentum} />
    )
    expect(screen.getByTestId("radar-Stock")).toBeInTheDocument()
    expect(screen.getByTestId("radar-Sector Median")).toBeInTheDocument()
    expect(screen.getByTestId("radar-Sector Top 10%")).toBeInTheDocument()
  })

  it("desktop wrapper hidden on mobile", () => {
    render(
      <FactorRadar quality={quality} value={value} momentum={momentum} />
    )
    const desktop = screen.getByTestId("radar-desktop")
    expect(desktop.className).toContain("hidden")
    expect(desktop.className).toContain("md:block")
  })

  it("mobile wrapper visible on mobile only", () => {
    render(
      <FactorRadar quality={quality} value={value} momentum={momentum} />
    )
    const mobile = screen.getByTestId("radar-mobile")
    expect(mobile.className).toContain("md:hidden")
  })

  it("dimmed variant adds opacity-60 class to container", () => {
    render(
      <FactorRadar
        quality={quality}
        value={value}
        momentum={momentum}
        variant="dimmed"
      />
    )
    const container = screen.getByTestId("factor-radar")
    expect(container.className).toContain("opacity-60")
  })
})
