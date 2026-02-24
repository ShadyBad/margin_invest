import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ValuationSection } from "../valuation-section"

describe("ValuationSection", () => {
  it("renders price ruler with buy, sell, intrinsic, and current", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{ dcf: 158.2, ev_fcf: 172.4, acquirers_multiple: 161.8, shareholder_yield: 170.5 }}
      />
    )
    expect(screen.getByTestId("price-ruler")).toBeInTheDocument()
    // Intrinsic value appears in both ruler and methods table
    expect(screen.getAllByText("$165.00").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("$187.42")).toBeInTheDocument()
  })

  it("shows overvalued warning when price > intrinsic", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{}}
      />
    )
    expect(screen.getByText(/ABOVE intrinsic value/)).toBeInTheDocument()
  })

  it("shows unavailable message when no intrinsic value", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={null}
        sellPrice={null}
        intrinsicValue={null}
        currentPrice={187.42}
        priceUpside={null}
        marginOfSafety={null}
        valuationMethods={null}
        invalidReason="Negative trailing earnings prevent reliable DCF computation."
      />
    )
    expect(screen.getByText(/Negative trailing earnings/)).toBeInTheDocument()
  })

  it("shows explanation when overvalued", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{}}
      />
    )
    expect(screen.getByText(/composite score ranks/i)).toBeInTheDocument()
  })

  it("renders valuation methods table", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{ dcf: 158.2, ev_fcf: 172.4 }}
      />
    )
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("$158.20")).toBeInTheDocument()
  })
})
