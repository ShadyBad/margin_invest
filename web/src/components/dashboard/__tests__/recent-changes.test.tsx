import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { RecentChanges } from "../recent-changes"
import type { ScoreChange } from "../recent-changes"

const mockChanges: ScoreChange[] = [
  {
    ticker: "EXPE",
    previousScore: 72,
    currentScore: 74,
    changedAt: "2026-03-08",
  },
  {
    ticker: "AAPL",
    previousScore: 85,
    currentScore: 80,
    changedAt: "2026-03-07",
  },
  {
    ticker: "MSFT",
    previousScore: 60,
    currentScore: 60,
    changedAt: "2026-03-06",
  },
]

describe("RecentChanges", () => {
  it("renders each change entry with ticker name", () => {
    render(<RecentChanges changes={mockChanges} />)
    expect(screen.getByText("EXPE")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("shows score transition", () => {
    render(<RecentChanges changes={[mockChanges[0]]} />)
    expect(screen.getByText("72")).toBeInTheDocument()
    expect(screen.getByText("74")).toBeInTheDocument()
  })

  it("shows positive delta with bullish styling", () => {
    render(<RecentChanges changes={[mockChanges[0]]} />)
    const delta = screen.getByText("(+2)")
    expect(delta).toBeInTheDocument()
    expect(delta.className).toContain("text-bullish")
  })

  it("shows negative delta with warning styling", () => {
    render(<RecentChanges changes={[mockChanges[1]]} />)
    const delta = screen.getByText("(-5)")
    expect(delta).toBeInTheDocument()
    expect(delta.className).toContain("text-warning")
  })

  it("shows zero delta with neutral styling", () => {
    render(<RecentChanges changes={[mockChanges[2]]} />)
    const delta = screen.getByText("(0)")
    expect(delta).toBeInTheDocument()
    expect(delta.className).toContain("text-text-secondary")
  })

  it("renders empty state when changes array is empty", () => {
    render(<RecentChanges changes={[]} />)
    expect(screen.getByText("No recent changes")).toBeInTheDocument()
  })

  it("renders date for each entry", () => {
    render(<RecentChanges changes={[mockChanges[0]]} />)
    expect(screen.getByText("Mar 8")).toBeInTheDocument()
  })
})
