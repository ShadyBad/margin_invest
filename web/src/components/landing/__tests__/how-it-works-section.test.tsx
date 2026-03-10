import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { HowItWorksSection } from "../sections/how-it-works-section"
import type { HomepageData } from "../shared/types"

const mockData: HomepageData = {
  candidates: [],
  allPicks: [],
  last_updated: "2026-03-09T00:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("HowItWorksSection", () => {
  it("renders 4 pipeline steps with live counts", () => {
    render(<HowItWorksSection data={mockData} />)
    expect(screen.getByText("3,056")).toBeInTheDocument()
    // eligible_count and total_scored are both 842 in this mock
    expect(screen.getAllByText("842").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText(/SCAN/)).toBeInTheDocument()
    expect(screen.getByText(/ELIMINATE/)).toBeInTheDocument()
    expect(screen.getByText(/SCORE/)).toBeInTheDocument()
    expect(screen.getByText(/SURFACE/)).toBeInTheDocument()
  })

  it("renders dashes when data is null", () => {
    render(<HowItWorksSection data={null} />)
    const dashes = screen.getAllByText("—")
    expect(dashes.length).toBeGreaterThanOrEqual(4)
  })
})
