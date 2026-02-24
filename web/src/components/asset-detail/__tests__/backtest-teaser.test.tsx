import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { BacktestTeaser } from "../backtest-teaser"

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode
    href: string
    [key: string]: unknown
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe("BacktestTeaser", () => {
  it("renders headline return numbers", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/\+387%/)).toBeInTheDocument()
    expect(screen.getByText(/\+214%/)).toBeInTheDocument()
  })

  it("renders drawdown comparison", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/-31%/)).toBeInTheDocument()
    expect(screen.getByText(/-56%/)).toBeInTheDocument()
  })

  it("renders upgrade CTA", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/See every decision/i)).toBeInTheDocument()
  })

  it("renders start year context", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/2006/)).toBeInTheDocument()
  })

  it("has a test id for integration tests", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByTestId("backtest-teaser")).toBeInTheDocument()
  })
})
