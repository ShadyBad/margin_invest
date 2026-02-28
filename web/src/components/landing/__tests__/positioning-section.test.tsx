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
  it("renders Not for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Narrative-driven conviction")).toBeInTheDocument()
    expect(screen.getByText("Signal chasers and day traders")).toBeInTheDocument()
    expect(screen.getByText("Anyone who needs an override button")).toBeInTheDocument()
  })

  it("renders For items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Investors who know their process is broken")).toBeInTheDocument()
    expect(screen.getByText("People who want math, not opinions")).toBeInTheDocument()
    expect(screen.getByText("Anyone willing to trust structure over stories")).toBeInTheDocument()
  })
})
