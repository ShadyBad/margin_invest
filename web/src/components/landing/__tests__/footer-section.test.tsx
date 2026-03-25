import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("../hero-search", () => ({
  HeroSearch: () => <div data-testid="hero-search" />,
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
    // Use getAllByText since FAQ answer also contains similar text
    const matches = screen.getAllByText(/deterministic scoring engine/i)
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it("renders copyright", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 margin invest/i)).toBeInTheDocument()
  })

  it("renders footer content container", () => {
    const { container } = render(<FooterSection />)
    const content = container.querySelector("[data-footer-content]")
    expect(content).toBeInTheDocument()
  })

  // FAQ accordion within footer
  it("renders FAQ accordion with all 7 questions", () => {
    render(<FooterSection />)
    expect(screen.getByText("What is Margin Invest?")).toBeInTheDocument()
    expect(screen.getByText("Is this investment advice?")).toBeInTheDocument()
    expect(screen.getByText("How is this different from Zacks or Morningstar?")).toBeInTheDocument()
    expect(screen.getByText("What are the elimination filters?")).toBeInTheDocument()
    expect(screen.getByText(/What does .sector-neutral. mean\?/)).toBeInTheDocument()
    expect(screen.getByText("Do you have a track record?")).toBeInTheDocument()
    expect(screen.getByText("Can I cancel anytime?")).toBeInTheDocument()
  })

  it("FAQ accordion expand/collapse works within footer", async () => {
    const user = userEvent.setup()
    render(<FooterSection />)

    const button = screen.getByText("What is Margin Invest?").closest("button")!
    expect(button).toHaveAttribute("aria-expanded", "false")

    await user.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")
  })

  it("renders Common Questions label", () => {
    render(<FooterSection />)
    expect(screen.getByText("Common Questions")).toBeInTheDocument()
  })

  it("renders CTA headline 'Score your first position.'", () => {
    render(<FooterSection />)
    expect(screen.getByText("Score your first position.")).toBeInTheDocument()
  })

  it("renders HeroSearch in CTA section", () => {
    render(<FooterSection />)
    expect(screen.getByTestId("hero-search")).toBeInTheDocument()
  })

  it("has data-footer-faq attribute on FAQ section", () => {
    const { container } = render(<FooterSection />)
    const faqSection = container.querySelector("[data-footer-faq]")
    expect(faqSection).toBeInTheDocument()
  })

  it("has data-footer-cta attribute on CTA section", () => {
    const { container } = render(<FooterSection />)
    const ctaSection = container.querySelector("[data-footer-cta]")
    expect(ctaSection).toBeInTheDocument()
  })
})
