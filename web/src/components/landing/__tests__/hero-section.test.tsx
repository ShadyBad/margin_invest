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
  it("renders DISCIPLINE and ENGINEER headline words", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("DISCIPLINE")).toBeInTheDocument()
    expect(screen.getByText("ENGINEERED")).toBeInTheDocument()
  })

  it("renders subtext about forensic scoring engine", () => {
    render(<HeroSection data={null} />)
    expect(
      screen.getByText(/forensic scoring engine/i)
    ).toBeInTheDocument()
  })

  it("renders search input via HeroSearch", () => {
    render(<HeroSection data={null} />)
    expect(
      screen.getByPlaceholderText(/search any ticker/i)
    ).toBeInTheDocument()
  })

  it("renders stat labels", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("UNIVERSE")).toBeInTheDocument()
    expect(screen.getByText("SCORED")).toBeInTheDocument()
    expect(screen.getByText("SURVIVING")).toBeInTheDocument()
    expect(screen.getByText("LAST CYCLE")).toBeInTheDocument()
  })

  it("renders browse top picks link", () => {
    render(<HeroSection data={null} />)
    const link = screen.getByRole("link", { name: /browse this week.s top picks/i })
    expect(link).toHaveAttribute("href", "/explore")
  })
})
