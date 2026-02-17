import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AnimatedScore } from "../animated-score"

describe("AnimatedScore", () => {
  it("renders the final value", () => {
    render(<AnimatedScore value={87} className="test" />)
    const el = screen.getByTestId("animated-score")
    expect(el).toBeInTheDocument()
  })

  it("applies className", () => {
    render(<AnimatedScore value={42} className="text-accent" />)
    const el = screen.getByTestId("animated-score")
    expect(el.className).toContain("text-accent")
  })
})
