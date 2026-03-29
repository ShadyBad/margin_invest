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

import { PickHeroCard } from "../pick-hero-card"

const heroPickNVDA: PickSummary = {
  score_id: 1,
  ticker: "NVDA",
  name: "NVIDIA Corporation",
  score: 91.3,
  universe_percentile: 99,
  composite_percentile: 99,
  composite_tier: "exceptional",
  signal: "strong",
  quality_percentile: 88,
  value_percentile: 45,
  momentum_percentile: 95,
  sentiment_percentile: 82,
  growth_percentile: 91,
  actual_price: 890.5,
  buy_price: 750,
  sell_price: 1050,
  price_upside: 0.18,
  sector: "Technology",
}

const enrichedPick: PickSummary = {
  ...heroPickNVDA,
  margin_of_safety: 0.24,
  opportunity_type: "compounder",
  data_freshness: "fresh" as const,
  scored_at: new Date(Date.now() - 2 * 3600_000).toISOString(),
}

describe("PickHeroCard", () => {
  it("renders ticker and company name", () => {
    render(<PickHeroCard pick={heroPickNVDA} rank={1} />)
    expect(screen.getByText("NVDA")).toBeInTheDocument()
    expect(screen.getByText("NVIDIA Corporation")).toBeInTheDocument()
  })

  it("renders score", () => {
    const { container } = render(
      <PickHeroCard pick={heroPickNVDA} rank={1} />
    )
    const scoreEl = container.querySelector(".text-\\[36px\\]")
    expect(scoreEl).toBeInTheDocument()
    expect(scoreEl?.textContent).toBe("91.30")
  })

  it("renders rank badge", () => {
    render(<PickHeroCard pick={heroPickNVDA} rank={1} />)
    expect(screen.getByText("#1")).toBeInTheDocument()
  })

  it("renders sector", () => {
    render(<PickHeroCard pick={heroPickNVDA} rank={1} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
  })

  it("omits sector when null", () => {
    render(
      <PickHeroCard pick={{ ...heroPickNVDA, sector: null }} rank={1} />
    )
    expect(screen.queryByText("Technology")).not.toBeInTheDocument()
  })

  it("renders Full report link pointing to /asset/NVDA", () => {
    render(<PickHeroCard pick={heroPickNVDA} rank={1} />)
    const link = screen.getByText(/Full report/)
    expect(link.closest("a")).toHaveAttribute("href", "/asset/NVDA")
  })

  it("renders price", () => {
    render(<PickHeroCard pick={heroPickNVDA} rank={1} />)
    expect(screen.getByText("$890.50")).toBeInTheDocument()
  })

  it("renders margin of safety when present", () => {
    render(<PickHeroCard pick={enrichedPick} rank={1} />)
    expect(screen.getByText(/MoS 24%/)).toBeInTheDocument()
  })

  it("renders price upside when present", () => {
    render(<PickHeroCard pick={enrichedPick} rank={1} />)
    expect(screen.getByText(/\+18\.0%/)).toBeInTheDocument()
  })

  it("renders opportunity type when present", () => {
    render(<PickHeroCard pick={enrichedPick} rank={1} />)
    expect(screen.getByText("compounder")).toBeInTheDocument()
  })

  it("renders freshness indicator", () => {
    render(<PickHeroCard pick={enrichedPick} rank={1} />)
    expect(screen.getByTestId("freshness-indicator")).toBeInTheDocument()
  })

  it("hides margin of safety when null", () => {
    render(<PickHeroCard pick={{ ...enrichedPick, margin_of_safety: null }} rank={1} />)
    expect(screen.queryByText(/MoS/)).toBeNull()
  })

  it("hides opportunity type when null", () => {
    render(<PickHeroCard pick={{ ...enrichedPick, opportunity_type: null }} rank={1} />)
    expect(screen.queryByText("compounder")).toBeNull()
  })

  it("truncates long company names", () => {
    render(<PickHeroCard pick={enrichedPick} rank={1} />)
    const nameEl = screen.getByTestId("pick-name")
    expect(nameEl.className).toContain("truncate")
  })
})
