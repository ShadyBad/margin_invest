import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { FactorTimeline } from "../factor-timeline"

const mockEntries = [
  { date: "2020-01-31", factors: ["quality", "value"] },
  { date: "2020-02-28", factors: ["quality", "value", "momentum"] },
  { date: "2020-03-31", factors: ["quality", "momentum"] },
  { date: "2020-04-30", factors: ["quality", "value", "momentum"] },
  { date: "2020-05-31", factors: ["value", "momentum"] },
  { date: "2020-06-30", factors: ["quality", "value", "momentum"] },
]

describe("FactorTimeline", () => {
  it("renders all factor names from entries", () => {
    render(<FactorTimeline entries={mockEntries} />)

    expect(screen.getByText("quality")).toBeInTheDocument()
    expect(screen.getByText("value")).toBeInTheDocument()
    expect(screen.getByText("momentum")).toBeInTheDocument()
  })

  it("renders timeline bars for each factor", () => {
    render(<FactorTimeline entries={mockEntries} />)

    // Each factor should have a timeline row
    expect(screen.getByTestId("factor-row-quality")).toBeInTheDocument()
    expect(screen.getByTestId("factor-row-value")).toBeInTheDocument()
    expect(screen.getByTestId("factor-row-momentum")).toBeInTheDocument()
  })

  it("shows correct date range labels", () => {
    render(<FactorTimeline entries={mockEntries} />)

    // Should show at least the first and last dates (as formatted labels)
    const container = screen.getByTestId("factor-timeline")
    // The first date label
    expect(container).toHaveTextContent("Jan 2020")
    // The last date label
    expect(container).toHaveTextContent("Jun 2020")
  })

  it("handles empty entries array", () => {
    render(<FactorTimeline entries={[]} />)

    expect(screen.getByText("No factor data available")).toBeInTheDocument()
  })

  it("derives allFactors from entries when not explicitly provided", () => {
    const entries = [
      { date: "2020-01-31", factors: ["quality"] },
      { date: "2020-02-28", factors: ["value"] },
      { date: "2020-03-31", factors: ["momentum"] },
    ]

    render(<FactorTimeline entries={entries} />)

    expect(screen.getByText("quality")).toBeInTheDocument()
    expect(screen.getByText("value")).toBeInTheDocument()
    expect(screen.getByText("momentum")).toBeInTheDocument()
  })

  it("uses allFactors prop when provided", () => {
    const entries = [
      { date: "2020-01-31", factors: ["quality"] },
    ]

    render(
      <FactorTimeline
        entries={entries}
        allFactors={["quality", "value", "momentum", "growth"]}
      />
    )

    expect(screen.getByText("quality")).toBeInTheDocument()
    expect(screen.getByText("value")).toBeInTheDocument()
    expect(screen.getByText("momentum")).toBeInTheDocument()
    expect(screen.getByText("growth")).toBeInTheDocument()
  })
})
