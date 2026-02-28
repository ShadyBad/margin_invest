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

import { HeroSection } from "../hero-section"

describe("HeroSection", () => {
  it("renders Discipline. and Engineered.", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline about deterministic capital allocation", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/deterministic capital allocation/)).toBeInTheDocument()
  })

  it("renders search input instead of old CTAs", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows AAPL from fallback when data is null", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })

  it("renders search-any-ticker call to action in subtext", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByText(/quantitative evidence/i)).toBeInTheDocument()
  })
})
