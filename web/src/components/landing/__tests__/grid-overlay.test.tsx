import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { GridOverlay } from "../grid-overlay"

describe("GridOverlay", () => {
  it("renders an SVG element", () => {
    const { container } = render(<GridOverlay />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })

  it("applies custom opacity", () => {
    const { container } = render(<GridOverlay opacity={0.02} />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveStyle({ opacity: "0.02" })
  })
})
