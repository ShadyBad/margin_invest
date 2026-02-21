import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: ({ children }: any) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  Cell: () => null,
  LabelList: ({ dataKey }: any) => <span data-testid={`label-${dataKey}`} />,
}))

import { ProofTiltChart } from "../proof-tilt-chart"
import type { CandidateCard } from "../types"

function makeCandidate(
  overrides: Partial<CandidateCard> & { growth_percentile: number; value_percentile: number }
): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    composite_percentile: 75,
    conviction_level: "high",
    quality_percentile: 70,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("ProofTiltChart", () => {
  it("renders empty state when no candidates", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(screen.getByText("No candidates scored yet")).toBeInTheDocument()
  })

  it("renders legend text", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(
      screen.getByText(/Candidates by dominant factor/)
    ).toBeInTheDocument()
  })

  it("renders bar chart when candidates provided", () => {
    const candidates = [
      makeCandidate({ growth_percentile: 80, value_percentile: 30 }),
    ]
    render(<ProofTiltChart candidates={candidates} />)
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
  })

  it("does not render bar chart in empty state", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument()
  })
})
