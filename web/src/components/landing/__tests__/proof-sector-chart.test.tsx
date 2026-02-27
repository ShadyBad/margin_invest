import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="sector-bar-chart">{children}</div>,
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
    conviction_level: "high",
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
      makeCandidate({ sector: "Technology", conviction_level: "exceptional" }),
      makeCandidate({ sector: "Healthcare", conviction_level: "high" }),
      makeCandidate({ sector: "Financials", conviction_level: "medium" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByTestId("sector-bar-chart")).toBeInTheDocument()
  })

  it("renders subtitle text", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", conviction_level: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/candidates by sector/i)).toBeInTheDocument()
  })

  it("renders sector-neutral safeguard note", () => {
    const candidates = [
      makeCandidate({ sector: "Technology", conviction_level: "high" }),
    ]
    render(<ProofSectorChart candidates={candidates} />)
    expect(screen.getByText(/sector-neutral/i)).toBeInTheDocument()
  })
})
