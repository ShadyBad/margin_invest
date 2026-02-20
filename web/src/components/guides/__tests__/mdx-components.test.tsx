import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Callout, Formula, Example } from "../mdx-components"

describe("Callout", () => {
  it("renders info callout with content", () => {
    render(<Callout type="info">This is an informational note.</Callout>)
    expect(screen.getByText("Note")).toBeInTheDocument()
    expect(screen.getByText("This is an informational note.")).toBeInTheDocument()
    const container = screen.getByText("Note").closest("div")!.parentElement!
    expect(container).toHaveClass("border-l-accent")
    expect(container).toHaveClass("bg-accent-subtle")
  })

  it("renders warning callout", () => {
    render(<Callout type="warning">Be careful here.</Callout>)
    expect(screen.getByText("Warning")).toBeInTheDocument()
    expect(screen.getByText("Be careful here.")).toBeInTheDocument()
    const container = screen.getByText("Warning").closest("div")!.parentElement!
    expect(container).toHaveClass("border-l-warning")
  })

  it("renders tip callout", () => {
    render(<Callout type="tip">A helpful tip.</Callout>)
    expect(screen.getByText("Tip")).toBeInTheDocument()
    expect(screen.getByText("A helpful tip.")).toBeInTheDocument()
    const container = screen.getByText("Tip").closest("div")!.parentElement!
    expect(container).toHaveClass("border-l-bullish")
  })
})

describe("Formula", () => {
  it("renders formula in monospace", () => {
    render(<Formula>score = value * weight</Formula>)
    const element = screen.getByText("score = value * weight")
    expect(element).toBeInTheDocument()
    expect(element.closest("div")).toHaveClass("font-mono")
  })
})

describe("Example", () => {
  it("renders example block with title", () => {
    render(<Example title="AAPL Analysis">Apple scores 87 overall.</Example>)
    expect(screen.getByText("AAPL Analysis")).toBeInTheDocument()
    expect(screen.getByText("Apple scores 87 overall.")).toBeInTheDocument()
    const titleEl = screen.getByText("AAPL Analysis")
    expect(titleEl).toHaveClass("uppercase")
    expect(titleEl).toHaveClass("tracking-wider")
  })

  it("renders example block without title", () => {
    render(<Example>Just content here.</Example>)
    expect(screen.getByText("Just content here.")).toBeInTheDocument()
    // Should not render a title element
    const container = screen.getByText("Just content here.").closest("div")!
    expect(container.querySelector(".uppercase")).toBeNull()
  })
})
