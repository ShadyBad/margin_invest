import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Footer } from "../footer"

describe("Footer", () => {
  it("renders Support link", () => {
    render(<Footer />)
    expect(screen.getByText("Support").closest("a")).toHaveAttribute("href", "/support")
  })

  it("renders Methodology link", () => {
    render(<Footer />)
    expect(screen.getByText("Methodology").closest("a")).toHaveAttribute("href", "/methodology")
  })

  it("renders Legal link", () => {
    render(<Footer />)
    expect(screen.getByText("Legal").closest("a")).toHaveAttribute("href", "/legal")
  })

  it("renders copyright text", () => {
    render(<Footer />)
    expect(screen.getByText(/Margin/)).toBeInTheDocument()
  })

  it("renders a footer element", () => {
    render(<Footer />)
    expect(screen.getByRole("contentinfo")).toBeInTheDocument()
  })
})
