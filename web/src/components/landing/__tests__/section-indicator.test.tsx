import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectionIndicator } from "../section-indicator"

describe("SectionIndicator", () => {
  it("renders navigation dots for all major sections", () => {
    render(<SectionIndicator />)
    const nav = screen.getByRole("navigation", { name: /page sections/i })
    expect(nav).toBeInTheDocument()
    const buttons = nav.querySelectorAll("button")
    expect(buttons.length).toBe(9)
  })
})
