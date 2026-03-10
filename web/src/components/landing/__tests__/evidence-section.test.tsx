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
vi.mock("@/components/ui/correlation-grid", () => ({
  CorrelationGrid: () => <div data-testid="correlation-grid" />,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { EvidenceSection } from "../sections/evidence-section"
import type { CandidateCard } from "../shared/types"

function makeCandidate(overrides: Partial<CandidateCard> = {}): CandidateCard {
  return {
    ticker: "AAPL",
    name: "Apple Inc",
    sector: "Technology",
    actual_price: 180,
    buy_price: 150,
    margin_of_safety: 20,
    score: 85,
    composite_percentile: 90,
    composite_tier: "exceptional",
    quality_percentile: 85,
    value_percentile: 72,
    momentum_percentile: 65,
    sentiment_percentile: 58,
    growth_percentile: 90,
    scored_at: "2026-03-01",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("EvidenceSection", () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockFetch.mockResolvedValue({ ok: false })
  })

  it("renders the System Panel header with status dot", () => {
    render(<EvidenceSection />)
    expect(screen.getByTestId("evidence-header")).toHaveTextContent(
      "System Output — Cycle Results"
    )
  })

  it("renders all three column labels", () => {
    render(<EvidenceSection />)
    expect(screen.getByText("Selectivity Funnel")).toBeInTheDocument()
    expect(screen.getByText("Sector Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Factor Correlation")).toBeInTheDocument()
  })

  it("renders the factor density curves row", () => {
    render(
      <EvidenceSection
        candidates={[makeCandidate()]}
        totalUniverse={3056}
        eligibleCount={1842}
        totalScored={500}
        survivingCount={143}
      />
    )
    expect(
      screen.getByText("Factor Distribution — All Candidates")
    ).toBeInTheDocument()
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

  it("passes pipeline counts to the selectivity funnel", () => {
    render(
      <EvidenceSection
        totalUniverse={3056}
        eligibleCount={1842}
        totalScored={500}
        survivingCount={143}
      />
    )
    // Funnel should display formatted counts
    expect(screen.getByText("3,056")).toBeInTheDocument()
    expect(screen.getByText("1,842")).toBeInTheDocument()
    expect(screen.getByText("143")).toBeInTheDocument()
  })

  it("renders sector data when candidates are provided", () => {
    render(
      <EvidenceSection
        candidates={[
          makeCandidate({ sector: "Technology" }),
          makeCandidate({ sector: "Financials" }),
        ]}
      />
    )
    expect(screen.getByTestId("sector-row-Technology")).toBeInTheDocument()
    expect(screen.getByTestId("sector-row-Financials")).toBeInTheDocument()
  })
})
