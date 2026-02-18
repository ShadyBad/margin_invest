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
  it("renders headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/disciplined capital allocators/)).toBeInTheDocument()
  })

  it("renders Not for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Narrative traders")).toBeInTheDocument()
    expect(screen.getByText("Signal chasers")).toBeInTheDocument()
    expect(screen.getByText("Emotion-driven decisions")).toBeInTheDocument()
  })

  it("renders For items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Long-horizon allocators")).toBeInTheDocument()
    expect(screen.getByText("Portfolio operators")).toBeInTheDocument()
    expect(screen.getByText("Structured decision-makers")).toBeInTheDocument()
  })
})
