import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TechnicalDetail } from "../technical-detail"

describe("TechnicalDetail", () => {
  it("renders collapsed by default — summary visible, children not visible", () => {
    render(
      <TechnicalDetail summary="How the score is calculated">
        <p>Detailed formula goes here.</p>
      </TechnicalDetail>
    )

    // Summary text should be visible
    expect(screen.getByText("How the score is calculated")).toBeInTheDocument()

    // Children should not be visible
    expect(screen.getByText("Detailed formula goes here.")).not.toBeVisible()

    // Button should indicate collapsed state
    const button = screen.getByRole("button")
    expect(button).toHaveAttribute("aria-expanded", "false")

    // Content region should be aria-hidden
    const content = screen.getByText("Detailed formula goes here.").closest("[aria-hidden]")
    expect(content).toHaveAttribute("aria-hidden", "true")
  })

  it("expands on click — children become visible", async () => {
    const user = userEvent.setup()

    render(
      <TechnicalDetail summary="Threshold details">
        <p>Revenue must exceed $1B.</p>
      </TechnicalDetail>
    )

    const button = screen.getByRole("button")
    await user.click(button)

    // Children should now be visible
    expect(screen.getByText("Revenue must exceed $1B.")).toBeVisible()

    // Button should indicate expanded state
    expect(button).toHaveAttribute("aria-expanded", "true")

    // Content region should not be aria-hidden
    const content = screen.getByText("Revenue must exceed $1B.").closest("[aria-hidden]")
    expect(content).toHaveAttribute("aria-hidden", "false")
  })

  it("collapses on second click", async () => {
    const user = userEvent.setup()

    render(
      <TechnicalDetail summary="Citation sources">
        <p>Fama-French 1993.</p>
      </TechnicalDetail>
    )

    const button = screen.getByRole("button")

    // First click — expand
    await user.click(button)
    expect(screen.getByText("Fama-French 1993.")).toBeVisible()
    expect(button).toHaveAttribute("aria-expanded", "true")

    // Second click — collapse
    await user.click(button)
    expect(screen.getByText("Fama-French 1993.")).not.toBeVisible()
    expect(button).toHaveAttribute("aria-expanded", "false")
  })

  it("renders expanded when defaultOpen is true", () => {
    render(
      <TechnicalDetail summary="Always-open section" defaultOpen>
        <p>This content starts visible.</p>
      </TechnicalDetail>
    )

    // Children should be visible immediately
    expect(screen.getByText("This content starts visible.")).toBeVisible()

    // Button should indicate expanded state
    const button = screen.getByRole("button")
    expect(button).toHaveAttribute("aria-expanded", "true")

    // Content region should not be aria-hidden
    const content = screen.getByText("This content starts visible.").closest("[aria-hidden]")
    expect(content).toHaveAttribute("aria-hidden", "false")
  })

  it("displays the monospace indicator", () => {
    render(
      <TechnicalDetail summary="Some detail">
        <p>Content</p>
      </TechnicalDetail>
    )

    // The { } indicator should be present
    expect(screen.getByText("{ }")).toBeInTheDocument()
    const indicator = screen.getByText("{ }")
    expect(indicator).toHaveClass("font-mono")
  })
})
