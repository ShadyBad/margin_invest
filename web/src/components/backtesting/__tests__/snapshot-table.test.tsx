import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { SnapshotTable } from "../snapshot-table"

const mockSnapshots = [
  {
    date: "2024-01-01",
    portfolio_value: 1050000.5,
    benchmark_value: 1020000.75,
    portfolio_return: 0.05,
    benchmark_return: 0.02,
    turnover: 0.15,
    transaction_costs: 250.5,
  },
  {
    date: "2024-02-01",
    portfolio_value: 1030000,
    benchmark_value: 1010000,
    portfolio_return: -0.019,
    benchmark_return: -0.0098,
    turnover: 0.1,
    transaction_costs: 180.0,
  },
  {
    date: "2024-03-01",
    portfolio_value: 1070000,
    benchmark_value: 1040000,
    portfolio_return: 0.0388,
    benchmark_return: 0.0297,
    turnover: 0.12,
    transaction_costs: 200.0,
  },
]

describe("SnapshotTable", () => {
  it("renders table with data", () => {
    render(<SnapshotTable snapshots={mockSnapshots} />)

    const table = screen.getByTestId("snapshot-table")
    expect(table).toBeInTheDocument()

    // Column headers should be visible
    expect(screen.getByText("Date")).toBeInTheDocument()
    expect(screen.getByText("Portfolio Value")).toBeInTheDocument()
    expect(screen.getByText("Benchmark Value")).toBeInTheDocument()
    expect(screen.getByText("Portfolio Return")).toBeInTheDocument()
    expect(screen.getByText("Benchmark Return")).toBeInTheDocument()
    expect(screen.getByText("Excess Return")).toBeInTheDocument()
    expect(screen.getByText("Turnover")).toBeInTheDocument()
    expect(screen.getByText("Transaction Costs")).toBeInTheDocument()
  })

  it("shows correct number of rows", () => {
    render(<SnapshotTable snapshots={mockSnapshots} />)

    expect(screen.getByTestId("snapshot-row-2024-01")).toBeInTheDocument()
    expect(screen.getByTestId("snapshot-row-2024-02")).toBeInTheDocument()
    expect(screen.getByTestId("snapshot-row-2024-03")).toBeInTheDocument()

    // 3 data rows
    const rows = screen.getAllByRole("row")
    // 1 header row + 3 data rows = 4
    expect(rows).toHaveLength(4)
  })

  it("shows empty state when no data", () => {
    render(<SnapshotTable snapshots={[]} />)

    expect(
      screen.getByText("No snapshot data available.")
    ).toBeInTheDocument()
    expect(screen.getByTestId("snapshot-table")).toBeInTheDocument()
  })

  it("formats values correctly (commas, percentages)", () => {
    render(<SnapshotTable snapshots={mockSnapshots} />)

    const firstRow = screen.getByTestId("snapshot-row-2024-01")

    // Portfolio value formatted with commas
    expect(firstRow).toHaveTextContent("1,050,000.50")

    // Benchmark value formatted with commas
    expect(firstRow).toHaveTextContent("1,020,000.75")

    // Portfolio return as percentage
    expect(firstRow).toHaveTextContent("5.00%")

    // Benchmark return as percentage
    expect(firstRow).toHaveTextContent("2.00%")

    // Excess return (5% - 2% = 3%)
    expect(firstRow).toHaveTextContent("3.00%")

    // Turnover as percentage
    expect(firstRow).toHaveTextContent("15.00%")

    // Transaction costs with dollar sign and commas
    expect(firstRow).toHaveTextContent("$250.50")
  })

  it("color-codes excess return", () => {
    render(<SnapshotTable snapshots={mockSnapshots} />)

    // First row: positive excess (5% - 2% = 3%)
    const firstRow = screen.getByTestId("snapshot-row-2024-01")
    const firstExcessCell = firstRow.querySelectorAll("td")[5]
    expect(firstExcessCell.className).toContain("text-bullish")

    // Second row: negative excess (-1.9% - (-0.98%) = -0.92%)
    const secondRow = screen.getByTestId("snapshot-row-2024-02")
    const secondExcessCell = secondRow.querySelectorAll("td")[5]
    expect(secondExcessCell.className).toContain("text-bearish")

    // Third row: positive excess (3.88% - 2.97% = 0.91%)
    const thirdRow = screen.getByTestId("snapshot-row-2024-03")
    const thirdExcessCell = thirdRow.querySelectorAll("td")[5]
    expect(thirdExcessCell.className).toContain("text-bullish")
  })
})
