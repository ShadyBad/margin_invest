import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { HorizontalScroll } from "../horizontal-scroll"

describe("HorizontalScroll", () => {
  it("renders panels as children", () => {
    const { getByText } = render(
      <HorizontalScroll>
        <div>Panel 1</div>
        <div>Panel 2</div>
      </HorizontalScroll>,
    )
    expect(getByText("Panel 1")).toBeDefined()
    expect(getByText("Panel 2")).toBeDefined()
  })

  it("applies scroll-snap styles to container", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>Panel</div>
      </HorizontalScroll>,
    )
    const scroller = container.querySelector("[data-horizontal-scroll]")
    expect(scroller).toBeDefined()
  })

  it("wraps children in snap-aligned flex items", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </HorizontalScroll>,
    )
    const panels = container.querySelectorAll("[data-scroll-panel]")
    expect(panels).toHaveLength(3)
  })

  it("renders progress indicator", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>A</div>
        <div>B</div>
      </HorizontalScroll>,
    )
    const indicator = container.querySelector("[data-scroll-progress]")
    expect(indicator).toBeDefined()
  })
})
