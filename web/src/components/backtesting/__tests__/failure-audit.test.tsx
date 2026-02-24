import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { FailureAudit } from "../failure-audit"

const mockPeriods = [
  {
    startDate: "2020-02-19",
    endDate: "2020-03-23",
    returnPct: -0.34,
    benchmarkReturnPct: -0.31,
    regime: "bear",
    maxDrawdown: -0.34,
    recoveryMonths: 5,
  },
  {
    startDate: "2022-01-03",
    endDate: "2022-10-12",
    returnPct: -0.25,
    benchmarkReturnPct: -0.22,
    regime: "bear",
    maxDrawdown: -0.28,
    recoveryMonths: null,
  },
  {
    startDate: "2018-09-20",
    endDate: "2018-12-24",
    returnPct: -0.18,
    benchmarkReturnPct: -0.15,
    regime: "correction",
    maxDrawdown: -0.2,
    recoveryMonths: 3,
  },
]

describe("FailureAudit", () => {
  it("renders all failure periods", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getByText("WORST PERIODS")).toBeInTheDocument()

    // Should render 3 periods
    const periods = screen.getAllByTestId(/^failure-period-/)
    expect(periods).toHaveLength(3)
  })

  it("shows returns in red with negative sign", () => {
    render(<FailureAudit periods={mockPeriods} />)

    // Worst period first: -34.00%
    const worstPeriod = screen.getByTestId("failure-period-0")
    expect(worstPeriod).toHaveTextContent("-34.00%")

    // All return values should be in bearish color
    const returnElements = screen.getAllByTestId(/^failure-return-/)
    for (const el of returnElements) {
      expect(el.className).toContain("text-bearish")
    }
  })

  it("shows 'Never recovered' for null recovery", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getByText("Never recovered")).toBeInTheDocument()
  })

  it("shows recovery months when provided", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getByText("5 months")).toBeInTheDocument()
    expect(screen.getByText("3 months")).toBeInTheDocument()
  })

  it("handles empty periods array", () => {
    render(<FailureAudit periods={[]} />)

    expect(screen.getByText("No significant drawdowns")).toBeInTheDocument()
  })

  it("sorts periods by worst return first", () => {
    // Pass periods in non-sorted order
    const unsorted = [mockPeriods[2], mockPeriods[0], mockPeriods[1]]
    render(<FailureAudit periods={unsorted} />)

    const periods = screen.getAllByTestId(/^failure-period-/)
    // First should be the -34% period
    expect(periods[0]).toHaveTextContent("-34.00%")
    // Second should be -25%
    expect(periods[1]).toHaveTextContent("-25.00%")
    // Third should be -18%
    expect(periods[2]).toHaveTextContent("-18.00%")
  })

  it("displays date ranges", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getByText(/2020-02-19/)).toBeInTheDocument()
    expect(screen.getByText(/2020-03-23/)).toBeInTheDocument()
  })

  it("displays regime labels", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getAllByText("bear")).toHaveLength(2)
    expect(screen.getByText("correction")).toBeInTheDocument()
  })

  it("displays benchmark returns", () => {
    render(<FailureAudit periods={mockPeriods} />)

    expect(screen.getByTestId("failure-period-0")).toHaveTextContent("-31.00%")
  })
})
