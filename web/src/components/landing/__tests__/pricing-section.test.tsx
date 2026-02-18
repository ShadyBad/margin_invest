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
  it("renders pre-headline", () => {
    render(<PricingSection />)
    expect(
      screen.getByText(/system scales with your responsibility/)
    ).toBeInTheDocument()
  })

  it("renders all 3 tiers", () => {
    render(<PricingSection />)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()
  })

  it("renders Most Popular tag", () => {
    render(<PricingSection />)
    expect(screen.getByText("Most Popular")).toBeInTheDocument()
  })

  it("renders prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })
})
