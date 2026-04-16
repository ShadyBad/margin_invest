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
vi.mock("../visualizations/selectivity-funnel", () => ({
  SelectivityFunnel: (props: Record<string, unknown>) => (
    <div data-testid="selectivity-funnel">
      <span>{(props.universeCount as number)?.toLocaleString()}</span>
      <span>{(props.eligibleCount as number)?.toLocaleString()}</span>
      <span>{(props.scoredCount as number)?.toLocaleString()}</span>
      <span>{(props.survivingCount as number)?.toLocaleString()}</span>
    </div>
  ),
}))
vi.mock("../visualizations/sector-bar-chart", () => ({
  SectorBarChart: ({ candidates }: { candidates: Array<{ sector: string }> }) => (
    <div data-testid="sector-bar-chart">
      {candidates.map((c, i) => (
        <span key={i} data-testid={`sector-row-${c.sector}`}>{c.sector}</span>
      ))}
    </div>
  ),
}))
vi.mock("../visualizations/factor-density-curves", () => ({
  FactorDensityCurves: () => <div data-testid="factor-density-curves" />,
}))
vi.mock("../proof-heatmap", () => ({
  ProofHeatmap: () => <div data-testid="proof-heatmap" />,
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

  it("renders The Selection Funnel heading", () => {
    render(<EvidenceSection />)
    expect(screen.getByText("The Selection Funnel")).toBeInTheDocument()
  })

  it("renders Forensic Analysis heading", () => {
    render(<EvidenceSection />)
    expect(screen.getByText("Forensic Analysis")).toBeInTheDocument()
  })

  it("renders three forensic card labels", () => {
    render(<EvidenceSection />)
    expect(screen.getByText("SECTOR BREAKDOWN")).toBeInTheDocument()
    expect(screen.getByText("FACTOR CORRELATION")).toBeInTheDocument()
    expect(screen.getByText("FACTOR DISTRIBUTIONS")).toBeInTheDocument()
  })

  it("renders the methodology link with correct href", () => {
    render(<EvidenceSection />)
    const link = screen.getByRole("link", {
      name: /see full methodology/i,
    })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/methodology")
  })

  it("renders data-funnel-block attribute", () => {
    const { container } = render(<EvidenceSection />)
    const funnelBlock = container.querySelector("[data-funnel-block]")
    expect(funnelBlock).toBeInTheDocument()
  })

  it("renders three data-forensic-card attributes", () => {
    const { container } = render(<EvidenceSection />)
    const cards = container.querySelectorAll("[data-forensic-card]")
    expect(cards).toHaveLength(3)
  })

  it("renders the forensic grid", () => {
    const { container } = render(<EvidenceSection />)
    const grid = container.querySelector(".grid.grid-cols-1.md\\:grid-cols-2")
    expect(grid).toBeInTheDocument()
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
