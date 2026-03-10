import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

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
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
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

  it("renders prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$19")).toBeInTheDocument()
    expect(screen.getByText("$49")).toBeInTheDocument()
  })
})
