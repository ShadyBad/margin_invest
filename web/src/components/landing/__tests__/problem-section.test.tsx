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

import { ProblemSection } from "../problem-section"

describe("ProblemSection", () => {
  it("renders headline", () => {
    render(<ProblemSection />)
    expect(
      screen.getByText("Most investors react. Few operate with structure.")
    ).toBeInTheDocument()
  })

  it("renders all 4 bullets", () => {
    render(<ProblemSection />)
    expect(screen.getByText("No filtering discipline")).toBeInTheDocument()
    expect(screen.getByText("No factor weighting memory")).toBeInTheDocument()
    expect(screen.getByText("No sector normalization")).toBeInTheDocument()
    expect(screen.getByText("No portfolio-level correlation awareness")).toBeInTheDocument()
  })
})
