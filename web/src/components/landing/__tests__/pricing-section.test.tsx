import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(() => ({ kill: vi.fn() })),
    set: vi.fn(),
    fromTo: vi.fn(() => ({ kill: vi.fn() })),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
      scrollTrigger: null,
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(() => ({ kill: vi.fn() })), getAll: () => [], refresh: vi.fn() },
}))

import { PricingSection } from "../sections/pricing-section"

describe("PricingSection", () => {
  it("renders headline", () => {
    render(<PricingSection />)
    expect(
      screen.getByText(/Start free\. Full access/)
    ).toBeInTheDocument()
  })

  it("renders all 3 tiers", () => {
    render(<PricingSection />)
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
  })

  it("renders monthly prices by default", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$19")).toBeInTheDocument()
    expect(screen.getByText("$49")).toBeInTheDocument()
  })

  it("does not apply opacity to Scout tier card", () => {
    render(<PricingSection />)
    // Find the Scout card by its name label
    const scoutLabel = screen.getByText("Scout")
    const card = scoutLabel.closest(".terminal-card")
    expect(card).toBeTruthy()
    const style = (card as HTMLElement).style
    expect(style.opacity).not.toBe("0.85")
  })

  it("renders billing toggle with Monthly and Annual buttons", () => {
    render(<PricingSection />)
    expect(screen.getByText("Monthly")).toBeInTheDocument()
    expect(screen.getByText("Annual")).toBeInTheDocument()
  })

  it("defaults to monthly billing", () => {
    render(<PricingSection />)
    const monthlyBtn = screen.getByText("Monthly")
    expect(monthlyBtn).toHaveAttribute("aria-pressed", "true")
    const annualBtn = screen.getByText("Annual")
    expect(annualBtn).toHaveAttribute("aria-pressed", "false")
  })

  it("switches to annual pricing on toggle", async () => {
    const user = userEvent.setup()
    render(<PricingSection />)

    const annualBtn = screen.getByText("Annual")
    await user.click(annualBtn)

    // Annual prices: $19*10 = $190, $49*10 = $490
    expect(screen.getByText("$190")).toBeInTheDocument()
    expect(screen.getByText("$490")).toBeInTheDocument()
    expect(screen.getByText("Free")).toBeInTheDocument()

    // Period should show /year
    const yearLabels = screen.getAllByText("/year")
    expect(yearLabels).toHaveLength(2)
  })

  it("switches back to monthly pricing", async () => {
    const user = userEvent.setup()
    render(<PricingSection />)

    // Switch to annual
    await user.click(screen.getByText("Annual"))
    expect(screen.getByText("$190")).toBeInTheDocument()

    // Switch back to monthly
    await user.click(screen.getByText("Monthly"))
    expect(screen.getByText("$19")).toBeInTheDocument()
    expect(screen.getByText("$49")).toBeInTheDocument()
  })

  it("shows '2 months free' badge", () => {
    render(<PricingSection />)
    expect(screen.getByText("2 months free")).toBeInTheDocument()
  })

  it("uses max-w-6xl container", () => {
    const { container } = render(<PricingSection />)
    const inner = container.querySelector(".max-w-6xl")
    expect(inner).toBeInTheDocument()
  })
})
