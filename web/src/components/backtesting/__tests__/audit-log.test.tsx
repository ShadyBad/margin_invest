import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { AuditLog } from "../audit-log"

const mockEntries = [
  {
    date: "2020-01-31",
    action: "rebalance",
    universeSize: 500,
    selectedCount: 25,
    factorCoverage: 0.85,
    regime: "bull",
    turnover: 0.32,
  },
  {
    date: "2020-02-28",
    action: "hold",
    universeSize: 500,
    selectedCount: 25,
    factorCoverage: 0.9,
    regime: "bear",
    turnover: 0.0,
  },
  {
    date: "2020-03-31",
    action: "rebalance",
    universeSize: 480,
    selectedCount: 20,
    factorCoverage: 0.72,
    regime: "recovery",
    turnover: 0.45,
  },
]

describe("AuditLog", () => {
  it("renders table with correct column headers", () => {
    render(<AuditLog entries={mockEntries} />)

    expect(screen.getByText("REBALANCE AUDIT LOG")).toBeInTheDocument()
    expect(screen.getByText("Date")).toBeInTheDocument()
    expect(screen.getByText("Action")).toBeInTheDocument()
    expect(screen.getByText("Universe")).toBeInTheDocument()
    expect(screen.getByText("Selected")).toBeInTheDocument()
    expect(screen.getByText("Coverage")).toBeInTheDocument()
    expect(screen.getByText("Regime")).toBeInTheDocument()
    expect(screen.getByText("Turnover")).toBeInTheDocument()
  })

  it("shows all audit entries as rows", () => {
    render(<AuditLog entries={mockEntries} />)

    // 1 header + 3 data rows
    const rows = screen.getAllByRole("row")
    expect(rows).toHaveLength(4)

    expect(screen.getByText("2020-01-31")).toBeInTheDocument()
    expect(screen.getByText("2020-02-28")).toBeInTheDocument()
    expect(screen.getByText("2020-03-31")).toBeInTheDocument()
  })

  it("formats coverage as percentage", () => {
    render(<AuditLog entries={mockEntries} />)

    expect(screen.getByText("85%")).toBeInTheDocument()
    expect(screen.getByText("90%")).toBeInTheDocument()
    expect(screen.getByText("72%")).toBeInTheDocument()
  })

  it("formats turnover as percentage", () => {
    render(<AuditLog entries={mockEntries} />)

    expect(screen.getByText("32%")).toBeInTheDocument()
    expect(screen.getByText("0%")).toBeInTheDocument()
    expect(screen.getByText("45%")).toBeInTheDocument()
  })

  it("handles empty entries array", () => {
    render(<AuditLog entries={[]} />)

    expect(screen.getByText("No audit entries")).toBeInTheDocument()
  })

  it("displays regime labels", () => {
    render(<AuditLog entries={mockEntries} />)

    expect(screen.getByText("bull")).toBeInTheDocument()
    expect(screen.getByText("bear")).toBeInTheDocument()
    expect(screen.getByText("recovery")).toBeInTheDocument()
  })
})
