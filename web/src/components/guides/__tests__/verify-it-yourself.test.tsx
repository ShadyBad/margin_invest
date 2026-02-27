import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { VerifyItYourself } from "../verify-it-yourself"

describe("VerifyItYourself", () => {
  it("renders the claim text", () => {
    render(
      <VerifyItYourself claim="Deterministic scoring">
        <p>Run the same ticker twice and compare outputs.</p>
      </VerifyItYourself>
    )

    expect(screen.getByText("Deterministic scoring")).toBeInTheDocument()
  })

  it("renders children content", () => {
    render(
      <VerifyItYourself claim="Transparent filters">
        <p>Check the elimination gauntlet for any ticker.</p>
      </VerifyItYourself>
    )

    expect(
      screen.getByText("Check the elimination gauntlet for any ticker.")
    ).toBeInTheDocument()
  })

  it('renders "Verify it yourself" label', () => {
    render(
      <VerifyItYourself claim="No human judgment">
        <p>Steps to verify.</p>
      </VerifyItYourself>
    )

    expect(screen.getByText("Verify it yourself")).toBeInTheDocument()
  })

  it("renders the claim in bold", () => {
    render(
      <VerifyItYourself claim="Sector-neutral ranking">
        <p>Compare two tickers in the same sector.</p>
      </VerifyItYourself>
    )

    const claim = screen.getByText("Sector-neutral ranking")
    expect(claim).toHaveClass("font-semibold")
  })
})
