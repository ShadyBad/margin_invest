import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(() => ({ kill: vi.fn() })),
    from: vi.fn(() => ({ kill: vi.fn() })),
    fromTo: vi.fn(() => ({ kill: vi.fn() })),
    set: vi.fn(),
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
// Mock apiFetch for HeroSearch
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  ApiError: class extends Error {
    status: number
    errorCode: string
    constructor(status: number, errorCode: string, message?: string) {
      super(message)
      this.status = status
      this.errorCode = errorCode
    }
  },
}))

import { HeroSection } from "../sections/hero-section"

describe("HeroSection", () => {
  it("renders Discipline. and Engineered.", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline about deterministic scoring engine", () => {
    render(<HeroSection data={null} />)
    expect(
      screen.getByText(/deterministic scoring engine/)
    ).toBeInTheDocument()
  })

  it("renders search input", () => {
    render(<HeroSection data={null} />)
    expect(
      screen.getByPlaceholderText(/search any ticker/i)
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows ticker suggestion chips in idle state", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText("Try:")).toBeInTheDocument()
  })

  it("renders search-one call to action in subtext", () => {
    render(<HeroSection data={null} />)
    expect(
      screen.getByText(/No opinions\. No overrides\. Search one\./)
    ).toBeInTheDocument()
  })
})
