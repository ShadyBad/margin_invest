import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

type MockProps = Record<string, unknown> & { children?: React.ReactNode }

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: MockProps) => (
      <div {...(props as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>
    ),
  },
}))

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
    ...rest
  }: {
    children: React.ReactNode
    href: string
    [key: string]: unknown
  }) => (
    <a href={href} {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}>
      {children}
    </a>
  ),
}))

// Mock EmptyState and ConvictionBadge
vi.mock("@/components/ui", () => ({
  EmptyState: ({
    title,
    description,
  }: {
    title: string
    description?: string
  }) => (
    <div>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
    </div>
  ),
  ConvictionBadge: ({ level }: { level: string }) => <span>{level}</span>,
}))

import { TieredPicksList } from "../tiered-picks-list"
import type { PickSummary } from "@/lib/api/types"

function makePick(
  ticker: string,
  score: number,
  overrides?: Partial<PickSummary>,
): PickSummary {
  return {
    score_id: Math.random(),
    ticker,
    name: `${ticker} Corp`,
    score,
    universe_percentile: score,
    composite_percentile: score,
    composite_tier:
      score >= 80 ? "exceptional" : score >= 60 ? "high" : "medium",
    signal: "strong",
    quality_percentile: score,
    value_percentile: score - 10,
    momentum_percentile: score - 5,
    sentiment_percentile: score - 15,
    growth_percentile: score - 3,
    actual_price: 100,
    buy_price: 90,
    sell_price: 120,
    price_upside: 0.2,
    ...overrides,
  }
}

describe("TieredPicksList", () => {
  it("renders empty state with 0 picks", () => {
    render(<TieredPicksList picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
  })

  it("renders empty state with stats when universe data provided", () => {
    render(
      <TieredPicksList picks={[]} totalScored={500} universeSize={2000} />,
    )
    expect(screen.getByText(/500/)).toBeInTheDocument()
  })

  it("renders hero card for single pick", () => {
    render(<TieredPicksList picks={[makePick("AAPL", 90)]} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
  })

  it("renders hero + medium for 2 picks", () => {
    render(
      <TieredPicksList
        picks={[makePick("AAPL", 90), makePick("MSFT", 85)]}
      />,
    )
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
  })

  it("renders hero + 2 medium for 3 picks", () => {
    const picks = [
      makePick("AAPL", 90),
      makePick("MSFT", 85),
      makePick("GOOG", 80),
    ]
    render(<TieredPicksList picks={picks} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-GOOG")).toBeInTheDocument()
  })

  it("renders hero + 2 medium + compact for 5 picks", () => {
    const picks = [
      makePick("AAPL", 90),
      makePick("MSFT", 85),
      makePick("GOOG", 80),
      makePick("AMZN", 75),
      makePick("META", 70),
    ]
    render(<TieredPicksList picks={picks} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-GOOG")).toBeInTheDocument()
    expect(screen.getByTestId("pick-compact-AMZN")).toBeInTheDocument()
    expect(screen.getByTestId("pick-compact-META")).toBeInTheDocument()
  })

  it("sorts picks by composite_percentile descending", () => {
    const picks = [makePick("LOW", 60), makePick("HIGH", 95)]
    render(<TieredPicksList picks={picks} />)
    expect(screen.getByTestId("pick-hero-HIGH")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-LOW")).toBeInTheDocument()
  })
})
