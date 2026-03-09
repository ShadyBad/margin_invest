import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(() => ({ kill: vi.fn() })), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("../hero-search", () => ({
  HeroSearch: () => <div data-testid="hero-search" />,
}))

import { FaqSection } from "../faq-section"

describe("FaqSection", () => {
  it("renders all 7 FAQ questions", () => {
    render(<FaqSection />)
    expect(screen.getByText("What is Margin Invest?")).toBeInTheDocument()
    expect(screen.getByText("Is this investment advice?")).toBeInTheDocument()
    expect(
      screen.getByText("How is this different from Zacks or Morningstar?")
    ).toBeInTheDocument()
    expect(screen.getByText("What are the elimination filters?")).toBeInTheDocument()
    expect(screen.getByText(/What does .sector-neutral. mean\?/)).toBeInTheDocument()
    expect(screen.getByText("Do you have a track record?")).toBeInTheDocument()
    expect(screen.getByText("Can I cancel anytime?")).toBeInTheDocument()
  })

  it("accordion toggle expands on click", async () => {
    const user = userEvent.setup()
    render(<FaqSection />)

    const button = screen.getByText("What is Margin Invest?").closest("button")!
    expect(button).toHaveAttribute("aria-expanded", "false")

    await user.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText(/deterministic scoring engine/)).toBeInTheDocument()
  })

  it("accordion toggle collapses on second click", async () => {
    const user = userEvent.setup()
    render(<FaqSection />)

    const button = screen.getByText("What is Margin Invest?").closest("button")!

    await user.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")

    await user.click(button)
    expect(button).toHaveAttribute("aria-expanded", "false")
  })

  it('renders "Common Questions" label', () => {
    render(<FaqSection />)
    expect(screen.getByText("Common Questions")).toBeInTheDocument()
  })

  it('renders closing CTA text "Score your first position."', () => {
    render(<FaqSection />)
    expect(screen.getByText("Score your first position.")).toBeInTheDocument()
  })

  it("renders HeroSearch component in the closing CTA", () => {
    render(<FaqSection />)
    expect(screen.getByTestId("hero-search")).toBeInTheDocument()
  })

  it("FAQ items have data-faq-item attribute", () => {
    const { container } = render(<FaqSection />)
    const items = container.querySelectorAll("[data-faq-item]")
    expect(items).toHaveLength(7)
  })

  it("label has data-faq-label attribute", () => {
    const { container } = render(<FaqSection />)
    const label = container.querySelector("[data-faq-label]")
    expect(label).toBeInTheDocument()
    expect(label).toHaveTextContent("Common Questions")
  })

  it("CTA block has data-faq-cta attribute", () => {
    const { container } = render(<FaqSection />)
    const cta = container.querySelector("[data-faq-cta]")
    expect(cta).toBeInTheDocument()
  })
})
