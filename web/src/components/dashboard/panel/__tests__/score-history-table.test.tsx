import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreHistoryTable } from "../score-history-table"

vi.mock("@/components/ui", () => ({
  SignalBadge: ({ signal }: { signal: string }) => <span data-testid="signal-badge">{signal}</span>,
}))

const mockHistory = [
  { date: "2026-02-16", score: 87, delta: 3, signal: "strong", conviction: "exceptional", keyChange: "Value \u2191 94\u219298" },
  { date: "2026-02-09", score: 84, delta: -1, signal: "strong", conviction: "high", keyChange: "Momentum \u2193 96\u219293" },
  { date: "2026-02-02", score: 85, delta: 5, signal: "strong", conviction: "high", keyChange: "Quality \u2191 58\u219265" },
]

describe("ScoreHistoryTable", () => {
  it("renders table with correct number of rows", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    expect(screen.getByTestId("score-history-table")).toBeInTheDocument()
    expect(screen.getByText("3 runs")).toBeInTheDocument()
    expect(screen.getAllByRole("row")).toHaveLength(4) // 1 header + 3 data
  })

  it("renders score values", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    expect(screen.getByText("87")).toBeInTheDocument()
    expect(screen.getByText("84")).toBeInTheDocument()
    expect(screen.getByText("85")).toBeInTheDocument()
  })

  it("renders positive delta with up arrow", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const deltas = screen.getAllByTestId("score-delta")
    expect(deltas[0]).toHaveTextContent("+3")
  })

  it("renders negative delta", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const deltas = screen.getAllByTestId("score-delta")
    expect(deltas[1]).toHaveTextContent("-1")
  })

  it("sorts by date descending by default", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const rows = screen.getAllByRole("row")
    expect(rows[1]).toHaveTextContent("Feb 16, 2026")
  })

  it("renders empty state", () => {
    render(<ScoreHistoryTable history={[]} />)
    expect(screen.getByText("No scoring history yet")).toBeInTheDocument()
  })
})
