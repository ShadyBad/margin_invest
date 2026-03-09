import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreDelta } from "../score-delta"

describe("ScoreDelta", () => {
  it("renders up arrow and positive delta with bullish color", () => {
    const { container } = render(<ScoreDelta current={85} previous={83} />)
    const el = screen.getByTestId("score-delta")
    expect(el).toBeInTheDocument()
    expect(el.textContent).toContain("\u25B2")
    expect(el.textContent).toContain("+2")
    expect(el.className).toContain("text-bullish")
  })

  it("renders down arrow and negative delta with warning color", () => {
    render(<ScoreDelta current={70} previous={74} />)
    const el = screen.getByTestId("score-delta")
    expect(el).toBeInTheDocument()
    expect(el.textContent).toContain("\u25BC")
    expect(el.textContent).toContain("-4")
    expect(el.className).toContain("text-warning")
  })

  it("returns null for zero delta", () => {
    const { container } = render(<ScoreDelta current={50} previous={50} />)
    expect(container.innerHTML).toBe("")
  })

  it("returns null when previous is null", () => {
    const { container } = render(<ScoreDelta current={50} previous={null} />)
    expect(container.innerHTML).toBe("")
  })
})
