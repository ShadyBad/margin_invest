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

  it("renders Margin Invest Value", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Margin Invest Value")).toBeInTheDocument()
    expect(screen.getByText("$28.50")).toBeInTheDocument()
  })

  it("renders current price and margin of safety in header trio", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Current Price")).toBeInTheDocument()
    expect(screen.getByText("$21.00")).toBeInTheDocument()
    expect(screen.getByText("Margin of Safety")).toBeInTheDocument()
    expect(screen.getByText("26%")).toBeInTheDocument()
  })

  it("renders all valuation method bars", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("EV/FCF")).toBeInTheDocument()
    expect(screen.getByText("EV/EBIT")).toBeInTheDocument()
    expect(screen.getByText("Shareholder Yield")).toBeInTheDocument()
  })

  it("renders empty state when no methods and no intrinsic value", () => {
    render(<PanelValuation {...baseProps} intrinsicValue={null} methods={{}} />)
    expect(screen.getByText("No valuation data")).toBeInTheDocument()
  })

  it("renders price ladder when buyBelow and sellPrice provided", () => {
    render(<PanelValuation {...baseProps} buyBelow={22.0} sellPrice={35.0} />)
    expect(screen.getByText("Buy Zone")).toBeInTheDocument()
    expect(screen.getByText("Hold Zone")).toBeInTheDocument()
    expect(screen.getByText("Sell Zone")).toBeInTheDocument()
  })

  it("does not render price ladder when buyBelow is null", () => {
    render(<PanelValuation {...baseProps} buyBelow={null} sellPrice={35.0} />)
    expect(screen.queryByText("Buy Zone")).not.toBeInTheDocument()
  })

  it("does not render price ladder when sellPrice is null", () => {
    render(<PanelValuation {...baseProps} buyBelow={22.0} sellPrice={null} />)
    expect(screen.queryByText("Buy Zone")).not.toBeInTheDocument()
  })

  it("renders valuation methods even without intrinsic value", () => {
    render(<PanelValuation {...baseProps} intrinsicValue={null} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.queryByText("Margin Invest Value")).not.toBeInTheDocument()
  })
})
