import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { MiniCandidateStack } from "../mini-candidate-stack"
import type { CandidateCard } from "../../shared/types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Corp",
    sector: "Technology",
    actual_price: 100,
    buy_price: 120,
    margin_of_safety: 0.167,
    score: 70,
    composite_percentile: 75,
    composite_tier: "high",
    quality_percentile: 80,
    value_percentile: 65,
    momentum_percentile: 72,
    sentiment_percentile: 60,
    growth_percentile: 68,
    scored_at: "2026-03-09T12:00:00Z",
    filters_passed: 6,
    filters_total: 6,
    ...overrides,
  }
}

const candidates: CandidateCard[] = [
  makeCandidate({ ticker: "AAPL", score: 82.4, sector: "Technology" }),
  makeCandidate({ ticker: "MSFT", score: 78.1, sector: "Technology" }),
  makeCandidate({ ticker: "JNJ", score: 71.3, sector: "Healthcare" }),
]

describe("MiniCandidateStack", () => {
  test("renders all candidate bars", () => {
    const { container } = render(<MiniCandidateStack candidates={candidates} />)
    const bars = container.querySelectorAll("[data-candidate-card]")
    expect(bars).toHaveLength(3)
  })

  test("displays ticker and formatted score for each candidate", () => {
    render(<MiniCandidateStack candidates={candidates} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("82.40")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("78.10")).toBeInTheDocument()
    expect(screen.getByText("JNJ")).toBeInTheDocument()
    expect(screen.getByText("71.30")).toBeInTheDocument()
  })

  test("sorts candidates ascending by score", () => {
    const { container } = render(<MiniCandidateStack candidates={candidates} />)
    const bars = container.querySelectorAll("[data-candidate-card]")
    expect(bars[0].getAttribute("data-candidate-card")).toBe("JNJ")
    expect(bars[1].getAttribute("data-candidate-card")).toBe("MSFT")
    expect(bars[2].getAttribute("data-candidate-card")).toBe("AAPL")
  })

  test("renders placeholder when candidates is empty", () => {
    render(<MiniCandidateStack candidates={[]} />)
    expect(screen.getByText(/loads after scoring cycle/i)).toBeInTheDocument()
  })

  test("applies className", () => {
    const { container } = render(
      <MiniCandidateStack candidates={candidates} className="my-stack" />
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.classList.contains("my-stack")).toBe(true)
  })

  test("renders all candidates (not just first 3)", () => {
    const fiveCandidates = [
      ...candidates,
      makeCandidate({ ticker: "JPM", score: 65.0, sector: "Financials" }),
      makeCandidate({ ticker: "PFE", score: 60.5, sector: "Healthcare" }),
    ]
    const { container } = render(<MiniCandidateStack candidates={fiveCandidates} />)
    const bars = container.querySelectorAll("[data-candidate-card]")
    expect(bars).toHaveLength(5)
  })
})
