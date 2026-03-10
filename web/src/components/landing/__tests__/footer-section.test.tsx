import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { FooterSection } from "../sections/footer-section"

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

  it("renders engine tagline", () => {
    render(<FooterSection />)
    expect(screen.getByText(/deterministic scoring engine/i)).toBeInTheDocument()
  })

  it("renders copyright", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 margin invest/i)).toBeInTheDocument()
  })

  it("renders horizontal rule divider", () => {
    const { container } = render(<FooterSection />)
    const hr = container.querySelector("hr")
    expect(hr).toBeInTheDocument()
  })
})
