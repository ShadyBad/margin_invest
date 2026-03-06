import { describe, it, expect, beforeEach, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectionIndicator } from "../section-indicator"

describe("SectionIndicator", () => {
  const origEnv = process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS

  beforeEach(() => {
    process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS = "1"
  })

  afterEach(() => {
    if (origEnv === undefined) {
      delete process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS
    } else {
      process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS = origEnv
    }
  })

  it("renders navigation dots for all major sections", () => {
    render(<SectionIndicator />)
    const nav = screen.getByRole("navigation", { name: /page sections/i })
    expect(nav).toBeInTheDocument()
    const buttons = nav.querySelectorAll("button")
    expect(buttons.length).toBe(9)
  })

  it("returns null when NEXT_PUBLIC_SHOW_DEV_TOOLS is not set", () => {
    delete process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS
    const { container } = render(<SectionIndicator />)
    expect(container.innerHTML).toBe("")
  })
})
