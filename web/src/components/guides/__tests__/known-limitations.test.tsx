import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KnownLimitations } from "../known-limitations"

describe("KnownLimitations", () => {
  it('renders "Known Limitations" heading', () => {
    render(
      <KnownLimitations>
        <ul>
          <li>Limited to US equities</li>
        </ul>
      </KnownLimitations>
    )

    expect(screen.getByText("Known Limitations")).toBeInTheDocument()
  })

  it("renders children content", () => {
    render(
      <KnownLimitations>
        <ul>
          <li>No options or futures support</li>
          <li>Requires 3 years of financial data</li>
        </ul>
      </KnownLimitations>
    )

    expect(screen.getByText("No options or futures support")).toBeInTheDocument()
    expect(
      screen.getByText("Requires 3 years of financial data")
    ).toBeInTheDocument()
  })

  it("renders with warning-colored label", () => {
    render(
      <KnownLimitations>
        <p>Some limitation.</p>
      </KnownLimitations>
    )

    const label = screen.getByText("Known Limitations")
    expect(label).toHaveClass("text-warning")
  })
})
