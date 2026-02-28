import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PositioningSection } from "../positioning-section"

describe("PositioningSection", () => {
  it("renders updated positioning headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/discipline isn.t enough/i)).toBeInTheDocument()
  })

  it("renders Not for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Narrative-driven investing")).toBeInTheDocument()
    expect(screen.getByText("Signal chasers")).toBeInTheDocument()
    expect(screen.getByText("Discretionary overrides")).toBeInTheDocument()
  })

  it("renders For items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Systematic decision-making")).toBeInTheDocument()
    expect(screen.getByText("Factor-based allocation")).toBeInTheDocument()
    expect(screen.getByText("Structured risk management")).toBeInTheDocument()
  })
})
