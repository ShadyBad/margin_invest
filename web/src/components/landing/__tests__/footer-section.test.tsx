import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  })
})

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { FooterSection } from "../sections/footer-section"

describe("FooterSection (landing)", () => {
  it("renders Margin Invest brand name", () => {
    render(<FooterSection />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })

  it("renders tagline in italic", () => {
    render(<FooterSection />)
    expect(
      screen.getByText(/A deterministic capital allocation system/)
    ).toBeInTheDocument()
  })

  it("renders all product links", () => {
    render(<FooterSection />)
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard")
    expect(screen.getByRole("link", { name: "Explore" })).toHaveAttribute("href", "/explore")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "API" })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute("href", "/status")
  })

  it("renders all company links", () => {
    render(<FooterSection />)
    expect(screen.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about")
    expect(screen.getByRole("link", { name: "Legal" })).toHaveAttribute("href", "/legal")
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms")
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy")
    expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact")
  })

  it("does not link to /api (reserved for API routes)", () => {
    render(<FooterSection />)
    const links = screen.getAllByRole("link")
    const apiLink = links.find((l) => l.getAttribute("href") === "/api")
    expect(apiLink).toBeUndefined()
  })

  it("renders copyright", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 MARGIN INVEST/i)).toBeInTheDocument()
  })

  it("renders DETERMINISTIC BY DESIGN tagline", () => {
    render(<FooterSection />)
    expect(screen.getByText("DETERMINISTIC BY DESIGN.")).toBeInTheDocument()
  })

  it("renders footer content container", () => {
    const { container } = render(<FooterSection />)
    const content = container.querySelector("[data-footer-content]")
    expect(content).toBeInTheDocument()
  })

  it("renders PRODUCT and COMPANY section headings", () => {
    render(<FooterSection />)
    expect(screen.getByText("PRODUCT")).toBeInTheDocument()
    expect(screen.getByText("COMPANY")).toBeInTheDocument()
  })
})
