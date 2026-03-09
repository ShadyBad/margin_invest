import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PricingSection } from "../pricing-section"

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
