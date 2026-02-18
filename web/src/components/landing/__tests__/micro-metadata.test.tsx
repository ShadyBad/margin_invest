import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MicroMetadata } from "../micro-metadata"

describe("MicroMetadata", () => {
  it("renders text content", () => {
    render(<MicroMetadata text="Engine v1.3.2" />)
    expect(screen.getByText("Engine v1.3.2")).toBeInTheDocument()
  })

  it("applies mono font and tertiary styling", () => {
    render(<MicroMetadata text="Test" />)
    const el = screen.getByText("Test")
    expect(el.className).toContain("font-mono")
    expect(el.className).toContain("text-text-tertiary")
  })
})
