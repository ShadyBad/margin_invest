import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PanelValuation } from "../panel-valuation"

describe("PanelValuation", () => {
  const baseProps = {
    intrinsicValue: 28.5,
    currentPrice: 21.0,
    marginOfSafety: 0.26,
    methods: { dcf: 32.1, ev_fcf: 24.8, acquirers_multiple: 28.9, shareholder_yield: 27.2 },
  }

  it("renders intrinsic value", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("$28.50")).toBeInTheDocument()
  })

  it("renders current price and margin of safety", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Current: $21.00")).toBeInTheDocument()
    expect(screen.getByText("26%")).toBeInTheDocument()
  })

  it("renders all valuation method bars", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("EV/FCF")).toBeInTheDocument()
    expect(screen.getByText("EV/EBIT")).toBeInTheDocument()
    expect(screen.getByText("Shareholder Yield")).toBeInTheDocument()
  })

  it("renders empty state when no methods", () => {
    render(<PanelValuation {...baseProps} methods={{}} />)
    expect(screen.getByText("No valuation data")).toBeInTheDocument()
  })
})
