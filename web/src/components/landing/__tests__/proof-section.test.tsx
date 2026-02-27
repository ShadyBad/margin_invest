import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  })
})

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Area: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}))
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection />)
    expect(
      screen.getByText(/structure creates measurable advantage/i)
    ).toBeInTheDocument()
  })

  it("renders all 5 proof card titles", () => {
    render(<ProofSection />)
    expect(screen.getByText("Factor Transparency")).toBeInTheDocument()
    expect(screen.getByText("System Selectivity")).toBeInTheDocument()
    expect(screen.getByText("Sector Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Correlation Heatmap")).toBeInTheDocument()
    expect(screen.getByText("Historical Application")).toBeInTheDocument()
  })

  it("does NOT render Growth vs Value Tilt (removed)", () => {
    render(<ProofSection />)
    expect(screen.queryByText("Growth vs Value Tilt")).not.toBeInTheDocument()
  })

  it("renders sector-neutral metadata", () => {
    render(<ProofSection />)
    expect(screen.getByText(/sector-neutral by design/i)).toBeInTheDocument()
  })

  it("renders factor bar labels", () => {
    render(<ProofSection />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })
})
