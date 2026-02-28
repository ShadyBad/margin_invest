import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { FooterSection } from "../footer-section"

describe("FooterSection (landing)", () => {
  it("renders all navigation links", () => {
    render(<FooterSection />)
    expect(screen.getByRole("link", { name: "Support" })).toHaveAttribute("href", "/support")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("href", "/security")
    expect(screen.getByRole("link", { name: "Legal" })).toHaveAttribute("href", "/legal")
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute("href", "/status")
    expect(screen.getByRole("link", { name: "API" })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact")
  })

  it("does not link to /api (reserved for API routes)", () => {
    render(<FooterSection />)
    const links = screen.getAllByRole("link")
    const apiLink = links.find((l) => l.getAttribute("href") === "/api")
    expect(apiLink).toBeUndefined()
  })

  it("renders engine version", () => {
    render(<FooterSection />)
    expect(screen.getByText(/engine v1.3.2/i)).toBeInTheDocument()
  })

  it("renders copyright", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 margin invest/i)).toBeInTheDocument()
  })
})
