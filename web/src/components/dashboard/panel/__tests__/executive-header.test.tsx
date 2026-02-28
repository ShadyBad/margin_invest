import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ExecutiveHeader } from "../executive-header"

vi.mock("@/components/ui", () => ({
  ConvictionBadge: ({ level }: { level: string }) => <span data-testid="conviction-badge">{level}</span>,
  ActionPill: (props: { buyPrice?: number | null; sellPrice?: number | null; actualPrice?: number | null }) => (
    <span data-testid="action-pill" data-buy-price={props.buyPrice ?? "none"} data-sell-price={props.sellPrice ?? "none"} data-actual-price={props.actualPrice ?? "none"} />
  ),
  AnimatedScore: ({ value }: { value: number }) => <span data-testid="animated-score">{value}</span>,
}))

vi.mock("../time-range-selector", () => ({
  TimeRangeSelector: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <div data-testid="time-range-selector" onClick={() => onChange("1Y")}>{value}</div>
  ),
}))

const baseProps = {
  ticker: "AAPL",
  companyName: "Apple Inc.",
  compositeScore: 92,
  scoreDelta: 3,
  conviction: "exceptional",
  signal: "strong",
  opportunityType: "compounder" as const,
  timeRange: "3M" as const,
  onTimeRangeChange: vi.fn(),
  onClose: vi.fn(),
}

describe("ExecutiveHeader", () => {
  it("renders ticker and company name", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders score and positive delta", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByTestId("animated-score")).toHaveTextContent("92")
    expect(screen.getByTestId("score-delta")).toHaveTextContent("+3")
  })

  it("renders negative delta in bearish style", () => {
    render(<ExecutiveHeader {...baseProps} scoreDelta={-5} />)
    const delta = screen.getByTestId("score-delta")
    expect(delta).toHaveTextContent("-5")
  })

  it("calls onClose when close button is clicked", () => {
    render(<ExecutiveHeader {...baseProps} />)
    fireEvent.click(screen.getByTestId("panel-close-btn"))
    expect(baseProps.onClose).toHaveBeenCalledOnce()
  })

  it("passes timeRange to TimeRangeSelector", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByTestId("time-range-selector")).toHaveTextContent("3M")
  })

  it("passes price props to ActionPill", () => {
    render(<ExecutiveHeader {...baseProps} buyPrice={140} sellPrice={200} actualPrice={150} />)
    const pill = screen.getByTestId("action-pill")
    expect(pill).toHaveAttribute("data-buy-price", "140")
    expect(pill).toHaveAttribute("data-sell-price", "200")
    expect(pill).toHaveAttribute("data-actual-price", "150")
  })
})
