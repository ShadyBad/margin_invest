import { render, screen } from "@testing-library/react"
import { MarketRegimeLabel } from "../market-regime-label"

describe("MarketRegimeLabel", () => {
  it("shows Overheated when 0 picks", () => {
    render(<MarketRegimeLabel pickCount={0} />)
    expect(screen.getByText(/Overheated/i)).toBeInTheDocument()
  })

  it("shows Overheated when 1 pick", () => {
    render(<MarketRegimeLabel pickCount={1} />)
    expect(screen.getByText(/Overheated/i)).toBeInTheDocument()
  })

  it("shows Concentrated when 3 picks", () => {
    render(<MarketRegimeLabel pickCount={3} />)
    expect(screen.getByText(/Concentrated/i)).toBeInTheDocument()
  })

  it("shows Concentrated when 5 picks", () => {
    render(<MarketRegimeLabel pickCount={5} />)
    expect(screen.getByText(/Concentrated/i)).toBeInTheDocument()
  })

  it("shows Normal when 6 picks", () => {
    render(<MarketRegimeLabel pickCount={6} />)
    expect(screen.getByText(/Normal/i)).toBeInTheDocument()
  })

  it("shows Normal when 8 picks", () => {
    render(<MarketRegimeLabel pickCount={8} />)
    expect(screen.getByText(/Normal/i)).toBeInTheDocument()
  })

  it("has the market-regime test id", () => {
    render(<MarketRegimeLabel pickCount={0} />)
    expect(screen.getByTestId("market-regime")).toBeInTheDocument()
  })
})
