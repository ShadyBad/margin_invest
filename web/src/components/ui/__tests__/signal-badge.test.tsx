import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SignalBadge } from "../signal-badge"

describe("SignalBadge", () => {
  it("renders signal text", () => {
    render(<SignalBadge signal="strong" />)
    expect(screen.getByText("strong")).toBeInTheDocument()
  })

  it("applies bullish color for strong", () => {
    const { container } = render(<SignalBadge signal="strong" />)
    expect(container.firstChild).toHaveClass("text-bullish")
  })

  it("handles case insensitivity", () => {
    const { container } = render(<SignalBadge signal="STRONG" />)
    expect(container.firstChild).toHaveClass("text-bullish")
  })
})
