import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Cell: () => null,
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection />)
    expect(
      screen.getByText(/structure creates measurable advantage/i)
    ).toBeInTheDocument()
  })

  it("renders all 4 proof card titles", () => {
    render(<ProofSection />)
    expect(screen.getByText("Factor Transparency")).toBeInTheDocument()
    expect(screen.getByText("Growth vs Value Tilt")).toBeInTheDocument()
    expect(screen.getByText("Correlation Heatmap")).toBeInTheDocument()
    expect(screen.getByText("Historical Application")).toBeInTheDocument()
  })

  it("renders sector-neutral metadata", () => {
    render(<ProofSection />)
    expect(screen.getByText(/sector-neutral by design/i)).toBeInTheDocument()
  })

  it("renders factor bar labels", () => {
    render(<ProofSection />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Sentiment")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
  })
})
