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

import { PickCompactRow } from "../pick-compact-row"

const compactPickGOOG: PickSummary = {
  score_id: 3,
  ticker: "GOOG",
  name: "Alphabet Inc.",
  score: 72.1,
  universe_percentile: 82,
  composite_percentile: 82,
  composite_tier: "high",
  signal: "strong",
  quality_percentile: 78,
  value_percentile: 65,
  momentum_percentile: 70,
  sentiment_percentile: 55,
  growth_percentile: 74,
  actual_price: 175.0,
  buy_price: 155,
  sell_price: 210,
  price_upside: 0.2,
  sector: "Communication Services",
}

describe("PickCompactRow", () => {
  it("renders ticker", () => {
    render(<PickCompactRow pick={compactPickGOOG} rank={5} />)
    expect(screen.getByText("GOOG")).toBeInTheDocument()
  })

  it("renders company name", () => {
    render(<PickCompactRow pick={compactPickGOOG} rank={5} />)
    expect(screen.getByText("Alphabet Inc.")).toBeInTheDocument()
  })

  it("renders score", () => {
    render(<PickCompactRow pick={compactPickGOOG} rank={5} />)
    expect(screen.getByText("72")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<PickCompactRow pick={compactPickGOOG} rank={5} />)
    expect(screen.getByText("High")).toBeInTheDocument()
  })

  it("renders inline factor dots", () => {
    const { container } = render(
      <PickCompactRow pick={compactPickGOOG} rank={5} />
    )
    const dots = container.querySelectorAll("[data-marker-dot]")
    expect(dots.length).toBeGreaterThan(0)
  })
})
