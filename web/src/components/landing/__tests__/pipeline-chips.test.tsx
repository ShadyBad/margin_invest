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

import { PipelineChips } from "../pipeline-chips"

describe("PipelineChips", () => {
  it("renders all 6 stage names", () => {
    render(<PipelineChips activeStage={0} />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("FILTER")).toBeInTheDocument()
    expect(screen.getByText("FACTOR MODEL")).toBeInTheDocument()
    expect(screen.getByText("NORMALIZE")).toBeInTheDocument()
    expect(screen.getByText("SCORE")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("renders Factor Model version metadata", () => {
    render(<PipelineChips activeStage={0} />)
    expect(screen.getByText(/Factor Model v2\.1/)).toBeInTheDocument()
  })

  it("marks stages as active up to activeStage (activeStage=3 means first 4 active)", () => {
    render(<PipelineChips activeStage={3} />)
    const stages = screen.getAllByTestId("pipeline-stage")
    expect(stages).toHaveLength(6)

    // First 4 should be active
    expect(stages[0]).toHaveAttribute("data-active", "true")
    expect(stages[1]).toHaveAttribute("data-active", "true")
    expect(stages[2]).toHaveAttribute("data-active", "true")
    expect(stages[3]).toHaveAttribute("data-active", "true")

    // Last 2 should be inactive
    expect(stages[4]).toHaveAttribute("data-active", "false")
    expect(stages[5]).toHaveAttribute("data-active", "false")
  })
})
