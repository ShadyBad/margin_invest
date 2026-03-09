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
// Mock scroll-canvas context — default: not smooth scrolling (mobile path)
vi.mock("../scroll-canvas", () => ({
  useScrollCanvas: vi.fn(() => ({ ready: false, isSmoothScrolling: false })),
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
  it("renders the indictment with elimination percentage", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={183} />
    )
    expect(screen.getByText("94% eliminated.")).toBeInTheDocument()
  })

  it("renders universe count and surviving count", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={183} />
    )
    expect(
      screen.getByText(/3,056 US equities scored\. 183 survived\./)
    ).toBeInTheDocument()
  })

  it("renders dash when survivingCount is 0", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(
      screen.getByText(/3,056 US equities scored\. \u2014 survived\./)
    ).toBeInTheDocument()
  })

  it("renders Discipline. and Engineered.", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline about deterministic scoring engine", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(
      screen.getByText(/deterministic scoring engine/)
    ).toBeInTheDocument()
  })

  it("renders search input", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(
      screen.getByPlaceholderText(/search any ticker/i)
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows ticker suggestion chips in idle state", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText("Try:")).toBeInTheDocument()
  })

  it("renders search-one call to action in subtext", () => {
    render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    expect(
      screen.getByText(/No opinions\. No overrides\. Search one\./)
    ).toBeInTheDocument()
  })

  it("uses fallback elimination percentage when universe is 0", () => {
    render(
      <HeroSection data={null} totalUniverse={0} survivingCount={0} />
    )
    expect(screen.getByText("94% eliminated.")).toBeInTheDocument()
  })

  it("renders scroll indicator line", () => {
    const { container } = render(
      <HeroSection data={null} totalUniverse={3056} survivingCount={0} />
    )
    const indicator = container.querySelector(".bg-text-tertiary")
    expect(indicator).toBeInTheDocument()
  })
})
