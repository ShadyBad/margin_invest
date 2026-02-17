import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { GlassSurface } from "../glass-surface"

describe("GlassSurface", () => {
  it("renders children", () => {
    const { getByText } = render(
      <GlassSurface>Hello</GlassSurface>,
    )
    expect(getByText("Hello")).toBeDefined()
  })

  it("applies glass class by default", () => {
    const { container } = render(
      <GlassSurface>Content</GlassSurface>,
    )
    expect(container.firstElementChild?.classList.contains("glass")).toBe(true)
  })

  it("applies glass-elevated when elevated prop is true", () => {
    const { container } = render(
      <GlassSurface elevated>Content</GlassSurface>,
    )
    expect(container.firstElementChild?.classList.contains("glass-elevated")).toBe(true)
  })

  it("merges custom className", () => {
    const { container } = render(
      <GlassSurface className="p-4">Content</GlassSurface>,
    )
    const el = container.firstElementChild
    expect(el?.classList.contains("glass")).toBe(true)
    expect(el?.classList.contains("p-4")).toBe(true)
  })

  it("renders as specified element via as prop", () => {
    const { container } = render(
      <GlassSurface as="section">Content</GlassSurface>,
    )
    expect(container.firstElementChild?.tagName).toBe("SECTION")
  })
})
