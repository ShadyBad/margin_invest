import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ComparisonSection } from "../comparison-section"

describe("ComparisonSection", () => {
  it("renders the section heading", () => {
    render(<ComparisonSection />)
    expect(screen.getByText(/how we compare/i)).toBeInTheDocument()
  })

  it("renders all three competitor columns", () => {
    render(<ComparisonSection />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
    expect(screen.getByText("Traditional Screeners")).toBeInTheDocument()
    expect(screen.getByText("Black-Box Ratings")).toBeInTheDocument()
  })

  it("renders comparison rows", () => {
    render(<ComparisonSection />)
    expect(screen.getByText("Scoring")).toBeInTheDocument()
    expect(screen.getByText("Transparency")).toBeInTheDocument()
    expect(screen.getByText("Auditability")).toBeInTheDocument()
  })

  it("uses semantic table markup with caption", () => {
    render(<ComparisonSection />)
    const table = screen.getByRole("table")
    expect(table).toBeInTheDocument()
  })
})
