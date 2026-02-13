import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SignalBadge } from "../signal-badge"

describe("SignalBadge", () => {
  it("renders signal text", () => {
    render(<SignalBadge signal="buy" />)
    expect(screen.getByText("buy")).toBeInTheDocument()
  })

  it("applies bullish color for buy", () => {
    const { container } = render(<SignalBadge signal="buy" />)
    expect(container.firstChild).toHaveClass("text-bullish")
  })

  it("handles case insensitivity", () => {
    const { container } = render(<SignalBadge signal="BUY" />)
    expect(container.firstChild).toHaveClass("text-bullish")
  })
})
