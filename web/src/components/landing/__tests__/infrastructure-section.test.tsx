import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { InfrastructureSection } from "../infrastructure-section"

describe("InfrastructureSection", () => {
  it("renders headline", () => {
    render(<InfrastructureSection />)
    expect(
      screen.getByText(/institutional-grade infrastructure/i)
    ).toBeInTheDocument()
  })

  it("renders subtext", () => {
    render(<InfrastructureSection />)
    expect(
      screen.getByText(/verified public data/)
    ).toBeInTheDocument()
  })

  it("renders all 5 bullet items", () => {
    render(<InfrastructureSection />)
    expect(screen.getByText(/SEC Filings \+ Earnings Transcripts/)).toBeInTheDocument()
    expect(screen.getByText(/Market Data Feeds \(Daily Refresh\)/)).toBeInTheDocument()
    expect(screen.getByText(/Encrypted API Key Storage/)).toBeInTheDocument()
    expect(screen.getByText(/Deterministic, Audit-Friendly Scoring/)).toBeInTheDocument()
    expect(screen.getByText(/No Hidden Heuristics/)).toBeInTheDocument()
  })
})
