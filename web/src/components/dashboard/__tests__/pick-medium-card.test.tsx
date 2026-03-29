import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import type { PickSummary } from "@/lib/api/types"

vi.mock("gsap", () => ({
  default: {
    set: vi.fn(),
    to: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      play: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode
    href: string
  }) => <a href={href}>{children}</a>,
}))

import { PickMediumCard } from "../pick-medium-card"

const mediumPickMSFT: PickSummary = {
  score_id: 2,
  ticker: "MSFT",
  name: "Microsoft Corporation",
  score: 78.2,
  universe_percentile: 88,
  composite_percentile: 88,
  composite_tier: "high",
  signal: "strong",
  quality_percentile: 82,
  value_percentile: 60,
  momentum_percentile: 75,
  sentiment_percentile: 68,
  growth_percentile: 80,
  actual_price: 420.0,
  buy_price: 380,
  sell_price: 500,
  price_upside: 0.19,
  sector: "Technology",
}

const enrichedMediumPick: PickSummary = {
  ...mediumPickMSFT,
  margin_of_safety: 0.15,
  opportunity_type: "compounder",
  scored_at: new Date(Date.now() - 3600_000).toISOString(),
}

describe("PickMediumCard", () => {
  it("renders ticker", () => {
    render(<PickMediumCard pick={mediumPickMSFT} rank={2} />)
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("renders rank", () => {
    render(<PickMediumCard pick={mediumPickMSFT} rank={2} />)
    expect(screen.getByText("#2")).toBeInTheDocument()
  })

  it("renders score", () => {
    render(<PickMediumCard pick={mediumPickMSFT} rank={2} />)
    expect(screen.getByText("78.20")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<PickMediumCard pick={mediumPickMSFT} rank={2} />)
    expect(screen.getByText("High")).toBeInTheDocument()
  })

  it("renders margin of safety when present", () => {
    render(<PickMediumCard pick={enrichedMediumPick} rank={1} />)
    expect(screen.getByText(/MoS 15%/)).toBeInTheDocument()
  })

  it("renders opportunity type when present", () => {
    render(<PickMediumCard pick={enrichedMediumPick} rank={1} />)
    expect(screen.getByText("compounder")).toBeInTheDocument()
  })

  it("hides margin of safety when null", () => {
    render(<PickMediumCard pick={{ ...enrichedMediumPick, margin_of_safety: null }} rank={1} />)
    expect(screen.queryByText(/MoS/)).toBeNull()
  })
})
