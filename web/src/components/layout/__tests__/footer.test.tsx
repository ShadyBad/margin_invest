import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Footer } from "../footer"

describe("Footer (authenticated)", () => {
  it("renders all navigation links", () => {
    render(<Footer />)
    expect(screen.getByRole("link", { name: "Support" })).toHaveAttribute("href", "/support")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "Legal" })).toHaveAttribute("href", "/legal")
    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("href", "/security")
    expect(screen.getByRole("link", { name: "API" })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact")
  })

  it("renders copyright text", () => {
    render(<Footer />)
    expect(screen.getByText(/Margin/)).toBeInTheDocument()
  })

  it("renders a footer element", () => {
    render(<Footer />)
    expect(screen.getByRole("contentinfo")).toBeInTheDocument()
  })

  it("renders cookie preferences button", () => {
    render(<Footer />)
    const cookieButton = screen.getByRole("button", { name: "Cookie Preferences" })
    expect(cookieButton).toBeInTheDocument()
    expect(cookieButton).toHaveClass("termly-display-preferences")
  })
})
