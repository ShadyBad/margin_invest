import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { HeroSection } from "../hero-section"

describe("HeroSection", () => {
  it("renders Conviction. and Engineered.", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline about deterministic capital allocation", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/deterministic capital allocation/)).toBeInTheDocument()
  })

  it("primary CTA links to /dashboard", () => {
    render(<HeroSection data={null} />)
    const link = screen.getByRole("link", { name: /open the dashboard/i })
    expect(link).toHaveAttribute("href", "/dashboard")
  })

  it("secondary CTA links to /methodology", () => {
    render(<HeroSection data={null} />)
    const link = screen.getByRole("link", { name: /see the methodology/i })
    expect(link).toHaveAttribute("href", "/methodology")
  })

  it("shows AAPL from fallback when data is null", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
