import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EliminatedHero } from "../eliminated-hero"

const baseProps = {
  ticker: "TSLA",
  name: "Tesla Inc.",
  sector: "Consumer Discretionary",
  growthStage: "high_growth",
  actualPrice: 241.87,
  failedCount: 2,
  totalFilters: 6,
  dataCoverage: 0.91,
  scoredAt: "2026-02-23T08:00:00Z",
}

describe("EliminatedHero — protective framing", () => {
  it("renders protective framing for mega-cap tickers (marketCap >= $100B)", () => {
    render(
      <EliminatedHero
        {...baseProps}
        marketCap={800_000_000_000}
      />
    )
    expect(screen.getByText(/Our filters don't care/)).toBeInTheDocument()
    expect(
      screen.getByText(/forensic signals? flagged elevated risk/)
    ).toBeInTheDocument()
  })

  it("does NOT render protective framing for small-cap (marketCap < $100B)", () => {
    render(
      <EliminatedHero
        {...baseProps}
        marketCap={500_000_000}
      />
    )
    expect(screen.queryByText(/Our filters don't care/)).not.toBeInTheDocument()
  })

  it("does NOT render protective framing when marketCap is not provided", () => {
    render(<EliminatedHero {...baseProps} />)
    expect(screen.queryByText(/Our filters don't care/)).not.toBeInTheDocument()
  })

  it("uses singular 'signal' when failedCount is 1", () => {
    render(
      <EliminatedHero
        {...baseProps}
        failedCount={1}
        marketCap={200_000_000_000}
      />
    )
    expect(screen.getByText(/1 forensic signal flagged/)).toBeInTheDocument()
  })

  it("uses plural 'signals' when failedCount > 1", () => {
    render(
      <EliminatedHero
        {...baseProps}
        failedCount={3}
        marketCap={200_000_000_000}
      />
    )
    expect(screen.getByText(/3 forensic signals flagged/)).toBeInTheDocument()
  })

  it("includes the company name in protective framing", () => {
    render(
      <EliminatedHero
        {...baseProps}
        marketCap={150_000_000_000}
      />
    )
    expect(
      screen.getByText(/Tesla Inc\. is among the largest companies/)
    ).toBeInTheDocument()
  })
})

describe("EliminatedHero — hypothetical teaser", () => {
  it("shows hypothetical teaser when hypotheticalPercentile is provided", () => {
    render(
      <EliminatedHero
        {...baseProps}
        hypotheticalPercentile={74}
      />
    )
    expect(screen.getByText(/If it passed/)).toBeInTheDocument()
    expect(screen.getByText(/74th percentile/)).toBeInTheDocument()
  })

  it("does NOT show hypothetical teaser when hypotheticalPercentile is not provided", () => {
    render(<EliminatedHero {...baseProps} />)
    expect(screen.queryByText(/If it passed/)).not.toBeInTheDocument()
  })

  it("does NOT show hypothetical teaser when hypotheticalPercentile is null", () => {
    render(
      <EliminatedHero
        {...baseProps}
        hypotheticalPercentile={null}
      />
    )
    expect(screen.queryByText(/If it passed/)).not.toBeInTheDocument()
  })

  it("shows both protective framing and hypothetical teaser together", () => {
    render(
      <EliminatedHero
        {...baseProps}
        marketCap={800_000_000_000}
        hypotheticalPercentile={62}
      />
    )
    expect(screen.getByText(/Our filters don't care/)).toBeInTheDocument()
    expect(screen.getByText(/If it passed/)).toBeInTheDocument()
    expect(screen.getByText(/62nd percentile/)).toBeInTheDocument()
  })
})
