import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { SectionIndicator } from "../section-indicator"

describe("SectionIndicator", () => {
  it("renders 6 navigation dots", () => {
    const { container } = render(<SectionIndicator />)
    const dots = container.querySelectorAll("[data-section-dot]")
    expect(dots).toHaveLength(6)
  })
})
