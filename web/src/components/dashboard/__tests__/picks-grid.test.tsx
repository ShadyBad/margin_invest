import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { PicksGrid } from "../picks-grid"

// Mock StockCard to avoid transitive dependency resolution
vi.mock("../stock-card", () => ({
  StockCard: ({ pick }: any) => <div data-testid={`stock-card-${pick.ticker}`} />,
}))

// Mock @/components/ui — provide real EmptyState so we can test its rendered output
vi.mock("@/components/ui", () => ({
  EmptyState: ({ title, description, className }: any) => (
    <div className={className}>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
    </div>
  ),
}))

describe("PicksGrid", () => {
  it("renders purposeful empty state when no picks", () => {
    render(<PicksGrid picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/nothing worth your capital/i)).toBeInTheDocument()
  })

  it("shows elimination stats when universe data provided and no picks", () => {
    render(<PicksGrid picks={[]} totalScored={847} universeSize={2847} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/847/)).toBeInTheDocument()
    expect(screen.getByText(/2,847/)).toBeInTheDocument()
  })
})
