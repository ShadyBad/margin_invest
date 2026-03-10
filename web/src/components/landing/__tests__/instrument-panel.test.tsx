import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    set: vi.fn(),
    to: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

import { InstrumentPanel } from "../sections/instrument-panel"
import type { CandidateCard } from "../shared/types"

const MOCK_CANDIDATE: CandidateCard = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  actual_price: 178.5,
  buy_price: 155.0,
  margin_of_safety: 0.15,
  score: 82,
  composite_percentile: 85,
  composite_tier: "exceptional",
  quality_percentile: 95,
  value_percentile: 68,
  momentum_percentile: 84,
  sentiment_percentile: 79,
  growth_percentile: 88,
  scored_at: new Date().toISOString(),
  filters_passed: 8,
  filters_total: 8,
}

describe("InstrumentPanel", () => {
  it("renders ticker and company name", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders composite score", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("82")).toBeInTheDocument()
  })

  it("renders Live Score header with ticker", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText(/live score/i)).toBeInTheDocument()
  })

  it("renders sector when present", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
  })

  it("omits sector when null", () => {
    const noSector = { ...MOCK_CANDIDATE, sector: null as unknown as string }
    render(<InstrumentPanel candidate={noSector} />)
    expect(screen.getByText("82")).toBeInTheDocument()
  })

  it("renders status dot", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByTestId("status-dot")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText(/exceptional/i)).toBeInTheDocument()
  })

  it("renders empty state when candidate is null", () => {
    render(<InstrumentPanel candidate={null} />)
    const dashes = screen.getAllByText("—")
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it("renders relative timestamp", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText(/scored|just now|ago/i)).toBeInTheDocument()
  })
})
