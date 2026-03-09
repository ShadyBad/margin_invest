import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
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
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    set: vi.fn(),
    fromTo: vi.fn(),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(() => ({ kill: vi.fn() })), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}))
vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))
vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      ...props
    }: Record<string, unknown> & { children?: React.ReactNode }) => (
      <div {...(props as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>
    ),
  },
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { EvidenceSection } from "../evidence-section"

describe("EvidenceSection", () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockFetch.mockResolvedValue({ ok: false })
  })

  it("renders the terminal header text", () => {
    render(<EvidenceSection />)
    expect(
      screen.getByText("System Output — Current Scoring Cycle")
    ).toBeInTheDocument()
  })

  it("renders all three column labels", () => {
    render(<EvidenceSection />)
    expect(screen.getByText("Selectivity Funnel")).toBeInTheDocument()
    expect(screen.getByText("Sector Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Factor Correlation")).toBeInTheDocument()
  })

  it("renders the methodology link with correct href", () => {
    render(<EvidenceSection />)
    const link = screen.getByRole("link", {
      name: /see full methodology/i,
    })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/methodology")
  })

  it("renders the 3-column grid layout", () => {
    const { container } = render(<EvidenceSection />)
    const grid = container.querySelector(".grid.grid-cols-1.md\\:grid-cols-3")
    expect(grid).toBeInTheDocument()
  })

  it("renders the evidence panel border", () => {
    const { container } = render(<EvidenceSection />)
    const panel = container.querySelector(".border.border-border-subtle.rounded-xl")
    expect(panel).toBeInTheDocument()
  })
})
