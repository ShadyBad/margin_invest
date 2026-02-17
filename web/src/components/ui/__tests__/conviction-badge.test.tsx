import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConvictionBadge } from "../conviction-badge"

describe("ConvictionBadge", () => {
  it("renders conviction level text", () => {
    render(<ConvictionBadge level="exceptional" />)
    expect(screen.getByText("exceptional")).toBeInTheDocument()
  })

  it("applies gold styling for exceptional", () => {
    const { container } = render(<ConvictionBadge level="exceptional" />)
    expect(container.firstChild).toHaveClass("bg-accent")
    expect(container.firstChild).toHaveClass("text-white")
  })

  it("handles unknown levels gracefully", () => {
    render(<ConvictionBadge level="unknown" />)
    expect(screen.getByText("unknown")).toBeInTheDocument()
  })
})
