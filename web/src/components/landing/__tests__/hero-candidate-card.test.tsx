import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
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

import { HeroCandidateCard } from "../hero-candidate-card"
import { FALLBACK_CANDIDATES } from "../candidate-data"

describe("HeroCandidateCard", () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it("renders first candidate ticker and name", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders header with Live Engine Output", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText(/live engine output/i)).toBeInTheDocument()
  })

  it("renders composite score as largest visual element", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("78")).toBeInTheDocument()
  })

  it("renders 5 factor bars", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Sentiment")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
  })

  it("renders margin of safety", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("19.4%")).toBeInTheDocument()
  })

  it("renders universe metadata", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} universeSize={1842} eligibleCount={143} />)
    expect(screen.getByText(/1,842/)).toBeInTheDocument()
    expect(screen.getByText(/143/)).toBeInTheDocument()
  })

  it("renders Engine version in header", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText(/v1\.3\.2/)).toBeInTheDocument()
  })

  it("does not auto-rotate with single candidate", () => {
    render(<HeroCandidateCard candidates={[FALLBACK_CANDIDATES[0]]} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
