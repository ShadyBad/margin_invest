import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { InstrumentHeader } from "../instrument-header"

vi.mock("next/link", () => ({
  default: ({ children, ...props }: { children: React.ReactNode; href: string }) => (
    <a {...props}>{children}</a>
  ),
}))

vi.mock("@/lib/format", () => ({
  formatScoredAt: (d: string) => d,
}))

const baseProps = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  growthStage: "mature",
  style: "compounder",
  score: 78,
  tier: "exceptional",
  signal: "strong",
  scoredAt: "2026-04-18T00:00:00Z",
  eliminated: false,
  universePercentile: 92,
}

describe("InstrumentHeader", () => {
  it("renders timing signal pill when timingSignal is provided", () => {
    render(<InstrumentHeader {...baseProps} timingSignal="buy_now" />)
    expect(screen.getByTestId("timing-signal-pill")).toBeInTheDocument()
    expect(screen.getByTestId("timing-signal-pill")).toHaveTextContent("BUY NOW")
  })

  it("does not render timing signal pill when null", () => {
    render(<InstrumentHeader {...baseProps} timingSignal={null} />)
    expect(screen.queryByTestId("timing-signal-pill")).not.toBeInTheDocument()
  })

  it("renders add_on_pullback with correct text", () => {
    render(<InstrumentHeader {...baseProps} timingSignal="add_on_pullback" />)
    const pill = screen.getByTestId("timing-signal-pill")
    expect(pill).toHaveTextContent("ADD ON PULLBACK")
  })

  it("does not render timing signal when eliminated", () => {
    render(<InstrumentHeader {...baseProps} eliminated={true} timingSignal="buy_now" />)
    expect(screen.queryByTestId("timing-signal-pill")).not.toBeInTheDocument()
  })
})
