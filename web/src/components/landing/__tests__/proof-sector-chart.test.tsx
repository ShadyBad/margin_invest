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

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="sector-bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Legend: () => null,
  Tooltip: () => null,
  Cell: () => null,
}))

import { ProofSectorChart } from "../proof-sector-chart"
import type { CandidateCard } from "../types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    score: 75,
    composite_percentile: 75,
    composite_tier: "high",
    quality_percentile: 70,
    value_percentile: 75,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    growth_percentile: 55,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("ProofSectorChart", () => {
  it("renders empty state when no candidates", () => {
    render(<ProofSectorChart candidates={[]} />)
    expect(screen.getByText(/scoring in progress/i)).toBeInTheDocument()
  })

  it("renders bar chart when candidates provided", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", composite_tier: "exceptional" }),
      makeCandidate({ sector: "Healthcare", composite_tier: "high" }),
      makeCandidate({ sector: "Financials", composite_tier: "medium" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByTestId("sector-bar-chart")).toBeInTheDocument()
  })

  it("renders subtitle text", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", composite_tier: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/candidates by sector/i)).toBeInTheDocument()
  })

  it("renders sector-neutral safeguard note", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", composite_tier: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/sector-neutral/i)).toBeInTheDocument()
  })
})
