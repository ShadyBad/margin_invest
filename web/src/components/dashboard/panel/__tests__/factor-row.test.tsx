import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FactorRow } from "../factor-row"

describe("FactorRow", () => {
  const baseProps = {
    name: "Quality",
    weight: 35,
    score: 65,
    interpretation: "Middle of the pack. Room for improvement.",
    subScores: [
      { label: "Gross Prof", value: 62 },
      { label: "ROIC", value: 85 },
      { label: "Accrual", value: 23 },
      { label: "Piotr", value: 85 },
    ],
  }

  it("renders factor name and weight", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("35%")).toBeInTheDocument()
  })

  it("renders score with percentile-appropriate color", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByTestId("factor-score")).toHaveTextContent("65")
  })

  it("renders interpretation text", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Middle of the pack. Room for improvement.")).toBeInTheDocument()
  })

  it("renders sub-score chips", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Gross Prof: 62")).toBeInTheDocument()
    expect(screen.getByText("ROIC: 85")).toBeInTheDocument()
    expect(screen.getByText("Accrual: 23")).toBeInTheDocument()
    expect(screen.getByText("Piotr: 85")).toBeInTheDocument()
  })

  it("renders progress bar", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByTestId("factor-progress-bar")).toBeInTheDocument()
  })
})
