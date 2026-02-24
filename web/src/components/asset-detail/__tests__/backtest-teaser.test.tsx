import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { BacktestTeaser } from "../backtest-teaser"

describe("BacktestTeaser", () => {
  const defaultProps = {
    modelReturn: 3.87,
    benchmarkReturn: 2.14,
    maxDrawdown: 0.31,
    benchmarkMaxDrawdown: 0.56,
    startDate: "2006-01-01",
  }

  it("renders the teaser card", () => {
    render(<BacktestTeaser {...defaultProps} />)
    expect(screen.getByTestId("backtest-teaser")).toBeInTheDocument()
    expect(screen.getByText("Backtest Preview")).toBeInTheDocument()
  })

  it("displays the start year extracted from startDate", () => {
    render(<BacktestTeaser {...defaultProps} />)
    expect(screen.getByText(/since 2006/)).toBeInTheDocument()
  })

  it("shows model return, benchmark return, and max drawdown", () => {
    render(<BacktestTeaser {...defaultProps} />)
    expect(screen.getByText("+387%")).toBeInTheDocument()
    expect(screen.getByText("+214%")).toBeInTheDocument()
    expect(screen.getByText("-31%")).toBeInTheDocument()
  })

  it("shows excess return and drawdown improvement", () => {
    render(<BacktestTeaser {...defaultProps} />)
    expect(screen.getByText("+173%")).toBeInTheDocument()
    expect(screen.getByText("+25%")).toBeInTheDocument()
  })

  it("links to the full backtest page", () => {
    render(<BacktestTeaser {...defaultProps} />)
    const link = screen.getByText(/Full backtest/)
    expect(link).toHaveAttribute("href", "/backtest")
  })
})
